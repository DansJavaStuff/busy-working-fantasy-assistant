from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re


WEEK_FIELD_RE = re.compile(
    r"^week_(\d+)_(projection|actual)$"
)

WEEK_STATS_RE = re.compile(
    r"^week_(\d+)_(projection|actual)_stats$"
)

WEEK_GAME_RE = re.compile(
    r"^week_(\d+)_(game_display|game_day|game_time|opponent|home_away)$"
)

LEGACY_WEEK_RE = re.compile(
    r"^week_\d+_"
)

EASTERN = ZoneInfo(
    "America/New_York"
)


def _week_entry(output, week):
    return output.setdefault(
        "weeks",
        {},
    ).setdefault(
        str(int(week)),
        {},
    )


def normalise_player(player):
    """Convert legacy week_N fields into the shared weeks{} model.

    Non-week Yahoo fields remain at player level.  The function is deliberately
    source-agnostic so the future Yahoo API provider can build the same shape.
    """
    output = {
        key: value
        for key, value in player.items()
        if not LEGACY_WEEK_RE.match(key)
    }

    output["weeks"] = {}

    for key, value in player.items():
        match = WEEK_FIELD_RE.match(key)
        if match:
            week, kind = match.groups()
            _week_entry(output, week)[kind] = value
            continue

        match = WEEK_STATS_RE.match(key)
        if match:
            week, kind = match.groups()
            _week_entry(output, week)[
                f"{kind}_stats"
            ] = value
            continue

        match = WEEK_GAME_RE.match(key)
        if match:
            week, field = match.groups()
            game = _week_entry(
                output,
                week,
            ).setdefault(
                "game",
                {},
            )

            game_key = {
                "game_display": "display",
                "game_day": "day",
                "game_time": "time",
                "opponent": "opponent",
                "home_away": "home_away",
            }[field]

            game[game_key] = value

    # Remove wholly empty nested game records while retaining explicit None
    # projection/actual values: absence and 'not played yet' are different.
    for week_data in output["weeks"].values():
        game = week_data.get("game")
        if game and all(
            value is None
            for value in game.values()
        ):
            week_data.pop("game", None)

    return output


def build_dataset(
    roster_players,
    available_players,
    source,
    generated_at=None,
):
    if generated_at is None:
        generated_at = datetime.now(
            timezone.utc
        )

    players = {}
    my_team_ids = []
    available_ids = []

    def add_player(player, target_ids):
        normalised = normalise_player(player)
        player_id = str(
            normalised.get("yahoo_player_id")
            or normalised.get("player_id")
            or normalised.get("name")
        )

        players[player_id] = normalised
        target_ids.append(player_id)

    for player in roster_players:
        add_player(player, my_team_ids)

    for player in available_players:
        add_player(player, available_ids)

    return {
        "schema_version": 1,
        "generated_at": generated_at.isoformat(),
        "source": source,
        "players": players,
        "my_team_ids": my_team_ids,
        "available_ids": available_ids,
    }


def player_for_week(player, week):
    """Return one normalized player's data for an arbitrary fantasy week."""
    return (
        player.get("weeks", {})
        .get(str(int(week)), {})
    )


def _week_1_thursday(season):
    september_1 = date(
        season,
        9,
        1,
    )

    days_until_monday = (
        0
        - september_1.weekday()
    ) % 7

    labor_day = (
        september_1
        + timedelta(
            days=days_until_monday
        )
    )

    return (
        labor_day
        + timedelta(days=3)
    )


def _fantasy_season_for_datetime(now):
    local_date = now.astimezone(
        EASTERN
    ).date()

    if local_date.month <= 2:
        return local_date.year - 1

    return local_date.year


def game_kickoff(
    week,
    game,
    season,
):
    """Return an aware Eastern kickoff datetime for normalized game data."""
    day = (game or {}).get("day")
    time_text = (game or {}).get("time")

    if not day or not time_text:
        return None

    day_offsets = {
        "Thu": 0,
        "Fri": 1,
        "Sat": 2,
        "Sun": 3,
        "Mon": 4,
        "Tue": 5,
        "Wed": 6,
    }

    offset = day_offsets.get(day)
    if offset is None:
        return None

    try:
        clock, meridiem = time_text.split()
        hour, minute = (
            int(value)
            for value in clock.split(":")
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
    ):
        return None

    meridiem = meridiem.lower()

    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    elif meridiem not in {"am", "pm"}:
        return None

    game_date = (
        _week_1_thursday(season)
        + timedelta(
            weeks=int(week) - 1,
            days=offset,
        )
    )

    return datetime(
        game_date.year,
        game_date.month,
        game_date.day,
        hour,
        minute,
        tzinfo=EASTERN,
    )


def week_is_locked(
    week,
    week_data,
    season,
    now=None,
):
    """True once a player/week has started producing actual results."""
    if week_data.get("actual") is not None:
        return True

    if now is None:
        now = datetime.now(
            timezone.utc
        )

    kickoff = game_kickoff(
        week,
        week_data.get("game") or {},
        season,
    )

    if kickoff is None:
        return False

    return now >= kickoff.astimezone(
        timezone.utc
    )


def preserve_locked_projections(
    previous_dataset,
    new_dataset,
    season=None,
    now=None,
):
    """Carry forward the last pre-kickoff projection for locked games.

    Before kickoff the newest Yahoo projection is allowed to replace the old
    value.  Once kickoff has passed (or an actual score exists), the previous
    normalized projection becomes the historical pre-game projection and is
    not overwritten by later refreshes.
    """
    if now is None:
        now = datetime.now(
            timezone.utc
        )

    if season is None:
        season = _fantasy_season_for_datetime(
            now
        )

    previous_players = (
        previous_dataset
        .get("players", {})
    )

    for player_id, new_player in (
        new_dataset
        .get("players", {})
        .items()
    ):
        previous_player = previous_players.get(
            player_id
        )

        if not previous_player:
            continue

        previous_weeks = previous_player.get(
            "weeks",
            {},
        )

        for week, new_week_data in (
            new_player.get("weeks", {}).items()
        ):
            previous_week_data = (
                previous_weeks.get(week)
            )

            if not previous_week_data:
                continue

            previous_projection = (
                previous_week_data.get(
                    "projection"
                )
            )

            if previous_projection is None:
                continue

            lock_source = dict(
                previous_week_data
            )
            lock_source.update(
                {
                    key: value
                    for key, value
                    in new_week_data.items()
                    if value is not None
                }
            )

            if week_is_locked(
                week,
                lock_source,
                season,
                now=now,
            ):
                new_week_data[
                    "projection"
                ] = previous_projection

    return new_dataset

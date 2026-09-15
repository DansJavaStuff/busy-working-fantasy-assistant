from datetime import datetime, timezone
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

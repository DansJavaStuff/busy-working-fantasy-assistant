from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import json

from database import load_season_roster
from yahoo_provider import yahoo_provider
from transaction_engine import (
    build_bye_coverage,
    build_transaction_recommendations,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

MY_TEAM_FILE = (
    DATA_DIR
    / "yahoo_my_team.json"
)

AVAILABLE_FILE = (
    DATA_DIR
    / "yahoo_available_players.json"
)

FLEX_POSITIONS = {
    "RB",
    "WR",
    "TE",
}

UNAVAILABLE_STATUSES = {
    "O",
    "IR",
    "IR-R",
    "PUP",
    "SUSP",
}


_TRANSACTION_CACHE = {
    "snapshot_key": None,
    "recommendations": None,
}


def cached_transaction_recommendations(
    roster,
    available,
    provider_status,
    week,
    waiver_priority=None,
):
    captured_at = provider_status.get(
        "captured_at"
    )

    snapshot_key = (
        captured_at.isoformat()
        if captured_at
        else None
    )

    if (
        _TRANSACTION_CACHE[
            "snapshot_key"
        ] == snapshot_key
        and _TRANSACTION_CACHE[
            "recommendations"
        ] is not None
    ):
        return _TRANSACTION_CACHE[
            "recommendations"
        ]

    recommendations = (
        build_transaction_recommendations(
            roster,
            available,
            limit=5,
            current_week=week,
            waiver_priority=waiver_priority,
        )
    )

    _TRANSACTION_CACHE[
        "snapshot_key"
    ] = snapshot_key

    _TRANSACTION_CACHE[
        "recommendations"
    ] = recommendations

    return recommendations


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def projection(
    player,
    field="week_1_projection",
):
    value = player.get(field)

    if value is None:
        return 0.0

    return float(value)


def is_available_to_play(player):
    status = (
        player.get("status")
        or ""
    ).upper()

    return (
        status
        not in UNAVAILABLE_STATUSES
    )


def add_roster_slots(
    players,
    season,
):
    local_roster = load_season_roster(
        season
    )

    by_name = {
        player["player_name"].lower():
            player
        for player in local_roster
    }

    for player in players:
        local = by_name.get(
            player["name"].lower()
        )

        # Yahoo uses short DST names such as
        # "Texans", while our local roster
        # contains "Houston Texans".
        if (
            local is None
            and player["position"] == "DST"
        ):
            for candidate in local_roster:
                if (
                    candidate["position"]
                    in {"DEF", "DST"}
                    and candidate.get("team")
                    == player.get("team")
                ):
                    local = candidate
                    break

        if local is None:
            player["roster_slot"] = None
            player["slot_index"] = None
            continue

        player["roster_slot"] = (
            local["roster_slot"]
        )

        player["slot_index"] = (
            local["slot_index"]
        )


def best_players(
    players,
    position,
    count,
    excluded_ids,
):
    candidates = [
        player
        for player in players
        if (
            player["position"] == position
            and player["yahoo_player_id"]
            not in excluded_ids
            and is_available_to_play(
                player
            )
        )
    ]

    candidates.sort(
        key=lambda player:
            projection(player),
        reverse=True,
    )

    selected = candidates[:count]

    excluded_ids.update(
        player["yahoo_player_id"]
        for player in selected
    )

    return selected


def build_best_lineup(players):
    used = set()
    lineup = []

    requirements = [
        ("QB", "QB", 1),
        ("RB", "RB", 2),
        ("WR", "WR", 2),
        ("TE", "TE", 1),
    ]

    for (
        slot,
        position,
        count,
    ) in requirements:
        selected = best_players(
            players,
            position,
            count,
            used,
        )

        for player in selected:
            lineup.append(
                {
                    "slot": slot,
                    "player": player,
                }
            )

    flex_candidates = [
        player
        for player in players
        if (
            player["position"]
            in FLEX_POSITIONS
            and player[
                "yahoo_player_id"
            ] not in used
            and is_available_to_play(
                player
            )
        )
    ]

    flex_candidates.sort(
        key=lambda player:
            projection(player),
        reverse=True,
    )

    if flex_candidates:
        flex = flex_candidates[0]

        used.add(
            flex["yahoo_player_id"]
        )

        lineup.append(
            {
                "slot": "FLEX",
                "player": flex,
            }
        )

    for position in [
        "K",
        "DST",
    ]:
        selected = best_players(
            players,
            position,
            1,
            used,
        )

        for player in selected:
            lineup.append(
                {
                    "slot": position,
                    "player": player,
                }
            )

    order = {
        "QB": 1,
        "RB": 2,
        "WR": 3,
        "TE": 4,
        "FLEX": 5,
        "K": 6,
        "DST": 7,
    }

    lineup.sort(
        key=lambda item:
            order[item["slot"]]
    )

    return lineup


def fantasy_season_for_date(
    today=None,
):
    if today is None:
        today = datetime.now(
            UK_TIME
        ).date()

    # January and February still belong
    # to the NFL season that started in
    # the previous calendar year.
    if today.month <= 2:
        return today.year - 1

    return today.year


def week_1_thursday(
    season,
):
    september_1 = date(
        season,
        9,
        1,
    )

    # US Labor Day is the first Monday
    # in September.
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


def week_1_start(
    season,
):
    # Fantasy week starts on the Tuesday
    # before the Thursday opener.
    return (
        week_1_thursday(season)
        - timedelta(days=2)
    )


def current_fantasy_week(
    season=None,
):
    today = datetime.now(
        UK_TIME
    ).date()

    if season is None:
        season = fantasy_season_for_date(
            today
        )

    start = week_1_start(
        season
    )

    if today < start:
        return 1

    week = (
        (
            today
            - start
        ).days
        // 7
        + 1
    )

    return max(
        1,
        min(18, week),
    )

EASTERN = ZoneInfo(
    "America/New_York"
)

UK_TIME = ZoneInfo(
    "Europe/London"
)


def game_date_for_week(
    season,
    week,
    game_day,
):
    week_thursday = (
        week_1_thursday(
            season
        )
        + timedelta(
            weeks=week - 1
        )
    )

    offsets = {
        "Thu": 0,
        "Fri": 1,
        "Sat": 2,
        "Sun": 3,
        "Mon": 4,
        "Tue": 5,
        "Wed": 6,
    }

    offset = offsets.get(
        game_day
    )

    if offset is None:
        return None

    return (
        week_thursday
        + timedelta(days=offset)
    )


def local_game_info(
    player,
    season,
    week,
):
    game_day = player.get(
        "game_day"
    )

    game_time = player.get(
        "game_time"
    )

    if not game_day or not game_time:
        return None

    game_date = game_date_for_week(
        season,
        week,
        game_day,
    )

    if game_date is None:
        return None

    try:
        clock, meridiem = (
            game_time.split()
        )

        hour, minute = (
            int(value)
            for value
            in clock.split(":")
        )

        if (
            meridiem.lower() == "pm"
            and hour != 12
        ):
            hour += 12

        if (
            meridiem.lower() == "am"
            and hour == 12
        ):
            hour = 0

    except ValueError:
        return None

    eastern = datetime(
        game_date.year,
        game_date.month,
        game_date.day,
        hour,
        minute,
        tzinfo=EASTERN,
    )

    local = eastern.astimezone(
        UK_TIME
    )

    return {
        "datetime": local,
        "day":
            local.strftime("%a"),
        "date":
            local.strftime("%-d %b"),
        "time":
            local.strftime("%H:%M"),
        "timezone":
            local.tzname(),
        "display":
            local.strftime(
                "%a %-d %b · %H:%M %Z"
            ),
    }



def enrich_player_game_time(
    player,
    season,
    week,
):
    local_info = local_game_info(
        player,
        season,
        week,
    )

    enriched = dict(player)

    enriched["local_game"] = (
        local_info
    )

    if local_info:
        enriched[
            "local_game_display"
        ] = local_info["display"]
    else:
        enriched[
            "local_game_display"
        ] = player.get(
            "game_display"
        )

    return enriched



def game_sort_key(player):
    day_order = {
        "Thu": 0,
        "Fri": 1,
        "Sat": 2,
        "Sun": 3,
        "Mon": 4,
        "Tue": 5,
        "Wed": 6,
    }

    day = player.get(
        "game_day"
    )

    time_text = player.get(
        "game_time"
    )

    minutes = 9999

    if time_text:
        try:
            clock, meridiem = (
                time_text.split()
            )

            hour, minute = (
                int(value)
                for value
                in clock.split(":")
            )

            if (
                meridiem.lower() == "pm"
                and hour != 12
            ):
                hour += 12

            if (
                meridiem.lower() == "am"
                and hour == 12
            ):
                hour = 0

            minutes = (
                hour * 60
                + minute
            )

        except (
            ValueError,
            AttributeError,
        ):
            pass

    return (
        day_order.get(
            day,
            99,
        ),
        minutes,
        player["name"],
    )


def build_lock_groups(
    roster,
    lineup,
    season,
    week,
):
    starter_slots = {
        item["player"][
            "yahoo_player_id"
        ]:
            item["slot"]
        for item in lineup
    }

    players = [
        player
        for player in roster
        if (
            player.get(
                "roster_slot"
            ) != "IR"
            and player.get(
                "game_day"
            )
            and player.get(
                "game_time"
            )
        )
    ]

    players.sort(
        key=game_sort_key
    )

    groups = []

    for player in players:
        key = (
            player["game_day"],
            player["game_time"],
        )

        if (
            not groups
            or groups[-1]["key"] != key
        ):
            local_info = local_game_info(
                player,
                season,
                week,
            )

            groups.append(
                {
                    "key": key,

                    "day":
                        player["game_day"],

                    "time":
                        player["game_time"],

                    "local":
                        local_info,

                    "players": [],
                }
            )

        game_display = (
            player.get(
                "game_display"
            )
            or ""
        )

        prefix = (
            f"{player['game_day']} "
            f"{player['game_time']} "
        )

        matchup = game_display

        if matchup.startswith(prefix):
            matchup = matchup[
                len(prefix):
            ]

        groups[-1][
            "players"
        ].append(
            {
                "role":
                    starter_slots.get(
                        player[
                            "yahoo_player_id"
                        ],
                        "BENCH",
                    ),
                "player": player,
                "matchup": matchup,
            }
        )

    return groups


def add_transaction_deadlines(
    transactions,
):
    now_local = datetime.now(
        UK_TIME
    )

    output = []

    for transaction in transactions:
        move = dict(transaction)

        add_player = move["add"]
        drop_player = move["drop"]

        add_game = (
            add_player.get("local_game")
            or {}
        )

        drop_game = (
            drop_player.get("local_game")
            or {}
        )

        add_time = add_game.get(
            "datetime"
        )

        drop_time = drop_game.get(
            "datetime"
        )

        possible_times = [
            value
            for value in [
                add_time,
                drop_time,
            ]
            if value is not None
        ]

        if not possible_times:
            move[
                "transaction_deadline"
            ] = None

            move[
                "transaction_deadline_note"
            ] = None

            output.append(move)
            continue

        deadline = min(
            possible_times
        )

        if (
            add_time is not None
            and drop_time is not None
            and add_time == drop_time
        ):
            note = (
                "Both players lock then"
            )

        elif (
            add_time is not None
            and add_time == deadline
        ):
            note = (
                f"{add_player['name']} "
                "locks first"
            )

        else:
            note = (
                f"{drop_player['name']} "
                "locks first"
            )

        move[
            "transaction_deadline"
        ] = {
            "datetime":
                deadline,

            "display":
                deadline.strftime(
                    "%a %-d %b · %H:%M %Z"
                ),

            "passed":
                deadline <= now_local,
        }

        move[
            "transaction_deadline_note"
        ] = note

        # A recommendation whose earliest
        # player has already locked is no
        # longer actionable this week.
        if deadline <= now_local:
            continue

        output.append(move)

    return output



def build_weekly_data(
    season=None,
    week=None,
):
    if season is None:
        season = (
            fantasy_season_for_date()
        )

    if week is None:
        week = current_fantasy_week(
            season
        )

    roster = (
        yahoo_provider
        .get_roster()
    )

    available = (
        yahoo_provider
        .get_available_players()
    )

    add_roster_slots(
        roster,
        season,
    )

    roster = [
        enrich_player_game_time(
            player,
            season,
            week,
        )
        for player in roster
    ]

    available = [
        enrich_player_game_time(
            player,
            season,
            week,
        )
        for player in available
    ]

    provider_status = (
        yahoo_provider
        .get_status()
    )

    bye_coverage = (
        build_bye_coverage(
            roster,
            week,
        )
    )

    future_bye_coverage = [
        item
        for item in bye_coverage
        if item["status"] != "GOOD"
    ]

    transactions = (
        cached_transaction_recommendations(
            roster,
            available,
            provider_status,
            week,
        )
    )

    transactions = (
        add_transaction_deadlines(
            transactions
        )
    )

    lineup = build_best_lineup(
        roster
    )

    starter_ids = {
        item["player"][
            "yahoo_player_id"
        ]
        for item in lineup
    }

    bench = [
        player
        for player in roster
        if (
            player[
                "yahoo_player_id"
            ] not in starter_ids
            and player.get(
                "roster_slot"
            ) != "IR"
        )
    ]

    bench.sort(
        key=lambda player:
            projection(player),
        reverse=True,
    )

    status_watch = [
        item
        for item in lineup
        if item["player"].get(
            "status"
        )
    ]

    ir_review = [
        player
        for player in roster
        if player.get(
            "roster_slot"
        ) == "IR"
    ]

    total_projection = sum(
        projection(
            item["player"]
        )
        for item in lineup
    )

    actual_so_far = sum(
        float(
            item["player"].get(
                "week_1_actual"
            )
            or 0
        )
        for item in lineup
        if item["player"].get(
            "week_1_actual"
        ) is not None
    )

    remaining_projection = sum(
        projection(
            item["player"]
        )
        for item in lineup
        if item["player"].get(
            "week_1_actual"
        ) is None
    )

    projected_final = (
        actual_so_far
        + remaining_projection
    )

    lock_groups = build_lock_groups(
        roster,
        lineup,
        season,
        week,
    )

    now_local = datetime.now(
        UK_TIME
    )

    upcoming_lock_groups = [
        group
        for group in lock_groups
        if (
            group.get("local")
            and group["local"].get(
                "datetime"
            )
            and group["local"][
                "datetime"
            ] > now_local
        )
    ]

    first_lock = (
        upcoming_lock_groups[0]
        if upcoming_lock_groups
        else None
    )

    next_decision = None

    if first_lock:
        starters = [
            item
            for item in first_lock["players"]
            if item["role"] != "BENCH"
        ]

        bench_players = [
            item
            for item in first_lock["players"]
            if item["role"] == "BENCH"
        ]

        concerns = [
            item
            for item in first_lock["players"]
            if item["player"].get("status")
        ]

        next_decision = {
            "lock": first_lock,
            "starters": starters,
            "bench_players": bench_players,
            "concerns": concerns,
            "starter_count": len(starters),
            "bench_count": len(bench_players),
            "concern_count": len(concerns),
        }

    return {
        "season": season,
        "week": week,
        "roster": roster,
        "lineup": lineup,
        "bench": bench,
        "status_watch":
            status_watch,

        "transactions":
            transactions,

        "future_bye_coverage":
            future_bye_coverage,

        "ir_review":
            ir_review,
        "lock_groups":
            lock_groups,

        "upcoming_lock_groups":
            upcoming_lock_groups,

        "first_lock":
            first_lock,

        "next_decision":
            next_decision,

        "total_projection":
            total_projection,

        "actual_so_far":
            actual_so_far,

        "remaining_projection":
            remaining_projection,

        "projected_final":
            projected_final,

        "provider_status":
            provider_status,
    }

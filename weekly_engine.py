from pathlib import Path
import json

from database import load_season_roster
from yahoo_provider import yahoo_provider


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
            groups.append(
                {
                    "key": key,
                    "day":
                        player["game_day"],
                    "time":
                        player["game_time"],
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


def build_weekly_data(
    season=2026,
    week=1,
):
    roster = (
        yahoo_provider
        .get_roster()
    )

    add_roster_slots(
        roster,
        season,
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

    lock_groups = build_lock_groups(
        roster,
        lineup,
    )

    first_lock = (
        lock_groups[0]
        if lock_groups
        else None
    )

    provider_status = (
        yahoo_provider
        .get_status()
    )

    return {
        "season": season,
        "week": week,
        "roster": roster,
        "lineup": lineup,
        "bench": bench,
        "status_watch":
            status_watch,
        "ir_review":
            ir_review,
        "lock_groups":
            lock_groups,
        "first_lock":
            first_lock,
        "total_projection":
            total_projection,

        "provider_status":
            provider_status,
    }

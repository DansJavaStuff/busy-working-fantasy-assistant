from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from database import load_season_roster


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


def projection(player, field):
    value = player.get(field)

    if value is None:
        return 0.0

    return float(value)


def weekly_average_4(player):
    return (
        projection(
            player,
            "next_4_weeks_projection",
        )
        / 4.0
    )


def short_term_score(player):
    """
    Week 1 matters most, but the four-week
    outlook stops us overreacting to one
    unusually good matchup.
    """
    week = projection(
        player,
        "week_1_projection",
    )

    four_week_average = (
        weekly_average_4(player)
    )

    return (
        week * 0.65
        + four_week_average * 0.35
    )


def is_available_to_play(player):
    status = (
        player.get("status")
        or ""
    ).upper()

    return (
        status
        not in UNAVAILABLE_STATUSES
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
            and is_available_to_play(player)
        )
    ]

    candidates.sort(
        key=lambda player:
            projection(
                player,
                "week_1_projection",
            ),
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

    slot_requirements = [
        ("QB", "QB", 1),
        ("RB", "RB", 2),
        ("WR", "WR", 2),
        ("TE", "TE", 1),
    ]

    for (
        slot,
        position,
        count,
    ) in slot_requirements:

        selected = best_players(
            players,
            position,
            count,
            used,
        )

        for player in selected:
            lineup.append(
                (
                    slot,
                    player,
                )
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
            projection(
                player,
                "week_1_projection",
            ),
        reverse=True,
    )

    if flex_candidates:
        flex = flex_candidates[0]

        used.add(
            flex["yahoo_player_id"]
        )

        lineup.append(
            (
                "FLEX",
                flex,
            )
        )

    for slot in ["K", "DST"]:
        selected = best_players(
            players,
            slot,
            1,
            used,
        )

        for player in selected:
            lineup.append(
                (
                    slot,
                    player,
                )
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
            order[item[0]]
    )

    return lineup


def print_lineup(players):
    lineup = build_best_lineup(
        players
    )

    starter_ids = {
        player["yahoo_player_id"]
        for _, player
        in lineup
    }

    print("WEEK 1 RECOMMENDED LINEUP")
    print("=========================")

    total = 0.0

    for slot, player in lineup:
        points = projection(
            player,
            "week_1_projection",
        )

        total += points

        status = (
            player.get("status")
            or ""
        )

        marker = (
            f" [{status}]"
            if status
            else ""
        )

        print(
            f"{slot:<5} "
            f"{player['name']:<24} "
            f"{points:>6.2f}"
            f"{marker}"
        )

    print("-------------------------")
    print(
        f"Projected total: "
        f"{total:.2f}"
    )

    print()
    print("BENCH")
    print("=====")

    bench = [
        player
        for player in players
        if (
            player["yahoo_player_id"]
            not in starter_ids
            and player["position"]
            != "DST"
            and player["position"]
            != "K"
        )
    ]

    bench.sort(
        key=lambda player:
            projection(
                player,
                "week_1_projection",
            ),
        reverse=True,
    )

    for player in bench:
        status = (
            player.get("status")
            or ""
        )

        marker = (
            f" [{status}]"
            if status
            else ""
        )

        print(
            f"{player['position']:<5} "
            f"{player['name']:<24} "
            f"{projection(player, 'week_1_projection'):>6.2f}"
            f"{marker}"
        )

    return lineup


def print_status_warnings(lineup):
    warnings = []

    for slot, player in lineup:
        status = player.get(
            "status"
        )

        if status:
            warnings.append(
                (
                    slot,
                    player,
                    status,
                )
            )

    print()
    print("STATUS WATCH")
    print("============")

    if not warnings:
        print(
            "No starting players "
            "currently flagged."
        )
        return

    for (
        slot,
        player,
        status,
    ) in warnings:
        print(
            f"{slot:<5} "
            f"{player['name']:<24} "
            f"{status}"
        )


def available_by_position(
    available,
    position,
):
    players = [
        player
        for player in available
        if player["position"] == position
    ]

    players.sort(
        key=short_term_score,
        reverse=True,
    )

    return players


def print_available_rankings(
    available,
):
    print()
    print("TOP AVAILABLE PLAYERS")
    print("=====================")

    for position in [
        "QB",
        "RB",
        "WR",
        "TE",
        "K",
        "DST",
    ]:
        print()
        print(position)
        print("-" * len(position))

        candidates = (
            available_by_position(
                available,
                position,
            )[:5]
        )

        for player in candidates:
            week_1 = projection(
                player,
                "week_1_projection",
            )

            four_avg = weekly_average_4(
                player
            )

            status = (
                player.get("status")
                or ""
            )

            marker = (
                f" {status}"
                if status
                else ""
            )

            print(
                f"{player['name']:<24} "
                f"W1 {week_1:>5.2f}  "
                f"4W avg {four_avg:>5.2f}  "
                f"{player['roster_status']}"
                f"{marker}"
            )


def print_simple_upgrades(
    roster,
    available,
):
    print()
    print("POSSIBLE FA/W UPGRADES")
    print("======================")

    found = False

    for position in [
        "QB",
        "RB",
        "WR",
        "TE",
        "K",
        "DST",
    ]:
        roster_players = [
            player
            for player in roster
            if (
                player["position"] == position
                and player.get(
                    "roster_slot"
                ) != "IR"
            )
        ]

        available_players = (
            available_by_position(
                available,
                position,
            )
        )

        if (
            not roster_players
            or not available_players
        ):
            continue

        weakest = min(
            roster_players,
            key=short_term_score,
        )

        best_available = (
            available_players[0]
        )

        roster_score = (
            short_term_score(
                weakest
            )
        )

        available_score = (
            short_term_score(
                best_available
            )
        )

        improvement = (
            available_score
            - roster_score
        )

        if improvement <= 0:
            continue

        found = True

        print()
        print(
            f"{position}: "
            f"{best_available['name']} "
            f"over "
            f"{weakest['name']}"
        )

        print(
            f"  Week 1: "
            f"{projection(best_available, 'week_1_projection'):.2f}"
            f" vs "
            f"{projection(weakest, 'week_1_projection'):.2f}"
        )

        print(
            f"  4W avg: "
            f"{weekly_average_4(best_available):.2f}"
            f" vs "
            f"{weekly_average_4(weakest):.2f}"
        )

        print(
            f"  Short-term edge: "
            f"+{improvement:.2f}"
        )

        print(
            f"  Availability: "
            f"{best_available['roster_status']}"
        )

    if not found:
        print(
            "No obvious same-position "
            "projection upgrades found."
        )


def add_roster_slots(players):
    local_roster = load_season_roster(
        2026
    )

    by_name = {
        player["player_name"].lower():
            player
        for player in local_roster
    }

    unmatched = []

    for player in players:
        local = by_name.get(
            player["name"].lower()
        )

        # Yahoo uses short defence names such
        # as "Texans", while our local roster
        # may contain "Houston Texans".
        # For DST, team code is the safer key.
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
            unmatched.append(
                player["name"]
            )
            continue

        player["roster_slot"] = (
            local["roster_slot"]
        )

        player["slot_index"] = (
            local["slot_index"]
        )

    return unmatched


def print_ir_stashes(roster):
    ir_players = [
        player
        for player in roster
        if player.get(
            "roster_slot"
        ) == "IR"
    ]

    print()
    print("IR STASH REVIEW")
    print("===============")

    if not ir_players:
        print("No players currently on IR.")
        return

    for player in ir_players:
        print(
            f"{player['name']:<24} "
            f"{player.get('status') or 'IR'}"
        )

        print(
            f"  Week 1: "
            f"{projection(player, 'week_1_projection'):.2f}"
        )

        print(
            f"  Week 2: "
            f"{projection(player, 'week_2_projection'):.2f}"
        )

        print(
            f"  Next 4: "
            f"{projection(player, 'next_4_weeks_projection'):.2f}"
        )

        print(
            "  Decision: REVIEW STASH VALUE"
        )

        print(
            "  Do not treat as an automatic "
            "drop based on current projection."
        )



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
                for value in clock.split(":")
            )

            if meridiem.lower() == "pm":
                if hour != 12:
                    hour += 12
            elif hour == 12:
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


def print_upcoming_decisions(
    roster,
    lineup,
):
    starter_slots = {
        player["yahoo_player_id"]:
            slot
        for slot, player
        in lineup
    }

    active_players = [
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

    active_players.sort(
        key=game_sort_key
    )

    print()
    print("UPCOMING LINEUP LOCKS")
    print("====================")

    if not active_players:
        print(
            "No game times available."
        )
        return

    first = active_players[0]

    print(
        f"First lock: "
        f"{first['game_day']} "
        f"{first['game_time']} ET"
    )

    current_lock = None

    for player in active_players:
        lock = (
            player["game_day"],
            player["game_time"],
        )

        if lock != current_lock:
            heading = (
                f"{player['game_day']} "
                f"{player['game_time']} ET"
            )

            print()
            print(heading)
            print(
                "-" * len(heading)
            )

            current_lock = lock

        starter_slot = (
            starter_slots.get(
                player[
                    "yahoo_player_id"
                ]
            )
        )

        role = (
            starter_slot
            if starter_slot
            else "BENCH"
        )

        status = (
            player.get("status")
            or ""
        )

        marker = (
            f" [{status}]"
            if status
            else ""
        )

        matchup = (
            player.get(
                "game_display"
            )
            or ""
        )

        # Remove the duplicated day/time
        # from the matchup for display.
        prefix = (
            f"{player['game_day']} "
            f"{player['game_time']} "
        )

        if matchup.startswith(prefix):
            matchup = matchup[
                len(prefix):
            ]

        print(
            f"{role:<6} "
            f"{player['name']:<24} "
            f"{matchup:<10}"
            f"{marker}"
        )


def main():
    roster = load_json(
        MY_TEAM_FILE
    )

    unmatched = add_roster_slots(
        roster
    )

    if unmatched:
        print(
            "WARNING: roster slot not found for:",
            ", ".join(unmatched),
        )
        print()

    available = load_json(
        AVAILABLE_FILE
    )

    lineup = print_lineup(
        roster
    )

    print_status_warnings(
        lineup
    )

    print_upcoming_decisions(
        roster,
        lineup,
    )

    print_available_rankings(
        available
    )

    print_ir_stashes(
        roster
    )

    print_simple_upgrades(
        roster,
        available,
    )


if __name__ == "__main__":
    main()

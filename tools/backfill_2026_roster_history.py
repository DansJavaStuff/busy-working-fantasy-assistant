from database import (
    backup_database,
    load_player_week_history,
    load_season_roster,
    load_week_lineup,
    load_week_roster,
    replace_season_transactions,
    replace_week_lineup,
    snapshot_season_roster,
)
from history_reconstruction import (
    canonical_history_roster,
    roster_at_week_end,
)
from yahoo_provider import (
    enrich_local_roster,
)


SEASON = 2026

# Confirmed from Daniel's Yahoo transaction history. The first/second Yahoo
# pages independently corroborate these rows; this list is deliberately kept
# explicit because the backfill is a one-off reconstruction, not a recurring
# transaction-scraping dependency.
WEEK_3_SUBMITTED_LINEUP = [
    ("30977", "Josh Allen", "QB", "QB", 1),
    ("41791", "Ashton Jeanty", "RB", "RB", 1),
    ("31905", "David Montgomery", "RB", "RB", 2),
    ("32703", "Tee Higgins", "WR", "WR", 1),
    ("27535", "Mike Evans", "WR", "WR", 2),
    ("40102", "Tucker Kraft", "TE", "TE", 1),
    ("31960", "Tony Pollard", "RB", "FLEX", 1),
    ("31482", "Eddy Pineiro", "K", "K", 1),
    ("100009", "Packers", "DST", "DEF", 1),
    ("40168", "Puka Nacua", "WR", "BN", 1),
    ("31010", "Courtland Sutton", "WR", "BN", 2),
    ("33415", "Rashod Bateman", "WR", "BN", 3),
    ("40641", "Keaton Mitchell", "RB", "BN", 4),
    ("40030", "C.J. Stroud", "QB", "BN", 5),
    ("42630", "Jordyn Tyson", "WR", "IR", 1),
]


TRANSACTIONS = [
    {
        "occurred_at": "2026-09-08T18:43:00",
        "transaction_type": "add",
        "add_player_id": "40641",
        "add_player_name": "Keaton Mitchell",
        "add_position": "RB",
        "add_team": "LAC",
        "acquisition_type": "free_agent",
        "drop_player_id": None,
        "drop_player_name": None,
        "drop_position": None,
        "drop_team": None,
    },
    {
        "occurred_at": "2026-09-12T10:27:00",
        "transaction_type": "add_drop",
        "add_player_id": "100008",
        "add_player_name": "Lions",
        "add_position": "DST",
        "add_team": "DET",
        "acquisition_type": "free_agent",
        "drop_player_id": "100034",
        "drop_player_name": "Texans",
        "drop_position": "DST",
        "drop_team": "HOU",
    },
    {
        "occurred_at": "2026-09-16T04:44:00",
        "transaction_type": "add_drop",
        "add_player_id": "100027",
        "add_player_name": "Buccaneers",
        "add_position": "DST",
        "add_team": "TB",
        "acquisition_type": "waiver",
        "drop_player_id": "100008",
        "drop_player_name": "Lions",
        "drop_position": "DST",
        "drop_team": "DET",
    },
    {
        "occurred_at": "2026-09-23T04:48:00",
        "transaction_type": "add_drop",
        "add_player_id": "100009",
        "add_player_name": "Packers",
        "add_position": "DST",
        "add_team": "GB",
        "acquisition_type": "waiver",
        "drop_player_id": "100027",
        "drop_player_name": "Buccaneers",
        "drop_position": "DST",
        "drop_team": "TB",
    },
    {
        "occurred_at": "2026-09-23T04:48:00",
        "transaction_type": "add_drop",
        "add_player_id": "40030",
        "add_player_name": "C.J. Stroud",
        "add_position": "QB",
        "add_team": "HOU",
        "acquisition_type": "waiver",
        "drop_player_id": "33389",
        "drop_player_name": "Trevor Lawrence",
        "drop_position": "QB",
        "drop_team": "JAX",
    },
    {
        "occurred_at": "2026-09-27T11:26:00",
        "transaction_type": "add_drop",
        "add_player_id": "31482",
        "add_player_name": "Eddy Pineiro",
        "add_position": "K",
        "add_team": "SF",
        "acquisition_type": "free_agent",
        "drop_player_id": "34344",
        "drop_player_name": "Cameron Dicker",
        "drop_position": "K",
        "drop_team": "LAC",
    },
]




def print_week_summary(
    week,
):
    roster = load_week_roster(
        week,
        season=SEASON,
    )

    submitted_lineup = {
        row["player_id"]: row
        for row in load_week_lineup(
            week,
            season=SEASON,
        )
    }

    history = {
        row["player_id"]: row
        for row in load_player_week_history(
            week,
            season=SEASON,
        )
    }

    actuals = [
        history[player["player_id"]]["actual"]
        for player in roster
        if (
            player["player_id"]
            in history
            and history[
                player["player_id"]
            ]["actual"]
            is not None
        )
    ]

    print()
    print(
        f"Week {week}: "
        f"{len(roster)} roster player(s), "
        f"{len(actuals)} actual score(s) available"
    )

    display_rows = []

    for player in roster:
        lineup = submitted_lineup.get(
            player["player_id"]
        )

        display_rows.append(
            {
                **player,
                "roster_slot": (
                    lineup["lineup_slot"]
                    if lineup
                    else player["roster_slot"]
                ),
                "slot_index": (
                    lineup["slot_index"]
                    if lineup
                    else player["slot_index"]
                ),
            }
        )

    slot_order = {
        "QB": 1,
        "RB": 2,
        "WR": 3,
        "TE": 4,
        "FLEX": 5,
        "K": 6,
        "DEF": 7,
        "BN": 8,
        "IR": 9,
    }

    display_rows.sort(
        key=lambda player: (
            slot_order.get(
                player["roster_slot"],
                99,
            ),
            player["slot_index"],
        )
    )

    for player in display_rows:
        result = history.get(
            player["player_id"],
            {},
        )

        actual = result.get(
            "actual"
        )

        actual_text = (
            f"{actual:.2f}"
            if actual is not None
            else "-"
        )

        print(
            "  "
            f"{player['roster_slot']:>4} "
            f"{player['slot_index']:>2}  "
            f"{player['player_name']:<24} "
            f"{actual_text:>7}"
        )


def main():
    current_local_roster = (
        load_season_roster(
            SEASON
        )
    )

    current_roster = (
        canonical_history_roster(
            enrich_local_roster(
                current_local_roster
            )
        )
    )

    current_ids = {
        str(player["player_id"])
        for player in current_roster
    }

    expected_current = {
        "40641",   # Keaton Mitchell
        "100009",  # Packers
        "40030",   # C.J. Stroud
        "31482",   # Eddy Pineiro
    }

    missing = (
        expected_current
        - current_ids
    )

    if missing:
        raise SystemExit(
            "Current roster does not match the expected "
            "post-transaction state. Missing player id(s): "
            + ", ".join(
                sorted(missing)
            )
        )

    backup = backup_database()

    print(
        "2026 ROSTER HISTORY BACKFILL"
    )
    print(
        "============================"
    )
    print(
        f"Database backup: {backup}"
    )

    transaction_count = (
        replace_season_transactions(
            TRANSACTIONS,
            season=SEASON,
            source=
                "confirmed_2026_backfill",
        )
    )

    print(
        f"Stored transactions: "
        f"{transaction_count}"
    )

    for week in (1, 2, 3):
        reconstructed = (
            roster_at_week_end(
                current_roster,
                TRANSACTIONS,
                target_week=week,
                season=SEASON,
            )
        )

        snapshot_season_roster(
            week,
            season=SEASON,
            roster=reconstructed,
        )

    print()
    print(
        "Tyson's pre-Week-1 IR placement is represented by the "
        "current roster state used as the reconstruction anchor; "
        "the Sep 8 Mitchell add therefore remains part of Week 1."
    )

    replace_week_lineup(
        3,
        [
            {
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "lineup_slot": lineup_slot,
                "slot_index": slot_index,
                "source": "confirmed_yahoo_screenshot",
            }
            for (
                player_id,
                player_name,
                position,
                lineup_slot,
                slot_index,
            )
            in WEEK_3_SUBMITTED_LINEUP
        ],
        season=SEASON,
        source="confirmed_yahoo_screenshot",
    )

    print()
    print(
        "Stored confirmed Week 3 submitted Yahoo lineup: "
        "15 player(s)"
    )

    for week in (1, 2, 3):
        print_week_summary(
            week
        )


if __name__ == "__main__":
    main()

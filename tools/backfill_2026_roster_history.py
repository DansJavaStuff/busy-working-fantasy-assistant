from database import (
    backup_database,
    load_player_week_history,
    load_season_roster,
    load_week_roster,
    replace_season_transactions,
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

    for player in roster:
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

    for week in (1, 2, 3):
        print_week_summary(
            week
        )


if __name__ == "__main__":
    main()

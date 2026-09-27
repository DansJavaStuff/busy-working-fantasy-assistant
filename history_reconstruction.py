from copy import deepcopy
from datetime import datetime

from fantasy_calendar import current_fantasy_week


def transaction_week(
    transaction,
    season,
):
    occurred_at = transaction[
        "occurred_at"
    ]

    if isinstance(
        occurred_at,
        str,
    ):
        occurred_at = datetime.fromisoformat(
            occurred_at
        )

    return current_fantasy_week(
        season,
        today=occurred_at.date(),
    )


def rewind_transaction(
    roster,
    transaction,
):
    """Undo one add/drop transaction from a roster snapshot."""

    output = deepcopy(roster)

    add_player_id = transaction.get(
        "add_player_id"
    )
    drop_player_id = transaction.get(
        "drop_player_id"
    )

    if add_player_id is None:
        return output

    add_player_id = str(
        add_player_id
    )

    add_index = next(
        (
            index
            for index, player
            in enumerate(output)
            if str(
                player["player_id"]
            )
            == add_player_id
        ),
        None,
    )

    if add_index is None:
        raise ValueError(
            "Cannot rewind transaction: "
            f"added player {add_player_id} "
            "is not on the reconstructed roster"
        )

    added = output.pop(
        add_index
    )

    if drop_player_id is None:
        return output

    restored = {
        **added,
        "player_id": str(
            drop_player_id
        ),
        "player_name":
            transaction[
                "drop_player_name"
            ],
        "position":
            transaction.get(
                "drop_position"
            )
            or added.get(
                "position"
            ),
        "team":
            transaction.get(
                "drop_team"
            ),
        "status": None,
        "source":
            "historical_reconstruction",
    }

    output.append(
        restored
    )

    return output


def roster_at_week_end(
    current_roster,
    transactions,
    target_week,
    season,
):
    """Reconstruct end-of-week ownership by rewinding later transactions."""

    roster = deepcopy(
        current_roster
    )

    later = [
        transaction
        for transaction
        in transactions
        if (
            transaction_week(
                transaction,
                season,
            )
            > int(target_week)
        )
    ]

    later.sort(
        key=lambda item:
            item["occurred_at"],
        reverse=True,
    )

    for transaction in later:
        roster = rewind_transaction(
            roster,
            transaction,
        )

    return roster

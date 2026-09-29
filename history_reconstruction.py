from copy import deepcopy
from datetime import datetime

from fantasy_calendar import current_fantasy_week





def canonical_history_roster(
    enriched_roster,
):
    """Convert an enriched local roster to Yahoo-keyed history rows.

    Current roster membership/slots remain locally authoritative, but Yahoo's
    player id is the canonical identity used by season_player_week. Using the
    same id here makes historical roster rows join directly to projections and
    actuals.
    """

    output = []

    for player in enriched_roster:
        yahoo_id = player.get(
            "yahoo_player_id"
        )

        if yahoo_id is None:
            raise ValueError(
                "Cannot persist historical roster row without Yahoo id: "
                + str(
                    player.get(
                        "name",
                        player.get(
                            "player_name",
                            "unknown player",
                        ),
                    )
                )
            )

        output.append(
            {
                "player_id": str(
                    yahoo_id
                ),
                "player_name":
                    player.get(
                        "name"
                    )
                    or player.get(
                        "player_name"
                    ),
                "position":
                    player.get(
                        "position"
                    ),
                "team":
                    player.get(
                        "team"
                    ),
                "roster_slot":
                    player.get(
                        "roster_slot"
                    ),
                "slot_index":
                    int(
                        player.get(
                            "slot_index",
                            1,
                        )
                    ),
                "bye_week":
                    player.get(
                        "bye_week"
                    ),
                "status":
                    player.get(
                        "status"
                    ),
                "source":
                    "yahoo_canonical_history",
            }
        )

    return output


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

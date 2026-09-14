from database import connect, get_or_create_season
from league_config import FLEX_ELIGIBLE


STARTER_SLOTS = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,
    "K": 1,
    "DEF": 1,
}


def player_can_fill_slot(position, roster_slot):
    """
    Return True if a player's natural position
    is eligible for a roster slot.
    """

    if roster_slot == "BN":
        return True

    if roster_slot == "FLEX":
        return position in FLEX_ELIGIBLE

    if roster_slot == "DEF":
        return position in {"DEF", "DST"}

    return position == roster_slot


def normalise_bench(db, season_id):
    """
    Re-number bench players sequentially after moves.

    Uses temporary indexes first to avoid primary-key
    collisions.
    """

    bench = db.execute(
        """
        SELECT player_id
        FROM season_roster
        WHERE season_id = ?
          AND roster_slot = 'BN'
        ORDER BY slot_index
        """,
        (season_id,),
    ).fetchall()

    for offset, row in enumerate(
        bench,
        start=100,
    ):
        db.execute(
            """
            UPDATE season_roster
            SET slot_index = ?
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                offset,
                season_id,
                row["player_id"],
            ),
        )

    for index, row in enumerate(
        bench,
        start=1,
    ):
        db.execute(
            """
            UPDATE season_roster
            SET
                slot_index = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                index,
                season_id,
                row["player_id"],
            ),
        )


def next_bench_index(db, season_id):
    row = db.execute(
        """
        SELECT COALESCE(
            MAX(slot_index),
            0
        ) AS max_index
        FROM season_roster
        WHERE season_id = ?
          AND roster_slot = 'BN'
        """,
        (season_id,),
    ).fetchone()

    return row["max_index"] + 1


def replace_roster_player(
    drop_player_id,
    add_player,
    season=2026,
):
    """
    Replace one rostered player with another.

    The incoming player inherits the dropped
    player's current roster slot and index.
    """

    required = {
        "player_id",
        "player_name",
        "position",
    }

    missing = required - set(add_player)

    if missing:
        raise ValueError(
            "Incoming player is missing: "
            + ", ".join(sorted(missing))
        )

    with connect() as db:
        season_id = get_or_create_season(
            db,
            season,
        )

        dropped = db.execute(
            """
            SELECT *
            FROM season_roster
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                season_id,
                str(drop_player_id),
            ),
        ).fetchone()

        if dropped is None:
            raise ValueError(
                "Dropped player is not on the roster"
            )

        existing = db.execute(
            """
            SELECT 1
            FROM season_roster
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                season_id,
                str(add_player["player_id"]),
            ),
        ).fetchone()

        if existing is not None:
            raise ValueError(
                "Incoming player is already on the roster"
            )

        if not player_can_fill_slot(
            add_player["position"],
            dropped["roster_slot"],
        ):
            raise ValueError(
                f'{add_player["player_name"]} '
                f'cannot fill '
                f'{dropped["roster_slot"]}'
            )

        db.execute(
            """
            DELETE FROM season_roster
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                season_id,
                dropped["player_id"],
            ),
        )

        db.execute(
            """
            INSERT INTO season_roster (
                season_id,
                roster_slot,
                slot_index,
                player_id,
                player_name,
                position,
                team,
                bye_week,
                status,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                season_id,
                dropped["roster_slot"],
                dropped["slot_index"],
                str(add_player["player_id"]),
                add_player["player_name"],
                add_player["position"],
                add_player.get("team"),
                add_player.get("bye_week"),
                add_player.get("status"),
                add_player.get(
                    "source",
                    "manual_transaction",
                ),
            ),
        )

        normalise_bench(
            db,
            season_id,
        )


def move_roster_player(
    player_id,
    target_slot,
    target_index=None,
    season=2026,
):
    """
    Move a rostered player to another slot.

    Occupied target:
        swap players if both resulting positions
        are legal.

    Empty starter:
        move player into it.

    Empty bench:
        allocate the next bench index automatically.
    """

    target_slot = str(
        target_slot
    ).upper()

    with connect() as db:
        season_id = get_or_create_season(
            db,
            season,
        )

        source = db.execute(
            """
            SELECT *
            FROM season_roster
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                season_id,
                str(player_id),
            ),
        ).fetchone()

        if source is None:
            raise ValueError(
                "Player is not on the roster"
            )

        if target_slot == "IR":
            raise ValueError(
                "IR moves are not enabled yet"
            )

        if not player_can_fill_slot(
            source["position"],
            target_slot,
        ):
            raise ValueError(
                f'{source["player_name"]} '
                f'cannot play {target_slot}'
            )

        if target_slot == "BN":
            if target_index is None:
                target_index = (
                    next_bench_index(
                        db,
                        season_id,
                    )
                )
        else:
            target_index = int(target_index)

            allowed_count = STARTER_SLOTS.get(
                target_slot
            )

            if (
                allowed_count is None
                or target_index < 1
                or target_index > allowed_count
            ):
                raise ValueError(
                    "Invalid roster destination"
                )

        source_slot = source["roster_slot"]
        source_index = source["slot_index"]

        if (
            source_slot == target_slot
            and source_index == target_index
        ):
            return

        target = db.execute(
            """
            SELECT *
            FROM season_roster
            WHERE season_id = ?
              AND roster_slot = ?
              AND slot_index = ?
            """,
            (
                season_id,
                target_slot,
                target_index,
            ),
        ).fetchone()

        if target is not None:
            if not player_can_fill_slot(
                target["position"],
                source_slot,
            ):
                raise ValueError(
                    f'{target["player_name"]} '
                    f'cannot play {source_slot}'
                )

            db.execute(
                """
                UPDATE season_roster
                SET
                    roster_slot = '__SWAP__',
                    slot_index = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE season_id = ?
                  AND player_id = ?
                """,
                (
                    season_id,
                    source["player_id"],
                ),
            )

            db.execute(
                """
                UPDATE season_roster
                SET
                    roster_slot = ?,
                    slot_index = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE season_id = ?
                  AND player_id = ?
                """,
                (
                    source_slot,
                    source_index,
                    season_id,
                    target["player_id"],
                ),
            )

        db.execute(
            """
            UPDATE season_roster
            SET
                roster_slot = ?,
                slot_index = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE season_id = ?
              AND player_id = ?
            """,
            (
                target_slot,
                target_index,
                season_id,
                source["player_id"],
            ),
        )

        normalise_bench(
            db,
            season_id,
        )

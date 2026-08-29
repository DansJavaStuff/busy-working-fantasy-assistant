import json
from datetime import datetime

from database import (
    active_draft_session,
    connect,
    get_or_create_season,
    initialise_database,
    list_seasons,
)

from league_config import DRAFT_ROSTER_SIZE

DEFAULT_TEAMS = 12
DEFAULT_YOUR_SLOT = 8

def _create_draft_session(
    db,
    teams,
    your_slot,
    name=None,
    session_type="mock",
    season_id=None,
):
    """
    Create a new active draft session.

    Any existing active session is retained as history but
    marked inactive.
    """

    if season_id is None:
        season_id = get_or_create_season(db)

    db.execute(
        """
        UPDATE draft_sessions
        SET
            is_active = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE is_active = 1
        """
    )

    if name is None:
        name = (
            "Mock draft "
            + datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
        )

    cursor = db.execute(
        """
        INSERT INTO draft_sessions (
            season_id,
            name,
            session_type,
            teams,
            your_slot,
            current_pick,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, 1, 1)
        """,
        (
            season_id,
            name,
            session_type,
            teams,
            your_slot,
        ),
    )

    return cursor.lastrowid

def _ensure_active_session(db):
    """
    Return the active session, creating a fresh mock if
    necessary.
    """

    session = active_draft_session(db)

    if session:
        return session

    session_id = _create_draft_session(
        db,
        DEFAULT_TEAMS,
        DEFAULT_YOUR_SLOT,
    )

    return db.execute(
        """
        SELECT *
        FROM draft_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()


def load_state():
    """
    Rebuild the current draft state from SQLite.

    The returned structure intentionally matches the old
    draft_state.json format so the rest of the application
    does not need to know storage has changed.
    """

    initialise_database()

    with connect() as db:
        session = _ensure_active_session(db)

        season = db.execute(
            """
            SELECT season
            FROM seasons
            WHERE id = ?
            """,
            (session["season_id"],),
        ).fetchone()

        rows = db.execute(
            """
            SELECT
                overall_pick,
                round_number,
                slot,
                is_yours,
                player_json
            FROM draft_picks
            WHERE draft_session_id = ?
            ORDER BY overall_pick
            """,
            (session["id"],),
        ).fetchall()

    drafted = []
    your_roster = []

    for row in rows:
        player = json.loads(
            row["player_json"]
        )

        drafted.append(
            {
                "overall_pick":
                    row["overall_pick"],
                "round":
                    row["round_number"],
                "slot":
                    row["slot"],
                "player":
                    player,
            }
        )

        if row["is_yours"]:
            your_roster.append(player)

    return {
        "session_id": session["id"],
        "session_type": session["session_type"],
        "session_name": session["name"],
        "season": season["season"],
        "teams": session["teams"],
        "your_slot": session["your_slot"],
        "current_pick":
            session["current_pick"],
        "drafted": drafted,
        "your_roster": your_roster,
    }

def start_actual_draft():
    """
    Start a new actual draft session.

    The current mock remains in SQLite as historical data.
    """

    initialise_database()

    with connect() as db:
        current = _ensure_active_session(db)

        _create_draft_session(
            db,
            current["teams"],
            current["your_slot"],
            name=(
                "Actual draft "
                + datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                )
            ),
            session_type="actual",
            season_id=current["season_id"],
        )

    return load_state()

def reset_state():
    """
    Start a new mock draft.

    Unlike the old JSON reset, the previous draft is retained
    in SQLite as an inactive historical session.
    """

    initialise_database()

    with connect() as db:
        current = _ensure_active_session(db)

        _create_draft_session(
            db,
            current["teams"],
            current["your_slot"],
            season_id=current["season_id"],
        )

    return load_state()


def pick_to_round_and_slot(
    pick_number,
    teams,
):
    round_number = (
        (pick_number - 1) // teams
    ) + 1

    index = (
        pick_number - 1
    ) % teams

    if round_number % 2 == 1:
        slot = index + 1
    else:
        slot = teams - index

    return round_number, slot

def total_draft_picks(state):
    """
    Total number of selections in the normal draft.

    IR is not an intentionally drafted roster slot, so the
    number of draft rounds comes from DRAFT_ROSTER_SIZE.
    """
    return (
        state["teams"]
        * DRAFT_ROSTER_SIZE
    )

def draft_is_complete(state):
    return (
        state["current_pick"]
        > total_draft_picks(state)
    )

def is_your_pick(state):
    if draft_is_complete(state):
        return False

    _, slot = pick_to_round_and_slot(
        state["current_pick"],
        state["teams"],
    )

    return slot == state["your_slot"]

def next_your_pick(state):
    pick = state["current_pick"]
    last_pick = total_draft_picks(state)

    while pick <= last_pick:
        _, slot = pick_to_round_and_slot(
            pick,
            state["teams"],
        )

        if slot == state["your_slot"]:
            return pick

        pick += 1

    return None

def draft_player(
    state,
    player,
):
    if draft_is_complete(state):
        return state
    """
    Record one draft selection in SQLite and update the
    in-memory state supplied by the caller.
    """

    round_number, slot = (
        pick_to_round_and_slot(
            state["current_pick"],
            state["teams"],
        )
    )

    overall_pick = state[
        "current_pick"
    ]

    drafted_entry = {
        "overall_pick": overall_pick,
        "round": round_number,
        "slot": slot,
        "player": player,
    }

    initialise_database()

    with connect() as db:
        session = _ensure_active_session(db)

        db.execute(
            """
            INSERT INTO draft_picks (
                draft_session_id,
                overall_pick,
                round_number,
                slot,
                player_id,
                player_name,
                position,
                is_yours,
                player_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["id"],
                overall_pick,
                round_number,
                slot,
                str(player["id"]),
                player["name"],
                player.get("position"),
                int(
                    slot
                    == state["your_slot"]
                ),
                json.dumps(player),
            ),
        )

        db.execute(
            """
            UPDATE draft_sessions
            SET
                current_pick = ?,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                overall_pick + 1,
                session["id"],
            ),
        )

    state["drafted"].append(
        drafted_entry
    )

    if slot == state["your_slot"]:
        state["your_roster"].append(
            player
        )

    state["current_pick"] += 1

    return state


def undo_last_pick(state):
    """
    Remove the most recent pick from the active draft.
    """

    initialise_database()

    with connect() as db:
        session = _ensure_active_session(db)

        last = db.execute(
            """
            SELECT
                id,
                overall_pick
            FROM draft_picks
            WHERE draft_session_id = ?
            ORDER BY overall_pick DESC
            LIMIT 1
            """,
            (session["id"],),
        ).fetchone()

        if not last:
            return load_state()

        db.execute(
            """
            DELETE FROM draft_picks
            WHERE id = ?
            """,
            (last["id"],),
        )

        db.execute(
            """
            UPDATE draft_sessions
            SET
                current_pick = ?,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                last["overall_pick"],
                session["id"],
            ),
        )

    return load_state()

def create_new_season(
    season,
    teams,
    your_slot,
):
    """
    Create a fresh season and make its first mock active.

    The previous season and all of its sessions remain stored.
    Draft-order names are copied forward as a starting point.
    """

    season = int(season)
    teams = int(teams)
    your_slot = int(your_slot)

    if season < 2000 or season > 2100:
        raise ValueError("Invalid season")

    if teams < 2:
        raise ValueError("Invalid team count")

    if your_slot < 1 or your_slot > teams:
        raise ValueError("Invalid draft slot")

    initialise_database()

    with connect() as db:
        current = _ensure_active_session(db)

        season_id = get_or_create_season(
            db,
            season,
        )

        existing = db.execute(
            """
            SELECT id
            FROM draft_sessions
            WHERE season_id = ?
            LIMIT 1
            """,
            (season_id,),
        ).fetchone()

        if existing:
            raise ValueError(
                "Season already exists"
            )

        old_order = db.execute(
            """
            SELECT
                slot,
                manager_name
            FROM season_draft_order
            WHERE season_id = ?
            ORDER BY slot
            """,
            (current["season_id"],),
        ).fetchall()

        for row in old_order:
            if row["slot"] > teams:
                continue

            db.execute(
                """
                INSERT INTO season_draft_order (
                    season_id,
                    slot,
                    manager_name
                )
                VALUES (?, ?, ?)
                """,
                (
                    season_id,
                    row["slot"],
                    row["manager_name"],
                ),
            )

        _create_draft_session(
            db,
            teams,
            your_slot,
            name=f"{season} initial mock draft",
            season_id=season_id,
        )

    return load_state()

def switch_season(season):
    """
    Make the newest draft session for an existing season active.
    """

    season = int(season)

    initialise_database()

    with connect() as db:
        season_row = db.execute(
            """
            SELECT s.id
            FROM seasons s
            JOIN leagues l
              ON l.id = s.league_id
            WHERE l.league_key = ?
              AND s.season = ?
            """,
            (
                "busy-working",
                season,
            ),
        ).fetchone()

        if not season_row:
            raise ValueError(
                "Season does not exist"
            )

        session = db.execute(
            """
            SELECT id
            FROM draft_sessions
            WHERE season_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (season_row["id"],),
        ).fetchone()

        if not session:
            raise ValueError(
                "Season has no draft sessions"
            )

        db.execute(
            """
            UPDATE draft_sessions
            SET is_active = 0
            WHERE is_active = 1
            """
        )

        db.execute(
            """
            UPDATE draft_sessions
            SET
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (session["id"],),
        )

    return load_state()

def update_settings(
    teams,
    your_slot,
):
    """
    Start a fresh draft session using the requested league
    size and draft slot.

    The previous session remains stored as history.
    """

    teams = int(teams)
    your_slot = int(your_slot)

    if teams < 2:
        raise ValueError(
            "Number of teams must be at least 2"
        )

    if (
        your_slot < 1
        or your_slot > teams
    ):
        raise ValueError(
            "Draft slot must be between 1 "
            "and the number of teams"
        )

    initialise_database()

    with connect() as db:
        current = _ensure_active_session(db)

        _create_draft_session(
            db,
            teams,
            your_slot,
            season_id=current["season_id"],
        )

    return load_state()

import sqlite3
from pathlib import Path
from datetime import date, datetime

BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "fantasy_assistant.db"
BACKUP_DIR = BASE_DIR / "backups"

CURRENT_LEAGUE_KEY = "busy-working"
CURRENT_LEAGUE_NAME = "Busy Working"
CURRENT_YAHOO_LEAGUE_ID = "688636"

SCHEMA_VERSION = 4


class ClosingConnection(sqlite3.Connection):
    """
    SQLite connection that closes when used
    as a context manager.
    """

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        try:
            return super().__exit__(
                exc_type,
                exc_value,
                traceback,
            )
        finally:
            self.close()


def connect():
    """
    Open the Fantasy Assistant SQLite database.
    """

    connection = sqlite3.connect(
        DB_FILE,
        factory=ClosingConnection,
    )
    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection

def backup_database():
    """
    Create a consistent timestamped SQLite backup.

    SQLite's backup API is used rather than copying the
    database file directly so this remains safe even if
    the database is open.
    """

    initialise_database()

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    backup_file = (
        BACKUP_DIR
        / f"fantasy_assistant_{timestamp}.db"
    )

    with connect() as source:
        with sqlite3.connect(backup_file) as destination:
            source.backup(destination)

    return backup_file

def initialise_database():
    """
    Create the database schema if it does not already exist.
    """

    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                yahoo_league_id TEXT
            );

            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                season INTEGER NOT NULL,

                FOREIGN KEY (league_id)
                    REFERENCES leagues(id),

                UNIQUE (league_id, season)
            );

            CREATE TABLE IF NOT EXISTS season_draft_order (
                season_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                manager_name TEXT NOT NULL,

                PRIMARY KEY (
                    season_id,
                    slot
                ),

                FOREIGN KEY (season_id)
                    REFERENCES seasons(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS season_team_identity (
                season_id INTEGER PRIMARY KEY,

                team_name TEXT NOT NULL,

                logo_path TEXT,

                primary_colour TEXT NOT NULL
                    DEFAULT '#041228',

                secondary_colour TEXT NOT NULL
                    DEFAULT '#9A1018',

                accent_colour TEXT NOT NULL
                    DEFAULT '#1685D0',

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (season_id)
                    REFERENCES seasons(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS season_roster (
                season_id INTEGER NOT NULL,

                roster_slot TEXT NOT NULL,
                slot_index INTEGER NOT NULL DEFAULT 1,

                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                position TEXT NOT NULL,

                team TEXT,
                bye_week INTEGER,
                status TEXT,

                source TEXT NOT NULL DEFAULT 'manual',

                acquired_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (
                    season_id,
                    roster_slot,
                    slot_index
                ),

                UNIQUE (
                    season_id,
                    player_id
                ),

                FOREIGN KEY (season_id)
                    REFERENCES seasons(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS draft_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                name TEXT NOT NULL,

                session_type TEXT NOT NULL
                    DEFAULT 'mock'
                    CHECK (
                        session_type IN (
                            'mock',
                            'actual'
                        )
                    ),

                teams INTEGER NOT NULL,
                your_slot INTEGER NOT NULL,
                current_pick INTEGER NOT NULL DEFAULT 1,

                is_active INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (is_active IN (0, 1)),

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (season_id)
                    REFERENCES seasons(id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS
                one_active_draft_session
            ON draft_sessions(is_active)
            WHERE is_active = 1;

            CREATE TABLE IF NOT EXISTS draft_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                draft_session_id INTEGER NOT NULL,

                overall_pick INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                slot INTEGER NOT NULL,

                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                position TEXT,

                is_yours INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (is_yours IN (0, 1)),

                player_json TEXT NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (draft_session_id)
                    REFERENCES draft_sessions(id)
                    ON DELETE CASCADE,

                UNIQUE (
                    draft_session_id,
                    overall_pick
                )
            );
            """
        )

        db.execute(
            """
            INSERT INTO schema_meta (
                key,
                value
            )
            VALUES (
                'schema_version',
                ?
            )
            ON CONFLICT(key)
            DO UPDATE SET
                value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )


def get_or_create_season(
    db,
    season=None,
):
    """
    Return the requested Busy Working season,
    creating it if necessary.

    If no year is supplied, use the current
    calendar year.
    """

    if season is None:
        season = date.today().year

    season = int(season)

    db.execute(
        """
        INSERT INTO leagues (
            league_key,
            name,
            yahoo_league_id
        )
        VALUES (?, ?, ?)
        ON CONFLICT(league_key)
        DO UPDATE SET
            name = excluded.name,
            yahoo_league_id =
                excluded.yahoo_league_id
        """,
        (
            CURRENT_LEAGUE_KEY,
            CURRENT_LEAGUE_NAME,
            CURRENT_YAHOO_LEAGUE_ID,
        ),
    )

    league = db.execute(
        """
        SELECT id
        FROM leagues
        WHERE league_key = ?
        """,
        (CURRENT_LEAGUE_KEY,),
    ).fetchone()

    db.execute(
        """
        INSERT INTO seasons (
            league_id,
            season
        )
        VALUES (?, ?)
        ON CONFLICT(league_id, season)
        DO NOTHING
        """,
        (
            league["id"],
            season,
        ),
    )

    season_row = db.execute(
        """
        SELECT id
        FROM seasons
        WHERE league_id = ?
          AND season = ?
        """,
        (
            league["id"],
            season,
        ),
    ).fetchone()

    return season_row["id"]

def list_seasons():
    """
    Return Busy Working seasons newest first.
    """

    initialise_database()

    with connect() as db:
        rows = db.execute(
            """
            SELECT
                s.id,
                s.season,
                COUNT(ds.id) AS session_count
            FROM seasons s
            JOIN leagues l
              ON l.id = s.league_id
            LEFT JOIN draft_sessions ds
              ON ds.season_id = s.id
            WHERE l.league_key = ?
            GROUP BY
                s.id,
                s.season
            ORDER BY s.season DESC
            """,
            (CURRENT_LEAGUE_KEY,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "season": row["season"],
            "session_count": row["session_count"],
        }
        for row in rows
    ]

def load_current_draft_order():
    """
    Return the draft order for the current season as:

        {
            1: "Chris",
            2: "Andrew",
            ...
        }
    """

    initialise_database()

    with connect() as db:
        session = active_draft_session(db)

        if session:
            season_id = session["season_id"]
        else:
            season_id = get_or_create_season(db)

        rows = db.execute(
            """
            SELECT
                slot,
                manager_name
            FROM season_draft_order
            WHERE season_id = ?
            ORDER BY slot
            """,
            (season_id,),
        ).fetchall()

    return {
        row["slot"]: row["manager_name"]
        for row in rows
    }


def save_current_draft_order(order):
    """
    Replace the current season's draft order.
    """

    initialise_database()

    with connect() as db:
        session = active_draft_session(db)

        if session:
            season_id = session["season_id"]
        else:
            season_id = get_or_create_season(db)

        db.execute(
            """
            DELETE FROM season_draft_order
            WHERE season_id = ?
            """,
            (season_id,),
        )

        for slot, manager_name in sorted(
            order.items()
        ):
            manager_name = str(
                manager_name
            ).strip()

            if not manager_name:
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
                    int(slot),
                    manager_name,
                ),
            )

def load_team_identity(season=None):
    """
    Return the team identity for a Busy Working season.
    """

    initialise_database()

    with connect() as db:
        season_id = get_or_create_season(
            db,
            season,
        )

        row = db.execute(
            """
            SELECT
                team_name,
                logo_path,
                primary_colour,
                secondary_colour,
                accent_colour,
                updated_at
            FROM season_team_identity
            WHERE season_id = ?
            """,
            (season_id,),
        ).fetchone()

    if row is None:
        return {
            "team_name": "My Team",
            "logo_path": None,
            "primary_colour": "#041228",
            "secondary_colour": "#9A1018",
            "accent_colour": "#1685D0",
            "updated_at": None,
        }

    return dict(row)


def save_team_identity(
    team_name,
    logo_path=None,
    primary_colour="#041228",
    secondary_colour="#9A1018",
    accent_colour="#1685D0",
    season=None,
):
    """
    Create or replace the team identity for a season.
    """

    initialise_database()

    with connect() as db:
        season_id = get_or_create_season(
            db,
            season,
        )

        db.execute(
            """
            INSERT INTO season_team_identity (
                season_id,
                team_name,
                logo_path,
                primary_colour,
                secondary_colour,
                accent_colour,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(season_id)
            DO UPDATE SET
                team_name = excluded.team_name,
                logo_path = excluded.logo_path,
                primary_colour = excluded.primary_colour,
                secondary_colour = excluded.secondary_colour,
                accent_colour = excluded.accent_colour,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                season_id,
                team_name,
                logo_path,
                primary_colour,
                secondary_colour,
                accent_colour,
            ),
        )


def load_season_roster(season=None):
    """
    Return the current roster for a Busy Working season.

    Rows are ordered in normal fantasy-roster order.
    """

    initialise_database()

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

    with connect() as db:
        season_id = get_or_create_season(
            db,
            season,
        )

        rows = db.execute(
            """
            SELECT
                roster_slot,
                slot_index,
                player_id,
                player_name,
                position,
                team,
                bye_week,
                status,
                source,
                acquired_at,
                updated_at
            FROM season_roster
            WHERE season_id = ?
            """,
            (season_id,),
        ).fetchall()

    roster = [
        dict(row)
        for row in rows
    ]

    roster.sort(
        key=lambda player: (
            slot_order.get(
                player["roster_slot"],
                99,
            ),
            player["slot_index"],
        )
    )

    return roster


def replace_season_roster(
    players,
    season=None,
):
    """
    Replace the complete roster for a Busy Working season.

    Intended for initial seeding, manual roster maintenance,
    and future Yahoo synchronisation.
    """

    initialise_database()

    with connect() as db:
        season_id = get_or_create_season(
            db,
            season,
        )

        db.execute(
            """
            DELETE FROM season_roster
            WHERE season_id = ?
            """,
            (season_id,),
        )

        for player in players:
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
                    player["roster_slot"],
                    player.get("slot_index", 1),
                    str(player["player_id"]),
                    player["player_name"],
                    player["position"],
                    player.get("team"),
                    player.get("bye_week"),
                    player.get("status"),
                    player.get("source", "manual"),
                ),
            )


def active_draft_session(db):
    return db.execute(
        """
        SELECT *
        FROM draft_sessions
        WHERE is_active = 1
        """
    ).fetchone()

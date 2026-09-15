from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json


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

UK_TIME = ZoneInfo(
    "Europe/London"
)

GAME_FIELDS = (
    "game_display",
    "game_day",
    "game_time",
    "opponent",
    "home_away",
)


def week_1_thursday(season):
    september_1 = date(
        season,
        9,
        1,
    )

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


def current_fantasy_week(
    season=None,
    today=None,
):
    if today is None:
        today = datetime.now(
            UK_TIME
        ).date()

    if season is None:
        season = (
            today.year - 1
            if today.month <= 2
            else today.year
        )

    week_1_start = (
        week_1_thursday(season)
        - timedelta(days=2)
    )

    if today < week_1_start:
        return 1

    week = (
        (
            today
            - week_1_start
        ).days
        // 7
        + 1
    )

    return max(
        1,
        min(18, week),
    )


def normalise_week(
    player,
    week=None,
):
    """
    Present the selected Yahoo week through the legacy
    fields still consumed by the weekly and transaction
    engines.

    The raw imported week_N_* fields are retained. The
    week_1_projection/week_1_actual aliases are temporary
    compatibility fields until the engines are fully
    week-aware themselves.
    """

    if week is None:
        week = current_fantasy_week()

    output = dict(player)
    prefix = f"week_{week}"

    current_projection = player.get(
        f"{prefix}_projection"
    )

    current_actual = player.get(
        f"{prefix}_actual"
    )

    output["current_week"] = week
    output[
        "current_week_projection"
    ] = current_projection
    output[
        "current_week_actual"
    ] = current_actual

    # Compatibility aliases for code that still calls
    # these Week 1 names. In Week 2+, they intentionally
    # represent the selected/current fantasy week.
    output[
        "week_1_projection"
    ] = current_projection
    output[
        "week_1_actual"
    ] = current_actual

    for field in GAME_FIELDS:
        output[field] = player.get(
            f"{prefix}_{field}"
        )

    return output


class YahooDataProvider:
    """
    Current Yahoo data source for the application.

    Today:
        loads the manual Yahoo HTML import JSON.

    Later:
        refresh() will fetch live Yahoo Fantasy API
        data and keep the resulting snapshot in memory.

    Yahoo-derived data should not be persisted here.
    """

    def __init__(self):
        self._roster = []
        self._available = []

        self._loaded_at = None
        self._source = None
        self._captured_at = None

    @staticmethod
    def _load_json(path):
        return json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

    def refresh(self):
        """
        Temporary fallback implementation.

        Reload the most recent manually imported
        Yahoo snapshot from disk.
        """

        self._roster = self._load_json(
            MY_TEAM_FILE
        )

        self._available = self._load_json(
            AVAILABLE_FILE
        )

        self._loaded_at = (
            datetime.now(
                timezone.utc
            )
        )

        self._captured_at = (
            self._manual_snapshot_time()
        )

        self._source = (
            "manual_import"
        )

    def ensure_loaded(self):
        if self._loaded_at is None:
            self.refresh()

    def get_roster(self):
        self.ensure_loaded()

        week = current_fantasy_week()

        return [
            normalise_week(
                player,
                week,
            )
            for player in self._roster
        ]

    def get_available_players(self):
        self.ensure_loaded()

        week = current_fantasy_week()

        return [
            normalise_week(
                player,
                week,
            )
            for player in self._available
        ]

    @staticmethod
    def _format_timestamp(value):
        if value is None:
            return None

        local = value.astimezone()

        return local.strftime(
            "%-d %b at %H:%M %Z"
        )

    def get_status(self):
        self.ensure_loaded()

        return {
            "source":
                self._source,

            "loaded_at":
                self._loaded_at,

            "roster_players":
                len(self._roster),

            "available_players":
                len(self._available),

            "current_week":
                current_fantasy_week(),

            "captured_at":
                self._captured_at,

            "captured_at_display":
                self._format_timestamp(
                    self._captured_at
                ),

            "loaded_at_display":
                self._format_timestamp(
                    self._loaded_at
                ),
        }

    def _manual_snapshot_time(self):
        source_files = list(
            DATA_DIR.glob(
                "Yahoo_*.html"
            )
        )

        if not source_files:
            return None

        newest = max(
            path.stat().st_mtime
            for path in source_files
        )

        return datetime.fromtimestamp(
            newest,
            timezone.utc,
        )


yahoo_provider = YahooDataProvider()


def enrich_local_roster(
    local_roster,
):
    """
    Combine our local roster-slot state with
    the current Yahoo player snapshot.

    Local data remains authoritative for roster layout
    and identity. Yahoo supplies status, matchup,
    projections, actual points and Yahoo player IDs.
    """

    yahoo_roster = (
        yahoo_provider
        .get_roster()
    )

    by_name = {
        player["name"].lower():
            player
        for player in yahoo_roster
    }

    enriched = []

    local_authoritative = {
        "name",
        "player_name",
        "player_id",
        "team",
        "position",
        "roster_slot",
        "slot_index",
    }

    for local_player in local_roster:
        player = dict(
            local_player
        )

        player["name"] = (
            local_player["player_name"]
        )

        yahoo_player = by_name.get(
            local_player[
                "player_name"
            ].lower()
        )

        # Defence names differ:
        # "Houston Texans" locally,
        # "Texans" in Yahoo.
        if (
            yahoo_player is None
            and local_player[
                "position"
            ] in {"DEF", "DST"}
        ):
            for candidate in yahoo_roster:
                if (
                    candidate[
                        "position"
                    ] == "DST"
                    and candidate.get(
                        "team"
                    )
                    == local_player.get(
                        "team"
                    )
                ):
                    yahoo_player = (
                        candidate
                    )
                    break

        if yahoo_player:
            for key, value in (
                yahoo_player.items()
            ):
                if key in local_authoritative:
                    continue

                player[key] = value

        enriched.append(
            player
        )

    return enriched


def get_yahoo_provider_status():
    return yahoo_provider.get_status()

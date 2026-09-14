from pathlib import Path
from datetime import datetime, timezone
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

        return [
            dict(player)
            for player in self._roster
        ]

    def get_available_players(self):
        self.ensure_loaded()

        return [
            dict(player)
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
                "Yahoo_MyTeam_*.html"
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

    Local data remains authoritative for:
        roster_slot
        slot_index

    Yahoo remains authoritative for:
        status
        matchup
        projections
        Yahoo player ID
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

    for local_player in local_roster:
        player = dict(
            local_player
        )

        # Keep the local database field, but also
        # expose the normalized provider-style name
        # expected by the weekly/transaction engines.
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
            player[
                "yahoo_player_id"
            ] = yahoo_player.get(
                "yahoo_player_id"
            )

            player["status"] = (
                yahoo_player.get(
                    "status"
                )
            )

            player[
                "game_display"
            ] = yahoo_player.get(
                "game_display"
            )

            player["game_day"] = (
                yahoo_player.get(
                    "game_day"
                )
            )

            player["game_time"] = (
                yahoo_player.get(
                    "game_time"
                )
            )

            player["opponent"] = (
                yahoo_player.get(
                    "opponent"
                )
            )

            player["home_away"] = (
                yahoo_player.get(
                    "home_away"
                )
            )

            player[
                "week_1_projection"
            ] = yahoo_player.get(
                "week_1_projection"
            )

            player[
                "week_1_actual"
            ] = yahoo_player.get(
                "week_1_actual"
            )

            player[
                "week_2_projection"
            ] = yahoo_player.get(
                "week_2_projection"
            )

            player[
                "next_4_weeks_projection"
            ] = yahoo_player.get(
                "next_4_weeks_projection"
            )

        enriched.append(
            player
        )

    return enriched


def get_yahoo_provider_status():
    return yahoo_provider.get_status()

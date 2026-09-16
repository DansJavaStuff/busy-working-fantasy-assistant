from pathlib import Path
from datetime import datetime, timezone
import json

from fantasy_calendar import current_fantasy_week
from yahoo_normalizer import player_for_week


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

NORMALIZED_FILE = (
    DATA_DIR
    / "yahoo_normalized.json"
)

MY_TEAM_FILE = (
    DATA_DIR
    / "yahoo_my_team.json"
)

AVAILABLE_FILE = (
    DATA_DIR
    / "yahoo_available_players.json"
)

GAME_FIELDS = (
    "game_display",
    "game_day",
    "game_time",
    "opponent",
    "home_away",
)


def normalise_week(
    player,
    week=None,
):
    """Expose one player's selected scoring week to application callers.

    The canonical source is ``player['weeks'][week]``. Current-week values
    are exposed explicitly as ``current_week_projection`` and
    ``current_week_actual``. Historical week-specific fields remain untouched.

    Legacy imported players are still accepted during the transition so a
    missing normalized file does not make the fallback path unusable.
    """

    if week is None:
        week = current_fantasy_week()

    output = dict(player)

    weeks = player.get("weeks")

    if isinstance(weeks, dict):
        week_data = player_for_week(
            player,
            week,
        )

        current_projection = (
            week_data.get("projection")
        )

        current_actual = (
            week_data.get("actual")
        )

        game = week_data.get("game") or {}

        output["game_display"] = (
            game.get("display")
        )
        output["game_day"] = (
            game.get("day")
        )
        output["game_time"] = (
            game.get("time")
        )
        output["opponent"] = (
            game.get("opponent")
        )
        output["home_away"] = (
            game.get("home_away")
        )

    else:
        # Transitional support for the previous imported JSON format.
        prefix = f"week_{week}"

        current_projection = player.get(
            f"{prefix}_projection"
        )

        current_actual = player.get(
            f"{prefix}_actual"
        )

        for field in GAME_FIELDS:
            output[field] = player.get(
                f"{prefix}_{field}"
            )

    output["current_week"] = week
    output[
        "current_week_projection"
    ] = current_projection
    output[
        "current_week_actual"
    ] = current_actual

    return output


class YahooDataProvider:
    """Provide one normalized Yahoo dataset to the application.

    The provider is intentionally source-agnostic. Today the normalized file
    is produced by the emergency HTML fallback importer. The Yahoo API path
    will produce the same schema, allowing Weekly and Transactions to consume
    identical player objects regardless of source.
    """

    def __init__(self):
        self._roster = []
        self._available = []
        self._dataset = None

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

    def _load_normalized(self):
        dataset = self._load_json(
            NORMALIZED_FILE
        )

        players = dataset.get(
            "players",
            {},
        )

        self._roster = [
            players[player_id]
            for player_id
            in dataset.get(
                "my_team_ids",
                [],
            )
            if player_id in players
        ]

        self._available = [
            players[player_id]
            for player_id
            in dataset.get(
                "available_ids",
                [],
            )
            if player_id in players
        ]

        self._dataset = dataset
        self._source = dataset.get(
            "source"
        ) or "normalized_snapshot"

    def _load_legacy(self):
        self._roster = self._load_json(
            MY_TEAM_FILE
        )

        self._available = self._load_json(
            AVAILABLE_FILE
        )

        self._dataset = None
        self._source = "manual_import_legacy"

    def refresh(self):
        """Reload the latest normalized Yahoo snapshot from disk.

        During migration, fall back to the two legacy JSON files if the
        normalized snapshot has not yet been generated.
        """

        if NORMALIZED_FILE.exists():
            self._load_normalized()
        else:
            self._load_legacy()

        self._loaded_at = (
            datetime.now(
                timezone.utc
            )
        )

        self._captured_at = (
            self._manual_snapshot_time()
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

        weeks = []

        if self._dataset:
            week_values = set()

            for player in self._dataset.get(
                "players",
                {},
            ).values():
                week_values.update(
                    str(value)
                    for value in player.get(
                        "weeks",
                        {},
                    )
                )

            weeks = sorted(
                (
                    int(value)
                    for value in week_values
                    if str(value).isdigit()
                )
            )

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

            "weeks":
                weeks,

            "schema_version":
                (
                    self._dataset.get(
                        "schema_version"
                    )
                    if self._dataset
                    else None
                ),

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
    """Combine local roster layout with the current Yahoo snapshot.

    Local roster membership is authoritative. A recently added player can
    still appear in Yahoo's saved available-player snapshot until the next
    Yahoo refresh, so enrichment searches both snapshot membership lists.
    """

    yahoo_players = (
        yahoo_provider.get_roster()
        + yahoo_provider.get_available_players()
    )

    by_name = {
        player["name"].lower():
            player
        for player in yahoo_players
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

        # Defence names can differ locally (for example "Tampa Bay
        # Buccaneers") from Yahoo's shorter display name ("Buccaneers").
        if (
            yahoo_player is None
            and local_player[
                "position"
            ] in {"DEF", "DST"}
        ):
            for candidate in yahoo_players:
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
                    yahoo_player = candidate
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

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import yahoo_provider


class YahooProviderNormalizedTests(TestCase):
    def test_provider_reads_normalized_membership_and_week_data(self):
        dataset = {
            "schema_version": 1,
            "source": "manual_html",
            "players": {
                "1": {
                    "yahoo_player_id": "1",
                    "name": "Roster Player",
                    "team": "BUF",
                    "position": "QB",
                    "weeks": {
                        "2": {
                            "projection": 24.5,
                            "actual": None,
                            "game": {
                                "display": "Sun 1:00 pm vs MIA",
                                "day": "Sun",
                                "time": "1:00 pm",
                                "opponent": "MIA",
                                "home_away": "home",
                            },
                        }
                    },
                    "next_4_weeks_projection": 90.0,
                },
                "2": {
                    "yahoo_player_id": "2",
                    "name": "Available Player",
                    "team": "KC",
                    "position": "WR",
                    "weeks": {
                        "2": {
                            "projection": 11.2,
                        }
                    },
                    "next_4_weeks_projection": 45.0,
                },
            },
            "my_team_ids": ["1"],
            "available_ids": ["2"],
        }

        with TemporaryDirectory() as directory:
            root = Path(directory)
            normalized = root / "yahoo_normalized.json"
            normalized.write_text(
                json.dumps(dataset),
                encoding="utf-8",
            )

            provider = yahoo_provider.YahooDataProvider()

            with patch.object(
                yahoo_provider,
                "NORMALIZED_FILE",
                normalized,
            ), patch.object(
                yahoo_provider,
                "DATA_DIR",
                root,
            ), patch.object(
                yahoo_provider,
                "current_fantasy_week",
                return_value=2,
            ):
                roster = provider.get_roster()
                available = provider.get_available_players()
                status = provider.get_status()

        self.assertEqual(len(roster), 1)
        self.assertEqual(len(available), 1)

        player = roster[0]
        self.assertEqual(player["current_week_projection"], 24.5)
        self.assertIsNone(player["current_week_actual"])
        self.assertEqual(player["week_1_projection"], 24.5)
        self.assertIsNone(player["week_1_actual"])
        self.assertEqual(player["game_day"], "Sun")
        self.assertEqual(player["opponent"], "MIA")
        self.assertEqual(player["next_4_weeks_projection"], 90.0)

        self.assertEqual(status["source"], "manual_html")
        self.assertEqual(status["schema_version"], 1)
        self.assertEqual(status["weeks"], [2])

    def test_normalise_week_supports_future_week_map(self):
        player = {
            "name": "Future Player",
            "weeks": {
                "17": {
                    "projection": 18.4,
                    "actual": None,
                }
            },
        }

        result = yahoo_provider.normalise_week(
            player,
            17,
        )

        self.assertEqual(result["current_week"], 17)
        self.assertEqual(result["current_week_projection"], 18.4)
        self.assertEqual(result["week_1_projection"], 18.4)

    def test_legacy_player_shape_still_works_during_migration(self):
        player = {
            "name": "Legacy Player",
            "week_2_projection": 13.1,
            "week_2_actual": None,
            "week_2_game_day": "Mon",
            "week_2_game_time": "8:15 pm",
            "week_2_opponent": "DAL",
            "week_2_home_away": "away",
        }

        result = yahoo_provider.normalise_week(
            player,
            2,
        )

        self.assertEqual(result["current_week_projection"], 13.1)
        self.assertEqual(result["game_day"], "Mon")
        self.assertEqual(result["opponent"], "DAL")

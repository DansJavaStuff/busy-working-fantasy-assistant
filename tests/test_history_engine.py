from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import database
from history_engine import build_history_week


class HistoryEngineTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()

        self.db_path = (
            Path(self.temp_dir.name)
            / "test_fantasy_assistant.db"
        )

        self.db_patch = mock.patch.object(
            database,
            "DB_FILE",
            self.db_path,
        )

        self.db_patch.start()

        database.initialise_database()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_history_joins_roster_to_player_week_scores(self):
        roster = [
            {
                "roster_slot": "QB",
                "slot_index": 1,
                "player_id": "1",
                "player_name": "Starter QB",
                "position": "QB",
                "team": "BUF",
            },
            {
                "roster_slot": "BN",
                "slot_index": 1,
                "player_id": "2",
                "player_name": "Bench WR",
                "position": "WR",
                "team": "KC",
            },
        ]

        database.snapshot_season_roster(
            1,
            season=2026,
            roster=roster,
        )

        database.upsert_player_week_history(
            {
                "1": {
                    "name": "Starter QB",
                    "position": "QB",
                    "team": "BUF",
                    "weeks": {
                        "1": {
                            "projection": 20.0,
                            "actual": 30.0,
                        }
                    },
                },
                "2": {
                    "name": "Bench WR",
                    "position": "WR",
                    "team": "KC",
                    "weeks": {
                        "1": {
                            "projection": 10.0,
                            "actual": 15.0,
                        }
                    },
                },
            },
            season=2026,
        )

        history = build_history_week(
            1,
            season=2026,
        )

        self.assertEqual(
            history["roster_count"],
            2,
        )
        self.assertEqual(
            history["starter_projection"],
            20.0,
        )
        self.assertEqual(
            history["starter_actual"],
            30.0,
        )
        self.assertEqual(
            history["bench_actual"],
            15.0,
        )
        self.assertTrue(
            history["complete_actuals"]
        )
        self.assertEqual(
            history["rows"][0]["variance"],
            10.0,
        )

    def test_incomplete_week_does_not_fake_missing_actual(self):
        database.snapshot_season_roster(
            3,
            season=2026,
            roster=[
                {
                    "roster_slot": "QB",
                    "slot_index": 1,
                    "player_id": "1",
                    "player_name": "Starter QB",
                    "position": "QB",
                    "team": "BUF",
                },
                {
                    "roster_slot": "RB",
                    "slot_index": 1,
                    "player_id": "2",
                    "player_name": "Starter RB",
                    "position": "RB",
                    "team": "DET",
                },
            ],
        )

        database.upsert_player_week_history(
            {
                "1": {
                    "name": "Starter QB",
                    "position": "QB",
                    "team": "BUF",
                    "weeks": {
                        "3": {
                            "projection": 20.0,
                            "actual": 25.0,
                        }
                    },
                },
                "2": {
                    "name": "Starter RB",
                    "position": "RB",
                    "team": "DET",
                    "weeks": {
                        "3": {
                            "projection": 12.0,
                            "actual": None,
                        }
                    },
                },
            },
            season=2026,
        )

        history = build_history_week(
            3,
            season=2026,
        )

        self.assertFalse(
            history["complete_actuals"]
        )
        self.assertEqual(
            history["starter_actual"],
            25.0,
        )
        self.assertEqual(
            history["starter_actual_count"],
            1,
        )
        self.assertIsNone(
            history["rows"][1]["variance"]
        )


if __name__ == "__main__":
    import unittest
    unittest.main()

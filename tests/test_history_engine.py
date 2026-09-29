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

    def test_submitted_lineup_overrides_reconstructed_slots(self):
        database.snapshot_season_roster(
            3,
            season=2026,
            roster=[
                {
                    "roster_slot": "WR",
                    "slot_index": 1,
                    "player_id": "puka",
                    "player_name": "Puka Nacua",
                    "position": "WR",
                    "team": "LAR",
                },
                {
                    "roster_slot": "BN",
                    "slot_index": 1,
                    "player_id": "pollard",
                    "player_name": "Tony Pollard",
                    "position": "RB",
                    "team": "TEN",
                },
            ],
        )

        database.replace_week_lineup(
            3,
            [
                {
                    "player_id": "puka",
                    "player_name": "Puka Nacua",
                    "position": "WR",
                    "lineup_slot": "BN",
                    "slot_index": 1,
                },
                {
                    "player_id": "pollard",
                    "player_name": "Tony Pollard",
                    "position": "RB",
                    "lineup_slot": "FLEX",
                    "slot_index": 1,
                },
            ],
            season=2026,
        )

        database.upsert_player_week_history(
            {
                "puka": {
                    "name": "Puka Nacua",
                    "position": "WR",
                    "team": "LAR",
                    "weeks": {
                        "3": {
                            "projection": 0.0,
                            "actual": None,
                        }
                    },
                },
                "pollard": {
                    "name": "Tony Pollard",
                    "position": "RB",
                    "team": "TEN",
                    "weeks": {
                        "3": {
                            "projection": 10.0,
                            "actual": 11.6,
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

        by_id = {
            row["player_id"]: row
            for row in history["rows"]
        }

        self.assertEqual(
            by_id["puka"]["roster_slot"],
            "BN",
        )
        self.assertFalse(
            by_id["puka"]["is_starter"]
        )
        self.assertEqual(
            by_id["pollard"]["roster_slot"],
            "FLEX",
        )
        self.assertTrue(
            by_id["pollard"]["is_starter"]
        )
        self.assertEqual(
            history["starter_actual"],
            11.6,
        )
        self.assertTrue(
            history[
                "submitted_lineup_available"
            ]
        )

    def test_completed_week_calculates_best_legal_actual_lineup(self):
        database.snapshot_season_roster(
            1,
            season=2026,
            roster=[
                {"roster_slot":"QB","slot_index":1,"player_id":"qb1","player_name":"QB One","position":"QB","team":"A"},
                {"roster_slot":"BN","slot_index":1,"player_id":"qb2","player_name":"QB Two","position":"QB","team":"B"},
                {"roster_slot":"RB","slot_index":1,"player_id":"rb1","player_name":"RB One","position":"RB","team":"A"},
                {"roster_slot":"RB","slot_index":2,"player_id":"rb2","player_name":"RB Two","position":"RB","team":"B"},
                {"roster_slot":"BN","slot_index":2,"player_id":"rb3","player_name":"RB Three","position":"RB","team":"C"},
                {"roster_slot":"WR","slot_index":1,"player_id":"wr1","player_name":"WR One","position":"WR","team":"A"},
                {"roster_slot":"WR","slot_index":2,"player_id":"wr2","player_name":"WR Two","position":"WR","team":"B"},
                {"roster_slot":"BN","slot_index":3,"player_id":"wr3","player_name":"WR Three","position":"WR","team":"C"},
                {"roster_slot":"TE","slot_index":1,"player_id":"te1","player_name":"TE One","position":"TE","team":"A"},
                {"roster_slot":"FLEX","slot_index":1,"player_id":"flex1","player_name":"Flex RB","position":"RB","team":"D"},
                {"roster_slot":"K","slot_index":1,"player_id":"k1","player_name":"K One","position":"K","team":"A"},
                {"roster_slot":"DEF","slot_index":1,"player_id":"d1","player_name":"DST One","position":"DST","team":"A"},
            ],
        )

        players = {}

        actuals = {
            "qb1": 10.0,
            "qb2": 20.0,
            "rb1": 8.0,
            "rb2": 9.0,
            "rb3": 18.0,
            "wr1": 7.0,
            "wr2": 6.0,
            "wr3": 16.0,
            "te1": 5.0,
            "flex1": 4.0,
            "k1": 3.0,
            "d1": 2.0,
        }

        positions = {
            "qb1": "QB",
            "qb2": "QB",
            "rb1": "RB",
            "rb2": "RB",
            "rb3": "RB",
            "wr1": "WR",
            "wr2": "WR",
            "wr3": "WR",
            "te1": "TE",
            "flex1": "RB",
            "k1": "K",
            "d1": "DST",
        }

        for player_id, actual in actuals.items():
            players[player_id] = {
                "name": player_id,
                "position": positions[player_id],
                "team": "X",
                "weeks": {
                    "1": {
                        "projection": actual,
                        "actual": actual,
                    }
                },
            }

        database.upsert_player_week_history(
            players,
            season=2026,
        )

        history = build_history_week(
            1,
            season=2026,
        )

        analysis = history[
            "optimal_analysis"
        ]

        self.assertTrue(
            analysis["complete"]
        )
        self.assertGreater(
            analysis["optimal_actual"],
            history["starter_actual"],
        )

        would_start_ids = {
            item["player"]["player_id"]
            for item in analysis["would_start"]
        }

        self.assertEqual(
            would_start_ids,
            {
                "qb2",
                "rb3",
                "wr3",
            },
        )

    def test_optimal_analysis_waits_for_complete_active_roster_actuals(self):
        database.snapshot_season_roster(
            3,
            season=2026,
            roster=[
                {"roster_slot":"QB","slot_index":1,"player_id":"qb","player_name":"QB","position":"QB","team":"A"},
                {"roster_slot":"BN","slot_index":1,"player_id":"wr","player_name":"WR","position":"WR","team":"B"},
                {"roster_slot":"IR","slot_index":1,"player_id":"ir","player_name":"IR","position":"WR","team":"C"},
            ],
        )

        database.upsert_player_week_history(
            {
                "qb": {
                    "name": "QB",
                    "position": "QB",
                    "team": "A",
                    "weeks": {
                        "3": {
                            "projection": 20.0,
                            "actual": 20.0,
                        }
                    },
                },
                "wr": {
                    "name": "WR",
                    "position": "WR",
                    "team": "B",
                    "weeks": {
                        "3": {
                            "projection": 10.0,
                            "actual": None,
                        }
                    },
                },
                "ir": {
                    "name": "IR",
                    "position": "WR",
                    "team": "C",
                    "weeks": {
                        "3": {
                            "projection": 0.0,
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
            history[
                "optimal_analysis"
            ]["complete"]
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

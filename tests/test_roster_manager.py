import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import database
import roster_manager
import history_reconstruction


class RosterManagerTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()

        self.db_path = (
            Path(self.temp_dir.name)
            / "test_fantasy_assistant.db"
        )

        self.db_file_patch = mock.patch.object(
            database,
            "DB_FILE",
            self.db_path,
        )

        self.db_file_patch.start()

        database.initialise_database()

        self.seed_roster()

    def tearDown(self):
        self.db_file_patch.stop()
        self.temp_dir.cleanup()

    def seed_roster(self):
        roster = [
            {
                "roster_slot": "QB",
                "slot_index": 1,
                "player_id": "qb1",
                "player_name": "Quarterback One",
                "position": "QB",
            },
            {
                "roster_slot": "RB",
                "slot_index": 1,
                "player_id": "rb1",
                "player_name": "Running Back One",
                "position": "RB",
            },
            {
                "roster_slot": "RB",
                "slot_index": 2,
                "player_id": "rb2",
                "player_name": "Running Back Two",
                "position": "RB",
            },
            {
                "roster_slot": "WR",
                "slot_index": 1,
                "player_id": "wr1",
                "player_name": "Receiver One",
                "position": "WR",
            },
            {
                "roster_slot": "WR",
                "slot_index": 2,
                "player_id": "wr2",
                "player_name": "Receiver Two",
                "position": "WR",
            },
            {
                "roster_slot": "TE",
                "slot_index": 1,
                "player_id": "te1",
                "player_name": "Tight End One",
                "position": "TE",
            },
            {
                "roster_slot": "FLEX",
                "slot_index": 1,
                "player_id": "wr3",
                "player_name": "Receiver Three",
                "position": "WR",
            },
            {
                "roster_slot": "K",
                "slot_index": 1,
                "player_id": "k1",
                "player_name": "Kicker One",
                "position": "K",
            },
            {
                "roster_slot": "DEF",
                "slot_index": 1,
                "player_id": "dst1",
                "player_name": "Defence One",
                "position": "DST",
            },
            {
                "roster_slot": "BN",
                "slot_index": 1,
                "player_id": "bench-rb",
                "player_name": "Bench Running Back",
                "position": "RB",
            },
            {
                "roster_slot": "BN",
                "slot_index": 2,
                "player_id": "bench-wr",
                "player_name": "Bench Receiver",
                "position": "WR",
            },
        ]

        database.replace_season_roster(
            roster,
            season=2026,
        )

    def roster_by_id(self):
        return {
            player["player_id"]: player
            for player
            in database.load_season_roster(2026)
        }

    def test_flex_accepts_rb_wr_te(self):
        self.assertTrue(
            roster_manager.player_can_fill_slot(
                "RB",
                "FLEX",
            )
        )

        self.assertTrue(
            roster_manager.player_can_fill_slot(
                "WR",
                "FLEX",
            )
        )

        self.assertTrue(
            roster_manager.player_can_fill_slot(
                "TE",
                "FLEX",
            )
        )

        self.assertFalse(
            roster_manager.player_can_fill_slot(
                "QB",
                "FLEX",
            )
        )

    def test_dst_can_fill_def_slot(self):
        self.assertTrue(
            roster_manager.player_can_fill_slot(
                "DST",
                "DEF",
            )
        )

    def test_illegal_swap_is_rejected(self):
        with self.assertRaises(ValueError):
            roster_manager.move_roster_player(
                "rb1",
                "FLEX",
                1,
                season=2026,
            )

        roster = self.roster_by_id()

        self.assertEqual(
            roster["rb1"]["roster_slot"],
            "RB",
        )

        self.assertEqual(
            roster["wr3"]["roster_slot"],
            "FLEX",
        )

    def test_legal_swap_moves_both_players(self):
        roster_manager.move_roster_player(
            "wr1",
            "FLEX",
            1,
            season=2026,
        )

        roster = self.roster_by_id()

        self.assertEqual(
            roster["wr1"]["roster_slot"],
            "FLEX",
        )

        self.assertEqual(
            roster["wr3"]["roster_slot"],
            "WR",
        )

        self.assertEqual(
            roster["wr3"]["slot_index"],
            1,
        )

    def test_starter_can_move_to_empty_bench(self):
        roster_manager.move_roster_player(
            "rb1",
            "BN",
            None,
            season=2026,
        )

        roster = self.roster_by_id()

        self.assertEqual(
            roster["rb1"]["roster_slot"],
            "BN",
        )

        self.assertEqual(
            roster["rb1"]["slot_index"],
            3,
        )

    def test_bench_player_can_fill_empty_starter_slot(self):
        roster_manager.move_roster_player(
            "rb1",
            "BN",
            None,
            season=2026,
        )

        roster_manager.move_roster_player(
            "bench-rb",
            "RB",
            1,
            season=2026,
        )

        roster = self.roster_by_id()

        self.assertEqual(
            roster["bench-rb"]["roster_slot"],
            "RB",
        )

        self.assertEqual(
            roster["bench-rb"]["slot_index"],
            1,
        )

    def test_bench_is_renumbered_after_move(self):
        roster_manager.move_roster_player(
            "bench-rb",
            "RB",
            1,
            season=2026,
        )

        roster = self.roster_by_id()

        self.assertEqual(
            roster["rb1"]["roster_slot"],
            "BN",
        )

        self.assertEqual(
            roster["rb1"]["slot_index"],
            1,
        )

        self.assertEqual(
            roster["bench-wr"]["slot_index"],
            2,
        )

    def test_replace_player_keeps_roster_slot(self):
        roster_manager.replace_roster_player(
            "dst1",
            {
                "player_id": "dst2",
                "player_name": "Defence Two",
                "position": "DST",
                "team": "DET",
                "bye_week": 6,
            },
            season=2026,
        )

        roster = self.roster_by_id()

        self.assertNotIn(
            "dst1",
            roster,
        )

        self.assertEqual(
            roster["dst2"]["roster_slot"],
            "DEF",
        )

        self.assertEqual(
            roster["dst2"]["slot_index"],
            1,
        )

        self.assertEqual(
            roster["dst2"]["team"],
            "DET",
        )

        self.assertEqual(
            roster["dst2"]["bye_week"],
            6,
        )

    def test_illegal_replacement_rolls_back(self):
        with self.assertRaises(ValueError):
            roster_manager.replace_roster_player(
                "dst1",
                {
                    "player_id": "qb2",
                    "player_name": "Quarterback Two",
                    "position": "QB",
                    "team": "TEST",
                },
                season=2026,
            )

        roster = self.roster_by_id()

        self.assertIn(
            "dst1",
            roster,
        )

        self.assertNotIn(
            "qb2",
            roster,
        )

    def test_player_week_history_preserves_actuals_and_projections(self):
        players = {
            "k1": {
                "name": "Kicker One",
                "position": "K",
                "team": "LAC",
                "weeks": {
                    "1": {
                        "projection": 7.0,
                        "actual": 9.0,
                    },
                    "2": {
                        "projection": 6.5,
                        "actual": 4.0,
                    },
                },
            }
        }

        database.upsert_player_week_history(
            players,
            season=2026,
        )

        week_one = (
            database.load_player_week_history(
                1,
                season=2026,
            )
        )
        week_two = (
            database.load_player_week_history(
                2,
                season=2026,
            )
        )

        self.assertEqual(
            week_one[0]["actual"],
            9.0,
        )
        self.assertEqual(
            week_one[0]["projection"],
            7.0,
        )
        self.assertEqual(
            week_two[0]["actual"],
            4.0,
        )

        # A later import that lacks an actual must not erase the historical
        # actual already stored for that player/week.
        database.upsert_player_week_history(
            {
                "k1": {
                    "name": "Kicker One",
                    "position": "K",
                    "team": "LAC",
                    "weeks": {
                        "1": {
                            "projection": 7.2,
                            "actual": None,
                        }
                    },
                }
            },
            season=2026,
        )

        refreshed = (
            database.load_player_week_history(
                1,
                season=2026,
            )
        )

        self.assertEqual(
            refreshed[0]["actual"],
            9.0,
        )
        self.assertEqual(
            refreshed[0]["projection"],
            7.2,
        )

    def test_weekly_roster_snapshots_keep_weeks_independent(self):
        database.snapshot_season_roster(
            2,
            season=2026,
        )

        roster_manager.replace_roster_player(
            "k1",
            {
                "player_id": "k2",
                "player_name": "Kicker Two",
                "position": "K",
                "team": "SF",
                "bye_week": 8,
            },
            season=2026,
        )

        database.snapshot_season_roster(
            3,
            season=2026,
        )

        week_two = {
            player["player_id"]: player
            for player in database.load_week_roster(
                2,
                season=2026,
            )
        }

        week_three = {
            player["player_id"]: player
            for player in database.load_week_roster(
                3,
                season=2026,
            )
        }

        self.assertIn(
            "k1",
            week_two,
        )
        self.assertNotIn(
            "k2",
            week_two,
        )
        self.assertNotIn(
            "k1",
            week_three,
        )
        self.assertIn(
            "k2",
            week_three,
        )

    def test_resnapshot_updates_only_current_week_copy(self):
        database.snapshot_season_roster(
            3,
            season=2026,
        )

        roster_manager.replace_roster_player(
            "k1",
            {
                "player_id": "k2",
                "player_name": "Kicker Two",
                "position": "K",
                "team": "SF",
                "bye_week": 8,
            },
            season=2026,
        )

        database.snapshot_season_roster(
            3,
            season=2026,
        )

        snapshot = {
            player["player_id"]: player
            for player in database.load_week_roster(
                3,
                season=2026,
            )
        }

        self.assertNotIn(
            "k1",
            snapshot,
        )
        self.assertIn(
            "k2",
            snapshot,
        )
        self.assertEqual(
            snapshot["k2"]["roster_slot"],
            "K",
        )

    def test_lock_aware_snapshot_preserves_locked_player(self):
        database.snapshot_season_roster(
            3,
            season=2026,
        )

        roster_manager.replace_roster_player(
            "k1",
            {
                "player_id": "k2",
                "player_name": "Kicker Two",
                "position": "K",
                "team": "SF",
            },
            season=2026,
        )

        database.snapshot_season_roster(
            3,
            season=2026,
            preserve_player_ids={"k1"},
        )

        snapshot = {
            player["player_id"]: player
            for player in database.load_week_roster(
                3,
                season=2026,
            )
        }

        self.assertIn(
            "k1",
            snapshot,
        )
        self.assertNotIn(
            "k2",
            snapshot,
        )

    def test_history_roster_uses_yahoo_player_id_for_join(self):
        roster = [
            {
                "player_id": "local-123",
                "yahoo_player_id": "31482",
                "player_name": "Eddy Pineiro",
                "name": "Eddy Pineiro",
                "position": "K",
                "team": "SF",
                "roster_slot": "K",
                "slot_index": 1,
            }
        ]

        history = (
            history_reconstruction
            .canonical_history_roster(
                roster
            )
        )

        self.assertEqual(
            history[0]["player_id"],
            "31482",
        )
        self.assertEqual(
            history[0]["roster_slot"],
            "K",
        )

    def test_history_reconstruction_rewinds_later_transactions(self):
        current = database.load_season_roster(
            2026
        )

        roster_manager.replace_roster_player(
            "k1",
            {
                "player_id": "k2",
                "player_name": "Kicker Two",
                "position": "K",
                "team": "SF",
            },
            season=2026,
        )

        current = database.load_season_roster(
            2026
        )

        transactions = [
            {
                "occurred_at":
                    "2026-09-27T11:26:00",
                "add_player_id": "k2",
                "add_player_name":
                    "Kicker Two",
                "add_position": "K",
                "add_team": "SF",
                "drop_player_id": "k1",
                "drop_player_name":
                    "Kicker One",
                "drop_position": "K",
                "drop_team": "LAC",
            }
        ]

        week_two = (
            history_reconstruction
            .roster_at_week_end(
                current,
                transactions,
                target_week=2,
                season=2026,
            )
        )

        by_id = {
            player["player_id"]: player
            for player in week_two
        }

        self.assertIn(
            "k1",
            by_id,
        )
        self.assertNotIn(
            "k2",
            by_id,
        )
        self.assertEqual(
            by_id["k1"]["roster_slot"],
            "K",
        )

    def test_ir_move_is_rejected_for_now(self):
        with self.assertRaises(ValueError):
            roster_manager.move_roster_player(
                "rb1",
                "IR",
                1,
                season=2026,
            )

    def test_empty_manual_cant_cut_list_keeps_authoritative_state(self):
        count = database.replace_week_cant_cut(
            4,
            [],
            season=2026,
            source="manual_settings",
        )

        self.assertEqual(count, 0)
        self.assertEqual(
            database.load_week_cant_cut(
                4,
                season=2026,
            ),
            [],
        )
        self.assertEqual(
            database.load_week_cant_cut_state(
                4,
                season=2026,
            )["source"],
            "manual_settings",
        )


if __name__ == "__main__":
    import unittest
    unittest.main()

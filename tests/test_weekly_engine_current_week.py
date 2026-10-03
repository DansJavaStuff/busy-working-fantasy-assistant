from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import patch

import weekly_engine
from weekly_engine import (
    add_transaction_deadlines,
    apply_submitted_lineup_slots,
    build_speculative_waiver_moves,
    build_status_watch,
    cached_start_sit_evidence,
    has_played,
    projection,
    waiver_available_date,
)


class WeeklyEngineCurrentWeekTests(TestCase):
    def test_projection_uses_current_week_field(self):
        player = {
            "current_week_projection": 12.5,
            "week_1_projection": 99.0,
        }

        self.assertEqual(
            projection(player),
            12.5,
        )

    def test_played_state_uses_current_week_actual(self):
        player = {
            "current_week_actual": None,
            "week_1_actual": 30.0,
        }

        self.assertFalse(
            has_played(player)
        )

        player["current_week_actual"] = 7.25

        self.assertTrue(
            has_played(player)
        )

    def test_submitted_lineup_slots_override_local_slots_for_locks(self):
        roster = [
            {
                "yahoo_player_id": "evans",
                "name": "Mike Evans",
                "position": "WR",
                "roster_slot": "FLEX",
                "slot_index": 1,
                "current_week_actual": 10.9,
            },
            {
                "yahoo_player_id": "pollard",
                "name": "Tony Pollard",
                "position": "RB",
                "roster_slot": "BN",
                "slot_index": 1,
                "current_week_actual": 11.6,
            },
            {
                "yahoo_player_id": "sutton",
                "name": "Courtland Sutton",
                "position": "WR",
                "roster_slot": "WR",
                "slot_index": 1,
                "current_week_actual": None,
            },
        ]

        submitted = [
            {
                "player_id": "evans",
                "lineup_slot": "WR",
                "slot_index": 2,
            },
            {
                "player_id": "pollard",
                "lineup_slot": "FLEX",
                "slot_index": 1,
            },
            {
                "player_id": "sutton",
                "lineup_slot": "BN",
                "slot_index": 2,
            },
        ]

        output = apply_submitted_lineup_slots(
            roster,
            submitted,
        )

        by_id = {
            player["yahoo_player_id"]: player
            for player in output
        }

        self.assertEqual(
            by_id["evans"]["roster_slot"],
            "WR",
        )
        self.assertEqual(
            by_id["pollard"]["roster_slot"],
            "FLEX",
        )
        self.assertEqual(
            by_id["sutton"]["roster_slot"],
            "BN",
        )

    def test_status_watch_includes_starter_and_bench_concerns(self):
        starter = {
            "yahoo_player_id": "1",
            "name": "Starter",
            "position": "WR",
            "status": "Q",
            "roster_slot": "WR",
        }

        bench = {
            "yahoo_player_id": "2",
            "name": "Bench",
            "position": "WR",
            "status": "O",
            "roster_slot": "BN",
        }

        ir = {
            "yahoo_player_id": "3",
            "name": "IR Player",
            "position": "WR",
            "status": "IR",
            "roster_slot": "IR",
        }

        watch = build_status_watch(
            [starter, bench, ir],
            [
                {
                    "slot": "WR",
                    "player": starter,
                }
            ],
        )

        self.assertEqual(
            [item["role"] for item in watch],
            ["STARTER", "BENCH"],
        )

        self.assertEqual(
            [item["player"]["name"] for item in watch],
            ["Starter", "Bench"],
        )

    def test_waiver_available_date_parses_yahoo_status(self):
        player = {
            "roster_status": "W (Sep 25)",
        }

        self.assertEqual(
            waiver_available_date(
                player,
                2099,
            ).isoformat(),
            "2099-09-25",
        )

    def test_waiver_add_is_suppressed_when_drop_locks_same_day(self):
        move = {
            "add": {
                "name": "Eagles",
                "roster_status": "W (Sep 25)",
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        27,
                        18,
                        0,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        25,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
        }

        self.assertEqual(
            add_transaction_deadlines(
                [move],
                2099,
            ),
            [],
        )

    def test_free_agent_add_remains_actionable_before_drop_lock(self):
        move = {
            "add": {
                "name": "Eagles",
                "roster_status": "FA",
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        27,
                        18,
                        0,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        25,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
        }

        output = add_transaction_deadlines(
            [move],
            2099,
        )

        self.assertEqual(
            len(output),
            1,
        )
        self.assertEqual(
            output[0][
                "transaction_deadline_note"
            ],
            "Packers locks first",
        )

    def test_small_speculative_waiver_upside_is_not_worth_predrop(self):
        move = {
            "week_gain": 0.55,
            "move_type": "DST STREAM",
            "add": {
                "name": "Eagles",
                "position": "DST",
                "roster_status": "W (Sep 25)",
                "yahoo_player_id": "eagles",
                "current_week_projection": 7.32,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        27,
                        18,
                        0,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "position": "DST",
                "yahoo_player_id": "packers",
                "current_week_projection": 6.77,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        25,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
        }

        available = [
            move["add"],
            {
                "name": "Bears",
                "position": "DST",
                "roster_status": "FA",
                "yahoo_player_id": "bears",
                "current_week_projection": 6.60,
                "status": None,
            },
        ]

        output = build_speculative_waiver_moves(
            [move],
            available,
            2099,
        )

        self.assertEqual(
            len(output),
            1,
        )
        self.assertEqual(
            output[0]["speculative_verdict"],
            "NOT WORTH PRE-DROP",
        )
        self.assertEqual(
            output[0]["fallback"]["name"],
            "Bears",
        )
        self.assertAlmostEqual(
            output[0]["fallback_delta"],
            -0.17,
            places=2,
        )

    def test_recommended_move_is_hidden_after_drop_player_has_actual(self):
        move = {
            "week_gain": 0.39,
            "move_type": "DST UPGRADE",
            "add": {
                "name": "Eagles",
                "position": "DST",
                "roster_status": "FA",
                "yahoo_player_id": "eagles",
                "current_week_projection": 7.16,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        29,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "position": "DST",
                "yahoo_player_id": "packers",
                "current_week_projection": 6.77,
                "current_week_actual": -2.0,
                "local_game": None,
            },
        }

        output = add_transaction_deadlines(
            [move],
            2099,
        )

        self.assertEqual(
            output,
            [],
        )

    def test_speculative_waiver_is_hidden_after_drop_player_locks(self):
        move = {
            "week_gain": 5.0,
            "move_type": "DST STREAM",
            "add": {
                "name": "Eagles",
                "position": "DST",
                "roster_status": "W (Sep 25)",
                "yahoo_player_id": "eagles",
                "current_week_projection": 10.0,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        27,
                        18,
                        0,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "position": "DST",
                "yahoo_player_id": "packers",
                "current_week_projection": 5.0,
                "current_week_actual": 2.0,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        25,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
        }

        output = build_speculative_waiver_moves(
            [move],
            [move["add"]],
            2099,
        )

        self.assertEqual(
            output,
            [],
        )

    def test_better_immediate_free_agent_beats_waiver_option(self):
        move = {
            "week_gain": 0.55,
            "move_type": "DST STREAM",
            "add": {
                "name": "Eagles",
                "position": "DST",
                "roster_status": "W (Sep 25)",
                "yahoo_player_id": "eagles",
                "current_week_projection": 7.32,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        27,
                        18,
                        0,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "position": "DST",
                "yahoo_player_id": "packers",
                "current_week_projection": 6.77,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        25,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
        }

        available = [
            move["add"],
            {
                "name": "Lions",
                "position": "DST",
                "roster_status": "FA",
                "yahoo_player_id": "lions",
                "current_week_projection": 7.45,
                "status": None,
            },
        ]

        output = build_speculative_waiver_moves(
            [move],
            available,
            2099,
        )

        self.assertEqual(
            output[0]["speculative_verdict"],
            "BETTER FA AVAILABLE",
        )
        self.assertEqual(
            output[0]["fallback"]["name"],
            "Lions",
        )
        self.assertAlmostEqual(
            output[0]["fallback_delta"],
            0.68,
            places=2,
        )

        # A small lineup gain must not make an inferior individual fallback
        # appear better than the waiver target.
        move["week_gain"] = 0.05
        available[1]["current_week_projection"] = 7.0
        output = build_speculative_waiver_moves([move], available, 2099)
        self.assertEqual(
            output[0]["speculative_verdict"],
            "NOT WORTH PRE-DROP",
        )

    def test_large_speculative_upside_with_safe_fallback_is_worth_reviewing(self):
        move = {
            "week_gain": 8.0,
            "move_type": "DST STREAM",
            "add": {
                "name": "Eagles",
                "position": "DST",
                "roster_status": "W (Sep 25)",
                "yahoo_player_id": "eagles",
                "current_week_projection": 14.77,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        27,
                        18,
                        0,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
            "drop": {
                "name": "Packers",
                "position": "DST",
                "yahoo_player_id": "packers",
                "current_week_projection": 6.77,
                "local_game": {
                    "datetime": datetime(
                        2099,
                        9,
                        25,
                        1,
                        15,
                        tzinfo=weekly_engine.UK_TIME,
                    )
                },
            },
        }

        available = [
            move["add"],
            {
                "name": "Bears",
                "position": "DST",
                "roster_status": "FA",
                "yahoo_player_id": "bears",
                "current_week_projection": 6.50,
                "status": None,
            },
        ]

        output = build_speculative_waiver_moves(
            [move],
            available,
            2099,
        )

        self.assertEqual(
            output[0]["speculative_verdict"],
            "WORTH REVIEWING",
        )

    def test_start_sit_evidence_is_cached_for_same_snapshot(self):
        lineup = [
            {
                "slot": "FLEX",
                "player": {
                    "name": "Starter",
                    "current_week_projection": 10.0,
                    "current_week_actual": None,
                },
            }
        ]

        bench = [
            {
                "name": "Bench",
                "current_week_projection": 9.0,
                "current_week_actual": None,
            }
        ]

        provider_status = {
            "captured_at": datetime(
                2026,
                9,
                21,
                12,
                0,
                tzinfo=UTC,
            ),
            "generated_at": datetime(
                2026,
                9,
                21,
                12,
                1,
                tzinfo=UTC,
            ),
        }

        weekly_engine._START_SIT_CACHE[
            "snapshot_key"
        ] = None
        weekly_engine._START_SIT_CACHE[
            "evidence"
        ] = None

        with patch.object(
            weekly_engine,
            "build_start_sit_evidence",
            return_value=[
                {
                    "recommendation":
                        "START Starter",
                }
            ],
        ) as builder:
            first = (
                cached_start_sit_evidence(
                    lineup,
                    bench,
                    provider_status,
                    2,
                )
            )

            second = (
                cached_start_sit_evidence(
                    lineup,
                    bench,
                    provider_status,
                    2,
                )
            )

            provider_status[
                "generated_at"
            ] = datetime(
                2026,
                9,
                21,
                12,
                2,
                tzinfo=UTC,
            )

            refreshed = (
                cached_start_sit_evidence(
                    lineup,
                    bench,
                    provider_status,
                    2,
                )
            )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            second,
            refreshed,
        )

        self.assertEqual(
            builder.call_count,
            2,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

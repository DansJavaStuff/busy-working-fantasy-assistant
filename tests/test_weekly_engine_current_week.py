from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

import weekly_engine
from weekly_engine import (
    add_transaction_deadlines,
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
                tzinfo=timezone.utc,
            )
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

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            builder.call_count,
            1,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

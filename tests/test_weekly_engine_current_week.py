from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

import weekly_engine
from weekly_engine import (
    cached_start_sit_evidence,
    has_played,
    projection,
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

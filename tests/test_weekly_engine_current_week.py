from unittest import TestCase

from weekly_engine import (
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


if __name__ == "__main__":
    import unittest

    unittest.main()

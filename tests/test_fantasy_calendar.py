from datetime import date
from unittest import TestCase

from fantasy_calendar import (
    CHAMPIONSHIP_WEEK,
    FINAL_FANTASY_WEEK,
    PLAYOFF_START_WEEK,
    REGULAR_SEASON_WEEKS,
    current_fantasy_week,
    fantasy_season_for_date,
    game_date_for_week,
    week_1_start,
    week_1_thursday,
)


class FantasyCalendarTests(TestCase):
    def test_2026_week_one_dates(self):
        self.assertEqual(
            week_1_thursday(2026),
            date(2026, 9, 10),
        )
        self.assertEqual(
            week_1_start(2026),
            date(2026, 9, 8),
        )

    def test_week_advances_on_tuesday(self):
        self.assertEqual(
            current_fantasy_week(
                2026,
                date(2026, 9, 14),
            ),
            1,
        )
        self.assertEqual(
            current_fantasy_week(
                2026,
                date(2026, 9, 15),
            ),
            2,
        )

    def test_busy_working_season_boundaries(self):
        self.assertEqual(REGULAR_SEASON_WEEKS, 14)
        self.assertEqual(PLAYOFF_START_WEEK, 15)
        self.assertEqual(CHAMPIONSHIP_WEEK, 17)
        self.assertEqual(FINAL_FANTASY_WEEK, 17)

    def test_current_week_stops_at_championship_week(self):
        self.assertEqual(
            current_fantasy_week(
                2026,
                date(2026, 12, 29),
            ),
            17,
        )
        self.assertEqual(
            current_fantasy_week(
                2026,
                date(2027, 1, 5),
            ),
            17,
        )

    def test_january_belongs_to_previous_season(self):
        self.assertEqual(
            fantasy_season_for_date(
                date(2027, 1, 15)
            ),
            2026,
        )
        self.assertEqual(
            fantasy_season_for_date(
                date(2026, 9, 15)
            ),
            2026,
        )

    def test_game_day_maps_to_calendar_date(self):
        self.assertEqual(
            game_date_for_week(
                2026,
                2,
                "Thu",
            ),
            date(2026, 9, 17),
        )
        self.assertEqual(
            game_date_for_week(
                2026,
                2,
                "Sun",
            ),
            date(2026, 9, 20),
        )
        self.assertIsNone(
            game_date_for_week(
                2026,
                2,
                "???",
            )
        )

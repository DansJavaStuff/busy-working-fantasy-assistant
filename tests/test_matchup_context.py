from unittest import TestCase

from matchup_context import (
    allowed_for_week_position,
    matchup_context,
)


class MatchupContextTests(TestCase):
    def test_allowed_points_are_rescored_with_busy_working_rules(self):
        rows = [
            {
                "player": {
                    "position": "RB",
                },
                "opponent": "IND",
                "stats": {
                    "rush_yd": 80,
                    "rush_td": 1,
                    "rec": 3,
                    "rec_yd": 20,
                },
            },
            {
                "player": {
                    "position": "RB",
                },
                "opponent": "IND",
                "stats": {
                    "rush_yd": 20,
                    "rec": 2,
                    "rec_yd": 10,
                },
            },
        ]

        allowed = (
            allowed_for_week_position(
                rows,
                "RB",
            )
        )

        self.assertEqual(
            allowed["IND"],
            20.5,
        )

    def test_matchup_context_compares_defence_with_league_average(self):
        cache = {
            "version": 1,
            "season": 2026,
            "weeks": {
                "1": {
                    "RB": {
                        "IND": 30.0,
                        "BUF": 10.0,
                    }
                },
                "2": {
                    "RB": {
                        "IND": 26.0,
                        "BUF": 14.0,
                    }
                },
            },
        }

        context = matchup_context(
            {
                "position": "RB",
                "opponent": "IND",
            },
            cache=cache,
        )

        self.assertEqual(
            context["label"],
            "FAVOURABLE",
        )
        self.assertEqual(
            context["games"],
            2,
        )
        self.assertEqual(
            context["allowed_average"],
            28.0,
        )
        self.assertEqual(
            context["league_average"],
            20.0,
        )
        self.assertEqual(
            context["delta_pct"],
            40.0,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

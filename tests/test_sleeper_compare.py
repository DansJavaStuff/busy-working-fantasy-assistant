from unittest import TestCase
from unittest.mock import patch

import sleeper_compare


class SleeperCompareTests(TestCase):
    def test_scores_busy_working_offense_rules(self):
        stats = {
            "pass_yd": 250,
            "pass_td": 2,
            "pass_int": 1,
            "rush_yd": 30,
            "rush_td": 1,
            "rec": 4,
            "rec_yd": 50,
            "rec_td": 1,
            "fum_lost": 1,
            "rush_2pt": 1,
        }

        # 250/25 + 2*5 -2 + 30/10 +6 + 4*.5 +50/10 +6 -2 +2
        self.assertEqual(
            sleeper_compare.score_offense_for_yahoo(stats),
            40.0,
        )

    def test_compare_fetches_only_needed_positions(self):
        rows = {
            "RB": [
                {
                    "player": {
                        "full_name": "Tony Pollard",
                        "team": "TEN",
                    },
                    "stats": {
                        "rush_yd": 60,
                        "rec": 2,
                        "rec_yd": 20,
                        "pts_half_ppr": 9.0,
                    },
                }
            ],
            "WR": [
                {
                    "player": {
                        "full_name": "Mike Evans",
                        "team": "SF",
                    },
                    "stats": {
                        "rec": 4,
                        "rec_yd": 70,
                        "rec_td": 0.5,
                        "pts_half_ppr": 12.0,
                    },
                }
            ],
        }

        calls = []

        def fake_fetch(position, week, season=2026):
            calls.append((position, week, season))
            return rows[position]

        players = [
            {
                "name": "Mike Evans",
                "position": "WR",
                "team": "SF",
                "current_week_projection": 9.88,
            },
            {
                "name": "Tony Pollard",
                "position": "RB",
                "team": "TEN",
                "current_week_projection": 7.46,
            },
        ]

        with patch.object(
            sleeper_compare,
            "fetch_week_position",
            side_effect=fake_fetch,
        ):
            result = sleeper_compare.compare_players(
                players,
                week=2,
            )

        self.assertEqual(
            [call[0] for call in calls],
            ["RB", "WR"],
        )
        self.assertEqual(result[0]["name"], "Mike Evans")
        self.assertEqual(
            result[0]["sleeper_yahoo_projection"],
            12.0,
        )
        self.assertEqual(
            result[1]["sleeper_yahoo_projection"],
            9.0,
        )


if __name__ == "__main__":
    import unittest
    unittest.main()

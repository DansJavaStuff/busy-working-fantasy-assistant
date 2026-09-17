from unittest import TestCase

from weekly_decisions import (
    build_start_sit_decisions,
)


class WeeklyDecisionTests(TestCase):
    def test_sources_agree_for_same_position(self):
        lineup = [
            {
                "slot": "WR",
                "player": {
                    "name": "Starter WR",
                    "position": "WR",
                    "current_week_projection": 10.0,
                    "current_week_actual": None,
                },
            }
        ]

        bench = [
            {
                "name": "Bench WR",
                "position": "WR",
                "current_week_projection": 9.0,
                "current_week_actual": None,
            }
        ]

        cache = {
            "feeds": {
                "WR": [
                    {
                        "name": "Starter WR",
                        "ecr": 6,
                        "position_rank": "WR6",
                    },
                    {
                        "name": "Bench WR",
                        "ecr": 9,
                        "position_rank": "WR9",
                    },
                ]
            }
        }

        decisions = build_start_sit_decisions(
            lineup,
            bench,
            cache,
        )

        self.assertEqual(len(decisions), 1)
        self.assertEqual(
            decisions[0]["label"],
            "CLOSE",
        )
        self.assertEqual(
            decisions[0]["fantasypros"]["agreement"],
            "agree",
        )
        self.assertEqual(
            decisions[0]["fantasypros"]["comparison"],
            "starter",
        )

    def test_sources_can_disagree(self):
        lineup = [
            {
                "slot": "WR",
                "player": {
                    "name": "Starter WR",
                    "position": "WR",
                    "current_week_projection": 10.0,
                    "current_week_actual": None,
                },
            }
        ]

        bench = [
            {
                "name": "Bench WR",
                "position": "WR",
                "current_week_projection": 9.4,
                "current_week_actual": None,
            }
        ]

        cache = {
            "feeds": {
                "WR": [
                    {
                        "name": "Starter WR",
                        "ecr": 10,
                    },
                    {
                        "name": "Bench WR",
                        "ecr": 4,
                    },
                ]
            }
        }

        decisions = build_start_sit_decisions(
            lineup,
            bench,
            cache,
        )

        self.assertEqual(
            decisions[0]["fantasypros"]["agreement"],
            "disagree",
        )
        self.assertEqual(
            decisions[0]["fantasypros"]["comparison"],
            "bench",
        )

    def test_cross_position_ecr_is_not_compared(self):
        lineup = [
            {
                "slot": "FLEX",
                "player": {
                    "name": "Starter WR",
                    "position": "WR",
                    "current_week_projection": 10.0,
                    "current_week_actual": None,
                },
            }
        ]

        bench = [
            {
                "name": "Bench RB",
                "position": "RB",
                "current_week_projection": 9.5,
                "current_week_actual": None,
            }
        ]

        cache = {
            "feeds": {
                "WR": [
                    {
                        "name": "Starter WR",
                        "ecr": 8,
                        "position_rank": "WR8",
                    }
                ],
                "RB": [
                    {
                        "name": "Bench RB",
                        "ecr": 3,
                        "position_rank": "RB3",
                    }
                ],
            }
        }

        decisions = build_start_sit_decisions(
            lineup,
            bench,
            cache,
        )

        self.assertEqual(
            decisions[0]["fantasypros"]["comparison"],
            "cross_position",
        )
        self.assertIsNone(
            decisions[0]["fantasypros"]["agreement"]
        )

    def test_missing_fantasypros_data_is_not_a_vote(self):
        lineup = [
            {
                "slot": "RB",
                "player": {
                    "name": "Starter RB",
                    "position": "RB",
                    "current_week_projection": 8.0,
                    "current_week_actual": None,
                },
            }
        ]

        bench = [
            {
                "name": "Bench RB",
                "position": "RB",
                "current_week_projection": 7.8,
                "current_week_actual": None,
            }
        ]

        decisions = build_start_sit_decisions(
            lineup,
            bench,
            {"feeds": {"RB": []}},
        )

        self.assertIsNone(
            decisions[0]["fantasypros"]["comparison"]
        )
        self.assertIsNone(
            decisions[0]["fantasypros"]["agreement"]
        )

    def test_played_players_are_not_reconsidered(self):
        lineup = [
            {
                "slot": "WR",
                "player": {
                    "name": "Locked WR",
                    "position": "WR",
                    "current_week_projection": 8.0,
                    "current_week_actual": 12.0,
                },
            }
        ]

        bench = [
            {
                "name": "Bench WR",
                "position": "WR",
                "current_week_projection": 9.0,
                "current_week_actual": None,
            }
        ]

        self.assertEqual(
            build_start_sit_decisions(
                lineup,
                bench,
            ),
            [],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

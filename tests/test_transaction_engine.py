from unittest import TestCase

from transaction_engine import (
    build_bye_coverage,
    build_transaction_recommendations,
    compare_bye_coverage,
)


def player(
    player_id,
    name,
    position,
    bye_week=None,
    week_projection=10.0,
    four_week_projection=40.0,
    roster_slot="BN",
):
    return {
        "yahoo_player_id": player_id,
        "name": name,
        "position": position,
        "bye_week": bye_week,
        "week_1_projection": week_projection,
        "next_4_weeks_projection": four_week_projection,
        "status": None,
        "roster_slot": roster_slot,
        "roster_status": "FA",
    }


def base_roster():
    return [
        player(
            "qb1",
            "Starting QB",
            "QB",
            bye_week=7,
            week_projection=20.0,
            four_week_projection=80.0,
            roster_slot="QB",
        ),
        player(
            "qb2",
            "Backup QB",
            "QB",
            bye_week=7,
            week_projection=18.0,
            four_week_projection=72.0,
        ),
        player(
            "rb1",
            "RB One",
            "RB",
            bye_week=8,
            week_projection=14.0,
            four_week_projection=56.0,
            roster_slot="RB",
        ),
        player(
            "rb2",
            "RB Two",
            "RB",
            bye_week=9,
            week_projection=13.0,
            four_week_projection=52.0,
            roster_slot="RB",
        ),
        player(
            "rb3",
            "RB Three",
            "RB",
            bye_week=10,
            week_projection=9.0,
            four_week_projection=36.0,
        ),
        player(
            "wr1",
            "WR One",
            "WR",
            bye_week=8,
            week_projection=14.0,
            four_week_projection=56.0,
            roster_slot="WR",
        ),
        player(
            "wr2",
            "WR Two",
            "WR",
            bye_week=9,
            week_projection=13.0,
            four_week_projection=52.0,
            roster_slot="WR",
        ),
        player(
            "wr3",
            "WR Three",
            "WR",
            bye_week=10,
            week_projection=10.0,
            four_week_projection=40.0,
            roster_slot="FLEX",
        ),
        player(
            "te1",
            "Tight End",
            "TE",
            bye_week=11,
            week_projection=8.0,
            four_week_projection=32.0,
            roster_slot="TE",
        ),
        player(
            "k1",
            "Kicker",
            "K",
            bye_week=7,
            week_projection=8.0,
            four_week_projection=32.0,
            roster_slot="K",
        ),
        player(
            "dst1",
            "Defence",
            "DST",
            bye_week=8,
            week_projection=8.0,
            four_week_projection=32.0,
            roster_slot="DST",
        ),
    ]


class TransactionEngineTests(TestCase):
    def test_normal_week_is_good(self):
        coverage = build_bye_coverage(
            base_roster(),
            current_week=1,
        )

        week_2 = next(
            item
            for item in coverage
            if item["week"] == 2
        )

        self.assertEqual(
            week_2["status"],
            "GOOD",
        )

        self.assertEqual(
            week_2["problems"],
            [],
        )

    def test_shared_qb_bye_requires_action(self):
        coverage = build_bye_coverage(
            base_roster(),
            current_week=1,
        )

        week_7 = next(
            item
            for item in coverage
            if item["week"] == 7
        )

        self.assertEqual(
            week_7["status"],
            "ACTION NEEDED",
        )

        self.assertIn(
            "QB",
            week_7["problems"],
        )

        self.assertIn(
            "K",
            week_7["problems"],
        )

    def test_dst_only_hole_is_stream(self):
        roster = base_roster()

        # Move every non-DST Week 8 conflict
        # away so the defence is the only
        # lineup hole that week.
        for item in roster:
            if (
                item["bye_week"] == 8
                and item["position"] != "DST"
            ):
                item["bye_week"] = 12

        coverage = build_bye_coverage(
            roster,
            current_week=1,
        )

        week_8 = next(
            item
            for item in coverage
            if item["week"] == 8
        )

        self.assertEqual(
            week_8["status"],
            "STREAM",
        )

        self.assertEqual(
            week_8["problems"],
            ["DST"],
        )

    def test_fixing_qb_bye_has_positive_value(self):
        roster = base_roster()

        before = build_bye_coverage(
            roster,
            current_week=1,
        )

        after_roster = [
            item
            for item in roster
            if item["yahoo_player_id"] != "qb2"
        ]

        after_roster.append(
            player(
                "qb3",
                "Replacement QB",
                "QB",
                bye_week=12,
                week_projection=18.0,
                four_week_projection=72.0,
            )
        )

        after = build_bye_coverage(
            after_roster,
            current_week=1,
        )

        comparison = compare_bye_coverage(
            before,
            after,
            current_week=1,
        )

        self.assertGreater(
            comparison["gain"],
            0.0,
        )

        self.assertIn(
            {
                "week": 7,
                "positions": ["QB"],
            },
            comparison["improvements"],
        )

    def test_moving_dst_problem_earlier_is_negative(self):
        roster = base_roster()

        before = build_bye_coverage(
            roster,
            current_week=1,
        )

        after_roster = [
            dict(item)
            for item in roster
        ]

        defence = next(
            item
            for item in after_roster
            if item["position"] == "DST"
        )

        defence["bye_week"] = 6

        after = build_bye_coverage(
            after_roster,
            current_week=1,
        )

        comparison = compare_bye_coverage(
            before,
            after,
            current_week=1,
        )

        self.assertLess(
            comparison["gain"],
            0.0,
        )

    def test_duplicate_qb_bye_fixes_are_collapsed(self):
        roster = base_roster()

        available = [
            player(
                "fa-qb1",
                "Cover QB One",
                "QB",
                bye_week=12,
                week_projection=18.2,
                four_week_projection=73.0,
            ),
            player(
                "fa-qb2",
                "Cover QB Two",
                "QB",
                bye_week=13,
                week_projection=18.0,
                four_week_projection=72.0,
            ),
        ]

        recommendations = (
            build_transaction_recommendations(
                roster,
                available,
                limit=5,
                current_week=1,
            )
        )

        week_7_qb_fixes = [
            move
            for move in recommendations
            if any(
                item["week"] == 7
                and "QB" in item["positions"]
                for item in move.get(
                    "bye_context",
                    {},
                ).get(
                    "improvements",
                    [],
                )
            )
        ]

        self.assertEqual(
            len(week_7_qb_fixes),
            1,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

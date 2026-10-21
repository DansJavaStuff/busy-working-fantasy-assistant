from unittest import TestCase

from transaction_engine import (
    build_bye_coverage,
    build_transaction_recommendations,
    compare_bye_coverage,
    roster_metrics,
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
        "current_week_projection": week_projection,
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
    def test_streams_prioritise_this_week_over_future_average_and_byes(self):
        for position, roster_id in (("DST", "dst1"), ("K", "k1")):
            with self.subTest(position=position):
                roster = base_roster()
                current = next(p for p in roster if p["yahoo_player_id"] == roster_id)
                current.update(current_week_projection=5.51, next_4_weeks_projection=21.48, bye_week=13)
                options = [
                    player("lions", "Long-term option", position, bye_week=12,
                           week_projection=5.79, four_week_projection=26.16),
                    player("titans", "Weekly option", position, bye_week=13,
                           week_projection=7.72, four_week_projection=16.48),
                    player("future", "Future only", position, bye_week=12,
                           week_projection=5.0, four_week_projection=80.0),
                ]
                moves = build_transaction_recommendations(roster, options, limit=20, current_week=7)
                streams = [m for m in moves if m["drop"]["yahoo_player_id"] == roster_id]
                self.assertEqual([m["add"]["yahoo_player_id"] for m in streams], ["titans", "lions"])
                self.assertAlmostEqual(streams[0]["score"], 2.21)
                self.assertEqual(streams[0]["label"], "STRONG MOVE")
                self.assertLess(streams[0]["four_week_gain"], 0)
                self.assertEqual(streams[0]["bye_score_adjustment"], 0)
                self.assertEqual(streams[1]["label"], "HOLD")

    def test_stream_is_not_excluded_by_general_candidate_cap(self):
        options = [player(str(i), "QB option", "QB", week_projection=30, four_week_projection=120)
                   for i in range(61)]
        options.append(player("stream", "Weekly defence", "DST", week_projection=10, four_week_projection=1))
        moves = build_transaction_recommendations(base_roster(), options, limit=100, current_week=1)
        self.assertTrue(any(m["add"]["yahoo_player_id"] == "stream" for m in moves))

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

    def test_cant_cut_player_is_never_recommended_as_drop(self):
        roster = base_roster()

        protected = next(
            item
            for item in roster
            if item["yahoo_player_id"] == "wr3"
        )

        protected[
            "current_week_projection"
        ] = 1.0
        protected[
            "next_4_weeks_projection"
        ] = 4.0

        available = [
            player(
                "fa-wr",
                "Available Star WR",
                "WR",
                bye_week=12,
                week_projection=20.0,
                four_week_projection=80.0,
            ),
        ]

        recommendations = (
            build_transaction_recommendations(
                roster,
                available,
                limit=20,
                current_week=4,
                cant_cut_ids={
                    "wr3",
                },
            )
        )

        self.assertFalse(
            any(
                move["drop"][
                    "yahoo_player_id"
                ] == "wr3"
                for move in recommendations
            )
        )

    def test_missing_four_week_projection_does_not_create_fake_upgrade(self):
        roster = base_roster()

        backup = next(
            item
            for item in roster
            if item["yahoo_player_id"] == "qb2"
        )
        backup["next_4_weeks_projection"] = None

        available = [
            player(
                "fa-qb",
                "Available QB",
                "QB",
                bye_week=7,
                week_projection=18.0,
                four_week_projection=73.0,
            ),
        ]

        recommendations = build_transaction_recommendations(
            roster,
            available,
            limit=10,
            current_week=1,
        )

        fake_upgrade = [
            move
            for move in recommendations
            if (
                move["add"]["yahoo_player_id"] == "fa-qb"
                and move["drop"]["yahoo_player_id"] == "qb2"
            )
        ]

        self.assertEqual(
            fake_upgrade,
            [],
        )

    def test_roster_metrics_ignore_stale_week_one_alias(self):
        roster = base_roster()

        for item in roster:
            item["week_1_projection"] = 999.0

        metrics = roster_metrics(
            roster,
            [],
        )

        self.assertIsNotNone(metrics)
        self.assertLess(
            metrics["current_week_total"],
            999.0,
        )
        self.assertNotIn(
            "week_1_total",
            metrics,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

from datetime import datetime, timezone
from unittest import TestCase

from yahoo_normalizer import (
    build_dataset,
    normalise_player,
    player_for_week,
)


class YahooNormalizerTests(TestCase):
    def test_week_fields_become_arbitrary_week_map(self):
        player = {
            "yahoo_player_id": "123",
            "name": "Example Player",
            "team": "BUF",
            "position": "QB",
            "week_1_projection": 21.5,
            "week_1_actual": 30.2,
            "week_1_projection_stats": {
                "pass_yards": 260.0,
            },
            "week_2_projection": 24.1,
            "week_2_actual": None,
            "week_2_game_display": "Thu 8:15 pm vs MIA",
            "week_2_game_day": "Thu",
            "week_2_game_time": "8:15 pm",
            "week_2_opponent": "MIA",
            "week_2_home_away": "home",
            "next_4_weeks_projection": 91.4,
        }

        result = normalise_player(player)

        self.assertNotIn("week_1_projection", result)
        self.assertEqual(
            result["weeks"]["1"]["projection"],
            21.5,
        )
        self.assertEqual(
            result["weeks"]["1"]["actual"],
            30.2,
        )
        self.assertEqual(
            result["weeks"]["2"]["projection"],
            24.1,
        )
        self.assertIsNone(
            result["weeks"]["2"]["actual"]
        )
        self.assertEqual(
            result["weeks"]["2"]["game"]["opponent"],
            "MIA",
        )
        self.assertEqual(
            result["next_4_weeks_projection"],
            91.4,
        )

    def test_future_week_requires_no_schema_change(self):
        player = {
            "yahoo_player_id": "456",
            "name": "Future Player",
            "week_17_projection": 18.7,
        }

        result = normalise_player(player)

        self.assertEqual(
            player_for_week(result, 17)["projection"],
            18.7,
        )

    def test_dataset_tracks_roster_and_available_membership(self):
        roster = [
            {
                "yahoo_player_id": "1",
                "name": "Roster Player",
                "week_2_projection": 10.0,
            }
        ]
        available = [
            {
                "yahoo_player_id": "2",
                "name": "Available Player",
                "week_2_projection": 9.0,
            }
        ]

        generated_at = datetime(
            2026,
            9,
            15,
            16,
            0,
            tzinfo=timezone.utc,
        )

        result = build_dataset(
            roster,
            available,
            source="manual_html",
            generated_at=generated_at,
        )

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["source"], "manual_html")
        self.assertEqual(result["my_team_ids"], ["1"])
        self.assertEqual(result["available_ids"], ["2"])
        self.assertEqual(
            result["players"]["1"]["weeks"]["2"]["projection"],
            10.0,
        )

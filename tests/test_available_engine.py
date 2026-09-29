from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

import available_engine
from available_engine import (
    _position_baselines,
    _position_value,
    build_available_rankings,
    target_week_projection,
)


class AvailableEngineTests(TestCase):
    def setUp(self):
        available_engine._AVAILABLE_CACHE[
            "snapshot_key"
        ] = None
        available_engine._AVAILABLE_CACHE[
            "data"
        ] = None

    def test_target_week_projection_reads_weeks_model(self):
        player = {
            "weeks": {
                "3": {
                    "projection": 12.5,
                }
            }
        }

        self.assertEqual(
            target_week_projection(
                player,
                3,
            ),
            12.5,
        )

    def test_position_value_compares_with_same_position(self):
        players = []

        for index, projection in enumerate(
            [
                12.0,
                11.0,
                10.0,
                9.0,
                8.0,
                7.0,
                6.0,
                5.0,
                4.0,
                3.0,
            ],
            start=1,
        ):
            players.append(
                {
                    "name":
                        f"Receiver {index}",
                    "position": "WR",
                    "weeks": {
                        "3": {
                            "projection":
                                projection,
                        }
                    },
                    "next_4_weeks_projection":
                        projection * 4,
                }
            )

        baselines = (
            _position_baselines(
                players,
                3,
            )
        )

        top_value = _position_value(
            "WR",
            12.0,
            12.0,
            baselines,
        )

        replacement_value = (
            _position_value(
                "WR",
                3.0,
                3.0,
                baselines,
            )
        )

        self.assertGreater(
            top_value["value"],
            0,
        )
        self.assertEqual(
            replacement_value["value"],
            0,
        )

    def test_rankings_use_sleeper_and_roster_fit(self):
        roster = [
            {
                "yahoo_player_id": "r1",
                "name": "Roster Player",
                "position": "WR",
            }
        ]

        available = [
            {
                "yahoo_player_id": "a1",
                "name": "Alpha Receiver",
                "position": "WR",
                "team": "AAA",
                "weeks": {
                    "3": {
                        "projection": 10.0,
                    }
                },
                "next_4_weeks_projection": 40.0,
            },
            {
                "yahoo_player_id": "a2",
                "name": "Beta Receiver",
                "position": "WR",
                "team": "BBB",
                "weeks": {
                    "3": {
                        "projection": 9.0,
                    }
                },
                "next_4_weeks_projection": 36.0,
            },
        ]

        moves = [
            {
                "add": available[0],
                "drop": roster[0],
                "score": 1.0,
                "bye_score_adjustment": 0.0,
                "label": "WATCH",
                "move_type": "DEPTH UPGRADE",
                "reasons": [
                    "Improves depth.",
                ],
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

        sleeper = [
            {
                "name": "Alpha Receiver",
                "sleeper_yahoo_projection": 12.0,
            },
            {
                "name": "Beta Receiver",
                "sleeper_yahoo_projection": 8.0,
            },
        ]

        with patch.object(
            available_engine,
            "load_season_roster",
            return_value=roster,
        ), patch.object(
            available_engine,
            "enrich_local_roster",
            return_value=roster,
        ), patch.object(
            available_engine,
            "load_season_league_state",
            return_value={
                "waiver_priority": 11,
            },
        ), patch.object(
            available_engine,
            "get_effective_available_players",
            return_value=available,
        ), patch.object(
            available_engine.yahoo_provider,
            "get_status",
            return_value=provider_status,
        ), patch.object(
            available_engine,
            "build_transaction_recommendations",
            return_value=moves,
        ), patch.object(
            available_engine,
            "four_week_average",
            side_effect=lambda player:
                float(
                    player.get(
                        "next_4_weeks_projection",
                        0,
                    )
                )
                / 4.0,
        ):
            result = build_available_rankings(
                2026,
                2,
                limit=2,
                sleeper_fetch=lambda *args, **kwargs:
                    sleeper,
            )

        self.assertEqual(
            result["rankings"][0][
                "player"
            ]["name"],
            "Alpha Receiver",
        )

        self.assertEqual(
            result["rankings"][0][
                "best_drop"
            ]["name"],
            "Roster Player",
        )

        self.assertEqual(
            result["rankings"][0][
                "sleeper_next_week"
            ],
            12.0,
        )

    def test_shared_qb_bye_is_presented_as_bye_fix(self):
        roster = [
            {
                "yahoo_player_id": "qb1",
                "name": "Josh Allen",
                "position": "QB",
                "bye_week": 7,
                "next_4_weeks_projection": 100.0,
            },
            {
                "yahoo_player_id": "qb2",
                "name": "Trevor Lawrence",
                "position": "QB",
                "bye_week": 7,
                "next_4_weeks_projection": 60.0,
            },
        ]

        available = [
            {
                "yahoo_player_id": "fa1",
                "name": "Jared Goff",
                "position": "QB",
                "team": "DET",
                "bye_week": 8,
                "weeks": {
                    "3": {
                        "projection": 20.0,
                    }
                },
                "next_4_weeks_projection": 80.0,
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

        with patch.object(
            available_engine,
            "load_season_roster",
            return_value=roster,
        ), patch.object(
            available_engine,
            "enrich_local_roster",
            return_value=roster,
        ), patch.object(
            available_engine,
            "load_season_league_state",
            return_value={
                "waiver_priority": 11,
            },
        ), patch.object(
            available_engine,
            "get_effective_available_players",
            return_value=available,
        ), patch.object(
            available_engine.yahoo_provider,
            "get_status",
            return_value=provider_status,
        ), patch.object(
            available_engine,
            "build_transaction_recommendations",
            return_value=[],
        ), patch.object(
            available_engine,
            "four_week_average",
            side_effect=lambda player:
                float(
                    player.get(
                        "next_4_weeks_projection",
                        0,
                    )
                )
                / 4.0,
        ):
            result = build_available_rankings(
                2026,
                2,
                limit=1,
                sleeper_fetch=lambda *args, **kwargs:
                    [],
            )

        top = result["rankings"][0]

        self.assertEqual(
            top["move_label"],
            "BYE FIX",
        )
        self.assertEqual(
            top["move_type"],
            "QB COVER",
        )
        self.assertEqual(
            top["best_drop"]["name"],
            "Trevor Lawrence",
        )


    def test_rankings_survive_sleeper_failure(self):
        roster = []
        available = [
            {
                "yahoo_player_id": "a1",
                "name": "Example Player",
                "position": "WR",
                "team": "AAA",
                "weeks": {
                    "3": {
                        "projection": 8.0,
                    }
                },
                "next_4_weeks_projection": 32.0,
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

        def fail(*args, **kwargs):
            raise RuntimeError(
                "Sleeper unavailable"
            )

        with patch.object(
            available_engine,
            "load_season_roster",
            return_value=roster,
        ), patch.object(
            available_engine,
            "enrich_local_roster",
            return_value=roster,
        ), patch.object(
            available_engine,
            "load_season_league_state",
            return_value={
                "waiver_priority": 11,
            },
        ), patch.object(
            available_engine,
            "get_effective_available_players",
            return_value=available,
        ), patch.object(
            available_engine.yahoo_provider,
            "get_status",
            return_value=provider_status,
        ), patch.object(
            available_engine,
            "build_transaction_recommendations",
            return_value=[],
        ), patch.object(
            available_engine,
            "four_week_average",
            return_value=8.0,
        ):
            result = build_available_rankings(
                2026,
                2,
                limit=1,
                sleeper_fetch=fail,
            )

        self.assertEqual(
            len(result["rankings"]),
            1,
        )

        self.assertIn(
            "Sleeper unavailable",
            result["sleeper_error"],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

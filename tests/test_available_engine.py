from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import patch

import available_engine
from available_engine import (
    _position_baselines,
    _position_value,
    _qb_bye_context,
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
        self.cant_cut_patcher = (
            patch.object(
                available_engine,
                "load_week_cant_cut",
                return_value=[],
            )
        )
        self.cant_cut_patcher.start()
        self.addCleanup(
            self.cant_cut_patcher.stop
        )

    def test_qb_bye_drop_excludes_cant_cut_player(self):
        roster = [
            {
                "yahoo_player_id": "qb1",
                "name": "Primary QB",
                "position": "QB",
                "bye_week": 7,
                "next_4_weeks_projection": 100.0,
            },
            {
                "yahoo_player_id": "qb2",
                "name": "Protected QB",
                "position": "QB",
                "bye_week": 7,
                "next_4_weeks_projection": 60.0,
            },
        ]

        context = _qb_bye_context(
            roster,
            {"qb2"},
        )

        self.assertTrue(context["conflict"])
        self.assertIsNone(
            context["bye_conflict_drop"]
        )

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
                tzinfo=UTC,
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

    def test_rankings_exclude_cant_cut_drop_and_refresh_cache(self):
        puka = {
            "yahoo_player_id": "puka",
            "name": "Puka Nacua",
            "position": "WR",
            "next_4_weeks_projection": 36.0,
        }
        sutton = {
            "yahoo_player_id": "sutton",
            "name": "Courtland Sutton",
            "position": "WR",
            "next_4_weeks_projection": 28.0,
        }
        braelon = {
            "yahoo_player_id": "braelon",
            "name": "Braelon Allen",
            "position": "RB",
            "team": "NYJ",
            "weeks": {
                "4": {
                    "projection": 8.0,
                }
            },
            "next_4_weeks_projection": 32.0,
        }
        roster = [puka, sutton]
        provider_status = {
            "captured_at": datetime(
                2026,
                9,
                30,
                12,
                0,
                tzinfo=UTC,
            )
        }

        def transaction_moves(*args, **kwargs):
            protected = kwargs.get(
                "cant_cut_ids",
                set(),
            )
            drop = (
                sutton
                if "puka" in protected
                else puka
            )
            return [
                {
                    "add": braelon,
                    "drop": drop,
                    "score": 2.0,
                    "bye_score_adjustment": 0.0,
                    "label": "ADD",
                    "move_type": "DEPTH UPGRADE",
                    "reasons": [],
                }
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
                "waiver_priority": 10,
            },
        ), patch.object(
            available_engine,
            "load_week_cant_cut",
            side_effect=[
                [],
                [
                    {
                        "player_id": "puka",
                        "player_name": "Puka Nacua",
                    }
                ],
            ],
        ), patch.object(
            available_engine,
            "get_effective_available_players",
            return_value=[braelon],
        ), patch.object(
            available_engine.yahoo_provider,
            "get_status",
            return_value=provider_status,
        ), patch.object(
            available_engine,
            "build_transaction_recommendations",
            side_effect=transaction_moves,
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
            unprotected = build_available_rankings(
                2026,
                4,
                limit=1,
                sleeper_fetch=lambda *args, **kwargs:
                    [],
            )
            protected = build_available_rankings(
                2026,
                4,
                limit=1,
                sleeper_fetch=lambda *args, **kwargs:
                    [],
            )

        self.assertEqual(
            unprotected["rankings"][0][
                "best_drop"
            ]["name"],
            "Puka Nacua",
        )
        self.assertEqual(
            protected["rankings"][0][
                "best_drop"
            ]["name"],
            "Courtland Sutton",
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
                tzinfo=UTC,
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
                tzinfo=UTC,
            ),
            "generated_at": datetime(
                2026,
                9,
                21,
                12,
                1,
                tzinfo=UTC,
            ),
        }
        refreshed_status = {
            **provider_status,
            "generated_at": datetime(
                2026,
                9,
                21,
                12,
                2,
                tzinfo=UTC,
            ),
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
            side_effect=[
                provider_status,
                refreshed_status,
            ],
        ), patch.object(
            available_engine,
            "build_transaction_recommendations",
            return_value=[],
        ) as builder, patch.object(
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
            refreshed = build_available_rankings(
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

        self.assertEqual(
            len(refreshed["rankings"]),
            1,
        )
        self.assertEqual(
            builder.call_count,
            2,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

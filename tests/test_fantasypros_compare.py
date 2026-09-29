import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import fantasypros_compare


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FantasyProsCompareTests(TestCase):
    def test_resolves_player_by_yahoo_id(self):
        database = [
            {
                "id": 123,
                "name": "Example Player",
                "position": "QB",
                "team": "BUF",
                "yahoo_id": "999",
            }
        ]

        result = fantasypros_compare.resolve_fantasypros_player(
            {
                "name": "Different Name",
                "position": "QB",
                "team": "BUF",
                "yahoo_player_id": "999",
            },
            database=database,
        )

        self.assertEqual(result["id"], "123")

    def test_resolves_canonical_catalog_shape(self):
        result = fantasypros_compare.resolve_fantasypros_player(
            {
                "name": "Mike Evans",
                "position": "WR",
                "team": "SF",
            },
            database=[
                {
                    "player_id": 9999,
                    "player_name": "Mike Evans",
                    "position_id": "WR",
                    "team_id": "SF",
                }
            ],
        )

        self.assertEqual(result["id"], "9999")
        self.assertEqual(result["position"], "WR")

    def test_rejects_synthetic_database_id(self):
        result = fantasypros_compare.resolve_fantasypros_player(
            {
                "name": "Example Player",
                "position": "WR",
                "team": "DEN",
            },
            database=[
                {
                    "id": "adp-exampleplayer",
                    "name": "Example Player",
                    "position": "WR",
                    "team": "DEN",
                }
            ],
        )

        self.assertIsNone(result)

    def test_refresh_player_catalog_caches_players(self):
        with TemporaryDirectory() as directory:
            catalog_file = Path(directory) / "players.json"
            payload = {
                "players": [
                    {
                        "player_id": 101,
                        "player_name": "Example Player",
                        "position_id": "QB",
                        "team_id": "BUF",
                    }
                ]
            }

            with patch.object(
                fantasypros_compare,
                "API_KEY",
                "test-key",
            ), patch.object(
                fantasypros_compare,
                "PLAYER_CATALOG_FILE",
                catalog_file,
            ), patch.object(
                fantasypros_compare.requests,
                "get",
                return_value=FakeResponse(payload),
            ) as request, patch.object(
                fantasypros_compare,
                "record_api_call",
                Mock(),
            ):
                players = fantasypros_compare.refresh_player_catalog()

            self.assertEqual(players, payload["players"])
            self.assertTrue(catalog_file.exists())
            self.assertTrue(request.call_args.args[0].endswith("/players"))

    def test_fetches_specific_half_ppr_players_and_caches(self):
        with TemporaryDirectory() as directory:
            cache_file = Path(directory) / "comparisons.json"
            calls = []

            def fake_get(url, headers, params, timeout):
                calls.append((url, params.copy()))
                return FakeResponse({"ok": True})

            resolved = [
                {
                    "id": "101",
                    "name": "A",
                    "position": "QB",
                    "team": "BUF",
                },
                {
                    "id": "202",
                    "name": "B",
                    "position": "QB",
                    "team": "CIN",
                },
            ]

            with patch.object(
                fantasypros_compare,
                "API_KEY",
                "test-key",
            ), patch.object(
                fantasypros_compare,
                "CACHE_FILE",
                cache_file,
            ), patch.object(
                fantasypros_compare,
                "_resolve_players",
                return_value=resolved,
            ), patch.object(
                fantasypros_compare.requests,
                "get",
                side_effect=fake_get,
            ), patch.object(
                fantasypros_compare,
                "record_api_call",
                Mock(),
            ):
                first = fantasypros_compare.fetch_targeted_comparison(
                    [
                        {"name": "A"},
                        {"name": "B"},
                    ],
                    week=2,
                    position="QB",
                )
                second = fantasypros_compare.fetch_targeted_comparison(
                    [
                        {"name": "B"},
                        {"name": "A"},
                    ],
                    week=2,
                    position="QB",
                )

            self.assertEqual(len(calls), 2)
            projection_params = calls[0][1]
            self.assertEqual(projection_params["week"], 2)
            self.assertEqual(projection_params["scoring"], "HALF")
            self.assertEqual(projection_params["position"], "QB")
            self.assertEqual(projection_params["players"], "101:202")
            self.assertEqual(first, second)
            self.assertTrue(cache_file.exists())

    def test_flex_uses_multi_position_projection_filter(self):
        with TemporaryDirectory() as directory:
            cache_file = Path(directory) / "comparisons.json"
            calls = []

            def fake_get(url, headers, params, timeout):
                calls.append((url, params.copy()))
                return FakeResponse({"ok": True})

            resolved = [
                {
                    "id": "301",
                    "name": "WR",
                    "position": "WR",
                    "team": "TB",
                },
                {
                    "id": "302",
                    "name": "RB",
                    "position": "RB",
                    "team": "TEN",
                },
            ]

            with patch.object(
                fantasypros_compare,
                "API_KEY",
                "test-key",
            ), patch.object(
                fantasypros_compare,
                "CACHE_FILE",
                cache_file,
            ), patch.object(
                fantasypros_compare,
                "_resolve_players",
                return_value=resolved,
            ), patch.object(
                fantasypros_compare.requests,
                "get",
                side_effect=fake_get,
            ), patch.object(
                fantasypros_compare,
                "record_api_call",
                Mock(),
            ):
                fantasypros_compare.fetch_targeted_comparison(
                    [
                        {"name": "WR"},
                        {"name": "RB"},
                    ],
                    week=2,
                    position="FLEX",
                )

            projection_params = calls[0][1]
            comparison_params = calls[1][1]

            self.assertNotIn("position", projection_params)
            self.assertEqual(
                projection_params["positions"],
                "RB:WR:TE",
            )
            self.assertEqual(
                comparison_params["position"],
                "FLX",
            )


if __name__ == "__main__":
    import unittest

    unittest.main()

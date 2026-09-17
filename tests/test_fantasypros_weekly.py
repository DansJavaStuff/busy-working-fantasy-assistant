import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import fantasypros_weekly


class FakeResponse:
    def __init__(self, position):
        self.position = position
        self.headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "players": [
                {
                    "player_id": f"{self.position}-1",
                    "player_name": f"{self.position} Player",
                    "player_position_id": self.position,
                    "player_team_id": "BUF",
                    "rank_ecr": 1,
                    "pos_rank": f"{self.position}1",
                    "tier": 1,
                }
            ]
        }


class FantasyProsWeeklyTests(TestCase):
    def test_refresh_requests_current_week_for_each_feed(self):
        with TemporaryDirectory() as directory:
            cache_file = (
                Path(directory)
                / "fantasypros_weekly.json"
            )

            calls = []

            def fake_get(url, headers, params, timeout):
                calls.append(
                    {
                        "url": url,
                        "headers": headers,
                        "params": params,
                        "timeout": timeout,
                    }
                )
                return FakeResponse(
                    params["position"]
                )

            with patch.object(
                fantasypros_weekly,
                "API_KEY",
                "test-key",
            ), patch.object(
                fantasypros_weekly,
                "CACHE_FILE",
                cache_file,
            ), patch.object(
                fantasypros_weekly.requests,
                "get",
                side_effect=fake_get,
            ), patch.object(
                fantasypros_weekly,
                "record_api_call",
                Mock(),
            ):
                cache = (
                    fantasypros_weekly
                    .refresh_weekly_cache(2)
                )

            self.assertEqual(
                len(calls),
                len(fantasypros_weekly.POSITIONS),
            )

            self.assertTrue(
                all(
                    call["params"]["week"] == 2
                    for call in calls
                )
            )

            self.assertEqual(cache["week"], 2)
            self.assertEqual(
                set(cache["feeds"]),
                set(fantasypros_weekly.POSITIONS),
            )
            self.assertTrue(cache_file.exists())

    def test_cache_from_another_week_is_not_used(self):
        with TemporaryDirectory() as directory:
            cache_file = (
                Path(directory)
                / "fantasypros_weekly.json"
            )

            cache_file.write_text(
                json.dumps(
                    {
                        "season": 2026,
                        "week": 1,
                        "feeds": {},
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(
                fantasypros_weekly,
                "CACHE_FILE",
                cache_file,
            ):
                self.assertIsNone(
                    fantasypros_weekly
                    .load_weekly_cache(2)
                )

                self.assertIsNotNone(
                    fantasypros_weekly
                    .load_weekly_cache(1)
                )


if __name__ == "__main__":
    import unittest

    unittest.main()

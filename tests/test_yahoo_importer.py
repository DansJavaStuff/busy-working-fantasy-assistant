from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from tools import import_yahoo_players
from yahoo_provider import (
    current_fantasy_week,
    normalise_week,
)


class YahooImporterFilenameTests(TestCase):
    def test_player_snapshot_names_are_discovered(self):
        prefix = (
            import_yahoo_players
            .PLAYER_SOURCE_PREFIX
        )

        cases = {
            "Yahoo_Player_list_week2-Proj.html":
                "week_2_projection",
            "Yahoo_Player_list_week2-Proj2.html":
                "week_2_projection",
            "Yahoo_Player_list_K_week2-Proj.html":
                "week_2_projection",
            "Yahoo_Player_list_DEF_week2-Proj.html":
                "week_2_projection",
            "Yahoo_Player_list_week2-Actual.html":
                "week_2_actual",
            "Yahoo_Player_list_week7-Proj-page2.html":
                "week_7_projection",
            "Yahoo_Player_list_4week-Proj.html":
                "next_4_weeks_projection",
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = (
                    import_yahoo_players
                    .snapshot_name_from_filename(
                        Path(filename),
                        prefix,
                    )
                )

                self.assertEqual(
                    result,
                    expected,
                )

    def test_discovery_merges_paginated_and_specialist_pages(self):
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)

            for filename in (
                "Yahoo_Player_list_week2-Proj.html",
                "Yahoo_Player_list_week2-Proj2.html",
                "Yahoo_Player_list_K_week2-Proj.html",
                "Yahoo_Player_list_DEF_week2-Proj.html",
                "Yahoo_Player_list_week2-Actual.html",
                "Yahoo_Player_list_week3-Proj.html",
                "ignore-me.html",
            ):
                (
                    data_dir
                    / filename
                ).write_text(
                    "",
                    encoding="utf-8",
                )

            with patch.object(
                import_yahoo_players,
                "DATA_DIR",
                data_dir,
            ):
                discovered = (
                    import_yahoo_players
                    .discover_source_files(
                        import_yahoo_players
                        .PLAYER_SOURCE_PREFIX
                    )
                )

            self.assertEqual(
                len(
                    discovered[
                        "week_2_projection"
                    ]
                ),
                4,
            )

            self.assertEqual(
                len(
                    discovered[
                        "week_2_actual"
                    ]
                ),
                1,
            )

            self.assertEqual(
                len(
                    discovered[
                        "week_3_projection"
                    ]
                ),
                1,
            )


class YahooProviderWeekTests(TestCase):
    def test_fantasy_week_advances_on_tuesday(self):
        self.assertEqual(
            current_fantasy_week(
                2026,
                date(2026, 9, 14),
            ),
            1,
        )

        self.assertEqual(
            current_fantasy_week(
                2026,
                date(2026, 9, 15),
            ),
            2,
        )

    def test_current_week_preserves_historical_week_one_data(self):
        player = {
            "name": "Example Player",
            "week_1_projection": 8.5,
            "week_1_actual": 11.2,
            "week_2_projection": 14.0,
            "week_2_actual": None,
            "week_2_game_display":
                "Sun 1:00 pm @ BUF",
            "week_2_game_day": "Sun",
            "week_2_game_time": "1:00 pm",
            "week_2_opponent": "BUF",
            "week_2_home_away": "away",
        }

        result = normalise_week(
            player,
            2,
        )

        self.assertEqual(
            result[
                "current_week_projection"
            ],
            14.0,
        )

        self.assertIsNone(
            result[
                "current_week_actual"
            ]
        )

        # Historical Week 1 values remain historical data.
        self.assertEqual(
            result[
                "week_1_projection"
            ],
            8.5,
        )

        self.assertEqual(
            result[
                "week_1_actual"
            ],
            11.2,
        )

        # Critical regression check: callers must use the explicit
        # current-week fields for Week 2 lock/projection decisions.
        self.assertEqual(
            result["game_day"],
            "Sun",
        )

        self.assertEqual(
            result["opponent"],
            "BUF",
        )


class YahooImporterParseCacheTests(TestCase):
    def test_unchanged_file_reuses_cached_parse(self):
        with TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "Yahoo_MyTeam_week2-Actual.html"
            )
            path.write_text(
                "first snapshot",
                encoding="utf-8",
            )

            cache = {
                "version":
                    import_yahoo_players
                    .PARSE_CACHE_VERSION,
                "files": {},
            }

            parsed = {
                "1": {
                    "name": "Example Player",
                }
            }

            with patch.object(
                import_yahoo_players,
                "parse_page",
                return_value=parsed,
            ) as parser:
                first, first_cached = (
                    import_yahoo_players
                    .parse_page_cached(
                        path,
                        cache,
                    )
                )

                second, second_cached = (
                    import_yahoo_players
                    .parse_page_cached(
                        path,
                        cache,
                    )
                )

            self.assertFalse(first_cached)
            self.assertTrue(second_cached)
            self.assertEqual(first, parsed)
            self.assertEqual(second, parsed)
            self.assertEqual(
                parser.call_count,
                1,
            )

    def test_changed_file_is_reparsed(self):
        with TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "Yahoo_MyTeam_week2-Actual.html"
            )
            path.write_text(
                "first",
                encoding="utf-8",
            )

            cache = {
                "version":
                    import_yahoo_players
                    .PARSE_CACHE_VERSION,
                "files": {},
            }

            with patch.object(
                import_yahoo_players,
                "parse_page",
                side_effect=[
                    {"1": {"projection": 1.0}},
                    {"1": {"projection": 2.0}},
                ],
            ) as parser:
                (
                    import_yahoo_players
                    .parse_page_cached(
                        path,
                        cache,
                    )
                )

                path.write_text(
                    "second snapshot is larger",
                    encoding="utf-8",
                )

                second, second_cached = (
                    import_yahoo_players
                    .parse_page_cached(
                        path,
                        cache,
                    )
                )

            self.assertFalse(second_cached)
            self.assertEqual(
                second["1"]["projection"],
                2.0,
            )
            self.assertEqual(
                parser.call_count,
                2,
            )

    def test_old_cache_version_is_discarded(self):
        with TemporaryDirectory() as directory:
            cache_path = (
                Path(directory)
                / "cache.json"
            )
            cache_path.write_text(
                '{"version": 0, "files": {"old": {}}}',
                encoding="utf-8",
            )

            with patch.object(
                import_yahoo_players,
                "PARSE_CACHE_FILE",
                cache_path,
            ):
                cache = (
                    import_yahoo_players
                    .load_parse_cache()
                )

            self.assertEqual(
                cache["version"],
                import_yahoo_players
                .PARSE_CACHE_VERSION,
            )
            self.assertEqual(
                cache["files"],
                {},
            )

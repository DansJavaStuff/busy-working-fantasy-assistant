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


class YahooImporterCombinedSourceTests(TestCase):
    def test_player_and_my_team_pages_share_one_snapshot_bucket(self):
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)

            player_file = (
                data_dir
                / "Yahoo_Player_list_week3-Proj.html"
            )
            team_file = (
                data_dir
                / "Yahoo_MyTeam_week3-Proj.html"
            )

            player_file.write_text(
                "",
                encoding="utf-8",
            )
            team_file.write_text(
                "",
                encoding="utf-8",
            )

            with patch.object(
                import_yahoo_players,
                "DATA_DIR",
                data_dir,
            ):
                player_sources = (
                    import_yahoo_players
                    .discover_source_files(
                        import_yahoo_players
                        .PLAYER_SOURCE_PREFIX
                    )
                )
                team_sources = (
                    import_yahoo_players
                    .discover_source_files(
                        import_yahoo_players
                        .MY_TEAM_SOURCE_PREFIX
                    )
                )

            combined = (
                import_yahoo_players
                .merge_source_maps(
                    player_sources,
                    team_sources,
                )
            )

            self.assertEqual(
                len(
                    combined[
                        "week_3_projection"
                    ]
                ),
                2,
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


class YahooImporterTableParsingTests(TestCase):
    def test_cant_cut_actions_use_yahoo_semantic_markers(self):
        html = """
        <table><tbody>
          <tr>
            <td>
              <a class="noactioncc-cantcut T-action-icon-cantcut"
                 title="Player is on can't cut list">x</a>
            </td>
            <td>
              <a data-ys-playerid="30977">Josh Allen</a>
              <span>BUF - QB</span>
            </td>
          </tr>
          <tr>
            <td>
              <a class="T-action-icon-drop" title="Drop Player">x</a>
            </td>
            <td>
              <a data-ys-playerid="31905">David Montgomery</a>
              <span>DET - RB</span>
            </td>
          </tr>
        </tbody></table>
        """

        with TemporaryDirectory() as directory:
            path = Path(directory) / "Yahoo_MyTeam_4week-Proj.html"
            path.write_text(html, encoding="utf-8")

            actions = (
                import_yahoo_players
                .parse_cant_cut_actions(path)
            )

        self.assertEqual(
            actions["30977"]["action"],
            "cant_cut",
        )
        self.assertEqual(
            actions["31905"]["action"],
            "drop",
        )

    def test_complete_my_team_pages_replace_week_cant_cut_list(self):
        html = """
        <table><tbody>
          <tr>
            <td><a class="T-action-icon-cantcut"
                   title="Player is on can't cut list">x</a></td>
            <td><a data-ys-playerid="30977">Josh Allen</a>
                <span>BUF - QB</span></td>
          </tr>
          <tr>
            <td><a class="T-action-icon-drop"
                   title="Drop Player">x</a></td>
            <td><a data-ys-playerid="31905">David Montgomery</a>
                <span>DET - RB</span></td>
          </tr>
        </tbody></table>
        """
        local_roster = [
            {
                "player_name": "Josh Allen",
                "position": "QB",
                "team": "BUF",
            },
            {
                "player_name": "David Montgomery",
                "position": "RB",
                "team": "DET",
            },
            {
                "player_name": "Example Kicker",
                "position": "K",
                "team": "BUF",
            },
            {
                "player_name": "Example Defence",
                "position": "DEF",
                "team": "BUF",
            },
        ]

        with TemporaryDirectory() as directory:
            path = Path(directory) / "Yahoo_MyTeam_4week-Proj.html"
            path.write_text(html, encoding="utf-8")
            sources = {
                "next_4_weeks_projection": [path],
            }

            with patch.object(
                import_yahoo_players,
                "replace_week_cant_cut",
            ) as replace:
                synced = (
                    import_yahoo_players
                    .sync_cant_cut_from_my_team(
                        sources,
                        local_roster,
                        week=4,
                    )
                )

        self.assertTrue(synced)
        replace.assert_called_once()
        args, kwargs = replace.call_args
        self.assertEqual(args[0], 4)
        self.assertEqual(
            args[1],
            [
                {
                    "player_id": "30977",
                    "player_name": "Josh Allen",
                    "source": "yahoo_html",
                }
            ],
        )
        self.assertEqual(kwargs["season"], 2026)

    def test_partial_my_team_page_preserves_existing_cant_cut_list(self):
        html = """
        <table><tbody><tr>
          <td><a class="T-action-icon-cantcut"
                 title="Player is on can't cut list">x</a></td>
          <td><a data-ys-playerid="30977">Josh Allen</a>
              <span>BUF - QB</span></td>
        </tr></tbody></table>
        """
        local_roster = [
            {
                "player_name": "Josh Allen",
                "position": "QB",
                "team": "BUF",
            },
            {
                "player_name": "David Montgomery",
                "position": "RB",
                "team": "DET",
            },
        ]

        with TemporaryDirectory() as directory:
            path = Path(directory) / "Yahoo_MyTeam_4week-Proj.html"
            path.write_text(html, encoding="utf-8")

            with patch.object(
                import_yahoo_players,
                "replace_week_cant_cut",
            ) as replace:
                synced = (
                    import_yahoo_players
                    .sync_cant_cut_from_my_team(
                        {
                            "next_4_weeks_projection": [path],
                        },
                        local_roster,
                        week=4,
                    )
                )

        self.assertFalse(synced)
        replace.assert_not_called()

    def test_one_unknown_action_is_tolerated_with_strong_coverage(self):
        rows = []
        local_roster = []

        for index in range(5):
            action = (
                '<a class="T-action-icon-drop" title="Drop Player">x</a>'
                if index < 4
                else ""
            )
            rows.append(
                f"""
                <tr>
                  <td>{action}</td>
                  <td><a data-ys-playerid="{index}">Player {index}</a>
                      <span>BUF - WR</span></td>
                </tr>
                """
            )
            local_roster.append(
                {
                    "player_name": f"Player {index}",
                    "position": "WR",
                    "team": "BUF",
                }
            )

        html = "<table><tbody>" + "".join(rows) + "</tbody></table>"

        with TemporaryDirectory() as directory:
            path = Path(directory) / "Yahoo_MyTeam_4week-Proj.html"
            path.write_text(html, encoding="utf-8")

            with patch.object(
                import_yahoo_players,
                "replace_week_cant_cut",
            ) as replace:
                synced = (
                    import_yahoo_players
                    .sync_cant_cut_from_my_team(
                        {
                            "next_4_weeks_projection": [path],
                        },
                        local_roster,
                        week=4,
                    )
                )

        self.assertTrue(synced)
        replace.assert_called_once()

    def test_projection_uses_proj_pts_not_bye_column(self):
        html = """
        <table>
          <thead>
            <tr>
              <th>Pos</th>
              <th>Offense</th>
              <th>Roster Status</th>
              <th>Bye</th>
              <th>Fan Pts \ue002</th>
              <th>Proj Pts \ue002</th>
              <th>% Start</th>
              <th>% Ros</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>QB</td>
              <td>
                <a data-ys-playerid="30123">Josh Allen</a>
                <span>BUF - QB</span>
                <span>Sun 1:00 pm vs LAC</span>
              </td>
              <td>FA</td>
              <td>7</td>
              <td>-</td>
              <td>24.84</td>
              <td>99%</td>
              <td>100%</td>
            </tr>
          </tbody>
        </table>
        """

        with TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "Yahoo_MyTeam_week3-Proj.html"
            )
            path.write_text(
                html,
                encoding="utf-8",
            )

            players = (
                import_yahoo_players
                .parse_page(path)
            )

        player = players["30123"]

        self.assertEqual(
            player["bye_week"],
            7,
        )
        self.assertEqual(
            player["projection"],
            24.84,
        )
        self.assertEqual(
            player["rostered_pct"],
            100.0,
        )
        self.assertEqual(
            player["roster_status"],
            "FA",
        )
        self.assertEqual(
            player["opponent"],
            "LAC",
        )

    def test_actual_snapshot_uses_fan_pts(self):
        html = """
        <table>
          <thead>
            <tr>
              <th>Pos</th>
              <th>Offense</th>
              <th>Bye</th>
              <th>Fan Pts \ue002</th>
              <th>Proj Pts \ue002</th>
              <th>% Start</th>
              <th>% Ros</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>QB</td>
              <td>
                <a data-ys-playerid="30123">Josh Allen</a>
                <span>BUF - QB</span>
              </td>
              <td>7</td>
              <td>43.82</td>
              <td>25.55</td>
              <td>99%</td>
              <td>100%</td>
            </tr>
          </tbody>
        </table>
        """

        with TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "Yahoo_MyTeam_week2-Actual.html"
            )
            path.write_text(
                html,
                encoding="utf-8",
            )

            players = (
                import_yahoo_players
                .parse_page(path)
            )

        self.assertEqual(
            players["30123"][
                "projection"
            ],
            43.82,
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

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import os

from tools import html_fallback_import
from tools import import_yahoo_players


class HtmlFallbackImportTests(TestCase):
    def test_html_metadata_wins_over_filename(self):
        html = """
        <html>
          <body>
            <select>
              <option value="S_PW_7" selected>Week 7 (proj)</option>
            </select>
          </body>
        </html>
        """

        with TemporaryDirectory() as directory:
            path = Path(directory) / "Yahoo_Player_list_week2-Proj.html"
            path.write_text(html, encoding="utf-8")

            result = html_fallback_import.classify_snapshot(
                path,
                import_yahoo_players.PLAYER_SOURCE_PREFIX,
            )

        self.assertEqual(
            result["snapshot_name"],
            "week_7_projection",
        )
        self.assertEqual(result["source"], "html")

    def test_filename_is_used_when_html_is_unclassifiable(self):
        html = "<html><body><p>saved Yahoo page</p></body></html>"

        with TemporaryDirectory() as directory:
            path = Path(directory) / "Yahoo_Player_list_week5-Proj.html"
            path.write_text(html, encoding="utf-8")

            result = html_fallback_import.classify_snapshot(
                path,
                import_yahoo_players.PLAYER_SOURCE_PREFIX,
            )

        self.assertEqual(
            result["snapshot_name"],
            "week_5_projection",
        )
        self.assertEqual(
            result["source"],
            "filename_fallback",
        )

    def test_discovery_groups_pages_by_html_metadata(self):
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)

            cases = {
                "Yahoo_Player_list_alpha.html": "Week 3 (proj)",
                "Yahoo_Player_list_beta.html": "Week 3 (proj)",
                "Yahoo_Player_list_gamma.html": "Week 3",
                "Yahoo_Player_list_delta.html": "Next 4 Weeks (proj)",
            }

            for filename, label in cases.items():
                (data_dir / filename).write_text(
                    f"""
                    <html><body><select>
                    <option value="S_TEST" selected>{label}</option>
                    </select></body></html>
                    """,
                    encoding="utf-8",
                )

            with patch.object(
                import_yahoo_players,
                "DATA_DIR",
                data_dir,
            ), patch.object(
                import_yahoo_players,
                "PARSE_CACHE_FILE",
                data_dir / "yahoo_html_store.json",
            ):
                discovered, diagnostics = (
                    html_fallback_import.discover_source_files(
                        import_yahoo_players.PLAYER_SOURCE_PREFIX
                    )
                )

        self.assertEqual(
            len(discovered["week_3_projection"]),
            2,
        )
        self.assertEqual(
            len(discovered["week_3_actual"]),
            1,
        )
        self.assertEqual(
            len(discovered["next_4_weeks_projection"]),
            1,
        )
        self.assertEqual(diagnostics["html"], 4)
        self.assertEqual(diagnostics["filename_fallback"], 0)
        self.assertEqual(diagnostics["unknown"], 0)

    def test_newest_duplicate_snapshot_is_processed_last(self):
        html = """
        <html><body><select>
        <option value="S_PW_2" selected>Week 2 (proj)</option>
        </select></body></html>
        """

        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            older = data_dir / "Yahoo_Player_list_week2-Proj.html"
            newer = data_dir / "Yahoo_Player_list_week2-Proj (1).html"

            older.write_text(html, encoding="utf-8")
            newer.write_text(html, encoding="utf-8")

            os.utime(older, (1000, 1000))
            os.utime(newer, (2000, 2000))

            with patch.object(
                import_yahoo_players,
                "DATA_DIR",
                data_dir,
            ), patch.object(
                import_yahoo_players,
                "PARSE_CACHE_FILE",
                data_dir / "yahoo_html_store.json",
            ):
                discovered, _ = (
                    html_fallback_import.discover_source_files(
                        import_yahoo_players.PLAYER_SOURCE_PREFIX
                    )
                )

        paths = discovered["week_2_projection"]
        self.assertEqual(paths[0].name, older.name)
        self.assertEqual(paths[-1].name, newer.name)


    def test_unchanged_file_reuses_cached_metadata(self):
        html = """
        <html><body><select>
        <option value="S_PW_2" selected>Week 2 (proj)</option>
        </select></body></html>
        """

        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            path = (
                data_dir
                / "Yahoo_Player_list_week2-Proj.html"
            )
            path.write_text(
                html,
                encoding="utf-8",
            )
            store_path = (
                data_dir
                / "yahoo_html_store.json"
            )

            with patch.object(
                import_yahoo_players,
                "DATA_DIR",
                data_dir,
            ), patch.object(
                import_yahoo_players,
                "PARSE_CACHE_FILE",
                store_path,
            ):
                _, first = (
                    html_fallback_import
                    .discover_source_files(
                        import_yahoo_players
                        .PLAYER_SOURCE_PREFIX
                    )
                )

                with patch.object(
                    html_fallback_import,
                    "classify_snapshot",
                    side_effect=AssertionError(
                        "unchanged HTML should not be reopened"
                    ),
                ):
                    discovered, second = (
                        html_fallback_import
                        .discover_source_files(
                            import_yahoo_players
                            .PLAYER_SOURCE_PREFIX
                        )
                    )

        self.assertEqual(
            first["classification_read"],
            1,
        )
        self.assertEqual(
            second["classification_reused"],
            1,
        )
        self.assertEqual(
            len(discovered["week_2_projection"]),
            1,
        )

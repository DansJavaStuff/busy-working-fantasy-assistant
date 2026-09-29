from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import app as app_module
import database
from daily_checklist import (
    checklist_for_day,
    tomorrow_checklist,
)


class DailyChecklistDefinitionTests(TestCase):
    def test_tuesday_matches_waiver_planning_workflow(self):
        checklist = checklist_for_day(
            date(2026, 9, 29)
        )

        self.assertEqual(
            checklist["day_name"],
            "Tuesday",
        )
        self.assertEqual(
            checklist["focus"],
            "Prepare this week's waiver claims",
        )
        self.assertEqual(
            [
                task["key"]
                for task in checklist["tasks"]
            ],
            [
                "tuesday_refresh",
                "tuesday_settings",
                "tuesday_history",
                "tuesday_claims",
                "tuesday_lineup",
            ],
        )

    def test_tuesday_preview_advances_to_waiver_results(self):
        preview = tomorrow_checklist(
            date(2026, 9, 29)
        )

        self.assertEqual(
            preview["day_name"],
            "Wednesday",
        )
        self.assertEqual(
            preview["tasks"][0]["key"],
            "wednesday_results",
        )


class DailyChecklistDatabaseTests(TestCase):
    def test_progress_can_be_checked_and_cleared(self):
        with TemporaryDirectory() as temp_dir:
            db_file = (
                Path(temp_dir)
                / "fantasy_assistant.db"
            )

            with patch.object(
                database,
                "DB_FILE",
                db_file,
            ), patch.object(
                database,
                "BACKUP_DIR",
                Path(temp_dir) / "backups",
            ):
                checklist_date = date(
                    2026,
                    9,
                    29,
                )

                database.set_daily_checklist_item(
                    checklist_date,
                    "tuesday_refresh",
                    True,
                    season=2026,
                )

                self.assertEqual(
                    database.load_daily_checklist_progress(
                        checklist_date,
                        season=2026,
                    ),
                    {"tuesday_refresh"},
                )

                database.set_daily_checklist_item(
                    checklist_date,
                    "tuesday_refresh",
                    False,
                    season=2026,
                )

                self.assertEqual(
                    database.load_daily_checklist_progress(
                        checklist_date,
                        season=2026,
                    ),
                    set(),
                )


class DailyChecklistRouteTests(TestCase):
    def test_today_page_and_checkbox_update(self):
        with TemporaryDirectory() as temp_dir:
            db_file = (
                Path(temp_dir)
                / "fantasy_assistant.db"
            )
            checklist_date = date(
                2026,
                9,
                29,
            )

            with patch.object(
                database,
                "DB_FILE",
                db_file,
            ), patch.object(
                database,
                "BACKUP_DIR",
                Path(temp_dir) / "backups",
            ), patch.object(
                app_module,
                "current_uk_date",
                return_value=checklist_date,
            ):
                client = app_module.app.test_client()

                response = client.get(
                    "/today"
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.assertIn(
                    b"Prepare this week&#39;s waiver claims",
                    response.data,
                )
                self.assertIn(
                    b"Reconcile waivers and update the roster",
                    response.data,
                )
                self.assertLess(
                    response.data.index(b'href="/today"'),
                    response.data.index(b'href="/weekly"'),
                )
                self.assertLess(
                    response.data.index(b'href="/available"'),
                    response.data.index(b'href="/my-team"'),
                )
                self.assertLess(
                    response.data.index(b'href="/my-team"'),
                    response.data.index(b'href="/history"'),
                )
                self.assertLess(
                    response.data.index(b'href="/history"'),
                    response.data.index(b'href="/draft"'),
                )

                response = client.post(
                    "/today/checklist",
                    data={
                        "task_key": "tuesday_refresh",
                        "completed": "1",
                    },
                    follow_redirects=True,
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.assertIn(
                    b"1 / 5 complete",
                    response.data,
                )
                self.assertEqual(
                    database.load_daily_checklist_progress(
                        checklist_date,
                        season=2026,
                    ),
                    {"tuesday_refresh"},
                )

    def test_invalid_task_is_not_saved(self):
        with TemporaryDirectory() as temp_dir:
            db_file = (
                Path(temp_dir)
                / "fantasy_assistant.db"
            )
            checklist_date = date(
                2026,
                9,
                29,
            )

            with patch.object(
                database,
                "DB_FILE",
                db_file,
            ), patch.object(
                app_module,
                "current_uk_date",
                return_value=checklist_date,
            ):
                client = app_module.app.test_client()
                response = client.post(
                    "/today/checklist",
                    data={
                        "task_key": "wednesday_results",
                        "completed": "1",
                    },
                    follow_redirects=True,
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.assertIn(
                    b"not part of today's workflow",
                    response.data,
                )
                self.assertEqual(
                    database.load_daily_checklist_progress(
                        checklist_date,
                        season=2026,
                    ),
                    set(),
                )


if __name__ == "__main__":
    import unittest

    unittest.main()

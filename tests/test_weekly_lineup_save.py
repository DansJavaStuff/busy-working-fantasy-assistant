from unittest import TestCase
from unittest.mock import patch

import app as app_module


def _weekly_data(*, started=False):
    starter = {
        "yahoo_player_id": "1",
        "name": "Starter",
        "position": "RB",
        "current_week_actual": (
            10.0
            if started
            else None
        ),
    }
    bench = {
        "yahoo_player_id": "2",
        "name": "Bench Player",
        "position": "WR",
        "current_week_actual": None,
    }

    return {
        "roster": [starter, bench],
        "lineup": [
            {
                "slot": "FLEX",
                "player": starter,
            }
        ],
        "bench": [bench],
        "ir_review": [],
    }


class WeeklyLineupSaveTests(TestCase):
    def test_existing_lineup_can_be_updated(self):
        existing = [
            {
                "player_id": "1",
                "lineup_slot": "FLEX",
            }
        ]

        with patch.object(
            app_module,
            "current_fantasy_week",
            return_value=4,
        ), patch.object(
            app_module,
            "load_week_lineup",
            return_value=existing,
        ), patch.object(
            app_module,
            "build_weekly_data",
            return_value=_weekly_data(),
        ), patch.object(
            app_module,
            "replace_week_lineup",
        ) as replace:
            response = (
                app_module.app.test_client()
                .post(
                    "/weekly/save-submitted-lineup"
                )
            )

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertIn(
            "lineup_updated=1",
            response.location,
        )
        replace.assert_called_once()

    def test_existing_lineup_can_update_after_a_player_locks(self):
        existing = [
            {
                "player_id": "1",
                "lineup_slot": "FLEX",
            }
        ]

        with patch.object(
            app_module,
            "current_fantasy_week",
            return_value=4,
        ), patch.object(
            app_module,
            "load_week_lineup",
            return_value=existing,
        ), patch.object(
            app_module,
            "build_weekly_data",
            return_value=_weekly_data(
                started=True,
            ),
        ), patch.object(
            app_module,
            "replace_week_lineup",
        ) as replace:
            response = (
                app_module.app.test_client()
                .post(
                    "/weekly/save-submitted-lineup"
                )
            )

        self.assertIn(
            "lineup_updated=1",
            response.location,
        )
        replace.assert_called_once()

    def test_first_save_is_blocked_after_week_starts(self):
        with patch.object(
            app_module,
            "current_fantasy_week",
            return_value=4,
        ), patch.object(
            app_module,
            "load_week_lineup",
            return_value=[],
        ), patch.object(
            app_module,
            "build_weekly_data",
            return_value=_weekly_data(
                started=True,
            ),
        ), patch.object(
            app_module,
            "replace_week_lineup",
        ) as replace:
            response = (
                app_module.app.test_client()
                .post(
                    "/weekly/save-submitted-lineup"
                )
            )

        self.assertIn(
            "lineup_locked=1",
            response.location,
        )
        replace.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()

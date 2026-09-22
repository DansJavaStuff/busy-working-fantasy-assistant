from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import database


class RecommendationActionDatabaseTests(TestCase):
    def test_record_list_and_resolve_action(self):
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
                database.initialise_database()

                action_id = (
                    database.record_recommendation_action(
                        season=2026,
                        week=3,
                        action_type="waiver_claim",
                        priority=2,
                        add_player_id="add-1",
                        add_player_name="C.J. Stroud",
                        add_position="QB",
                        drop_player_id="drop-1",
                        drop_player_name="Trevor Lawrence",
                        drop_position="QB",
                        recommendation_label="BYE FIX",
                        move_type="QB COVER",
                        recommendation_rank=1,
                    )
                )

                actions = (
                    database.list_recommendation_actions(
                        season=2026,
                    )
                )

                self.assertEqual(
                    len(actions),
                    1,
                )
                self.assertEqual(
                    actions[0]["id"],
                    action_id,
                )
                self.assertEqual(
                    actions[0]["status"],
                    "pending",
                )
                self.assertEqual(
                    actions[0]["priority"],
                    2,
                )

                database.update_recommendation_action_status(
                    action_id,
                    "succeeded",
                    season=2026,
                )

                updated = (
                    database.list_recommendation_actions(
                        season=2026,
                    )[0]
                )

                self.assertEqual(
                    updated["status"],
                    "succeeded",
                )
                self.assertIsNotNone(
                    updated["resolved_at"],
                )


if __name__ == "__main__":
    import unittest

    unittest.main()

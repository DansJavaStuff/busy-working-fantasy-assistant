import copy
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from flask import Flask

import database
import matchup_routes
from matchups import SLOTS, list_matchups, load_matchup, matchup_summary, save_matchups


def record(week=1, status="final"):
    result = {"week": week, "opponent": "Opponent", "status": status,
              "own_actual": 8, "opponent_actual": 9,
              "own_projection": 10, "opponent_projection": 11}
    for side in ("own", "opponent"):
        result[side + "_lineup"] = [
            {"slot": slot, "name": side + " " + slot,
             "position": "RB" if slot == "FLEX" else slot.rstrip("12"),
             "team": "GB", "projection": 1,
             "actual": (0 if slot == "DST" and side == "own" else 1),
             "state": "final" if status == "final" else "not_started"}
            for slot in SLOTS
        ]
    return result


class MatchupTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_patch = patch.object(database, "DB_FILE", Path(self.temp.name) / "test.db")
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        database.initialise_database()

    def test_round_trip_season_isolation_and_idempotent_import(self):
        save_matchups([record()])
        save_matchups([record()])
        self.assertEqual(len(list_matchups()), 1)
        self.assertEqual(list_matchups(2027), [])
        saved = load_matchup(1)
        self.assertEqual(saved["own_lineup"][-1]["actual"], 0)
        self.assertEqual(matchup_summary(saved)["result"], "Lost")
        with database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM matchup_revisions").fetchone()[0], 0)

    def test_final_protection_and_explicit_correction_retains_revision(self):
        save_matchups([record()])
        changed = record()
        changed["opponent"] = "Corrected opponent"
        with self.assertRaisesRegex(ValueError, "final"):
            save_matchups([changed])
        save_matchups([changed], correct_confirmed=True)
        self.assertEqual(load_matchup(1)["opponent"], "Corrected opponent")
        with database.connect() as db:
            previous = json.loads(db.execute("SELECT payload FROM matchup_revisions").fetchone()[0])
            self.assertEqual(previous["opponent"], "Opponent")

    def test_failed_batch_rolls_back_all_changes(self):
        save_matchups([record()])
        changed = record()
        changed["opponent"] = "Should not save"
        with self.assertRaises(ValueError):
            save_matchups([record(2), changed])
        self.assertIsNone(load_matchup(2))
        self.assertEqual(load_matchup(1)["opponent"], "Opponent")

    def test_reinitialisation_does_not_rewrite_historical_lineups(self):
        save_matchups([record()])
        original = load_matchup(1)
        database.initialise_database()
        self.assertEqual(load_matchup(1), original)

    def test_negative_scores_and_final_result(self):
        entry = record()
        entry["own_lineup"][-1]["actual"] = -2
        entry["own_actual"] = 6
        save_matchups([entry])
        self.assertEqual(load_matchup(1)["own_lineup"][-1]["actual"], -2)

    def test_unknown_scores_stay_unknown(self):
        save_matchups([{"week": 7, "opponent": "Next opponent"}])
        saved = load_matchup(7)
        self.assertIsNone(saved["own_actual"])
        self.assertEqual(matchup_summary(saved)["result"], "Not final")

    def test_reject_invalid_entries_before_writing(self):
        for change in (lambda m: m.update(week=18),
                       lambda m: m.update(own_actual=float("nan")),
                       lambda m: m.update(own_actual=999),
                       lambda m: m["own_lineup"].pop(),
                       lambda m: m["own_lineup"][0].update(actual=None),
                       lambda m: m["own_lineup"][0].update(position="WR"),
                       lambda m: m["own_lineup"][0].update(name=m["own_lineup"][1]["name"])):
            entry = record()
            change(entry)
            with self.assertRaises(ValueError):
                save_matchups([entry])
        self.assertEqual(list_matchups(), [])

    def test_locked_identity_is_protected_while_scores_can_update(self):
        entry = record(status="live")
        entry["own_lineup"][0]["state"] = "locked"
        save_matchups([entry])
        changed = copy.deepcopy(entry)
        changed["own_lineup"][0]["name"] = "Different player"
        with self.assertRaisesRegex(ValueError, "locked"):
            save_matchups([changed])
        changed = copy.deepcopy(entry)
        changed["own_lineup"][0]["state"] = "not_started"
        with self.assertRaisesRegex(ValueError, "locked"):
            save_matchups([changed])
        entry["own_lineup"][0]["actual"] = 5
        save_matchups([entry])
        self.assertEqual(load_matchup(1)["own_lineup"][0]["actual"], 5)

    def client(self):
        app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
        app.register_blueprint(matchup_routes.blueprint)
        for endpoint in ("settings_page", "weekly", "available_players", "today_page", "history", "my_team", "dashboard"):
            app.add_url_rule("/stub/" + endpoint, endpoint, lambda: "OK")
        return app.test_client()

    def test_page_renders_missing_and_completed_week_and_escapes_names(self):
        with patch.object(matchup_routes, "load_team_identity", return_value={"team_name": "Your team"}), \
             patch.object(matchup_routes, "opponent_names", return_value=[]):
            response = self.client().get("/matchup?week=7")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Opponent not set", response.data)
            entry = record()
            entry["opponent"] = "<script>bad</script>"
            save_matchups([entry])
            response = self.client().get("/matchup?week=1")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"&lt;script&gt;", response.data)
            self.assertNotIn(b"<script>bad", response.data)
            self.assertIn(b"Lost", response.data)

    def test_upload_import_and_validation_failure(self):
        response = self.client().post("/settings/import-matchups", data={
            "matchup_file": (io.BytesIO(json.dumps({"season": 2026, "matchups": [record()]}).encode()), "matchups.json")
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(list_matchups()), 1)
        response = self.client().post("/settings/import-matchups", data={
            "matchup_file": (io.BytesIO(b'{"season":2027}'), "wrong.json")
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(list_matchups()), 1)

    def test_manual_form_saves_and_preserves_invalid_draft(self):
        entry = record(7, status="live")
        form = {"week": "7", "opponent": entry["opponent"], "status": "final",
                "own_projection": 10, "opponent_projection": 11,
                "own_actual": 8, "opponent_actual": 9}
        for side in ("own", "opponent"):
            for row in entry[side + "_lineup"]:
                for field in ("name", "team", "position", "projection", "actual", "state"):
                    form[side + "_" + row["slot"] + "_" + field] = row[field]
        with patch.object(matchup_routes, "opponent_names", return_value=[]):
            response = self.client().post("/matchup/save", data=form)
            self.assertEqual(response.status_code, 302)
            form["opponent"] = "A correction to keep typed"
            response = self.client().post("/matchup/save", data=form)
            self.assertEqual(response.status_code, 400)
            self.assertIn(b"A correction to keep typed", response.data)
            self.assertEqual(load_matchup(7)["opponent"], "Opponent")
            form["correct_confirmed"] = "yes"
            response = self.client().post("/matchup/save", data=form)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(load_matchup(7)["opponent"], "A correction to keep typed")

    def test_schedule_keeps_lineups_and_rejects_final_opponent_change(self):
        save_matchups([record()])
        response = self.client().post("/settings/season-schedule", data={"opponent_1": "Different"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(load_matchup(1)["own_lineup"]), 9)
        response = self.client().post("/settings/season-schedule", data={"opponent_8": "Future opponent"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(load_matchup(8)["opponent"], "Future opponent")

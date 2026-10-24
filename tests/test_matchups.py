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
from matchups import fill_actuals_from_history, matchup_player_choices, selected_player_choice, SLOTS, list_matchups, load_matchup, matchup_summary, save_matchups


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


class MatchupActualsTests(TestCase):
    setUp = MatchupTests.setUp
    client = MatchupTests.client
    # Reuse the isolated database setup and route client, without rerunning base tests.
    def test_fill_uses_both_lineups_and_reconciles_zero_negative_totals(self):
        entry = record(7, "live")
        players = {}
        for side in ("own", "opponent"):
            for i, row in enumerate(entry[side + "_lineup"]):
                players[side + str(i)] = {"name": row["name"], "position": row["position"],
                    "team": row["team"], "weeks": {"7": {"actual": i - 2, "projection": 999}}}
        database.upsert_player_week_history(players, 2026)
        original = copy.deepcopy(entry)
        draft, filled, issues = fill_actuals_from_history(entry)
        self.assertEqual(entry, original)
        self.assertEqual(filled, 18)
        self.assertEqual(issues, [])
        self.assertEqual(draft["own_actual"], 18)
        self.assertEqual(draft["opponent_actual"], 18)
        self.assertEqual(draft["own_lineup"][0]["actual"], -2)
        self.assertEqual(draft["own_lineup"][2]["actual"], 0)
        self.assertEqual(draft["status"], "live")
        self.assertEqual(draft["own_projection"], 10)
        self.assertIsNone(load_matchup(7))
        draft["status"] = "final"
        save_matchups([draft])
        self.assertEqual(matchup_summary(load_matchup(7))["result"], "Tied")

    def test_wrong_week_season_and_projection_only_remain_unknown(self):
        entry = record(7, "live")
        row = entry["own_lineup"][0]
        player = {"p": {"name": row["name"], "position": "QB", "team": "GB",
                         "weeks": {"6": {"actual": 42}, "7": {"projection": 20}}}}
        database.upsert_player_week_history(player, 2026)
        player["p"]["weeks"] = {"7": {"actual": 99}}
        database.upsert_player_week_history(player, 2027)
        draft, filled, issues = fill_actuals_from_history(entry)
        self.assertEqual(filled, 0)
        self.assertEqual(len(issues), 18)
        self.assertIsNone(draft["own_actual"])
        self.assertIsNone(draft["own_lineup"][0]["actual"])

    def test_suffix_and_defence_aliases_and_team_disambiguation(self):
        entry = record(7, "live")
        entry["own_lineup"][0].update(name="Patrick Mahomes II", team="KC")
        entry["own_lineup"][-1].update(name="Jaguars", team="JAX")
        database.upsert_player_week_history({
            "p": {"name": "Patrick Mahomes", "position": "QB", "team": "KC", "weeks": {"7": {"actual": 20}}},
            "q": {"name": "Patrick Mahomes", "position": "QB", "team": "GB", "weeks": {"7": {"actual": 99}}},
            "d": {"name": "Jacksonville Jaguars", "position": "DEF", "team": "JAC", "weeks": {"7": {"actual": -1}}},
        }, 2026)
        draft, filled, _ = fill_actuals_from_history(entry)
        self.assertEqual(filled, 2)
        self.assertEqual(draft["own_lineup"][0]["actual"], 20)
        self.assertEqual(draft["own_lineup"][-1]["actual"], -1)

    def test_ambiguous_identity_and_team_mismatch_never_guess(self):
        entry = record(7, "live")
        name = entry["own_lineup"][0]["name"]
        database.upsert_player_week_history({
            str(i): {"name": name, "position": "QB", "team": "GB", "weeks": {"7": {"actual": i}}}
            for i in (1, 2)
        }, 2026)
        draft, _, issues = fill_actuals_from_history(entry)
        self.assertIsNone(draft["own_lineup"][0]["actual"])
        self.assertIn("ambiguous", issues[0])
        entry["own_lineup"][0]["team"] = "KC"
        draft, filled, _ = fill_actuals_from_history(entry)
        self.assertEqual(filled, 0)

    def test_form_preview_is_unsaved_and_final_record_stays_protected(self):
        entry = record(7)
        save_matchups([entry])
        row = entry["own_lineup"][0]
        database.upsert_player_week_history({"p": {"name": row["name"], "position": "QB", "team": "GB",
            "weeks": {"7": {"actual": 30}}}}, 2026)
        form = {"week": "7", "opponent": "Opponent", "status": "final", "action": "fill_actuals",
                "own_actual": 8, "opponent_actual": 9}
        for side in ("own", "opponent"):
            for r in entry[side + "_lineup"]:
                for key in ("name", "position", "team", "projection", "actual", "state"):
                    form[side + "_" + r["slot"] + "_" + key] = r[key]
        response = self.client().post("/matchup/save", data=form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Filled 1 starter scores", response.data)
        self.assertIn(b"Nothing has been saved yet", response.data)
        self.assertEqual(load_matchup(7)["own_actual"], 8)
        del form["action"]
        form["own_QB_actual"] = 30
        form["own_actual"] = 37
        response = self.client().post("/matchup/save", data=form)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(load_matchup(7)["own_actual"], 8)


class MatchupPlayerSelectorTests(TestCase):
    setUp = MatchupTests.setUp
    client = MatchupTests.client

    def seed(self):
        database.upsert_player_week_history({
            "qb": {"name": "Quarter Back", "position": "QB", "team": "GB", "weeks": {"6": {"actual": 15}, "7": {"projection": 22}}},
            "wr": {"name": "Receiver Jr.", "position": "WR", "team": "KC", "weeks": {"7": {"actual": 8}}},
            "dst": {"name": "Jacksonville Jaguars", "position": "DEF", "team": "JAC", "weeks": {"7": {"actual": -2}}},
            "future": {"name": "Future player", "position": "RB", "team": "GB", "weeks": {"8": {"projection": 10}}},
        }, 2026)

    def test_choices_are_season_and_historical_week_specific(self):
        self.seed()
        choices = matchup_player_choices(7)
        self.assertEqual({p["player_id"] for p in choices}, {"qb", "wr", "dst"})
        self.assertEqual(matchup_player_choices(5), [])
        self.assertEqual(matchup_player_choices(7, 2027), [])
        self.assertEqual(next(p for p in choices if p["player_id"] == "dst")["position"], "DST")

    def test_saved_name_aliases_match_without_changing_historical_identity(self):
        self.seed()
        choices = matchup_player_choices(7)
        self.assertEqual(selected_player_choice({"name": "Receiver", "position": "WR", "team": "KC"}, choices), "wr")
        self.assertEqual(selected_player_choice({"name": "Jaguars", "position": "DST", "team": "JAX"}, choices), "dst")
        self.assertEqual(selected_player_choice({"name": "Missing player", "position": "RB", "team": "GB"}, choices), "saved")

    def test_selector_filters_by_slot_and_renders_saved_missing_player(self):
        self.seed()
        save_matchups([record(7, "live")])
        response = self.client().get("/matchup?week=7")
        html = response.get_data(as_text=True)
        import re
        qb = re.search(r'<select[^>]*name="own_QB_player_id"[^>]*>(.*?)</select>', html, re.S)[1]
        flex = re.search(r'<select[^>]*name="own_FLEX_player_id"[^>]*>(.*?)</select>', html, re.S)[1]
        self.assertIn('value="qb"', qb)
        self.assertNotIn('value="wr"', qb)
        self.assertIn('value="saved" selected', qb)
        self.assertIn('value="wr"', flex)
        self.assertNotIn('value="qb"', flex)
        self.assertIn('Search Your starters QB players', html)

    def test_selected_id_resolves_identity_server_side_and_fetches_actual(self):
        self.seed()
        form = {"week": "7", "opponent": "Opponent", "status": "live", "action": "fill_actuals",
                "own_WR1_player_id": "wr", "own_WR1_name": "Old stale player",
                "own_WR1_team": "GB", "own_WR1_position": "RB", "own_WR1_actual": 99}
        response = self.client().post("/matchup/save", data=form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Filled 1 starter scores", response.data)
        self.assertIn(b'Receiver Jr.', response.data)
        form.pop("action")
        response = self.client().post("/matchup/save", data=form)
        self.assertEqual(response.status_code, 302)
        player = load_matchup(7)["own_lineup"][0]
        self.assertEqual((player["name"], player["position"], player["team"], player["player_id"]),
                         ("Receiver Jr.", "WR", "KC", "wr"))
        self.assertIsNone(player["actual"])

    def test_invalid_ids_ineligible_slots_and_forged_saved_option_rejected(self):
        self.seed()
        for selection in ("missing", "wr", "saved"):
            response = self.client().post("/matchup/save", data={
                "week": "7", "opponent": "Opponent", "status": "live", "own_QB_player_id": selection})
            self.assertEqual(response.status_code, 400)
            self.assertIsNone(load_matchup(7))

    def test_stable_player_id_resolves_duplicate_names(self):
        self.seed()
        database.upsert_player_week_history({"wr2": {"name": "Receiver Jr.", "position": "WR", "team": "KC",
                                                     "weeks": {"7": {"actual": 99}}}}, 2026)
        entry = {"week": 7, "opponent": "Opponent", "own_lineup": [{"slot": "WR1", "name": "Receiver Jr.",
                  "position": "WR", "team": "KC", "player_id": "wr"}]}
        draft, filled, _ = fill_actuals_from_history(entry)
        self.assertEqual(filled, 1)
        self.assertEqual(draft["own_lineup"][0]["actual"], 8)

    def test_unchanged_selected_historical_alias_keeps_projection_and_name(self):
        self.seed()
        entry = {"week": 7, "opponent": "Opponent", "own_lineup": [{"slot": "WR1", "name": "Receiver",
                  "position": "WR", "team": "KC", "projection": 11, "state": "locked"}]}
        save_matchups([entry])
        response = self.client().post("/matchup/save", data={"week": "7", "opponent": "Opponent", "status": "live",
            "own_WR1_player_id": "wr", "own_WR1_name": "Receiver", "own_WR1_position": "WR",
            "own_WR1_team": "KC", "own_WR1_projection": "11", "own_WR1_state": "locked"})
        self.assertEqual(response.status_code, 302)
        row = load_matchup(7)["own_lineup"][0]
        self.assertEqual(row["name"], "Receiver")
        self.assertEqual(row["projection"], 11)

    def test_same_player_id_cannot_occupy_two_slots_even_with_different_aliases(self):
        entry = {"week": 7, "opponent": "Opponent", "own_lineup": [
            {"slot": "WR1", "name": "Receiver", "position": "WR", "team": "KC", "player_id": "wr"},
            {"slot": "FLEX", "name": "Receiver Jr.", "position": "WR", "team": "KC", "player_id": "wr"}]}
        with self.assertRaisesRegex(ValueError, "unique valid identity"):
            save_matchups([entry])

    def test_unchanged_final_legacy_record_does_not_require_correction_for_id_upgrade(self):
        self.seed()
        entry = record(7)
        entry["own_lineup"][0]["name"] = "Quarter Back"
        save_matchups([entry])
        original = load_matchup(7)
        form = {"week": "7", "opponent": "Opponent", "status": "final",
                "own_actual": 8, "opponent_actual": 9, "own_projection": 10, "opponent_projection": 11}
        for side in ("own", "opponent"):
            for row in entry[side + "_lineup"]:
                prefix = side + "_" + row["slot"] + "_"
                form[prefix + "player_id"] = "qb" if side == "own" and row["slot"] == "QB" else "saved"
                for key in ("name", "position", "team", "projection", "actual", "state"):
                    form[prefix + key] = row[key]
        response = self.client().post("/matchup/save", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(load_matchup(7), original)

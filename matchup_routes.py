import json

from flask import Blueprint, redirect, render_template, request, url_for

from database import load_team_identity
from fantasy_calendar import current_fantasy_week
from matchups import SLOTS, load_matchup, matchup_summary, opponent_names, save_matchups

blueprint = Blueprint("matchups", __name__)
SEASON = 2026


def selected_week():
    week = request.values.get("week", default=current_fantasy_week(SEASON), type=int)
    if week is None or not 1 <= week <= 17:
        raise ValueError("Choose a week from 1 to 17.")
    return week


def render_page(week, edit_record=None, error=None):
    match = load_matchup(week, SEASON) or {
        "week": week, "opponent": "", "status": "planned", "source": "manual_entry",
        "own_lineup": [], "opponent_lineup": [],
        "own_projection": None, "opponent_projection": None,
        "own_actual": None, "opponent_actual": None,
    }
    edit = edit_record or match
    def rows_for(record):
        return [{"slot": slot, **{side: next((r for r in record.get(side + "_lineup", [])
                                             if r["slot"] == slot), {})
                                   for side in ("own", "opponent")}} for slot in SLOTS]
    return render_template("matchup.html", match=matchup_summary(match), edit=edit,
                           rows=rows_for(match), edit_rows=rows_for(edit),
                           names=opponent_names(SEASON), data={"team": load_team_identity(SEASON)},
                           error=error, saved=request.args.get("saved"))


@blueprint.get("/matchup")
def page():
    try:
        week = selected_week()
    except ValueError as exc:
        return str(exc), 400
    return render_page(week)


@blueprint.post("/matchup/save")
def save():
    try:
        week = selected_week()
        old = load_matchup(week, SEASON)
        record = {"week": week, "opponent": request.form.get("opponent"),
                  "status": request.form.get("status"),
                  "source": old["source"] if old else "manual_entry"}
        for side in ("own", "opponent"):
            for field in ("projection", "actual"):
                record[side + "_" + field] = request.form.get(side + "_" + field)
            rows = []
            for slot in SLOTS:
                prefix = side + "_" + slot + "_"
                row = {key: request.form.get(prefix + key, "")
                       for key in ("name", "position", "team", "projection", "actual", "state")}
                if not row["name"].strip():
                    if row["projection"].strip() or row["actual"].strip():
                        raise ValueError("Enter a player name for each score you record.")
                    continue
                rows.append({"slot": slot, **row})
            record[side + "_lineup"] = rows
        save_matchups([record], SEASON, correct_confirmed=request.form.get("correct_confirmed") == "yes")
    except ValueError as exc:
        if "record" in locals():
            return render_page(week, edit_record=record, error=str(exc)), 400
        return render_template("matchup_error.html", error=str(exc)), 400
    return redirect(url_for("matchups.page", week=week, saved="1"))


@blueprint.post("/settings/season-schedule")
def schedule():
    try:
        records = []
        for week in range(1, 18):
            name = request.form.get("opponent_" + str(week), "").strip()
            if not name:
                continue
            old = load_matchup(week, SEASON)
            records.append({**(old or {"week": week}), "opponent": name})
        save_matchups(records, SEASON)
    except ValueError as exc:
        return render_template("matchup_error.html", error=str(exc)), 400
    return redirect(url_for("settings_page", schedule_saved="1", _anchor="season-schedule"))


@blueprint.post("/settings/import-matchups")
def import_file():
    upload = request.files.get("matchup_file")
    try:
        if upload is None:
            raise ValueError("Choose the matchup JSON file to import.")
        content = upload.stream.read(262145)
        if len(content) > 262144:
            raise ValueError("Matchup imports must be smaller than 256 KB.")
        payload = json.loads(content)
        if not isinstance(payload, dict) or payload.get("season") != SEASON:
            raise ValueError("This import must be for the 2026 season.")
        save_matchups(payload.get("matchups"), SEASON)
    except (ValueError, UnicodeError) as exc:
        return render_template("matchup_error.html", error=str(exc)), 400
    return redirect(url_for("settings_page", schedule_saved="1", _anchor="season-schedule"))

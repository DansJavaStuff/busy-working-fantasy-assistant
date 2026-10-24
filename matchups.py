"""Manually confirmed fantasy matchups, independent of current ownership imports."""
import copy
import json
import math

import database
from player_database import fantasypros_team_key, normalise_name, normalise_name_without_suffix
from yahoo_provider import NORMALIZED_FILE, is_directly_acquirable

SLOTS = ("QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "K", "DST")
STATES = ("not_started", "locked", "final")


def points(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError("Scores and projections must be numbers.") from None
    if not math.isfinite(number) or not -1000 <= number <= 3000:
        raise ValueError("Score or projection is outside the supported range.")
    return round(number, 2)


def validate_matchup(raw):
    if not isinstance(raw, dict):
        raise ValueError("Each matchup must be an object.")
    try:
        week = int(raw.get("week", 0))
    except (ValueError, TypeError):
        raise ValueError("Choose a week from 1 to 17.") from None
    if not 1 <= week <= 17 or str(raw.get("week")) != str(week):
        raise ValueError("Choose a week from 1 to 17.")
    opponent = str(raw.get("opponent") or "").strip()
    if not opponent or len(opponent) > 100:
        raise ValueError("Enter an opponent name (up to 100 characters).")
    status = raw.get("status", "planned")
    if not isinstance(status, str) or status not in {"planned", "live", "final"}:
        raise ValueError("Choose planned, live or final.")
    result = {"week": week, "opponent": opponent, "status": status,
              "source": str(raw.get("source") or "manual_entry")[:200]}
    for key in ("own_projection", "opponent_projection", "own_actual", "opponent_actual"):
        result[key] = points(raw.get(key))
    for side in ("own", "opponent"):
        rows = raw.get(side + "_lineup", [])
        if not isinstance(rows, list) or len(rows) > 9:
            raise ValueError("Each side supports nine starting slots.")
        clean, seen_slots, seen_names, seen_ids = [], set(), set(), set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid lineup row.")
            slot = row.get("slot")
            name = str(row.get("name") or "").strip()
            if slot not in SLOTS or slot in seen_slots or not name or len(name) > 100:
                raise ValueError("Lineup rows need a name and a unique valid slot.")
            name_key = normalise_name(name)
            if not name_key or name_key in seen_names:
                raise ValueError("A player cannot occupy two starting slots on the same side.")
            position = str(row.get("position") or slot.rstrip("12")).upper()
            allowed = {"RB", "WR", "TE"} if slot == "FLEX" else {slot.rstrip("12")}
            if position not in allowed:
                raise ValueError("Player position does not match the starting slot.")
            state = row.get("state", "not_started")
            if state not in STATES:
                raise ValueError("Invalid recorded game state.")
            clean.append({"slot": slot, "name": name, "position": position,
                          "team": str(row.get("team") or "").strip()[:10],
                          "projection": points(row.get("projection")),
                          "actual": points(row.get("actual")), "state": state})
            if row.get("player_id"):
                player_id = str(row["player_id"])
                if len(player_id) > 100 or player_id in seen_ids:
                    raise ValueError("A player must have a unique valid identity on each side.")
                clean[-1]["player_id"] = player_id
                seen_ids.add(player_id)
            seen_slots.add(slot)
            seen_names.add(name_key)
        result[side + "_lineup"] = sorted(clean, key=lambda r: SLOTS.index(r["slot"]))
        if status == "final":
            total = result[side + "_actual"]
            if len(clean) != 9 or total is None or any(r["actual"] is None for r in clean):
                raise ValueError("Final matchups need nine starters and actual scores on both sides.")
            if abs(sum(r["actual"] for r in clean) - total) > .05:
                raise ValueError("Final starter scores do not add up to the team total.")
            for row in clean:
                row["state"] = "final"
    return result


def list_matchups(season=2026):
    database.initialise_database()
    with database.connect() as db:
        season_id = database.get_or_create_season(db, season)
        return [json.loads(r["payload"]) for r in db.execute(
            "SELECT payload FROM season_matchups WHERE season_id = ? ORDER BY week", (season_id,)
        )]


def load_matchup(week, season=2026):
    return next((m for m in list_matchups(season) if m["week"] == week), None)


def save_matchups(records, season=2026, correct_confirmed=False):
    """Validate the complete batch before writing; a bad row rolls back all edits."""
    if not isinstance(records, list) or not 1 <= len(records) <= 17:
        raise ValueError("Import between one and seventeen matchups.")
    clean = [validate_matchup(record) for record in records]
    if len({m["week"] for m in clean}) != len(clean):
        raise ValueError("The import contains the same week more than once.")
    database.initialise_database()
    with database.connect() as db:
        season_id = database.get_or_create_season(db, season)
        for match in clean:
            existing = db.execute("SELECT payload FROM season_matchups WHERE season_id=? AND week=?",
                                  (season_id, match["week"])).fetchone()
            old = json.loads(existing["payload"]) if existing else None
            if old == match:
                continue
            if old and not correct_confirmed:
                if old["status"] == "final":
                    raise ValueError("Week %s is final. Enable explicit corrections to replace it." % match["week"])
                for side in ("own", "opponent"):
                    incoming = {r["slot"]: r for r in match[side + "_lineup"]}
                    for row in old[side + "_lineup"]:
                        new = incoming.get(row["slot"], {})
                        if row["state"] in {"locked", "final"} and (
                            any(row[k] != new.get(k) for k in ("name", "position", "team", "projection"))
                            or (row.get("player_id") and row["player_id"] != new.get("player_id"))
                            or STATES.index(new.get("state", "not_started")) < STATES.index(row["state"])
                        ):
                            raise ValueError("A recorded locked starter changed. Enable explicit corrections.")
                if old["opponent"] != match["opponent"] and any(old[s + "_lineup"] for s in ("own", "opponent")):
                    raise ValueError("This week already has lineups. Correct it in the matchup editor.")
            if existing:
                db.execute("INSERT INTO matchup_revisions (season_id,week,payload) VALUES (?,?,?)",
                           (season_id, match["week"], existing["payload"]))
            db.execute("""INSERT INTO season_matchups (season_id,week,opponent,payload) VALUES (?,?,?,?)
                ON CONFLICT(season_id,week) DO UPDATE SET opponent=excluded.opponent,
                payload=excluded.payload, updated_at=CURRENT_TIMESTAMP""",
                       (season_id, match["week"], match["opponent"], json.dumps(match)))
    return len(clean)


def opponent_names(season=2026):
    names = {m["opponent"] for m in list_matchups(season)}
    try:
        players = json.loads(NORMALIZED_FILE.read_text()).get("players", {})
        for player in players.values():
            status = str(player.get("roster_status") or "").strip()
            if status and not is_directly_acquirable(player):
                names.add(status)
    except (OSError, ValueError, AttributeError):
        pass
    return sorted(names, key=str.casefold)


def matchup_summary(match):
    if not match:
        return None
    own, other = match["own_actual"], match["opponent_actual"]
    result = "Not final"
    if match["status"] == "final":
        result = "Won" if own > other else "Lost" if own < other else "Tied"
    return {**match, "result": result,
            "margin": round(own - other, 2) if own is not None and other is not None else None}


def fill_actuals_from_history(record, season=2026):
    """Preview imported actuals for the selected starters; never save or finalise."""
    draft = copy.deepcopy(record)
    # Validate identities without requiring final totals before we have filled them.
    check = {**draft, "status": "planned"}
    draft = {**validate_matchup(check), "status": record.get("status", "planned")}
    history = database.load_player_week_history(draft["week"], season)
    issues = []
    filled = 0
    for side in ("own", "opponent"):
        for row in draft[side + "_lineup"]:
            position = row["position"]
            team = fantasypros_team_key(row["team"])
            candidates = [p for p in history
                          if ("DST" if p["position"] in {"DEF", "D/ST"} else p["position"]) == position
                          and (not team or fantasypros_team_key(p["team"]) == team)]
            if row.get("player_id"):
                candidates = [p for p in candidates if str(p["player_id"]) == row["player_id"]]
            exact = [p for p in candidates if normalise_name(p["player_name"]) == normalise_name(row["name"])]
            if not row.get("player_id"):
                if exact:
                    candidates = exact
                elif position != "DST":
                    candidates = [p for p in candidates if normalise_name_without_suffix(p["player_name"])
                                  == normalise_name_without_suffix(row["name"])]
                elif not team:
                    candidates = []
            # No guessing across duplicate identities, and projections never count as actuals.
            row["actual"] = None
            if len(candidates) == 1 and candidates[0]["actual"] is not None:
                row["actual"] = points(candidates[0]["actual"])
                filled += 1
            else:
                reason = "ambiguous player match" if len(candidates) > 1 else "no imported actual score"
                issues.append(f"{'Your' if side == 'own' else 'Opponent'} {row['slot']} · {row['name']}: {reason}.")
        rows = draft[side + "_lineup"]
        draft[side + "_actual"] = (round(sum(r["actual"] for r in rows), 2)
                                   if len(rows) == 9 and all(r["actual"] is not None for r in rows) else None)
    return draft, filled, issues


def matchup_player_choices(week, season=2026):
    """Use this season's imported identities as known at the requested week."""
    database.initialise_database()
    with database.connect() as db:
        season_id = database.get_or_create_season(db, season)
        rows = db.execute("""SELECT player_id, player_name, position, team, week
            FROM season_player_week WHERE season_id=? AND week<=?
            ORDER BY week DESC, player_id""", (season_id, week)).fetchall()
    choices = {}
    for row in rows:
        player_id = str(row["player_id"])
        if player_id in choices:
            continue
        position = "DST" if row["position"] in {"DEF", "D/ST"} else row["position"]
        if position not in {"QB", "RB", "WR", "TE", "K", "DST"}:
            continue
        choices[player_id] = {"player_id": player_id, "name": row["player_name"],
                              "position": position, "team": row["team"] or ""}
    return sorted(choices.values(), key=lambda p: (p["name"].casefold(), p["team"], p["player_id"]))


def selected_player_choice(row, choices):
    if not row.get("name"):
        return ""
    candidates = [p for p in choices if p["position"] == row["position"]
                  and fantasypros_team_key(p["team"]) == fantasypros_team_key(row.get("team"))]
    if row.get("player_id"):
        candidates = [p for p in candidates if p["player_id"] == row["player_id"]]
    else:
        exact = [p for p in candidates if normalise_name(p["name"]) == normalise_name(row["name"])]
        candidates = exact or [p for p in candidates
                               if normalise_name_without_suffix(p["name"])
                               == normalise_name_without_suffix(row["name"])]
        if not candidates and row["position"] == "DST" and row.get("team"):
            candidates = [p for p in choices if p["position"] == "DST"
                          and fantasypros_team_key(p["team"]) == fantasypros_team_key(row["team"])]
    return candidates[0]["player_id"] if len(candidates) == 1 else "saved"

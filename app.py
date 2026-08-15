from flask import Flask, redirect, render_template, request, url_for

from draft_engine import (
    draft_player,
    is_your_pick,
    load_state,
    next_your_pick,
    pick_to_round_and_slot,
    reset_state,
    undo_last_pick,
    update_settings,
)
from player_database import load_players
from recommendation_engine import get_recommendations

app = Flask(__name__)

@app.route("/")
def dashboard():
    state = load_state()
    players = load_players()

    drafted_ids = {
        item["player"]["id"]
        for item in state["drafted"]
    }

    available = sorted(
        [
            player
            for player in players
            if player["id"] not in drafted_ids
        ],
        key=lambda player: player["adp_rank"],
    )

    round_number, slot = pick_to_round_and_slot(
        state["current_pick"],
        state["teams"],
    )

    recommendations = get_recommendations(
        available,
        state,
    )
    data = {
        "league": {
            "name": "Busy Working",
            "season": 2026,
            "teams": state["teams"],
        },
        "draft": {
            "round": round_number,
            "current_pick": state["current_pick"],
            "current_slot": slot,
            "your_slot": state["your_slot"],
            "your_next_pick": next_your_pick(state),
            "is_your_pick": is_your_pick(state),
            "decision_pick": (
                state["current_pick"]
                if is_your_pick(state)
                else next_your_pick(state)
            ),},
        "available": available,
        "recent_picks": list(reversed(state["drafted"][-8:])),
        "your_roster": state["your_roster"],
        "recommendations": recommendations,
    }

    return render_template(
        "dashboard.html",
        data=data,
    )
      
@app.post("/draft/<string:player_id>")
def make_pick(player_id):
    state = load_state()

    player = next(
        (
            p
            for p in load_players()
            if str(p["id"]) == str(player_id)
        ),
        None,
    )

    if player:
        draft_player(state, player)

    return redirect(url_for("dashboard"))

@app.post("/undo")
def undo():
    state = load_state()
    undo_last_pick(state)

    return redirect(url_for("dashboard"))

@app.post("/settings")
def settings():
    teams = request.form.get("teams", type=int)
    your_slot = request.form.get("your_slot", type=int)

    if teams is None or your_slot is None:
        return redirect(url_for("dashboard"))

    try:
        update_settings(teams, your_slot)
    except ValueError:
        pass

    return redirect(url_for("dashboard"))

@app.post("/reset")
def reset():
    reset_state()

    return redirect(url_for("dashboard"))

@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
    )

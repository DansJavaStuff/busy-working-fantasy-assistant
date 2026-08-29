from flask import Flask, redirect, render_template, request, url_for

from draft_engine import (
    create_new_season,
    draft_player,
    is_your_pick,
    load_state,
    next_your_pick,
    pick_to_round_and_slot,
    reset_state,
    start_actual_draft,
    switch_season,
    undo_last_pick,
    update_settings,
)
from player_database import load_players
from recommendation_engine import get_recommendations
from simulator import choose_opponent_pick
from database import (
    list_seasons,
    load_current_draft_order,
    save_current_draft_order,
)

app = Flask(__name__)

@app.route("/")
def dashboard():
    state = load_state()
    players = load_players()

    draft_order = load_current_draft_order()

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
            "season": state["season"],
            "teams": state["teams"],
        },
        "draft": {
            "round": round_number,
            "current_pick": state["current_pick"],
            "current_slot": slot,
            "current_manager": (
                draft_order.get(
                    slot,
                    f"Slot {slot}",
                )
            ),
            "your_slot": state["your_slot"],
            "your_next_pick": next_your_pick(state),
            "is_your_pick": is_your_pick(state),
            "session_type": state["session_type"],
            "session_name": state["session_name"],
            "decision_pick": (
                state["current_pick"]
                if is_your_pick(state)
                else next_your_pick(state)
            ),},
        "available": available,
        "recent_picks": [
            {
                **pick,
                "manager":
                    draft_order.get(
                        pick["slot"],
                        f'Slot {pick["slot"]}',
                    ),
            }
            for pick in reversed(
                state["drafted"][-8:]
            )
        ],
        "your_roster": state["your_roster"],
        "recommendations": recommendations,
    }

    return render_template(
        "dashboard.html",
        data=data,
    )

@app.get("/settings")
def settings_page():
    state = load_state()

    data = {
        "league": {
            "name": "Busy Working",
            "season": state["season"],
            "teams": state["teams"],
        },
        "draft": {
            "your_slot": state["your_slot"],
            "session_type": state["session_type"],
        },
        "draft_order":
            load_current_draft_order(),
        "seasons":
            list_seasons(),
    }

    return render_template(
        "settings.html",
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

@app.post("/settings/draft")
def update_draft_settings():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )

    teams = request.form.get(
        "teams",
        type=int,
    )
    your_slot = request.form.get(
        "your_slot",
        type=int,
    )

    if teams is None or your_slot is None:
        return redirect(
            url_for("settings_page")
        )

    try:
        update_settings(
            teams,
            your_slot,
        )
    except ValueError:
        pass

    return redirect(
        url_for("settings_page")
    )

@app.post("/draft-order")
def draft_order():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )

    order = {}

    for slot in range(
        1,
        state["teams"] + 1,
    ):
        manager_name = request.form.get(
            f"manager_{slot}",
            "",
        ).strip()

        if manager_name:
            order[slot] = manager_name

    save_current_draft_order(order)

    return redirect(
        url_for("settings_page")
    )

@app.post("/reset")
def reset():
    reset_state()

    return redirect(url_for("dashboard"))

@app.route("/health")
def health():
    return {"status": "ok"}

@app.post("/start-draft-night")
def start_draft_night():
    start_actual_draft()

    return redirect(
        url_for("dashboard")
    )

@app.post("/season/create")
def create_season():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )
    season = request.form.get(
        "season",
        type=int,
    )
    teams = request.form.get(
        "teams",
        type=int,
    )
    your_slot = request.form.get(
        "your_slot",
        type=int,
    )

    try:
        create_new_season(
            season,
            teams,
            your_slot,
        )
    except (TypeError, ValueError):
        pass

    return redirect(
        url_for("settings_page")
    )

@app.post("/season/switch")
def change_season():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )

    season = request.form.get(
        "season",
        type=int,
    )

    try:
        switch_season(season)
    except (TypeError, ValueError):
        pass

    return redirect(
        url_for("settings_page")
    )

@app.post("/simulate-to-my-pick")
def simulate_to_my_pick():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("dashboard")
        )

    if next_your_pick(state) is None:
        return redirect(url_for("dashboard"))

    players = load_players()

    while not is_your_pick(state):
        drafted_ids = {
            str(item["player"]["id"])
            for item in state["drafted"]
        }

        available = sorted(
            [
                player
                for player in players
                if str(player["id"]) not in drafted_ids
            ],
            key=lambda player: player["adp_rank"],
        )

        if not available:
            break

        # v1 opponent logic:
        # take the best available player by consensus ADP.
        opponent_pick = choose_opponent_pick(
            available,
            state,
        )

        if opponent_pick is None:
            break

        draft_player(
            state,
            opponent_pick,
        )

    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
    )

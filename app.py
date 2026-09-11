from flask import Flask, redirect, render_template, request, url_for
from pathlib import Path
import subprocess
import sys
from draft_engine import (
    create_new_season,
    draft_is_complete,
    draft_player,
    is_your_pick,
    load_state,
    next_your_pick,
    pick_to_round_and_slot,
    reset_state,
    start_actual_draft,
    switch_season,
    total_draft_picks,
    undo_last_pick,
    update_settings,
)
from player_database import load_players
from recommendation_engine import get_recommendations
from simulator import choose_opponent_pick
from database import (
    CURRENT_LEAGUE_NAME,
    list_seasons,
    load_current_draft_order,
    load_season_roster,
    load_team_identity,
    save_current_draft_order,
)
from data_status import get_data_status
from fantasypros import get_api_usage
from refresh_data import (
    rebuild_database,
    refresh_all,
    refresh_ffc,
)
from roster_display import build_roster_slots
from roster_manager import move_roster_player
from weekly_engine import build_weekly_data
from yahoo_provider import (
    enrich_local_roster,
    get_yahoo_provider_status,
    yahoo_provider,
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

    complete = draft_is_complete(state)

    if complete:
        final_pick = total_draft_picks(state)

        round_number, _ = pick_to_round_and_slot(
            final_pick,
            state["teams"],
        )

        slot = None
        recommendations = []

    else:
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
            "name": CURRENT_LEAGUE_NAME,
            "season": state["season"],
            "teams": state["teams"],
        },
        "draft": {
            "round": round_number,
            "current_pick": state["current_pick"],
            "complete": complete,
            "total_picks": total_draft_picks(state),
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
        "roster_slots": build_roster_slots(
            state["your_roster"]
        ),
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
            "name": CURRENT_LEAGUE_NAME,
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
        "player_data":
            get_data_status(),
        "fantasypros_usage":
            get_api_usage(),
        "refresh_complete":
            request.args.get("refreshed") == "1",
        "quota_blocked":
            request.args.get("quota_blocked") == "1",
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

@app.get("/weekly")
def weekly():
    season = 2026

    weekly_data = build_weekly_data(
        season=season,
        week=1,
    )

    data = {
        "league": {
            "name":
                CURRENT_LEAGUE_NAME,
            "season":
                season,
        },
        "team":
            load_team_identity(
                season
            ),
        "weekly":
            weekly_data,
    }

    return render_template(
        "weekly.html",
        data=data,
    )


@app.get("/my-team")
def my_team():
    season = 2026

    local_roster = load_season_roster(
        season
    )

    roster = enrich_local_roster(
        local_roster
    )

    identity = load_team_identity(
        season
    )

    roster_by_slot = {
        (
            player["roster_slot"],
            player["slot_index"],
        ): player
        for player in roster
    }

    starter_layout = [
        ("QB", 1),
        ("RB", 1),
        ("RB", 2),
        ("WR", 1),
        ("WR", 2),
        ("TE", 1),
        ("FLEX", 1),
        ("K", 1),
        ("DEF", 1),
    ]

    starter_slots = [
        {
            "roster_slot": roster_slot,
            "slot_index": slot_index,
            "player": roster_by_slot.get(
                (roster_slot, slot_index)
            ),
        }
        for roster_slot, slot_index
        in starter_layout
    ]

    bench_slots = [
        {
            "roster_slot": "BN",
            "slot_index": player["slot_index"],
            "player": player,
        }
        for player in roster
        if player["roster_slot"] == "BN"
    ]

    # Yahoo allows a starter to be benched even when
    # the normal five bench places are already occupied.
    # This synthetic empty row represents that action.
    bench_slots.append(
        {
            "roster_slot": "BN",
            "slot_index": None,
            "player": None,
        }
    )

    ir_players = [
        player
        for player in roster
        if player["roster_slot"] == "IR"
    ]

    data = {
        "league": {
            "name": CURRENT_LEAGUE_NAME,
            "season": season,
        },
        "team": identity,
        "roster": roster,
        "starter_slots": starter_slots,
        "bench_slots": bench_slots,
        "ir_players": ir_players,
        "yahoo_status":
            get_yahoo_provider_status(),
        "move_success":
            request.args.get("moved") == "1",
        "move_error":
            request.args.get("move_error"),
    }

    return render_template(
        "my_team.html",
        data=data,
    )


@app.post("/my-team/move")
def move_my_team_player():
    player_id = request.form.get(
        "player_id",
        "",
    ).strip()

    target_slot = request.form.get(
        "target_slot",
        "",
    ).strip()

    target_index = request.form.get(
        "target_index",
        type=int,
    )

    if (
        not player_id
        or not target_slot
    ):
        return redirect(
            url_for(
                "my_team",
                move_error="Invalid roster move",
            )
        )

    if (
        target_slot.upper() != "BN"
        and target_index is None
    ):
        return redirect(
            url_for(
                "my_team",
                move_error="Invalid roster move",
            )
        )

    try:
        move_roster_player(
            player_id,
            target_slot,
            target_index,
            season=2026,
        )
    except ValueError as exc:
        return redirect(
            url_for(
                "my_team",
                move_error=str(exc),
            )
        )

    return redirect(
        url_for(
            "my_team",
            moved="1",
        )
    )


@app.post("/yahoo/refresh")
def refresh_yahoo_data():
    project_root = Path(
        __file__
    ).resolve().parent

    importer = (
        project_root
        / "tools"
        / "import_yahoo_players.py"
    )

    try:
        subprocess.run(
            [
                sys.executable,
                str(importer),
            ],
            cwd=project_root,
            check=True,
            timeout=180,
        )

        yahoo_provider.refresh()

        return redirect(
            url_for(
                "weekly",
                refreshed="1",
            )
        )

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return redirect(
            url_for(
                "weekly",
                refresh_error="1",
            )
        )


@app.route("/health")
def health():
    return {"status": "ok"}

@app.post("/start-draft-night")
def start_draft_night():
    start_actual_draft()

    return redirect(
        url_for("dashboard")
    )

@app.post("/abandon-draft-night")
def abandon_draft_night():
    state = load_state()

    if state["session_type"] != "actual":
        return redirect(
            url_for("dashboard")
        )

    reset_state()

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

@app.post("/data/refresh")
def refresh_player_data():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )

    usage = get_api_usage()

    if not usage["can_refresh"]:
        return redirect(
            url_for(
                "settings_page",
                quota_blocked="1",
            )
        )

    refresh_all()

    return redirect(
        url_for(
            "settings_page",
            refreshed="all",
        )
    )


@app.post("/data/refresh-ffc")
def refresh_ffc_data():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )

    refresh_ffc()

    return redirect(
        url_for(
            "settings_page",
            refreshed="ffc",
        )
    )


@app.post("/data/rebuild")
def rebuild_player_data():
    state = load_state()

    if state["session_type"] != "mock":
        return redirect(
            url_for("settings_page")
        )

    rebuild_database()

    return redirect(
        url_for(
            "settings_page",
            refreshed="rebuild",
        )
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
    )

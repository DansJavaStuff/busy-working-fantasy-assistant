import json
from pathlib import Path

STATE_FILE = Path("draft_state.json")


def default_state():
    return {
        "teams": 12,
        "your_slot": 2,
        "current_pick": 1,
        "drafted": [],
        "your_roster": [],
    }


def load_state():
    if not STATE_FILE.exists():
        state = default_state()
        save_state(state)
        return state

    return json.loads(STATE_FILE.read_text())


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def reset_state():
    state = default_state()
    save_state(state)
    return state


def pick_to_round_and_slot(pick_number, teams):
    round_number = ((pick_number - 1) // teams) + 1
    index = (pick_number - 1) % teams

    if round_number % 2 == 1:
        slot = index + 1
    else:
        slot = teams - index

    return round_number, slot


def is_your_pick(state):
    _, slot = pick_to_round_and_slot(
        state["current_pick"],
        state["teams"],
    )
    return slot == state["your_slot"]


def next_your_pick(state):
    pick = state["current_pick"]

    while True:
        _, slot = pick_to_round_and_slot(pick, state["teams"])

        if slot == state["your_slot"]:
            return pick

        pick += 1


def draft_player(state, player):
    round_number, slot = pick_to_round_and_slot(
        state["current_pick"],
        state["teams"],
    )

    drafted_entry = {
        "overall_pick": state["current_pick"],
        "round": round_number,
        "slot": slot,
        "player": player,
    }

    state["drafted"].append(drafted_entry)

    if slot == state["your_slot"]:
        state["your_roster"].append(player)

    state["current_pick"] += 1
    save_state(state)

    return state


def undo_last_pick(state):
    if not state["drafted"]:
        return state

    last = state["drafted"].pop()

    if last["slot"] == state["your_slot"]:
        if state["your_roster"]:
            state["your_roster"].pop()

    state["current_pick"] -= 1
    save_state(state)

    return state

def update_settings(teams, your_slot):
    teams = int(teams)
    your_slot = int(your_slot)

    if teams < 2:
        raise ValueError("Number of teams must be at least 2")

    if your_slot < 1 or your_slot > teams:
        raise ValueError(
            "Draft slot must be between 1 and the number of teams"
        )

    state = default_state()
    state["teams"] = teams
    state["your_slot"] = your_slot

    save_state(state)

    return state

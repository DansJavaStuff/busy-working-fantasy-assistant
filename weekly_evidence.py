from sleeper_compare import compare_players
from weekly_decisions import (
    build_start_sit_decisions,
    normalise_name,
    yahoo_call,
)


def _unique_decision_players(decisions):
    players = []
    seen = set()

    for decision in decisions:
        for key in ("start", "sit"):
            player = decision[key]
            name_key = normalise_name(player.get("name"))

            if not name_key or name_key in seen:
                continue

            seen.add(name_key)
            players.append(player)

    return players


def _sleeper_index(results):
    return {
        normalise_name(item.get("name")): item
        for item in (results or [])
        if item.get("name")
    }


def _call_from_edge(edge):
    if edge is None:
        return None
    return yahoo_call(edge)


def _recommendation(decision, sleeper_call):
    yahoo = decision["yahoo_call"]
    start_name = decision["start"]["name"]
    sit_name = decision["sit"]["name"]

    if sleeper_call is None:
        if yahoo == "bench":
            return f"REVIEW {sit_name}"
        if yahoo == "tie":
            return "TOSS-UP"
        return f"LEAN {start_name}"

    if yahoo == sleeper_call:
        if yahoo == "starter":
            return f"START {start_name}"
        if yahoo == "bench":
            return f"START {sit_name}"
        return "TOSS-UP"

    if yahoo == "tie":
        if sleeper_call == "starter":
            return f"LEAN {start_name}"
        if sleeper_call == "bench":
            return f"LEAN {sit_name}"

    if sleeper_call == "tie":
        if yahoo == "starter":
            return f"LEAN {start_name}"
        if yahoo == "bench":
            return f"LEAN {sit_name}"

    return "SOURCES DISAGREE"


def build_start_sit_evidence(
    lineup,
    bench,
    week,
    threshold=3.0,
    sleeper_fetch=compare_players,
):
    """Build close Yahoo start/sit calls and add Sleeper second-opinion evidence.

    Yahoo projections define which decisions are close enough to review. Sleeper
    is then queried only for players in those decisions, and Sleeper's raw stat
    projections are rescored using Busy Working's Yahoo scoring rules by
    ``sleeper_compare``.
    """

    decisions = build_start_sit_decisions(
        lineup,
        bench,
        threshold=threshold,
    )

    if not decisions:
        return []

    players = _unique_decision_players(decisions)

    try:
        sleeper_results = sleeper_fetch(
            players,
            week=week,
        )
        sleeper_error = None
    except Exception as exc:
        sleeper_results = []
        sleeper_error = str(exc)

    sleeper = _sleeper_index(sleeper_results)
    output = []

    for decision in decisions:
        item = dict(decision)
        start_name = decision["start"]["name"]
        sit_name = decision["sit"]["name"]

        start_result = sleeper.get(normalise_name(start_name))
        sit_result = sleeper.get(normalise_name(sit_name))

        start_projection = (
            start_result.get("sleeper_yahoo_projection")
            if start_result
            else None
        )
        sit_projection = (
            sit_result.get("sleeper_yahoo_projection")
            if sit_result
            else None
        )

        sleeper_edge = None
        if (
            start_projection is not None
            and sit_projection is not None
        ):
            sleeper_edge = round(
                float(start_projection)
                - float(sit_projection),
                2,
            )

        sleeper_call = _call_from_edge(sleeper_edge)
        yahoo = decision["yahoo_call"]

        agreement = None
        if sleeper_call is not None:
            if (
                yahoo == sleeper_call
                or yahoo == "tie"
                or sleeper_call == "tie"
            ):
                agreement = "agree"
            else:
                agreement = "disagree"

        item["sleeper"] = {
            "start_projection": start_projection,
            "sit_projection": sit_projection,
            "edge": sleeper_edge,
            "call": sleeper_call,
            "agreement": agreement,
            "error": sleeper_error,
        }
        item["recommendation"] = _recommendation(
            decision,
            sleeper_call,
        )

        output.append(item)

    return output

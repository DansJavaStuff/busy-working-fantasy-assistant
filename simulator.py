import random
import hashlib

from collections import Counter

from draft_engine import pick_to_round_and_slot
from league_config import (
    BUSY_WORKING_ROSTER,
    DRAFT_ROSTER_SIZE,
    normalised_position,
)


def roster_for_slot(state, slot):
    """
    Reconstruct one opponent's roster from the draft history.
    """

    return [
        item["player"]
        for item in state["drafted"]
        if item["slot"] == slot
    ]


def roster_counts(roster):
    return Counter(
        normalised_position(
            player["position"]
        )
        for player in roster
    )


def roster_completion(roster):
    """
    Work out which mandatory positions this team still needs.
    """

    counts = roster_counts(roster)

    rb = counts.get("RB", 0)
    wr = counts.get("WR", 0)
    te = counts.get("TE", 0)

    flex_players = (
        max(
            rb - BUSY_WORKING_ROSTER["RB"],
            0,
        )
        + max(
            wr - BUSY_WORKING_ROSTER["WR"],
            0,
        )
        + max(
            te - BUSY_WORKING_ROSTER["TE"],
            0,
        )
    )

    missing = {
        "QB": max(
            BUSY_WORKING_ROSTER["QB"]
            - counts.get("QB", 0),
            0,
        ),
        "RB": max(
            BUSY_WORKING_ROSTER["RB"]
            - rb,
            0,
        ),
        "WR": max(
            BUSY_WORKING_ROSTER["WR"]
            - wr,
            0,
        ),
        "TE": max(
            BUSY_WORKING_ROSTER["TE"]
            - te,
            0,
        ),
        "FLEX": (
            0
            if flex_players
            >= BUSY_WORKING_ROSTER["FLEX"]
            else 1
        ),
        "K": max(
            BUSY_WORKING_ROSTER["K"]
            - counts.get("K", 0),
            0,
        ),
        "DST": max(
            BUSY_WORKING_ROSTER["DEF"]
            - counts.get("DST", 0),
            0,
        ),
    }

    return {
        "counts": counts,
        "missing": missing,
        "spots_left": max(
            DRAFT_ROSTER_SIZE - len(roster),
            0,
        ),
        "missing_starters": sum(
            missing.values()
        ),
    }


def fills_required_position(
    position,
    missing,
):
    position = normalised_position(
        position
    )

    if position in (
        "QB",
        "K",
        "DST",
    ):
        return missing[position] > 0

    if position in (
        "RB",
        "WR",
        "TE",
    ):
        if missing[position] > 0:
            return True

        if missing["FLEX"] > 0:
            return True

    return False


def fallback_market_adp(player):
    """
    Market centre when FFC doesn't have enough observations.
    """

    yahoo = player.get(
        "yahoo_adp"
    )

    if yahoo is not None:
        return float(yahoo)

    adp = player.get("adp")

    if adp is not None:
        return float(adp)

    return float(
        player.get(
            "adp_rank",
            999,
        )
    )


def default_stdev(mean):
    """
    Reasonable fallback variation for players without a useful
    FFC sample.
    """

    if mean <= 36:
        return 3.0

    if mean <= 84:
        return 5.0

    if mean <= 132:
        return 8.0

    return 11.0

def sampled_market_pick(
    player,
    state,
):
    """
    Give every player one stable simulated draft position for
    this mock.

    Yahoo ADP is the primary market centre because Busy Working
    drafts on Yahoo.

    FFC human mocks tell us how much real drafts tend to vary
    around market expectations.

    K/DST use FFC more heavily because Yahoo special-teams ADP
    can be unusually volatile.
    """

    baseline = fallback_market_adp(
        player
    )

    position = normalised_position(
        player["position"]
    )

    ffc_adp = player.get(
        "ffc_adp"
    )

    ffc_stdev = player.get(
        "ffc_stdev"
    )

    observations = (
        player.get(
            "ffc_times_drafted"
        )
        or 0
    )

    # ---------------------------------------------------------
    # Choose the centre of the simulated market.
    # ---------------------------------------------------------

    if (
        position in ("K", "DST")
        and ffc_adp is not None
        and observations >= 10
    ):
        # FFC human drafts are particularly useful for
        # special-teams timing.
        mean = float(
            ffc_adp
        )

    elif (
        ffc_adp is not None
        and observations >= 25
    ):
        # Yahoo remains dominant.
        #
        # FFC can gently pull the centre towards observed
        # human behaviour without replacing the Yahoo market.
        mean = (
            baseline * 0.8
            + float(ffc_adp) * 0.2
        )

    elif (
        ffc_adp is not None
        and observations >= 10
    ):
        # Small FFC sample: only a very light influence.
        mean = (
            baseline * 0.9
            + float(ffc_adp) * 0.1
        )

    else:
        mean = baseline

    # ---------------------------------------------------------
    # Human variability.
    # ---------------------------------------------------------

    if (
        ffc_stdev is not None
        and observations >= 25
    ):
        # FFC stdev is useful, but using the entire observed
        # spread makes our simulated board too chaotic.
        stdev = float(
            ffc_stdev
        ) * 0.55

    elif (
        ffc_stdev is not None
        and observations >= 10
    ):
        stdev = float(
            ffc_stdev
        ) * 0.4

    else:
        stdev = default_stdev(
            mean
        ) * 0.6

    stdev = max(
        1.0,
        min(stdev, 10.0),
    )

    # ---------------------------------------------------------
    # Stable result for this player in this mock.
    # ---------------------------------------------------------

    seed_text = (
        f'{state.get("session_id", 0)}:'
        f'{player["id"]}'
    )

    digest = hashlib.sha256(
        seed_text.encode("utf-8")
    ).digest()

    seed = int.from_bytes(
        digest[:8],
        "big",
    )

    rng = random.Random(
        seed
    )

    sampled_pick = rng.gauss(
        mean,
        stdev,
    )

    return max(
        1.0,
        sampled_pick,
    )

def roster_penalty(
    player,
    roster,
    round_number,
):
    """
    Adjust raw market behaviour so simulated teams still build
    vaguely sensible Yahoo rosters.
    """

    position = normalised_position(
        player["position"]
    )

    completion = (
        roster_completion(
            roster
        )
    )

    counts = completion[
        "counts"
    ]

    missing = completion[
        "missing"
    ]

    spots_left = completion[
        "spots_left"
    ]

    missing_starters = completion[
        "missing_starters"
    ]

    required = (
        fills_required_position(
            position,
            missing,
        )
    )

    # ---------------------------------------------------------
    # End-of-draft protection.
    # ---------------------------------------------------------

    if (
        spots_left
        <= missing_starters
    ):
        if required:
            return -12

        return 200

    penalty = 0

    # ---------------------------------------------------------
    # Quarterback.
    # ---------------------------------------------------------

    if position == "QB":

        if counts.get("QB", 0) >= 2:
            return 80

        if counts.get("QB", 0) == 1:
            if round_number <= 9:
                penalty += 25
            else:
                penalty += 8

        elif round_number >= 7:
            penalty -= 3

    # ---------------------------------------------------------
    # Tight end.
    # ---------------------------------------------------------

    elif position == "TE":

        if counts.get("TE", 0) >= 2:
            penalty += 40

        elif counts.get("TE", 0) == 1:
            if round_number <= 9:
                penalty += 18
            else:
                penalty += 6

        elif round_number >= 7:
            penalty -= 2

    # ---------------------------------------------------------
    # Kicker.
    # ---------------------------------------------------------

    elif position == "K":

        if counts.get("K", 0):
            return 100

        if round_number <= 8:
            penalty += 35
        elif round_number <= 10:
            penalty += 18
        elif round_number <= 11:
            penalty += 7

    # ---------------------------------------------------------
    # Defence.
    # ---------------------------------------------------------

    elif position == "DST":

        if counts.get("DST", 0):
            return 100

        if round_number <= 8:
            penalty += 30
        elif round_number <= 10:
            penalty += 15
        elif round_number <= 11:
            penalty += 6

    # ---------------------------------------------------------
    # RB / WR roster shape.
    # ---------------------------------------------------------

    elif position in (
        "RB",
        "WR",
    ):

        if counts.get(
            position,
            0,
        ) < 2:
            penalty -= 3

        if counts.get(
            position,
            0,
        ) >= 6:
            penalty += 15

    return penalty


def choose_opponent_pick(
    available,
    state,
):
    """
    Choose one simulated opponent selection.

    Lower score = more likely human pick.
    """

    if not available:
        return None

    round_number, slot = (
        pick_to_round_and_slot(
            state["current_pick"],
            state["teams"],
        )
    )

    roster = roster_for_slot(
        state,
        slot,
    )

    scored = []

    for player in available:

        market_pick = (
            sampled_market_pick(
                player,
                state,
            )
        )

        penalty = roster_penalty(
            player,
            roster,
            round_number,
        )

        score = (
            market_pick
            + penalty
        )

        scored.append(
            (
                score,
                player,
            )
        )

    scored.sort(
        key=lambda item: item[0]
    )

    return scored[0][1]

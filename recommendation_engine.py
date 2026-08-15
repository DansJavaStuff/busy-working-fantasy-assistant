from collections import Counter

from draft_engine import (
    is_your_pick,
    next_your_pick,
    pick_to_round_and_slot,
)

def next_pick_for_slot_after(current_pick, teams, your_slot):
    """
    Find YOUR next pick after the current selection.

    Example:
        12 teams, slot 6
        current pick 6 -> next pick 19
    """

    pick = current_pick + 1

    while True:
        _, slot = pick_to_round_and_slot(
            pick,
            teams,
        )

        if slot == your_slot:
            return pick

        pick += 1


def roster_counts(roster):
    return Counter(
        player["position"]
        for player in roster
    )


def roster_bonus(position, counts, round_number):
    """
    Simple roster-construction rules for v1.

    Positive = position is useful.
    Negative = we're getting over-invested or drafting it too early.
    """

    count = counts.get(position, 0)

    if position == "RB":
        if count == 0:
            return 6, "You have no RB yet"
        if count == 1:
            return 4, "A second RB fills an important starting spot"
        if count == 2:
            return 0, None
        if count >= 3 and round_number <= 6:
            return -5, "You already have good early RB depth"

    if position == "WR":
        if count == 0:
            return 6, "You have no WR yet"
        if count == 1:
            return 4, "A second WR fills an important starting spot"
        if count == 2:
            return 1, "Extra WR depth is useful for FLEX"
        if count >= 4 and round_number <= 6:
            return -4, "You already have substantial WR depth"

    if position == "QB":
        if count >= 1:
            return -12, "You already have a starting QB"

        if round_number <= 3:
            return -7, "QB is usually less urgent this early"

        if round_number <= 5:
            return 1, None

        return 5, "This is a reasonable stage to address QB"

    if position == "TE":
        if count >= 1:
            return -8, "You already have a starting TE"

        if round_number <= 2:
            return -4, "TE is normally less urgent this early"

        if round_number <= 4:
            return 1, None

        return 4, "This is a reasonable stage to address TE"

    return 0, None

def recommendation_action(
    player,
    current_pick,
    decision_pick,
    next_pick,
    waiting_for_turn,
):
    """
    Give the recommendation a simple draft-night action label.
    """

    adp = player.get("adp")

    if adp is None:
        adp = player.get("adp_rank", 999)

    yahoo_adp = player.get("yahoo_adp")

    if yahoo_adp is None:
        yahoo_adp = adp

    # While waiting, these aren't actionable picks yet.
    if waiting_for_turn:
        if yahoo_adp <= decision_pick:
            return "WATCH CLOSELY"

        return "WATCH"

    # We're on the clock.
    # A player at/beyond market value who is unlikely to
    # survive until our following pick is a strong take-now.
    if (
        yahoo_adp <= current_pick
        and adp <= current_pick + 2
    ):
        return "TAKE NOW"

    # Player is expected to go well before our following pick.
    if yahoo_adp < next_pick:
        return "CONSIDER"

    # Market suggests we have a reasonable chance of waiting.
    return "COULD WAIT"

def score_player(
    player,
    current_pick,
    decision_pick,
    next_pick,
    round_number,
    counts,
):
    """
    Produce an explainable draft score.

    current_pick:
        Where the draft actually is now.

    decision_pick:
        The next pick where we can actually select a player.

    next_pick:
        Our selection after decision_pick.
    """

    adp = player.get("adp")
    yahoo_adp = player.get("yahoo_adp")

    if adp is None:
        adp = player.get("adp_rank", 999)

    if yahoo_adp is None:
        yahoo_adp = adp

    score = 100.0
    reasons = []

    waiting_for_turn = decision_pick > current_pick

    # ---------------------------------------------------------
    # 1. Market value / reaching
    #
    # If we're waiting, evaluate whether the player is sensible
    # at our FUTURE decision pick.
    #
    # If we're on the clock, evaluate at the CURRENT pick.
    # ---------------------------------------------------------

    evaluation_pick = (
        decision_pick
        if waiting_for_turn
        else current_pick
    )

    reach = adp - evaluation_pick

    if reach > 0:
        penalty = min(
            reach * 1.8,
            35,
        )

        score -= penalty

        if reach >= 5:
            reasons.append(
                f"ADP {adp:.1f}: likely too early at pick "
                f"{evaluation_pick}"
            )

    # ---------------------------------------------------------
    # 2. Actual value from a player falling.
    #
    # Only the REAL draft position counts here.
    # A player hasn't fallen merely because we're planning
    # ahead to a later pick.
    # ---------------------------------------------------------

    value = current_pick - adp

    if value >= 2:
        bonus = min(
            value * 1.25,
            20,
        )

        score += bonus

        reasons.append(
            f"Value: has slipped {value:.1f} picks past "
            f"consensus ADP"
        )

    # ---------------------------------------------------------
    # 3. Yahoo availability logic.
    # ---------------------------------------------------------

    if waiting_for_turn:

        # We're NOT on the clock.
        # The only question is:
        #
        # "Is this player realistically likely to reach us?"

        if yahoo_adp < decision_pick:

            survival_gap = decision_pick - yahoo_adp

            penalty = min(
                survival_gap * 2.0,
                30,
            )

            score -= penalty

            if survival_gap >= 5:
                reasons.append(
                    f"Yahoo ADP {yahoo_adp:.1f}: unlikely to "
                    f"reach pick {decision_pick}"
                )
            else:
                reasons.append(
                    f"Yahoo ADP {yahoo_adp:.1f}: could go "
                    f"before pick {decision_pick}"
                )

        else:

            score += 3

            reasons.append(
                f"Yahoo ADP {yahoo_adp:.1f}: realistic "
                f"candidate for pick {decision_pick}"
            )

    else:

        # We're ON THE CLOCK.
        #
        # Now the question changes to:
        #
        # "If we don't take him now, is he likely to survive
        # until our following pick?"

        picks_until_next = next_pick - current_pick

        if yahoo_adp < current_pick:

            # The player has already fallen beyond Yahoo ADP.
            value_gap = current_pick - yahoo_adp

            bonus = min(
                5 + value_gap * 0.75,
                10,
            )

            score += bonus

            reasons.append(
                f"Yahoo ADP {yahoo_adp:.1f}: already available "
                f"later than expected"
            )

        elif yahoo_adp == current_pick:

            score += 5

            reasons.append(
                f"Yahoo ADP {yahoo_adp:.1f}: right at expected "
                f"draft value"
            )

        elif yahoo_adp < next_pick:

            # He's expected to go before we're back.
            #
            # Give an urgency bonus, but don't massively reward
            # players simply because their ADP is slightly later.
            picks_after_current = yahoo_adp - current_pick

            if picks_after_current <= 3:
                bonus = 4
            elif picks_after_current <= 8:
                bonus = 3
            else:
                bonus = 2

            score += bonus

            if picks_until_next <= 4:
                reasons.append(
                    f"Yahoo ADP {yahoo_adp:.1f}: may survive the "
                    f"short turn to pick {next_pick}"
                )
            else:
                reasons.append(
                    f"Yahoo ADP {yahoo_adp:.1f}: unlikely to "
                    f"survive until pick {next_pick}"
                )

        else:

            gap = yahoo_adp - next_pick

            penalty = min(
                gap * 0.35,
                8,
            )

            score -= penalty

            reasons.append(
                f"Yahoo ADP {yahoo_adp:.1f}: reasonable chance "
                f"he survives to pick {next_pick}"
            )

    # ---------------------------------------------------------
    # 4. Roster construction.
    # ---------------------------------------------------------

    bonus, roster_reason = roster_bonus(
        player["position"],
        counts,
        round_number,
    )

    score += bonus

    if roster_reason:
        reasons.append(roster_reason)

    # ---------------------------------------------------------
    # 5. FantasyPros positional tier.
    # ---------------------------------------------------------

    tier = player.get("tier")

    if tier == 1:
        score += 3

        reasons.append(
            f"FantasyPros Tier {tier} at "
            f"{player['position']}"
        )

    elif tier == 2:
        score += 1

    action = recommendation_action(
        player,
        current_pick,
        decision_pick,
        next_pick,
        waiting_for_turn,
    )

    return {
        "player": player,
        "score": round(score, 1),
        "value": round(value, 1),
        "decision_pick": decision_pick,
        "next_pick": next_pick,
        "action": action,
        "reasons": reasons,
    }

def get_recommendations(
    available,
    state,
    limit=5,
):
    if not available:
        return []

    current_pick = state["current_pick"]
    teams = state["teams"]
    your_slot = state["your_slot"]

    # The pick we're actually making a decision for.
    if is_your_pick(state):
        decision_pick = current_pick
    else:
        decision_pick = next_your_pick(state)

    round_number, _ = pick_to_round_and_slot(
        decision_pick,
        teams,
    )

    # Our selection AFTER the decision we're currently planning.
    next_pick = next_pick_for_slot_after(
        decision_pick,
        teams,
        your_slot,
    )

    counts = roster_counts(
        state["your_roster"]
    )

    candidates = available[:50]

    scored = [
        score_player(
            player,
            current_pick,
            decision_pick,
            next_pick,
            round_number,
            counts,
        )
        for player in candidates
    ]

    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return scored[:limit]

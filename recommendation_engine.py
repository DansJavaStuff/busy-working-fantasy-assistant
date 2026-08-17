from collections import Counter

from draft_engine import (
    is_your_pick,
    next_your_pick,
    pick_to_round_and_slot,
)

from league_config import BUSY_WORKING_ROSTER, FLEX_ELIGIBLE

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
    Busy Working roster-construction rules.

    Starting lineup:
        QB
        RB
        RB
        WR
        WR
        TE
        W/R/T
        K
        DEF

    Plus 5 bench and 1 IR.
    """

    count = counts.get(position, 0)

    # ---------------------------------------------------------
    # Work out whether the FLEX position is already covered.
    #
    # Any RB/WR/TE beyond their normal starting allocation
    # can occupy the W/R/T FLEX slot.
    # ---------------------------------------------------------

    rb_extra = max(
        counts.get("RB", 0) - BUSY_WORKING_ROSTER["RB"],
        0,
    )

    wr_extra = max(
        counts.get("WR", 0) - BUSY_WORKING_ROSTER["WR"],
        0,
    )

    te_extra = max(
        counts.get("TE", 0) - BUSY_WORKING_ROSTER["TE"],
        0,
    )

    flex_filled = (rb_extra + wr_extra + te_extra) >= 1

    # ---------------------------------------------------------
    # RB
    # ---------------------------------------------------------

    if position == "RB":
        starters = BUSY_WORKING_ROSTER["RB"]

        if count < starters:
            slot_number = count + 1

            return (
                6,
                f"Fills your RB{slot_number} starting position",
            )

        if not flex_filled:
            return (
                3,
                "Strong candidate for your W/R/T FLEX position",
            )

        if count >= 4 and round_number <= 6:
            return (
                -5,
                "Starting RB slots and FLEX are already well covered",
            )

        return (
            1,
            "Adds useful RB bench depth",
        )

    # ---------------------------------------------------------
    # WR
    # ---------------------------------------------------------

    if position == "WR":
        starters = BUSY_WORKING_ROSTER["WR"]

        if count < starters:
            slot_number = count + 1

            return (
                6,
                f"Fills your WR{slot_number} starting position",
            )

        if not flex_filled:
            return (
                3,
                "Strong candidate for your W/R/T FLEX position",
            )

        if count >= 4 and round_number <= 6:
            return (
                -4,
                "Starting WR slots and FLEX are already well covered",
            )

        return (
            1,
            "Adds useful WR bench depth",
        )

    # ---------------------------------------------------------
    # QB
    # ---------------------------------------------------------

    if position == "QB":
        starters = BUSY_WORKING_ROSTER["QB"]

        if count >= starters:
            return (
                -12,
                "Your starting QB position is already filled",
            )

        if round_number <= 2:
            return (
                -5,
                "Only one QB starts, so the position is less urgent this early",
            )

        if round_number == 3:
            return (
                -2,
                "QB is becoming viable, although RB/WR starters still matter",
            )

        if round_number <= 5:
            return (
                2,
                "Reasonable stage to fill your starting QB position",
            )

        return (
            5,
            "Starting QB is now an important roster need",
        )

    # ---------------------------------------------------------
    # TE
    # ---------------------------------------------------------

    if position == "TE":
        starters = BUSY_WORKING_ROSTER["TE"]

        if count < starters:
            if round_number <= 2:
                return (
                    -3,
                    "TE is normally less urgent in the opening rounds",
                )

            if round_number <= 4:
                return (
                    2,
                    "Would fill your starting TE position",
                )

            return (
                4,
                "Fills an open starting TE position",
            )

        # We already have our starting TE.
        # A second TE can technically use FLEX, but we don't
        # want to encourage that as strongly as RB/WR.
        if not flex_filled and position in FLEX_ELIGIBLE:
            return (
                -2,
                "Starting TE is filled; a second TE would mainly be FLEX/depth",
            )

        return (
            -8,
            "Your starting TE position is already filled",
        )

    # ---------------------------------------------------------
    # Kicker / Defence
    #
    # They are required starters, but we deliberately avoid
    # encouraging them until the closing rounds.
    # ---------------------------------------------------------

    if position in ("K", "DEF", "DST"):
        if count >= 1:
            return (
                -20,
                f"You already have a starting {position}",
            )

        if round_number <= 10:
            return (
                -40,
                f"Wait until the late rounds to draft {position}",
            )

        if round_number <= 12:
            return (
                -10,
                f"{position} can usually still wait",
            )

        return (
            2,
            f"Reasonable stage to fill your starting {position}",
        )

    return 0, None

def consensus_adp(player):
    """
    Best available consensus ADP for comparing player quality.
    """
    adp = player.get("adp")

    if adp is None:
        adp = player.get("adp_rank", 999)

    return float(adp)


def market_adp(player):
    """
    Yahoo ADP is our best guide to when players may actually
    disappear in the Busy Working draft.
    """
    adp = player.get("yahoo_adp")

    if adp is None:
        adp = consensus_adp(player)

    return float(adp)


def positional_scarcity_bonus(
    player,
    available,
    counts,
    next_pick,
):
    """
    Identify QB/TE positional drop-offs.

    Availability is estimated using Yahoo ADP.

    The size of the quality drop is measured primarily using
    positional rank rather than overall ADP.

    FantasyPros tier is used as an additional signal only when
    both players have tier data.
    """

    position = player["position"]

    if position not in ("QB", "TE"):
        return 0, None

    starters = BUSY_WORKING_ROSTER[position]

    if counts.get(position, 0) >= starters:
        return 0, None

    same_position = sorted(
        [
            candidate
            for candidate in available
            if candidate["position"] == position
        ],
        key=consensus_adp,
    )

    if len(same_position) < 2:
        return 0, None

    # Only apply scarcity to the best remaining player
    # at the position.
    if str(same_position[0]["id"]) != str(player["id"]):
        return 0, None

    player_market = market_adp(player)

    # If this player is likely to survive until our next pick,
    # there is little reason to pay a scarcity premium now.
    if player_market >= next_pick:
        return 0, None

    # Find the best player at this position that Yahoo ADP
    # suggests has a reasonable chance of surviving.
    likely_survivors = [
        candidate
        for candidate in same_position[1:]
        if market_adp(candidate) >= next_pick
    ]

    if not likely_survivors:
        return (
            5,
            f"Major {position} scarcity: no likely starter-level "
            f"option is expected to reach pick {next_pick}",
        )

    fallback = likely_survivors[0]

    player_rank = player.get("position_rank")
    fallback_rank = fallback.get("position_rank")

    # If positional rank data is unavailable, don't invent
    # a quality gap from overall ADP.
    if player_rank is None or fallback_rank is None:
        return 0, None

    rank_gap = fallback_rank - player_rank

    # Base scarcity bonus from positional-rank drop.
    if rank_gap >= 6:
        bonus = 5
    elif rank_gap >= 4:
        bonus = 4
    elif rank_gap >= 2:
        bonus = 2
    else:
        bonus = 0

    # FantasyPros tier can strengthen the signal, but only
    # when both players actually have tier information.
    player_tier = player.get("tier")
    fallback_tier = fallback.get("tier")

    tier_drop = (
        player_tier is not None
        and fallback_tier is not None
        and fallback_tier > player_tier
    )

    if tier_drop and bonus > 0:
        bonus = min(bonus + 1, 5)

    if bonus == 0:
        return 0, None

    reason = (
        f"{position} drop-off if you wait: "
        f"{player['name']} {position}{player_rank} → "
        f"{fallback['name']} {position}{fallback_rank}"
    )

    if tier_drop:
        reason += (
            f" (Tier {player_tier} → Tier {fallback_tier})"
        )

    return bonus, reason

def recommendation_action(
    player,
    current_pick,
    decision_pick,
    next_pick,
    waiting_for_turn,
    score,
):
    """
    Turn the recommendation score and market timing into
    a simple draft-night action.

    The score answers:
        "How much do we want this player?"

    Yahoo ADP answers:
        "Do we need to act now?"
    """

    adp = consensus_adp(player)
    yahoo_adp = market_adp(player)

    # ---------------------------------------------------------
    # We're waiting for our turn.
    #
    # These are watchlist labels rather than draft actions.
    # ---------------------------------------------------------

    if waiting_for_turn:
        if yahoo_adp <= decision_pick:
            return "WATCH CLOSELY"

        return "WATCH"

    # ---------------------------------------------------------
    # We're ON THE CLOCK.
    # ---------------------------------------------------------

    likely_gone = yahoo_adp < next_pick
    already_at_value = yahoo_adp <= current_pick
    near_consensus_value = adp <= current_pick + 2

    # A genuinely strong recommendation that is unlikely
    # to survive until our next selection.
    if score >= 110 and likely_gone:
        return "TAKE NOW"

    # Also allow TAKE NOW for a strong player who has already
    # fallen to/past market value, even if the overall score
    # doesn't quite reach 110.
    if (
        score >= 106
        and already_at_value
        and near_consensus_value
    ):
        return "TAKE NOW"

    # Good player, but not strong enough to call mandatory.
    if likely_gone:
        return "CONSIDER"

    # Market suggests there is a reasonable chance that
    # we can wait until our following selection.
    return "COULD WAIT"

def score_player(
    player,
    current_pick,
    decision_pick,
    next_pick,
    round_number,
    counts,
    available,
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
        #
        # Rank players based on how desirable they would be
        # IF they reach our decision pick.
        #
        # Survival risk is communicated separately by the
        # WATCH / WATCH CLOSELY badge.
    
        if yahoo_adp < decision_pick:
            survival_gap = decision_pick - yahoo_adp
    
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

    # ---------------------------------------------------------
    # 6. Positional scarcity.
    #
    # QB and TE are one-starter positions, so the value of
    # taking one depends heavily on the quality drop to the
    # next available option.
    # ---------------------------------------------------------

    scarcity_bonus, scarcity_reason = positional_scarcity_bonus(
        player,
        available,
        counts,
        next_pick,
    )

    score += scarcity_bonus

    if scarcity_reason:
        reasons.append(scarcity_reason)
        
    action = recommendation_action(
        player,
        current_pick,
        decision_pick,
        next_pick,
        waiting_for_turn,
        score,
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
            available,
        )
        for player in candidates
    ]

    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return scored[:limit]

from collections import Counter

from draft_engine import (
    is_your_pick,
    next_your_pick,
    pick_to_round_and_slot,
)

from league_config import (
    BUSY_WORKING_ROSTER,
    DRAFT_ROSTER_SIZE,
    FLEX_ELIGIBLE,
    normalised_position,
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

def roster_completion_state(counts):
    """
    Work out how many required starting positions are still
    empty and how many normal draft roster spots remain.
    """

    rb_count = counts.get("RB", 0)
    wr_count = counts.get("WR", 0)
    te_count = counts.get("TE", 0)

    flex_players = (
        max(rb_count - BUSY_WORKING_ROSTER["RB"], 0)
        + max(wr_count - BUSY_WORKING_ROSTER["WR"], 0)
        + max(te_count - BUSY_WORKING_ROSTER["TE"], 0)
    )

    defence_count = (
        counts.get("DEF", 0)
        + counts.get("DST", 0)
    )

    missing = {
        "QB": max(
            BUSY_WORKING_ROSTER["QB"]
            - counts.get("QB", 0),
            0,
        ),
        "RB": max(
            BUSY_WORKING_ROSTER["RB"]
            - rb_count,
            0,
        ),
        "WR": max(
            BUSY_WORKING_ROSTER["WR"]
            - wr_count,
            0,
        ),
        "TE": max(
            BUSY_WORKING_ROSTER["TE"]
            - te_count,
            0,
        ),
        "FLEX": (
            0
            if flex_players >= BUSY_WORKING_ROSTER["FLEX"]
            else 1
        ),
        "K": max(
            BUSY_WORKING_ROSTER["K"]
            - counts.get("K", 0),
            0,
        ),
        "DEF": max(
            BUSY_WORKING_ROSTER["DEF"]
            - defence_count,
            0,
        ),
    }

    rostered = sum(counts.values())

    spots_left = max(
        DRAFT_ROSTER_SIZE - rostered,
        0,
    )

    missing_starters = sum(missing.values())

    return {
        "missing": missing,
        "spots_left": spots_left,
        "missing_starters": missing_starters,
    }


def fills_required_start(position, missing):
    """
    Does drafting this position fill a currently empty
    starting slot?
    """

    if position in ("DEF", "DST"):
        return missing["DEF"] > 0

    if position in ("QB", "K"):
        return missing[position] > 0

    if position in FLEX_ELIGIBLE:
        if missing.get(position, 0) > 0:
            return True

        if missing["FLEX"] > 0:
            return True

    return False


def roster_completion_bonus(
    position,
    counts,
    round_number,
):
    """
    Protect the end of the draft from leaving required
    starting positions empty.
    """

    state = roster_completion_state(counts)

    missing = state["missing"]
    spots_left = state["spots_left"]
    missing_starters = state["missing_starters"]

    required = fills_required_start(
        position,
        missing,
    )

    if spots_left <= 0:
        return (
            -100,
            "Your normal draft roster is already full",
        )

    # Every remaining roster spot is needed for an
    # unfilled starter. Do not draft another bench player.
    if spots_left <= missing_starters:
        if required:
            return (
                20,
                "Remaining roster spots must now fill "
                "open starting positions",
            )

        return (
            -50,
            "Must reserve the remaining roster spots "
            "for unfilled starters",
        )

    # Only one discretionary roster position remains.
    if spots_left == missing_starters + 1:
        if required:
            return (
                4,
                "Starting lineup still needs completing",
            )

        if position in ("RB", "WR"):
            return (
                2,
                "Only one discretionary bench spot remains; "
                "prefer RB/WR depth",
            )

        if position in ("QB", "TE"):
            return (
                -2,
                "Only one discretionary bench spot remains; "
                "backup QB/TE is lower priority than RB/WR depth",
            )

    # Kicker and defence should naturally become viable
    # near the end rather than being forced too early.
    if position == "K" and missing["K"] > 0:
        if round_number >= 13:
            return (
                6,
                "Late-round stage to fill your kicker slot",
            )

    if (
        position in ("DEF", "DST")
        and missing["DEF"] > 0
    ):
        if round_number >= 13:
            return (
                6,
                "Late-round stage to fill your defence slot",
            )

    return 0, None

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
            missing_core_starter = any(
                counts.get(pos, 0)
                < BUSY_WORKING_ROSTER[pos]
                for pos in ("RB", "WR", "TE")
            )

            if missing_core_starter:
                return (
                    -25,
                    "Starting QB is filled; complete remaining "
                    "RB/WR/TE starting positions before "
                    "considering a backup QB",
                )

            if round_number <= 10:
                return (
                    -20,
                    "Only one QB starts; with QB1 filled, preserve "
                    "bench spots for RB/WR depth",
                )

            if round_number <= 12:
                return (
                    -12,
                    "Backup QB remains a lower-priority roster need",
                )

            return (
                -5,
                "A backup QB is reasonable this late only if "
                "the value is exceptional",
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

        # Two TEs is already plenty in this one-TE league.
        # A third TE would consume one of only five bench
        # spots and should require truly exceptional value.
        if count >= 2:
            return (
                -35,
                "You already have two TEs; preserve remaining "
                "bench spots for RB/WR depth",
            )

        # We already have our starting TE.
        #
        # A second TE can technically fill FLEX, but while
        # normal RB/WR starting positions remain open we
        # should strongly prefer completing those first.
        missing_rb = max(
            BUSY_WORKING_ROSTER["RB"]
            - counts.get("RB", 0),
            0,
        )

        missing_wr = max(
            BUSY_WORKING_ROSTER["WR"]
            - counts.get("WR", 0),
            0,
        )

        if missing_rb or missing_wr:
            return (
                -12,
                "Starting TE is filled; complete your RB/WR "
                "starting positions before considering a second TE",
            )

        if not flex_filled:
            return (
                -5,
                "Starting TE is filled; RB/WR are preferred "
                "for the FLEX position",
            )

        if round_number <= 9:
            return (
                -8,
                "Starting TE is filled; prioritise RB/WR depth",
            )

        if round_number <= 11:
            return (
                -5,
                "Backup TE is still a lower-priority roster need",
            )

        return (
            -2,
            "A backup TE is now reasonable if the value is strong",
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

        if round_number <= 12:
            return (
                -40,
                f"Preserve rounds 1-12 for skill-position depth; "
                f"{position} can wait until the final two rounds",
            )

        return (
            2,
            f"Reasonable stage to fill your starting {position}",
        )

    return 0, None

def bench_balance_bonus(
    position,
    counts,
):
    """
    Encourage balanced RB/WR bench construction.

    Busy Working starts two RB and two WR, so comparing the
    number rostered at each position is a useful indication of
    where our depth is becoming thin or excessive.

    This only applies once the W/R/T FLEX spot is already covered.
    """

    if position not in ("RB", "WR"):
        return 0, None

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

    flex_filled = (
        rb_extra
        + wr_extra
        + te_extra
    ) >= 1

    if not flex_filled:
        return 0, None

    rb_count = counts.get("RB", 0)
    wr_count = counts.get("WR", 0)

    if position == "RB":
        position_count = rb_count
        other_count = wr_count
        other_position = "WR"
    else:
        position_count = wr_count
        other_count = rb_count
        other_position = "RB"

    depth_gap = other_count - position_count

    # Moderate imbalance: gently favour the thinner position.
    if depth_gap == 2:
        return (
            4,
            f"Balances your RB/WR depth: {position} is "
            f"thinner than {other_position}",
        )

    if depth_gap == -2:
        return (
            -4,
            f"You already have more {position} depth than "
            f"{other_position}",
        )

    # Large imbalance: roster construction should now matter
    # considerably more than squeezing out a little extra ADP value.
    if depth_gap >= 3:
        return (
            8,
            f"RB/WR depth is heavily imbalanced; prioritise "
            f"{position} over {other_position}",
        )

    if depth_gap <= -3:
        return (
            -8,
            f"RB/WR depth is heavily imbalanced; avoid adding "
            f"more {position} unless the value is exceptional",
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
    Yahoo ADP is our best guide to when normal skill players
    may actually disappear in the Busy Working draft.

    Kicker and defence are handled primarily through roster
    completion rather than Yahoo market timing, because their
    ADP can be unusually volatile.
    """

    if player["position"] in ("K", "DEF", "DST"):
        return consensus_adp(player)

    adp = player.get("yahoo_adp")

    if adp is None:
        adp = consensus_adp(player)

    return float(adp)

def special_teams_run_bonus(
    player,
    available,
    state,
    round_number,
):
    """
    Track K/DST market depletion without blindly following runs.

    Two signals matter:

      1. Elite depletion:
         How many of the FantasyPros top-four options have
         disappeared anywhere in the draft?

      2. Recent run:
         Have at least three players at the position gone in
         the last eight picks?

    A slow drain of elite options matters even when it never
    forms a traditional draft run.
    """

    position = normalised_position(
        player["position"]
    )

    if position not in ("K", "DST"):
        return 0, None

    # Special teams remain deliberately suppressed through
    # the early and middle rounds.
    if round_number < 11:
        return 0, None

    def position_rank(candidate):
        """
        Prefer the full FantasyPros positional CSV ranking.

        Fall back to the older merged position_rank when
        necessary.
        """

        rank = candidate.get(
            "fantasypros_position_rank"
        )

        if rank is None:
            rank = candidate.get(
                "position_rank"
            )

        return rank

    def is_elite(candidate):
        if normalised_position(
            candidate["position"]
        ) != position:
            return False

        rank = position_rank(candidate)

        return (
            rank is not None
            and rank <= 4
        )

    # ---------------------------------------------------------
    # How many elite options have disappeared anywhere in
    # the draft?
    # ---------------------------------------------------------

    elite_drafted = [
        item["player"]
        for item in state["drafted"]
        if is_elite(item["player"])
    ]

    elite_drafted_ids = {
        str(candidate["id"])
        for candidate in elite_drafted
    }

    elite_gone = len(elite_drafted_ids)

    elite_remaining = sorted(
        [
            candidate
            for candidate in available
            if is_elite(candidate)
        ],
        key=lambda candidate: (
            position_rank(candidate)
            if position_rank(candidate) is not None
            else 999
        ),
    )

    player_rank = position_rank(player)

    # Only elite candidates benefit from elite-depletion
    # awareness.
    if (
        player_rank is None
        or player_rank > 4
    ):
        return 0, None

    # ---------------------------------------------------------
    # Also recognise a conventional recent run.
    # ---------------------------------------------------------

    recent = state["drafted"][-8:]

    recent_at_position = [
        item
        for item in recent
        if normalised_position(
            item["player"]["position"]
        ) == position
    ]

    run_size = len(recent_at_position)
    recent_run = run_size >= 3

    # ---------------------------------------------------------
    # Several elite options remain.
    #
    # A recent run is worth mentioning, but don't manufacture
    # urgency while we still have alternatives.
    # ---------------------------------------------------------

    if len(elite_remaining) > 1:
        if recent_run:
            return (
                0,
                f"{position} run developing: {run_size} taken "
                f"in the last 8 picks, but "
                f"{len(elite_remaining)} top-four options remain",
            )

        return 0, None

    # We only want depletion urgency when we can prove that
    # three of the top four have actually been drafted.
    if (
        elite_gone < 3
        or len(elite_remaining) != 1
    ):
        return 0, None

    # Only the actual last elite option gets the bonus.
    if (
        str(elite_remaining[0]["id"])
        != str(player["id"])
    ):
        return 0, None

    run_note = (
        f"; {run_size} {position} have also gone "
        f"in the last 8 picks"
        if recent_run
        else ""
    )

    # ---------------------------------------------------------
    # Round 11:
    #
    # Start getting nervous, but don't automatically sacrifice
    # useful RB/WR depth.
    # ---------------------------------------------------------

    if round_number == 11:
        bonus = (
            15
            if recent_run
            else 10
        )

        return (
            bonus,
            f"Only one FantasyPros top-four {position} remains: "
            f"3 of 4 elite options are already gone"
            f"{run_note}",
        )

    # ---------------------------------------------------------
    # Round 12:
    #
    # Waiting another full turn now creates a genuine risk of
    # losing the final elite option.
    # ---------------------------------------------------------

    if round_number == 12:
        bonus = (
            35
            if recent_run
            else 30
        )

        return (
            bonus,
            f"Last FantasyPros top-four {position} remaining: "
            f"3 of 4 elite options are already gone"
            f"{run_note}; waiting until round 13 risks losing it",
        )

    # ---------------------------------------------------------
    # Rounds 13+:
    #
    # We're already in the intended K/DST drafting window.
    # Give a small additional preference to the last elite
    # option.
    # ---------------------------------------------------------

    return (
        5,
        f"Last FantasyPros top-four {position} remaining",
    )


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
    Convert recommendation strength and market timing into
    a simple draft-night action.

    Draft score answers:
        "How much do we want this player?"

    Yahoo ADP answers:
        "How urgently do we need to act?"
    """

    adp = consensus_adp(player)
    yahoo_adp = market_adp(player)

    # ---------------------------------------------------------
    # Waiting for our turn.
    #
    # WATCH CLOSELY should mean:
    #   - we genuinely like the player
    #   - AND there is a meaningful risk he disappears
    #
    # Otherwise he simply remains on the watchlist.
    # ---------------------------------------------------------

    if waiting_for_turn:
        likely_gone_before_turn = yahoo_adp < decision_pick

        if (
            score >= 105
            and likely_gone_before_turn
        ):
            return "WATCH CLOSELY"

        return "WATCH"

    # ---------------------------------------------------------
    # We're ON THE CLOCK.
    # ---------------------------------------------------------

    likely_gone = yahoo_adp < next_pick
    already_at_value = yahoo_adp <= current_pick
    near_consensus_value = adp <= current_pick + 2

    # ---------------------------------------------------------
    # TAKE NOW
    #
    # Strong recommendation + significant risk of losing him.
    # ---------------------------------------------------------

    if (
        score >= 110
        and likely_gone
    ):
        return "TAKE NOW"

    # Strong player who has already fallen to/past his
    # expected market value.
    if (
        score >= 106
        and already_at_value
        and near_consensus_value
    ):
        return "TAKE NOW"

    # ---------------------------------------------------------
    # CONSIDER
    #
    # Good recommendation and likely unavailable next time.
    # ---------------------------------------------------------

    if (
        score >= 101
        and likely_gone
    ):
        return "CONSIDER"

    # A decent recommendation that has already reached
    # market value is also worth considering.
    if (
        score >= 100
        and already_at_value
        and near_consensus_value
    ):
        return "CONSIDER"

    # ---------------------------------------------------------
    # LOW PRIORITY
    #
    # Player may disappear, but our recommendation score
    # isn't strong enough to chase him just because of ADP.
    # ---------------------------------------------------------

    if likely_gone:
        return "LOW PRIORITY"

    # ---------------------------------------------------------
    # COULD WAIT
    #
    # We like the player enough to show him, but market timing
    # suggests there is a reasonable chance he survives.
    # ---------------------------------------------------------

    return "COULD WAIT"

def score_player(
    player,
    current_pick,
    decision_pick,
    next_pick,
    round_number,
    counts,
    available,
    state,
    final_roster_pick,
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

    adp = consensus_adp(player)
    yahoo_adp = market_adp(player)

    if normalised_position(
        player["position"]
    ) in ("K", "DST"):
        market_label = "Consensus ADP"
    else:
        market_label = "Yahoo ADP"

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
    # 3. Market availability logic.
    # ---------------------------------------------------------

    if final_roster_pick:

        # There is no following selection after this one.
        # Market survival therefore no longer matters.
        reasons.append(
            "Final roster pick: choose the best remaining "
            "required starter"
        )

    elif waiting_for_turn:

        # We're NOT on the clock.
        #
        # Rank players based on how desirable they would be
        # IF they reach our decision pick.
        #
        # Survival risk is communicated separately by the
        # WATCH / WATCH CLOSELY badge.

        if yahoo_adp < decision_pick:
            survival_gap = (
                decision_pick - yahoo_adp
            )

            if survival_gap >= 5:
                reasons.append(
                    f"{market_label} {yahoo_adp:.1f}: unlikely to "
                    f"reach pick {decision_pick}"
                )
            else:
                reasons.append(
                    f"{market_label} {yahoo_adp:.1f}: could go "
                    f"before pick {decision_pick}"
                )

        else:
            reasons.append(
                f"{market_label} {yahoo_adp:.1f}: realistic "
                f"candidate for pick {decision_pick}"
            )

    else:

        # We're ON THE CLOCK.
        #
        # Now the question changes to:
        #
        # "If we don't take him now, is he likely to survive
        # until our following pick?"

        picks_until_next = (
            next_pick - current_pick
        )

        if yahoo_adp < current_pick:

            # The player has already fallen beyond expected
            # market value.

            value_gap = (
                current_pick - yahoo_adp
            )

            bonus = min(
                5 + value_gap * 0.75,
                10,
            )

            score += bonus

            reasons.append(
                f"{market_label} {yahoo_adp:.1f}: already "
                f"available later than expected"
            )

        elif yahoo_adp == current_pick:

            score += 5

            reasons.append(
                f"{market_label} {yahoo_adp:.1f}: right at "
                f"expected draft value"
            )

        elif yahoo_adp < next_pick:

            # He's expected to go before we're back.
            #
            # Give an urgency bonus, but don't massively reward
            # players simply because their ADP is slightly later.

            picks_after_current = (
                yahoo_adp - current_pick
            )

            if picks_after_current <= 3:
                bonus = 4
            elif picks_after_current <= 8:
                bonus = 3
            else:
                bonus = 2

            score += bonus

            if picks_until_next <= 4:
                reasons.append(
                    f"{market_label} {yahoo_adp:.1f}: may "
                    f"survive the short turn to pick {next_pick}"
                )
            else:
                reasons.append(
                    f"{market_label} {yahoo_adp:.1f}: unlikely "
                    f"to survive until pick {next_pick}"
                )

        else:

            gap = (
                yahoo_adp - next_pick
            )

            penalty = min(
                gap * 0.35,
                8,
            )

            score -= penalty

            reasons.append(
                f"{market_label} {yahoo_adp:.1f}: reasonable "
                f"chance he survives to pick {next_pick}"
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
    # 5. Bench balance.
    # ---------------------------------------------------------

    bench_bonus, bench_reason = bench_balance_bonus(
        player["position"],
        counts,
    )

    score += bench_bonus

    if bench_reason:
        reasons.append(bench_reason)

    # ---------------------------------------------------------
    # 6. Late-round roster completion.
    # ---------------------------------------------------------

    completion_bonus, completion_reason = (
        roster_completion_bonus(
            player["position"],
            counts,
            round_number,
        )
    )

    score += completion_bonus

    if completion_reason:
        reasons.append(completion_reason)

    # ---------------------------------------------------------
    # Special-teams draft-run awareness.
    # ---------------------------------------------------------

    run_bonus, run_reason = (
        special_teams_run_bonus(
            player,
            available,
            state,
            round_number,
        )
    )

    score += run_bonus

    if run_reason:
        reasons.append(run_reason)

    # ---------------------------------------------------------
    # 7. FantasyPros positional tier.
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
    # 8. K/DST positional quality.
    #
    # Once we are considering special teams, prefer the
    # FantasyPros positional ranking over small differences
    # in overall ADP.
    # ---------------------------------------------------------

    special_position = normalised_position(
        player["position"]
    )

    if special_position in ("K", "DST"):
        fp_position_rank = player.get(
            "fantasypros_position_rank"
        )

        if fp_position_rank is None:
            fp_position_rank = player.get(
                "position_rank"
            )

        if fp_position_rank is not None:
            if fp_position_rank <= 4:
                score += 8
            elif fp_position_rank <= 8:
                score += 5
            elif fp_position_rank <= 12:
                score += 3
            elif fp_position_rank <= 16:
                score += 1
            elif fp_position_rank > 20:
                score -= 3

    # ---------------------------------------------------------
    # 9. Positional scarcity.
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
        
    if final_roster_pick:
        completion = roster_completion_state(
            counts
        )

        if fills_required_start(
            player["position"],
            completion["missing"],
        ):
            action = "TAKE NOW"
        else:
            action = "LOW PRIORITY"
    else:
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
        "next_pick": (
            None
            if final_roster_pick
            else next_pick
        ),
        "action": action,
        "reasons": reasons,
    }

def build_candidate_pool(
    available,
    counts,
    base_limit=50,
):
    """
    Start with the best 50 overall players, but make sure
    positions needed to complete the starting lineup aren't
    accidentally excluded late in the draft.
    """

    candidates = list(
        available[:base_limit]
    )

    existing_ids = {
        str(player["id"])
        for player in candidates
    }

    state = roster_completion_state(counts)
    missing = state["missing"]

    needed_positions = set()

    if missing["QB"]:
        needed_positions.add("QB")

    if missing["TE"]:
        needed_positions.add("TE")

    if missing["K"]:
        needed_positions.add("K")

    if missing["DEF"]:
        needed_positions.update(
            {"DEF", "DST"}
        )

    added_by_position = {
        position: 0
        for position in needed_positions
    }

    for player in available:
        position = player["position"]

        if position not in needed_positions:
            continue

        if str(player["id"]) in existing_ids:
            continue

        if added_by_position[position] >= 10:
            continue

        candidates.append(player)
        existing_ids.add(str(player["id"]))
        added_by_position[position] += 1

    return candidates

def get_recommendations(
    available,
    state,
    limit=5,
):
    if not available:
        return []

    if len(state["your_roster"]) >= DRAFT_ROSTER_SIZE:
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

    final_roster_pick = (
        is_your_pick(state)
        and len(state["your_roster"])
            == DRAFT_ROSTER_SIZE - 1
    )

    candidates = build_candidate_pool(
        available,
        counts,
    )

    scored = [
        score_player(
            player,
            current_pick,
            decision_pick,
            next_pick,
            round_number,
            counts,
            available,
            state,
            final_roster_pick,
        )
        for player in candidates
    ]

    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )
    
    # TAKE NOW should be a decisive draft-night recommendation,
    # not a badge applied to several alternatives at once.
    #
    # Keep the highest-scoring TAKE NOW candidate and demote
    # any additional ones to CONSIDER.
    take_now_seen = False

    for item in scored:
        if item["action"] != "TAKE NOW":
            continue

        if not take_now_seen:
            take_now_seen = True
        else:
            item["action"] = "CONSIDER"

    return scored[:limit]

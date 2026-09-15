FLEX_POSITIONS = {
    "RB",
    "WR",
    "TE",
}

UNAVAILABLE_STATUSES = {
    "O",
    "IR",
    "IR-R",
    "PUP",
    "SUSP",
}


def projection(
    player,
    field,
):
    value = player.get(field)

    if value is None:
        return 0.0

    return float(value)


def playable(player):
    status = (
        player.get("status")
        or ""
    ).upper()

    return (
        status
        not in UNAVAILABLE_STATUSES
    )

def on_bye(
    player,
    week,
):
    bye_week = player.get(
        "bye_week"
    )

    if bye_week in {
        None,
        "",
    }:
        return False

    try:
        return int(bye_week) == int(week)
    except (
        TypeError,
        ValueError,
    ):
        return False


def build_bye_coverage(
    roster,
    current_week,
    through_week=14,
):
    coverage = []

    for week in range(
        current_week + 1,
        through_week + 1,
    ):
        bye_players = [
            player
            for player in roster
            if (
                player.get(
                    "roster_slot"
                ) != "IR"
                and on_bye(
                    player,
                    week,
                )
            )
        ]

        usable = [
            player
            for player in roster
            if (
                player.get(
                    "roster_slot"
                ) != "IR"
                and playable(player)
                and not on_bye(
                    player,
                    week,
                )
            )
        ]

        counts = {
            position: sum(
                1
                for player in usable
                if (
                    player["position"]
                    == position
                )
            )
            for position in [
                "QB",
                "RB",
                "WR",
                "TE",
                "K",
                "DST",
            ]
        }

        problems = []
        thin = []

        if counts["QB"] < 1:
            problems.append("QB")

        if counts["RB"] < 2:
            problems.append("RB")
        elif counts["RB"] == 2:
            thin.append("RB")

        if counts["WR"] < 2:
            problems.append("WR")
        elif counts["WR"] == 2:
            thin.append("WR")

        if counts["TE"] < 1:
            problems.append("TE")

        if counts["K"] < 1:
            problems.append("K")

        if counts["DST"] < 1:
            problems.append("DST")

        # After reserving 2 RB, 2 WR and 1 TE,
        # we still need one remaining RB/WR/TE
        # to fill FLEX.
        flex_remaining = (
            max(
                counts["RB"] - 2,
                0,
            )
            + max(
                counts["WR"] - 2,
                0,
            )
            + max(
                counts["TE"] - 1,
                0,
            )
        )

        if flex_remaining < 1:
            problems.append("FLEX")
        elif flex_remaining == 1:
            thin.append("FLEX")

        skill_problems = [
            position
            for position in problems
            if position not in {
                "K",
                "DST",
            }
        ]

        stream_problems = [
            position
            for position in problems
            if position in {
                "K",
                "DST",
            }
        ]

        if skill_problems:
            status = (
                "ACTION NEEDED"
            )
        elif stream_problems:
            status = "STREAM"
        elif thin:
            status = "WATCH"
        else:
            status = "GOOD"

        coverage.append(
            {
                "week": week,
                "status": status,
                "bye_players":
                    bye_players,
                "counts":
                    counts,
                "flex_remaining":
                    flex_remaining,
                "problems":
                    problems,
                "thin":
                    thin,
            }
        )

    return coverage


def bye_week_risk(
    week_info,
    current_week,
):
    weeks_away = max(
        week_info["week"]
        - current_week,
        1,
    )

    # Future problems matter, but their
    # importance increases as they approach.
    if weeks_away <= 1:
        urgency = 1.00
    elif weeks_away == 2:
        urgency = 0.80
    elif weeks_away == 3:
        urgency = 0.60
    elif weeks_away == 4:
        urgency = 0.45
    elif weeks_away == 5:
        urgency = 0.35
    elif weeks_away == 6:
        urgency = 0.30
    elif weeks_away == 7:
        urgency = 0.25
    else:
        urgency = 0.15

    skill_problems = [
        position
        for position
        in week_info["problems"]
        if position not in {
            "K",
            "DST",
        }
    ]

    stream_problems = [
        position
        for position
        in week_info["problems"]
        if position in {
            "K",
            "DST",
        }
    ]

    risk = (
        len(skill_problems) * 4.0
        + len(stream_problems) * 0.75
        + len(week_info["thin"]) * 0.50
    )

    return risk * urgency


def compare_bye_coverage(
    before,
    after,
    current_week,
):
    before_by_week = {
        item["week"]: item
        for item in before
    }

    after_by_week = {
        item["week"]: item
        for item in after
    }

    improvements = []
    regressions = []

    before_risk = 0.0
    after_risk = 0.0

    for week in sorted(
        set(before_by_week)
        | set(after_by_week)
    ):
        before_week = before_by_week.get(
            week
        )

        after_week = after_by_week.get(
            week
        )

        if (
            before_week is None
            or after_week is None
        ):
            continue

        before_risk += bye_week_risk(
            before_week,
            current_week,
        )

        after_risk += bye_week_risk(
            after_week,
            current_week,
        )

        before_problems = set(
            before_week["problems"]
        )

        after_problems = set(
            after_week["problems"]
        )

        resolved = sorted(
            before_problems
            - after_problems
        )

        created = sorted(
            after_problems
            - before_problems
        )

        if resolved:
            improvements.append(
                {
                    "week": week,
                    "positions": resolved,
                }
            )

        if created:
            regressions.append(
                {
                    "week": week,
                    "positions": created,
                }
            )

    return {
        "gain":
            before_risk
            - after_risk,

        "before_risk":
            before_risk,

        "after_risk":
            after_risk,

        "improvements":
            improvements,

        "regressions":
            regressions,
    }


def build_bye_reasons(
    bye_context,
):
    reasons = []

    for item in bye_context[
        "improvements"
    ]:
        positions = ", ".join(
            item["positions"]
        )

        reasons.append(
            f"Fixes Week {item['week']} "
            f"bye coverage at {positions}."
        )

    for item in bye_context[
        "regressions"
    ]:
        positions = ", ".join(
            item["positions"]
        )

        reasons.append(
            f"Creates a Week {item['week']} "
            f"bye-week problem at {positions}."
        )

    return reasons


def four_week_average(player):
    return (
        projection(
            player,
            "next_4_weeks_projection",
        )
        / 4.0
    )


def optimise_lineup(
    players,
    projection_field,
):
    usable = [
        player
        for player in players
        if playable(player)
    ]

    qbs = [
        p for p in usable
        if p["position"] == "QB"
    ]

    rbs = [
        p for p in usable
        if p["position"] == "RB"
    ]

    wrs = [
        p for p in usable
        if p["position"] == "WR"
    ]

    tes = [
        p for p in usable
        if p["position"] == "TE"
    ]

    kickers = [
        p for p in usable
        if p["position"] == "K"
    ]

    defenses = [
        p for p in usable
        if p["position"] == "DST"
    ]

    if (
        not qbs
        or len(rbs) < 2
        or len(wrs) < 2
        or not tes
        or not kickers
        or not defenses
    ):
        return None

    qb = max(
        qbs,
        key=lambda p:
            projection(
                p,
                projection_field,
            ),
    )

    kicker = max(
        kickers,
        key=lambda p:
            projection(
                p,
                projection_field,
            ),
    )

    defense = max(
        defenses,
        key=lambda p:
            projection(
                p,
                projection_field,
            ),
    )

    best = None

    for rb1_index in range(len(rbs)):
        for rb2_index in range(
            rb1_index + 1,
            len(rbs),
        ):
            selected_rbs = {
                rbs[rb1_index][
                    "yahoo_player_id"
                ],
                rbs[rb2_index][
                    "yahoo_player_id"
                ],
            }

            for wr1_index in range(
                len(wrs)
            ):
                for wr2_index in range(
                    wr1_index + 1,
                    len(wrs),
                ):
                    selected_wrs = {
                        wrs[wr1_index][
                            "yahoo_player_id"
                        ],
                        wrs[wr2_index][
                            "yahoo_player_id"
                        ],
                    }

                    for te in tes:
                        selected_ids = (
                            selected_rbs
                            | selected_wrs
                            | {
                                te[
                                    "yahoo_player_id"
                                ]
                            }
                        )

                        flex_candidates = [
                            p
                            for p in usable
                            if (
                                p["position"]
                                in FLEX_POSITIONS
                                and p[
                                    "yahoo_player_id"
                                ]
                                not in selected_ids
                            )
                        ]

                        if not flex_candidates:
                            continue

                        flex = max(
                            flex_candidates,
                            key=lambda p:
                                projection(
                                    p,
                                    projection_field,
                                ),
                        )

                        lineup = [
                            ("QB", qb),
                            (
                                "RB",
                                rbs[rb1_index],
                            ),
                            (
                                "RB",
                                rbs[rb2_index],
                            ),
                            (
                                "WR",
                                wrs[wr1_index],
                            ),
                            (
                                "WR",
                                wrs[wr2_index],
                            ),
                            ("TE", te),
                            ("FLEX", flex),
                            ("K", kicker),
                            ("DST", defense),
                        ]

                        total = sum(
                            projection(
                                player,
                                projection_field,
                            )
                            for _, player
                            in lineup
                        )

                        if (
                            best is None
                            or total > best["total"]
                        ):
                            best = {
                                "total": total,
                                "lineup": lineup,
                            }

    return best


def replacement_level(
    available,
    position,
    roster_ids,
):
    candidates = [
        player
        for player in available
        if (
            player["position"] == position
            and playable(player)
            and player[
                "yahoo_player_id"
            ] not in roster_ids
        )
    ]

    if not candidates:
        return 0.0

    best = max(
        candidates,
        key=four_week_average,
    )

    return four_week_average(
        best
    )


def bench_value(
    roster,
    lineup,
    available,
):
    starter_ids = {
        player["yahoo_player_id"]
        for _, player
        in lineup
    }

    roster_ids = {
        player["yahoo_player_id"]
        for player in roster
    }

    bench = [
        player
        for player in roster
        if (
            player["yahoo_player_id"]
            not in starter_ids
            and playable(player)
            and player["position"]
            not in {
                "K",
                "DST",
            }
        )
    ]

    total = 0.0

    for player in bench:
        value = four_week_average(
            player
        )

        replacement = replacement_level(
            available,
            player["position"],
            roster_ids,
        )

        total += max(
            value - replacement,
            0.0,
        )

    return total


def roster_metrics(
    roster,
    available,
):
    current_week = optimise_lineup(
        roster,
        "current_week_projection",
    )

    four_week = optimise_lineup(
        roster,
        "next_4_weeks_projection",
    )

    if (
        current_week is None
        or four_week is None
    ):
        return None

    return {
        "current_week_total":
            current_week["total"],

        "four_week_weekly":
            four_week["total"] / 4.0,

        "bench_value":
            bench_value(
                roster,
                current_week["lineup"],
                available,
            ),
    }


def transaction_allowed(
    roster,
    add_player,
    drop_player,
):
    # IR gets reviewed separately rather than
    # being treated as an ordinary bench drop.
    if (
        drop_player.get(
            "roster_slot"
        ) == "IR"
    ):
        return False

    simulated = [
        player
        for player in roster
        if (
            player["yahoo_player_id"]
            != drop_player[
                "yahoo_player_id"
            ]
        )
    ]

    simulated.append(
        add_player
    )

    counts = {}

    for player in simulated:
        position = player["position"]

        counts[position] = (
            counts.get(position, 0)
            + 1
        )

    if counts.get("QB", 0) > 2:
        return False

    if counts.get("K", 0) > 1:
        return False

    if counts.get("DST", 0) > 1:
        return False

    return True


def replacement_candidates(
    available,
    position,
    roster_ids=None,
):
    roster_ids = roster_ids or set()

    candidates = [
        player
        for player in available
        if (
            player["position"] == position
            and playable(player)
            and player["yahoo_player_id"]
            not in roster_ids
        )
    ]

    candidates.sort(
        key=four_week_average,
        reverse=True,
    )

    return candidates


def build_depth_context(
    roster,
    available,
    add_player,
    drop_player,
):
    roster_ids = {
        player["yahoo_player_id"]
        for player in roster
    }

    # The player being added would no longer
    # be available after the transaction.
    roster_ids.add(
        add_player["yahoo_player_id"]
    )

    replacements = replacement_candidates(
        available,
        drop_player["position"],
        roster_ids,
    )

    best_replacement = (
        replacements[0]
        if replacements
        else None
    )

    drop_average = four_week_average(
        drop_player
    )

    replacement_average = (
        four_week_average(
            best_replacement
        )
        if best_replacement
        else 0.0
    )

    comparable_replacements = [
        player
        for player in replacements
        if (
            four_week_average(player)
            >= drop_average - 1.0
        )
    ]

    context = {
        "drop_position":
            drop_player["position"],

        "drop_four_week_avg":
            drop_average,

        "best_replacement":
            best_replacement,

        "replacement_four_week_avg":
            replacement_average,

        "replacement_gap":
            (
                drop_average
                - replacement_average
            ),

        "comparable_replacements":
            len(
                comparable_replacements
            ),

        "primary_qb":
            None,

        "covers_primary_qb_bye":
            None,
    }

    if drop_player["position"] == "QB":
        other_qbs = [
            player
            for player in roster
            if (
                player["position"] == "QB"
                and player[
                    "yahoo_player_id"
                ]
                != drop_player[
                    "yahoo_player_id"
                ]
            )
        ]

        if other_qbs:
            primary_qb = max(
                other_qbs,
                key=lambda player:
                    projection(
                        player,
                        "current_week_projection",
                    ),
            )

            context["primary_qb"] = (
                primary_qb
            )

            context[
                "covers_primary_qb_bye"
            ] = (
                drop_player.get(
                    "bye_week"
                )
                != primary_qb.get(
                    "bye_week"
                )
            )

    return context

def replacement_security(
    player,
    roster,
    available,
    current_week,
    waiver_priority=None,
):
    roster_ids = {
        p["yahoo_player_id"]
        for p in roster
    }

    replacements = replacement_candidates(
        available,
        player["position"],
        roster_ids,
    )

    player_average = four_week_average(
        player
    )

    comparable = [
        candidate
        for candidate in replacements
        if (
            four_week_average(candidate)
            >= player_average - 1.0
        )
    ]

    comparable_count = len(
        comparable
    )

    bye_week = player.get(
        "bye_week"
    )

    weeks_until_bye = None

    if (
        bye_week is not None
        and current_week is not None
    ):
        weeks_until_bye = max(
            int(bye_week)
            - int(current_week),
            0,
        )

    risk_points = 0

    if comparable_count <= 1:
        risk_points += 3
    elif comparable_count <= 2:
        risk_points += 2
    elif comparable_count <= 4:
        risk_points += 1

    if weeks_until_bye is not None:
        if weeks_until_bye <= 1:
            risk_points += 3
        elif weeks_until_bye <= 2:
            risk_points += 2
        elif weeks_until_bye <= 4:
            risk_points += 1

    if waiver_priority is not None:
        if waiver_priority >= 10:
            risk_points += 2
        elif waiver_priority >= 7:
            risk_points += 1

    if risk_points >= 5:
        level = "LOW"
    elif risk_points >= 3:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "level": level,
        "comparable_count": (
            comparable_count
        ),
        "weeks_until_bye": (
            weeks_until_bye
        ),
        "bye_week": bye_week,
        "waiver_priority": (
            waiver_priority
        ),
    }

def classify_roster_role(
    roster,
    available,
    player,
    current_week,
    waiver_priority=None,
):
    roster_ids = {
        p["yahoo_player_id"]
        for p in roster
    }

    replacements = replacement_candidates(
        available,
        player["position"],
        roster_ids,
    )

    best_replacement = (
        replacements[0]
        if replacements
        else None
    )

    player_average = four_week_average(
        player
    )

    replacement_average = (
        four_week_average(
            best_replacement
        )
        if best_replacement
        else 0.0
    )

    replacement_gap = (
        player_average
        - replacement_average
    )

    comparable = [
        candidate
        for candidate in replacements
        if (
            four_week_average(candidate)
            >= player_average - 1.0
        )
    ]

    result = {
        "role": "USEFUL DEPTH",
        "replacement_gap": replacement_gap,
        "comparable_replacements": len(comparable),
        "best_replacement": best_replacement,
        "bye_cover": None,
        "reason": None,
    }

    result["replacement_security"] = (
        replacement_security(
            player,
            roster,
            available,
            current_week,
            waiver_priority,
        )
    )

    if player["position"] in {
        "K",
        "DST",
    }:
        if (
            replacement_gap <= 1.0
            and len(comparable) >= 3
        ):
            result["role"] = (
                "STREAMABLE POSITION"
            )
            result["reason"] = (
                f"{len(comparable)} comparable "
                f"{player['position']} options "
                "remain available."
            )

            return result

        if replacement_gap >= 2.0:
            result["role"] = (
                "STRONG STARTER"
            )
            result["reason"] = (
                f"Projects {replacement_gap:.2f} "
                "pts/week above the best "
                "available replacement."
            )

            return result

    if player["position"] == "QB":
        other_qbs = [
            p
            for p in roster
            if (
                p["position"] == "QB"
                and p["yahoo_player_id"]
                != player["yahoo_player_id"]
            )
        ]

        if other_qbs:
            primary_qb = max(
                other_qbs,
                key=lambda p: projection(
                    p,
                    "current_week_projection",
                ),
            )

            same_bye = (
                player.get("bye_week")
                == primary_qb.get("bye_week")
            )

            result["bye_cover"] = not same_bye

            if (
                same_bye
                and len(comparable) >= 2
            ):
                result["role"] = (
                    "REPLACEABLE BENCH SPOT"
                )
                result["reason"] = (
                    f"Shares {primary_qb['name']}'s "
                    f"Week {primary_qb.get('bye_week')} bye "
                    f"and {len(comparable)} comparable QBs "
                    "remain available."
                )

                return result

            if not same_bye:
                result["role"] = "USEFUL BYE COVER"
                result["reason"] = (
                    f"Provides bye-week cover for "
                    f"{primary_qb['name']}."
                )

                return result

    if replacement_gap >= 2.0:
        result["role"] = "STRONG DEPTH"
        result["reason"] = (
            f"Projects {replacement_gap:.2f} pts/week "
            "above the best available replacement."
        )

        return result

    if (
        replacement_gap <= 1.0
        and len(comparable) >= 3
    ):
        result["role"] = (
            "REPLACEABLE BENCH SPOT"
        )
        result["reason"] = (
            f"{len(comparable)} comparable "
            f"{player['position']} options remain "
            "available."
        )

        return result

    result["reason"] = (
        f"Projects {replacement_gap:.2f} pts/week "
        "above the best available replacement."
    )

    return result

def build_reasons(
    result,
    add_player,
    drop_player,
    depth_context,
):
    reasons = []

    if result["week_gain"] >= 0.25:
        reasons.append(
            "Improves the current week starting "
            f"lineup by {result['week_gain']:.2f} pts."
        )
    elif abs(result["week_gain"]) < 0.10:
        reasons.append(
            "Does not change the current week "
            "starting-lineup projection."
        )

    if result["four_week_gain"] >= 0.25:
        reasons.append(
            "Improves the four-week outlook "
            f"by {result['four_week_gain']:.2f} "
            "pts/week."
        )
    elif result["four_week_gain"] <= -0.25:
        reasons.append(
            "Weakens the four-week outlook "
            f"by {abs(result['four_week_gain']):.2f} "
            "pts/week."
        )

    if result["bench_gain"] >= 0.50:
        reasons.append(
            "Improves positional bench/depth "
            f"value by {result['bench_gain']:.2f}."
        )

    if drop_player["position"] == "QB":
        primary_qb = depth_context.get(
            "primary_qb"
        )

        if primary_qb:
            if (
                depth_context[
                    "covers_primary_qb_bye"
                ]
                is False
            ):
                reasons.append(
                    f"{drop_player['name']} and "
                    f"{primary_qb['name']} share "
                    f"the same Week "
                    f"{primary_qb.get('bye_week')} bye."
                )
            else:
                reasons.append(
                    f"{drop_player['name']} provides "
                    f"bye-week cover for "
                    f"{primary_qb['name']}."
                )

        replacement = depth_context.get(
            "best_replacement"
        )

        if replacement:
            reasons.append(
                f"{depth_context['comparable_replacements']} "
                "comparable QB"
                f"{'' if depth_context['comparable_replacements'] == 1 else 's'} "
                "remain available; best currently "
                f"{replacement['name']} at "
                f"{depth_context['replacement_four_week_avg']:.2f} "
                "pts/week."
            )

    return reasons



def score_transaction(
    before,
    after,
):
    week_gain = (
        after["current_week_total"]
        - before["current_week_total"]
    )

    four_week_gain = (
        after["four_week_weekly"]
        - before["four_week_weekly"]
    )

    bench_gain = (
        after["bench_value"]
        - before["bench_value"]
    )

    score = (
        week_gain
        + four_week_gain * 0.75
        + bench_gain * 0.20
    )

    return {
        "score":
            score,

        "week_gain":
            week_gain,

        "four_week_gain":
            four_week_gain,

        "bench_gain":
            bench_gain,
    }


def classify(result):
    if result["week_gain"] >= 1.5:
        return "STRONG MOVE"

    if result["score"] >= 1.5:
        return "CONSIDER"

    if result["score"] >= 0.75:
        return "WATCH"

    return "HOLD"


def move_type(
    result,
    add_player,
    drop_player,
):
    if (
        add_player["position"] == "DST"
        and drop_player["position"] == "DST"
    ):
        if (
            result["week_gain"]
            > result["four_week_gain"]
        ):
            return "DST STREAM"

        return "DST UPGRADE"

    if (
        add_player["position"] == "K"
        and drop_player["position"] == "K"
    ):
        return "KICKER STREAM"

    if result["week_gain"] >= 0.75:
        return "STARTER UPGRADE"

    if (
        result["week_gain"] <= 0.10
        and result["bench_gain"] >= 0.75
    ):
        return "DEPTH UPGRADE"

    if result["four_week_gain"] >= 0.50:
        return "LONGER-TERM UPGRADE"

    return "ROSTER MOVE"


def build_transaction_recommendations(
    roster,
    available,
    limit=5,
    current_week=1,
    waiver_priority=None,
):
    before = roster_metrics(
        roster,
        available,
    )

    if before is None:
        return []

    before_bye_coverage = (
        build_bye_coverage(
            roster,
            current_week,
        )
    )

    # Limit the first pass to realistic
    # candidates rather than every obscure FA.
    candidates = sorted(
        available,
        key=lambda player: (
            projection(
                player,
                "current_week_projection",
            )
            + four_week_average(
                player
            )
        ),
        reverse=True,
    )[:60]

    results = []

    for add_player in candidates:
        for drop_player in roster:
            if not transaction_allowed(
                roster,
                add_player,
                drop_player,
            ):
                continue

            simulated = [
                player
                for player in roster
                if (
                    player[
                        "yahoo_player_id"
                    ]
                    != drop_player[
                        "yahoo_player_id"
                    ]
                )
            ]

            simulated.append(
                add_player
            )

            after = roster_metrics(
                simulated,
                available,
            )

            if after is None:
                continue

            after_bye_coverage = (
                build_bye_coverage(
                    simulated,
                    current_week,
                )
            )

            bye_context = (
                compare_bye_coverage(
                    before_bye_coverage,
                    after_bye_coverage,
                    current_week,
                )
            )

            result = score_transaction(
                before,
                after,
            )

            result[
                "bye_coverage_gain"
            ] = bye_context["gain"]

            result[
                "bye_score_adjustment"
            ] = (
                bye_context["gain"]
                * 0.25
            )

            result["score"] += (
                result[
                    "bye_score_adjustment"
                ]
            )

            if result["score"] <= 0.10:
                continue

            depth_context = (
                build_depth_context(
                    roster,
                    available,
                    add_player,
                    drop_player,
                )
            )

            reasons = build_reasons(
                result,
                add_player,
                drop_player,
                depth_context,
            )

            reasons.extend(
                build_bye_reasons(
                    bye_context
                )
            )

            result.update(
                {
                    "add":
                        add_player,

                    "drop":
                        drop_player,

                    "label":
                        classify(
                            result
                        ),

                    "move_type":
                        move_type(
                            result,
                            add_player,
                            drop_player,
                        ),

                    "drop_roster_role":
                        classify_roster_role(
                            roster,
                            available,
                            drop_player,
                            current_week,
                            waiver_priority,
                        ),
                    "bye_context":
                        bye_context,

                    "depth_context":
                        depth_context,

                    "reasons":
                        reasons,
                }
            )

            results.append(
                result
            )

    results.sort(
        key=lambda item:
            item["score"],
        reverse=True,
    )

    # Avoid filling the page with five
    # different drop options for one addition.
    output = []
    seen_adds = set()
    seen_bye_fixes = set()

    for result in results:
        add_id = result[
            "add"
        ][
            "yahoo_player_id"
        ]

        if add_id in seen_adds:
            continue

        bye_fix_key = tuple(
            (
                item["week"],
                tuple(item["positions"]),
            )
            for item in result.get(
                "bye_context",
                {}
            ).get(
                "improvements",
                [],
            )
        )

        if (
            bye_fix_key
            and bye_fix_key
            in seen_bye_fixes
        ):
            continue

        seen_adds.add(
            add_id
        )

        if bye_fix_key:
            seen_bye_fixes.add(
                bye_fix_key
            )

        output.append(
            result
        )

        if len(output) >= limit:
            break

    return output
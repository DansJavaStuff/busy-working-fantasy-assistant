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
    week_1 = optimise_lineup(
        roster,
        "week_1_projection",
    )

    four_week = optimise_lineup(
        roster,
        "next_4_weeks_projection",
    )

    if (
        week_1 is None
        or four_week is None
    ):
        return None

    return {
        "week_1_total":
            week_1["total"],

        "four_week_weekly":
            four_week["total"] / 4.0,

        "bench_value":
            bench_value(
                roster,
                week_1["lineup"],
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
                        "week_1_projection",
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


def build_reasons(
    result,
    add_player,
    drop_player,
    depth_context,
):
    reasons = []

    if result["week_gain"] >= 0.25:
        reasons.append(
            "Improves the Week 1 starting "
            f"lineup by {result['week_gain']:.2f} pts."
        )
    elif abs(result["week_gain"]) < 0.10:
        reasons.append(
            "Does not change the Week 1 "
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
        after["week_1_total"]
        - before["week_1_total"]
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
):
    before = roster_metrics(
        roster,
        available,
    )

    if before is None:
        return []

    # Limit the first pass to realistic
    # candidates rather than every obscure FA.
    candidates = sorted(
        available,
        key=lambda player: (
            projection(
                player,
                "week_1_projection",
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

            result = score_transaction(
                before,
                after,
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

    for result in results:
        add_id = result[
            "add"
        ][
            "yahoo_player_id"
        ]

        if add_id in seen_adds:
            continue

        seen_adds.add(
            add_id
        )

        output.append(
            result
        )

        if len(output) >= limit:
            break

    return output

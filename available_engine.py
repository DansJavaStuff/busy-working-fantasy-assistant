from database import (
    load_season_league_state,
    load_season_roster,
)
from sleeper_compare import compare_players
from transaction_engine import (
    build_transaction_recommendations,
    four_week_average,
)
from yahoo_provider import (
    enrich_local_roster,
    get_effective_available_players,
    yahoo_provider,
)


_AVAILABLE_CACHE = {
    "snapshot_key": None,
    "data": None,
}


# Replacement level is deliberately based on the available pool rather than
# absolute fantasy points.  In a 12-team league these cut-offs represent the
# sort of player likely to remain obtainable if we pass on the current option.
REPLACEMENT_RANK = {
    "QB": 6,
    "RB": 10,
    "WR": 10,
    "TE": 6,
    "K": 5,
    "DST": 5,
}


def next_week_projection(player, week):
    value = (
        player.get("weeks", {})
        .get(str(int(week) + 1), {})
        .get("projection")
    )

    if value is None:
        return 0.0

    return float(value)


def _name_key(value):
    return "".join(
        char.lower()
        for char in str(value or "")
        if char.isalnum()
    )


def _sleeper_index(results):
    return {
        _name_key(item.get("name")):
            item
        for item in (results or [])
        if item.get("name")
    }


def _position_baselines(
    available,
    week,
):
    grouped = {}

    for player in available:
        position = player.get(
            "position"
        )

        if position not in (
            REPLACEMENT_RANK
        ):
            continue

        grouped.setdefault(
            position,
            [],
        ).append(player)

    baselines = {}

    for position, players in (
        grouped.items()
    ):
        rank = REPLACEMENT_RANK[
            position
        ]

        next_values = sorted(
            (
                next_week_projection(
                    player,
                    week,
                )
                for player in players
            ),
            reverse=True,
        )

        four_values = sorted(
            (
                four_week_average(
                    player
                )
                for player in players
            ),
            reverse=True,
        )

        next_index = min(
            rank - 1,
            len(next_values) - 1,
        )

        four_index = min(
            rank - 1,
            len(four_values) - 1,
        )

        baselines[position] = {
            "rank": rank,
            "next_week":
                (
                    next_values[
                        next_index
                    ]
                    if next_values
                    else 0.0
                ),
            "four_week":
                (
                    four_values[
                        four_index
                    ]
                    if four_values
                    else 0.0
                ),
        }

    return baselines


def _position_value(
    position,
    next_week,
    four_week,
    baselines,
):
    baseline = baselines.get(
        position,
        {
            "next_week": 0.0,
            "four_week": 0.0,
        },
    )

    next_edge = (
        float(next_week)
        - float(
            baseline[
                "next_week"
            ]
        )
    )

    four_edge = (
        float(four_week)
        - float(
            baseline[
                "four_week"
            ]
        )
    )

    value = (
        next_edge * 0.55
        + four_edge * 0.45
    )

    return {
        "value": round(
            value,
            2,
        ),
        "next_edge": round(
            next_edge,
            2,
        ),
        "four_edge": round(
            four_edge,
            2,
        ),
        "baseline": baseline,
    }


def _bye_week(player):
    try:
        return int(
            player.get("bye_week")
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def _qb_bye_context(roster):
    qbs = [
        player
        for player in roster
        if (
            player.get("position")
            == "QB"
            and player.get(
                "roster_slot"
            ) != "IR"
        )
    ]

    if not qbs:
        return {
            "primary": None,
            "bye_week": None,
            "conflict": False,
            "bye_conflict_drop": None,
        }

    primary = max(
        qbs,
        key=four_week_average,
    )

    primary_bye = _bye_week(
        primary
    )

    known_byes = [
        _bye_week(player)
        for player in qbs
        if _bye_week(player)
        is not None
    ]

    conflict = (
        len(known_byes) >= 2
        and primary_bye is not None
        and all(
            bye == primary_bye
            for bye in known_byes
        )
    )

    bye_conflict_drop = None

    if conflict:
        alternatives = [
            player
            for player in qbs
            if player is not primary
        ]

        if alternatives:
            bye_conflict_drop = min(
                alternatives,
                key=four_week_average,
            )

    return {
        "primary": primary,
        "bye_week": primary_bye,
        "conflict": conflict,
        "bye_conflict_drop":
            bye_conflict_drop,
    }


def _qb_bye_adjustment(
    player,
    qb_context,
):
    if (
        player.get("position")
        != "QB"
        or not qb_context[
            "conflict"
        ]
    ):
        return 0.0

    primary_bye = qb_context[
        "bye_week"
    ]
    candidate_bye = _bye_week(
        player
    )

    if (
        candidate_bye is None
        or primary_bye is None
    ):
        return 0.0

    if candidate_bye != primary_bye:
        return 4.0

    return -4.0


def build_available_rankings(
    season,
    week,
    limit=20,
    sleeper_fetch=compare_players,
):
    local_roster = load_season_roster(
        season
    )

    roster = enrich_local_roster(
        local_roster
    )

    league_state = (
        load_season_league_state(
            season
        )
    )

    waiver_priority = (
        league_state.get(
            "waiver_priority"
        )
    )

    available = (
        get_effective_available_players(
            local_roster
        )
    )

    provider_status = (
        yahoo_provider.get_status()
    )

    captured_at = provider_status.get(
        "captured_at"
    )

    snapshot_key = (
        (
            captured_at.isoformat()
            if captured_at
            else None
        ),
        int(week),
        tuple(
            sorted(
                str(
                    player.get(
                        "yahoo_player_id",
                        player.get("name", ""),
                    )
                )
                for player in roster
            )
        ),
        int(limit),
        waiver_priority,
    )

    if (
        _AVAILABLE_CACHE["snapshot_key"]
        == snapshot_key
        and _AVAILABLE_CACHE["data"]
        is not None
    ):
        return _AVAILABLE_CACHE["data"]

    qb_context = (
        _qb_bye_context(
            roster
        )
    )

    position_baselines = (
        _position_baselines(
            available,
            week,
        )
    )

    moves = (
        build_transaction_recommendations(
            roster,
            available,
            limit=40,
            current_week=week,
            waiver_priority=waiver_priority,
        )
    )

    move_by_add = {
        str(
            item["add"][
                "yahoo_player_id"
            ]
        ): item
        for item in moves
    }

    candidates = []

    for player in available:
        next_week = next_week_projection(
            player,
            week,
        )
        four_week = four_week_average(
            player
        )

        # Ignore the long tail of players who have no useful
        # forward projection in either horizon.
        if (
            next_week <= 0
            and four_week <= 0
        ):
            continue

        move = move_by_add.get(
            str(
                player[
                    "yahoo_player_id"
                ]
            )
        )

        roster_gain = (
            float(move["score"])
            if move
            else 0.0
        )

        bye_gain = (
            float(
                move.get(
                    "bye_score_adjustment",
                    0.0,
                )
            )
            if move
            else 0.0
        )

        qb_bye_adjustment = (
            _qb_bye_adjustment(
                player,
                qb_context,
            )
        )

        position_value = (
            _position_value(
                player.get(
                    "position"
                ),
                next_week,
                four_week,
                position_baselines,
            )
        )

        # First-pass score is now position-relative: a 7-point TE can outrank
        # a 19-point QB if the TE is exceptional compared with other available
        # TEs.  Roster need and bye coverage remain separate signals.
        preliminary = (
            position_value[
                "value"
            ]
            + roster_gain * 1.25
            + bye_gain
            + qb_bye_adjustment
        )

        candidates.append(
            {
                "player": player,
                "next_week_projection":
                    next_week,
                "four_week_average":
                    four_week,
                "move": move,
                "qb_bye_adjustment":
                    qb_bye_adjustment,
                "position_value":
                    position_value,
                "preliminary_score":
                    preliminary,
            }
        )

    candidates.sort(
        key=lambda item:
            item[
                "preliminary_score"
            ],
        reverse=True,
    )

    # Keep the network call targeted.  Sleeper currently
    # supports the offensive positions we rescore here.
    sleeper_targets = [
        item["player"]
        for item in candidates[:30]
        if item["player"].get(
            "position"
        )
        in {
            "QB",
            "RB",
            "WR",
            "TE",
        }
    ]

    sleeper_error = None

    try:
        sleeper_results = (
            sleeper_fetch(
                sleeper_targets,
                week=int(week) + 1,
                season=season,
            )
            if sleeper_targets
            else []
        )
    except Exception as exc:
        sleeper_results = []
        sleeper_error = str(exc)

    sleeper = _sleeper_index(
        sleeper_results
    )

    for item in candidates:
        player = item["player"]

        sleeper_row = sleeper.get(
            _name_key(
                player.get("name")
            )
        )

        sleeper_projection = (
            sleeper_row.get(
                "sleeper_yahoo_projection"
            )
            if sleeper_row
            else None
        )

        item["sleeper_next_week"] = (
            sleeper_projection
        )

        if sleeper_projection is None:
            consensus_next_week = (
                item[
                    "next_week_projection"
                ]
            )
        else:
            consensus_next_week = (
                (
                    item[
                        "next_week_projection"
                    ]
                    + float(
                        sleeper_projection
                    )
                )
                / 2.0
            )

        item[
            "consensus_next_week"
        ] = consensus_next_week

        move = item["move"]
        roster_gain = (
            float(move["score"])
            if move
            else 0.0
        )

        bye_gain = (
            float(
                move.get(
                    "bye_score_adjustment",
                    0.0,
                )
            )
            if move
            else 0.0
        )

        position_value = (
            _position_value(
                player.get(
                    "position"
                ),
                consensus_next_week,
                item[
                    "four_week_average"
                ],
                position_baselines,
            )
        )

        item[
            "position_value"
        ] = position_value

        item["score"] = (
            position_value[
                "value"
            ]
            + roster_gain * 1.25
            + bye_gain
            + item[
                "qb_bye_adjustment"
            ]
        )

        reasons = []

        if (
            position_value[
                "value"
            ] >= 1.0
        ):
            reasons.append(
                "Projects clearly above the available "
                f"{player.get('position')} replacement level."
            )
        elif (
            position_value[
                "value"
            ] <= -1.0
        ):
            reasons.append(
                "Projects below the available "
                f"{player.get('position')} replacement level."
            )

        if (
            item[
                "qb_bye_adjustment"
            ] > 0
        ):
            reasons.append(
                "Covers the shared QB bye "
                f"in Week {qb_context['bye_week']}."
            )
        elif (
            item[
                "qb_bye_adjustment"
            ] < 0
        ):
            reasons.append(
                "Does not solve the shared QB "
                f"bye in Week {qb_context['bye_week']}."
            )

        if move:
            reasons.extend(
                move.get(
                    "reasons",
                    [],
                )[:2]
            )

        if sleeper_projection is not None:
            delta = (
                float(
                    sleeper_projection
                )
                - item[
                    "next_week_projection"
                ]
            )

            if delta >= 1.0:
                reasons.append(
                    "Sleeper is more optimistic "
                    "than Yahoo for next week."
                )
            elif delta <= -1.0:
                reasons.append(
                    "Sleeper is more cautious "
                    "than Yahoo for next week."
                )
            else:
                reasons.append(
                    "Yahoo and Sleeper are broadly "
                    "aligned for next week."
                )

        item["reasons"] = reasons

    candidates.sort(
        key=lambda item:
            item["score"],
        reverse=True,
    )

    ranked = []
    position_counts = {}
    position_limits = {
        "QB": 3,
        "RB": 6,
        "WR": 6,
        "TE": 3,
        "K": 2,
        "DST": 2,
    }

    selected = []

    for item in candidates:
        position = item[
            "player"
        ].get("position")

        limit_for_position = (
            position_limits.get(
                position,
                limit,
            )
        )

        if (
            position_counts.get(
                position,
                0,
            )
            >= limit_for_position
        ):
            continue

        selected.append(item)
        position_counts[position] = (
            position_counts.get(
                position,
                0,
            )
            + 1
        )

        if len(selected) >= limit:
            break

    for index, item in enumerate(
        selected,
        start=1,
    ):
        move = item["move"]

        bye_fix = (
            item[
                "qb_bye_adjustment"
            ] > 0
        )

        best_drop = (
            move.get("drop")
            if move
            else None
        )

        if (
            bye_fix
            and best_drop is None
        ):
            best_drop = qb_context.get(
                "bye_conflict_drop"
            )

        move_label = (
            "BYE FIX"
            if bye_fix
            else (
                move.get("label")
                if move
                else "SHORTLIST"
            )
        )

        move_type_label = (
            "QB COVER"
            if bye_fix
            else (
                move.get("move_type")
                if move
                else "FREE AGENT"
            )
        )

        ranked.append(
            {
                **item,
                "rank": index,
                "best_drop":
                    best_drop,
                "move_label":
                    move_label,
                "move_type":
                    move_type_label,
                "roster_gain":
                    (
                        float(
                            move.get(
                                "score",
                                0.0,
                            )
                        )
                        if move
                        else None
                    ),
                "bye_gain":
                    (
                        float(
                            move.get(
                                "bye_score_adjustment",
                                0.0,
                            )
                        )
                        if move
                        else 0.0
                    ),
            }
        )

    data = {
        "rankings": ranked,
        "provider_status":
            provider_status,
        "sleeper_error":
            sleeper_error,
        "week":
            int(week),
        "target_week":
            int(week) + 1,

        "waiver_priority":
            waiver_priority,

        "position_baselines":
            position_baselines,
    }

    _AVAILABLE_CACHE[
        "snapshot_key"
    ] = snapshot_key
    _AVAILABLE_CACHE[
        "data"
    ] = data

    return data

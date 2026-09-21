from database import load_season_roster
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
    )

    if (
        _AVAILABLE_CACHE["snapshot_key"]
        == snapshot_key
        and _AVAILABLE_CACHE["data"]
        is not None
    ):
        return _AVAILABLE_CACHE["data"]

    moves = (
        build_transaction_recommendations(
            roster,
            available,
            limit=40,
            current_week=week,
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

        # First-pass score selects the shortlist before the
        # independent Sleeper call.  It deliberately favours
        # forward value and roster fit over this week's score.
        preliminary = (
            next_week * 0.55
            + four_week * 0.45
            + roster_gain * 1.25
            + bye_gain
        )

        candidates.append(
            {
                "player": player,
                "next_week_projection":
                    next_week,
                "four_week_average":
                    four_week,
                "move": move,
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

        item["score"] = (
            consensus_next_week * 0.55
            + item[
                "four_week_average"
            ] * 0.45
            + roster_gain * 1.25
            + bye_gain
        )

        reasons = []

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

    for index, item in enumerate(
        candidates[:limit],
        start=1,
    ):
        move = item["move"]

        ranked.append(
            {
                **item,
                "rank": index,
                "best_drop":
                    (
                        move.get("drop")
                        if move
                        else None
                    ),
                "move_label":
                    (
                        move.get("label")
                        if move
                        else "WATCH"
                    ),
                "move_type":
                    (
                        move.get("move_type")
                        if move
                        else "FREE AGENT"
                    ),
                "roster_gain":
                    (
                        float(
                            move.get(
                                "score",
                                0.0,
                            )
                        )
                        if move
                        else 0.0
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
    }

    _AVAILABLE_CACHE[
        "snapshot_key"
    ] = snapshot_key
    _AVAILABLE_CACHE[
        "data"
    ] = data

    return data

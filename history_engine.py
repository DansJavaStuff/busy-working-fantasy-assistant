from database import (
    load_player_week_history,
    load_week_lineup,
    load_week_roster,
)


NON_SCORING_SLOTS = {
    "BN",
    "IR",
}





OPTIMAL_SLOTS = (
    "QB",
    "RB",
    "RB",
    "WR",
    "WR",
    "TE",
    "FLEX",
    "K",
    "DEF",
)


def _slot_accepts(
    slot,
    position,
):
    position = (
        "DEF"
        if position in {
            "DEF",
            "DST",
        }
        else position
    )

    if slot == "FLEX":
        return position in {
            "RB",
            "WR",
            "TE",
        }

    return slot == position


def _best_actual_lineup(
    rows,
):
    """Return the highest-scoring legal lineup from the owned roster."""

    candidates = [
        row
        for row in rows
        if (
            row["roster_slot"] != "IR"
            and row["actual"] is not None
        )
    ]

    best_score = None
    best_lineup = None

    def search(
        slot_index,
        used_ids,
        selected,
        score,
    ):
        nonlocal best_score
        nonlocal best_lineup

        if slot_index == len(
            OPTIMAL_SLOTS
        ):
            if (
                best_score is None
                or score > best_score
            ):
                best_score = score
                best_lineup = [
                    dict(item)
                    for item in selected
                ]
            return

        slot = OPTIMAL_SLOTS[
            slot_index
        ]

        for player in candidates:
            player_id = str(
                player["player_id"]
            )

            if player_id in used_ids:
                continue

            if not _slot_accepts(
                slot,
                player["position"],
            ):
                continue

            selected.append(
                {
                    "slot": slot,
                    "player": player,
                }
            )

            search(
                slot_index + 1,
                used_ids
                | {
                    player_id,
                },
                selected,
                score
                + float(
                    player["actual"]
                ),
            )

            selected.pop()

    search(
        0,
        set(),
        [],
        0.0,
    )

    return (
        best_score,
        best_lineup,
    )


def _build_optimal_analysis(
    rows,
    starter_actual,
):
    active_rows = [
        row
        for row in rows
        if row["roster_slot"] != "IR"
    ]

    complete = (
        bool(active_rows)
        and all(
            row["actual"] is not None
            for row in active_rows
        )
    )

    if not complete:
        return {
            "complete": False,
            "optimal_actual": None,
            "lineup_delta": None,
            "would_start": [],
            "would_sit": [],
            "optimal_lineup": [],
        }

    (
        optimal_actual,
        optimal_lineup,
    ) = _best_actual_lineup(
        rows
    )

    if (
        optimal_actual is None
        or optimal_lineup is None
    ):
        return {
            "complete": False,
            "optimal_actual": None,
            "lineup_delta": None,
            "would_start": [],
            "would_sit": [],
            "optimal_lineup": [],
        }

    submitted_ids = {
        str(row["player_id"])
        for row in rows
        if row["is_starter"]
    }

    optimal_ids = {
        str(
            item["player"][
                "player_id"
            ]
        )
        for item in optimal_lineup
    }

    would_start = [
        item
        for item in optimal_lineup
        if str(
            item["player"][
                "player_id"
            ]
        ) not in submitted_ids
    ]

    would_sit = [
        row
        for row in rows
        if (
            row["is_starter"]
            and str(
                row["player_id"]
            )
            not in optimal_ids
        )
    ]

    would_start.sort(
        key=lambda item:
            float(
                item["player"][
                    "actual"
                ]
            ),
        reverse=True,
    )

    would_sit.sort(
        key=lambda row:
            float(
                row["actual"]
            ),
    )

    return {
        "complete": True,
        "optimal_actual":
            optimal_actual,
        "lineup_delta":
            optimal_actual
            - starter_actual,
        "would_start":
            would_start,
        "would_sit":
            would_sit,
        "optimal_lineup":
            optimal_lineup,
    }


def build_history_week(
    week,
    season=2026,
):
    """Join historical roster ownership to durable player/week results."""

    week = int(week)

    roster = load_week_roster(
        week,
        season=season,
    )

    submitted_lineup = {
        row["player_id"]: row
        for row in load_week_lineup(
            week,
            season=season,
        )
    }

    player_history = {
        row["player_id"]: row
        for row in load_player_week_history(
            week,
            season=season,
        )
    }

    rows = []

    starter_projection = 0.0
    starter_actual = 0.0
    starter_projection_count = 0
    starter_actual_count = 0

    bench_actual = 0.0
    bench_actual_count = 0

    for roster_player in roster:
        result = player_history.get(
            roster_player["player_id"],
            {},
        )

        lineup = submitted_lineup.get(
            roster_player["player_id"]
        )

        effective_slot = (
            lineup["lineup_slot"]
            if lineup
            else roster_player[
                "roster_slot"
            ]
        )

        effective_index = (
            lineup["slot_index"]
            if lineup
            else roster_player[
                "slot_index"
            ]
        )

        projection = result.get(
            "projection"
        )
        actual = result.get(
            "actual"
        )

        variance = None

        if (
            projection is not None
            and actual is not None
        ):
            variance = (
                float(actual)
                - float(projection)
            )

        is_starter = (
            effective_slot
            not in NON_SCORING_SLOTS
        )

        if is_starter:
            if projection is not None:
                starter_projection += float(
                    projection
                )
                starter_projection_count += 1

            if actual is not None:
                starter_actual += float(
                    actual
                )
                starter_actual_count += 1
        elif (
            roster_player["roster_slot"]
            == "BN"
            and actual is not None
        ):
            bench_actual += float(
                actual
            )
            bench_actual_count += 1

        rows.append(
            {
                **roster_player,
                "roster_slot":
                    effective_slot,
                "slot_index":
                    effective_index,
                "projection": projection,
                "actual": actual,
                "variance": variance,
                "is_starter": is_starter,
                "has_history":
                    bool(result),
                "lineup_source":
                    (
                        lineup.get(
                            "source"
                        )
                        if lineup
                        else None
                    ),
            }
        )

    slot_order = {
        "QB": 1,
        "RB": 2,
        "WR": 3,
        "TE": 4,
        "FLEX": 5,
        "K": 6,
        "DEF": 7,
        "BN": 8,
        "IR": 9,
    }

    rows.sort(
        key=lambda row: (
            slot_order.get(
                row["roster_slot"],
                99,
            ),
            row["slot_index"],
        )
    )

    optimal_analysis = (
        _build_optimal_analysis(
            rows,
            starter_actual,
        )
    )

    return {
        "season": int(season),
        "week": week,
        "rows": rows,
        "roster_count": len(roster),
        "starter_count": sum(
            1
            for row in rows
            if row["is_starter"]
        ),
        "starter_projection":
            starter_projection,
        "starter_projection_count":
            starter_projection_count,
        "starter_actual":
            starter_actual,
        "starter_actual_count":
            starter_actual_count,
        "bench_actual":
            bench_actual,
        "bench_actual_count":
            bench_actual_count,
        "complete_actuals":
            bool(rows)
            and all(
                row["actual"] is not None
                for row in rows
                if row["is_starter"]
            ),
        "submitted_lineup_available":
            bool(submitted_lineup),
        "optimal_analysis":
            optimal_analysis,
    }

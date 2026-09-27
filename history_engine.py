from database import (
    load_player_week_history,
    load_week_roster,
)


NON_SCORING_SLOTS = {
    "BN",
    "IR",
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
            roster_player["roster_slot"]
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
                "projection": projection,
                "actual": actual,
                "variance": variance,
                "is_starter": is_starter,
                "has_history":
                    bool(result),
            }
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
    }

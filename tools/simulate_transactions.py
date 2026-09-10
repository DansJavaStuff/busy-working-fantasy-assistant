from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

ROSTER_FILE = DATA_DIR / "yahoo_my_team.json"
AVAILABLE_FILE = DATA_DIR / "yahoo_available_players.json"


STARTER_REQUIREMENTS = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "K": 1,
    "DST": 1,
}

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


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


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
        status not in UNAVAILABLE_STATUSES
    )


def optimise_lineup(
    players,
    projection_field,
):
    """
    Find the best legal lineup.

    Roster:
      QB
      RB
      RB
      WR
      WR
      TE
      FLEX
      K
      DST
    """

    usable = [
        player
        for player in players
        if playable(player)
    ]

    best = None

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

    qbs.sort(
        key=lambda p:
            projection(
                p,
                projection_field,
            ),
        reverse=True,
    )

    kickers.sort(
        key=lambda p:
            projection(
                p,
                projection_field,
            ),
        reverse=True,
    )

    defenses.sort(
        key=lambda p:
            projection(
                p,
                projection_field,
            ),
        reverse=True,
    )

    qb = qbs[0]
    kicker = kickers[0]
    defense = defenses[0]

    # Small roster, so brute-force RB/WR/TE/FLEX.
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

            for wr1_index in range(len(wrs)):
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


def four_week_average(player):
    return (
        projection(
            player,
            "next_4_weeks_projection",
        )
        / 4.0
    )


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
        player_value = (
            four_week_average(
                player
            )
        )

        replacement = (
            replacement_level(
                available,
                player["position"],
                roster_ids,
            )
        )

        value_above_replacement = (
            player_value
            - replacement
        )

        total += max(
            value_above_replacement,
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

        "four_week_total":
            four_week["total"],

        "four_week_weekly":
            (
                four_week["total"]
                / 4.0
            ),

        "bench_value":
            bench_value(
                roster,
                week_1["lineup"],
                available,
            ),

        "week_1_lineup":
            week_1["lineup"],
    }


def transaction_allowed(
    roster,
    add_player,
    drop_player,
):
    """
    Apply basic roster-construction rules.

    We don't want the optimiser valuing a
    third QB, second kicker, or second DST
    merely because their raw fantasy points
    are higher than a bench WR/RB.
    """

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



def transaction_score(
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

    # Starting points matter most.
    score = (
        week_gain * 1.00
        + four_week_gain * 0.75
        + bench_gain * 0.20
    )

    return {
        "score": score,
        "week_gain": week_gain,
        "four_week_gain":
            four_week_gain,
        "bench_gain": bench_gain,
    }


def move_type(
    result,
    add_player,
    drop_player,
):
    week_gain = result[
        "week_gain"
    ]

    four_week_gain = result[
        "four_week_gain"
    ]

    bench_gain = result[
        "bench_gain"
    ]

    if (
        add_player["position"] == "DST"
        and drop_player["position"] == "DST"
    ):
        if week_gain > four_week_gain:
            return "DST STREAM"
        return "DST UPGRADE"

    if (
        add_player["position"] == "K"
        and drop_player["position"] == "K"
    ):
        return "KICKER STREAM"

    if week_gain >= 0.75:
        return "STARTER UPGRADE"

    if (
        week_gain <= 0.10
        and bench_gain >= 0.75
    ):
        return "DEPTH UPGRADE"

    if four_week_gain >= 0.50:
        return "LONGER-TERM UPGRADE"

    return "ROSTER MOVE"



def classify(result):
    week_gain = result[
        "week_gain"
    ]

    score = result["score"]

    if week_gain >= 1.5:
        return "STRONG MOVE"

    if score >= 1.5:
        return "CONSIDER"

    if score >= 0.75:
        return "WATCH"

    return "HOLD"


def main():
    roster = load_json(
        ROSTER_FILE
    )

    available = load_json(
        AVAILABLE_FILE
    )

    before = roster_metrics(
        roster,
        available,
    )

    if before is None:
        raise SystemExit(
            "Current roster cannot fill "
            "a legal starting lineup."
        )

    print(
        "CURRENT WEEK 1 PROJECTION"
    )
    print(
        "========================="
    )
    print(
        f"{before['week_1_total']:.2f}"
    )

    results = []

    # Keep this first run manageable.
    candidates = sorted(
        available,
        key=lambda p: (
            projection(
                p,
                "week_1_projection",
            )
            + four_week_average(p)
        ),
        reverse=True,
    )[:60]

    for add_player in candidates:
        for drop_player in roster:

            if not transaction_allowed(
                roster,
                add_player,
                drop_player,
            ):
                continue

            # IR is evaluated separately as a
            # stash decision for now.
            if (
                drop_player.get("status")
                or ""
            ).upper() in {
                "IR",
                "IR-R",
            }:
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

            result = transaction_score(
                before,
                after,
            )

            # Ignore numerical noise.
            if result["score"] <= 0.10:
                continue

            results.append(
                {
                    **result,
                    "add": add_player,
                    "drop": drop_player,
                }
            )

    results.sort(
        key=lambda item:
            item["score"],
        reverse=True,
    )

    print()
    print("TOP TRANSACTION SIMULATIONS")
    print("===========================")

    shown = 0
    seen_adds = set()

    for result in results:
        add_player = result["add"]
        drop_player = result["drop"]

        # Don't fill the report with five
        # different ways to add the same guy.
        add_id = add_player[
            "yahoo_player_id"
        ]

        if add_id in seen_adds:
            continue

        seen_adds.add(add_id)

        label = classify(
            result
        )

        transaction_type = move_type(
            result,
            add_player,
            drop_player,
        )

        print()
        print(
            f"{shown + 1}. "
            f"{label} - "
            f"{transaction_type}"
        )

        print(
            f"   ADD  "
            f"{add_player['name']} "
            f"({add_player['position']}, "
            f"bye {add_player.get('bye_week')})"
        )

        print(
            f"   DROP "
            f"{drop_player['name']} "
            f"({drop_player['position']}, "
            f"bye {drop_player.get('bye_week')})"
        )

        print(
            f"   Availability: "
            f"{add_player.get('roster_status') or '?'}"
        )

        print(
            f"   Week 1 lineup: "
            f"{result['week_gain']:+.2f}"
        )

        print(
            f"   4-week weekly: "
            f"{result['four_week_gain']:+.2f}"
        )

        print(
            f"   Bench/depth: "
            f"{result['bench_gain']:+.2f}"
        )

        print(
            f"   Score: "
            f"{result['score']:+.2f}"
        )

        status = (
            add_player.get("status")
            or ""
        )

        if status:
            print(
                f"   Add status: {status}"
            )

        drop_status = (
            drop_player.get("status")
            or ""
        )

        if drop_status:
            print(
                f"   Drop status: "
                f"{drop_status}"
            )

        shown += 1

        if shown >= 10:
            break


if __name__ == "__main__":
    main()

import re
import unicodedata


FLEX_POSITIONS = {
    "RB",
    "WR",
    "TE",
}


def normalise_name(name):
    if not name:
        return ""

    value = unicodedata.normalize(
        "NFKD",
        str(name),
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    return re.sub(
        r"[^a-z0-9]",
        "",
        value.lower(),
    )


def slot_accepts(slot, position):
    slot = (slot or "").upper()
    position = (position or "").upper()

    if slot == "FLEX":
        return position in FLEX_POSITIONS

    if slot in {"DEF", "DST"}:
        return position in {"DEF", "DST"}

    return slot == position


def fantasypros_index(cache):
    index = {}

    if not cache:
        return index

    for feed_name, players in (
        cache.get("feeds", {})
        .items()
    ):
        # The weekly cache intentionally contains only positional feeds.
        # Positional ECR is comparable only within the same position.
        if feed_name not in {
            "QB",
            "RB",
            "WR",
            "TE",
        }:
            continue

        for player in players:
            key = (
                normalise_name(
                    player.get("name")
                ),
                feed_name,
            )

            index[key] = player

    return index


def fantasypros_player(
    player,
    index,
):
    position = (
        player.get("position")
        or ""
    ).upper()

    if position == "DEF":
        position = "DST"

    return index.get(
        (
            normalise_name(
                player.get("name")
            ),
            position,
        )
    )


def yahoo_call(edge):
    if edge < -0.05:
        return "bench"
    if edge > 0.05:
        return "starter"
    return "tie"


def decision_label(edge):
    if edge < -0.05:
        return "REVIEW"
    if edge <= 0.5:
        return "TOSS-UP"
    if edge <= 1.5:
        return "CLOSE"
    return "LEAN START"


def fantasypros_context(
    starter,
    bench_player,
    fp_index,
):
    starter_fp = fantasypros_player(
        starter,
        fp_index,
    )
    bench_fp = fantasypros_player(
        bench_player,
        fp_index,
    )

    context = {
        "starter": starter_fp,
        "bench": bench_fp,
        "comparison": None,
        "agreement": None,
    }

    if not starter_fp or not bench_fp:
        return context

    starter_position = (
        starter.get("position")
        or ""
    ).upper()
    bench_position = (
        bench_player.get("position")
        or ""
    ).upper()

    # Positional ECR cannot fairly compare a WR18 with an RB14. In that case
    # surface the two ranks as context but do not turn them into a winner.
    if starter_position != bench_position:
        context["comparison"] = (
            "cross_position"
        )
        return context

    starter_ecr = starter_fp.get("ecr")
    bench_ecr = bench_fp.get("ecr")

    if (
        starter_ecr is None
        or bench_ecr is None
    ):
        return context

    starter_ecr = float(starter_ecr)
    bench_ecr = float(bench_ecr)

    if starter_ecr < bench_ecr:
        context["comparison"] = "starter"
    elif bench_ecr < starter_ecr:
        context["comparison"] = "bench"
    else:
        context["comparison"] = "tie"

    return context


def build_start_sit_decisions(
    lineup,
    bench,
    fantasypros_cache=None,
    threshold=3.0,
):
    """Return actionable close start/sit calls.

    Yahoo's current-week projection identifies close choices. FantasyPros weekly
    positional ECR is an optional independent signal when both players are in
    the limited weekly feed. Missing FantasyPros data is never treated as a
    vote, and cross-position ECR is never compared directly.
    """

    fp_index = fantasypros_index(
        fantasypros_cache
    )

    unlocked_starters = [
        item
        for item in lineup
        if item.get("player")
        and item["player"].get(
            "current_week_actual"
        ) is None
    ]

    unlocked_bench = [
        player
        for player in bench
        if player.get(
            "current_week_actual"
        ) is None
    ]

    decisions = []

    for bench_player in unlocked_bench:
        eligible = [
            item
            for item in unlocked_starters
            if slot_accepts(
                item.get("slot"),
                bench_player.get("position"),
            )
        ]

        if not eligible:
            continue

        starter_item = min(
            eligible,
            key=lambda item: float(
                item["player"].get(
                    "current_week_projection"
                )
                or 0
            ),
        )

        starter = starter_item["player"]

        starter_projection = float(
            starter.get(
                "current_week_projection"
            )
            or 0
        )
        bench_projection = float(
            bench_player.get(
                "current_week_projection"
            )
            or 0
        )

        edge = (
            starter_projection
            - bench_projection
        )

        if edge > threshold:
            continue

        fp = fantasypros_context(
            starter,
            bench_player,
            fp_index,
        )

        yahoo = yahoo_call(edge)

        if fp["comparison"] in {
            "starter",
            "bench",
            "tie",
        }:
            if (
                yahoo == fp["comparison"]
                or fp["comparison"] == "tie"
                or yahoo == "tie"
            ):
                fp["agreement"] = "agree"
            else:
                fp["agreement"] = "disagree"

        decisions.append(
            {
                "label": decision_label(edge),
                "slot": starter_item.get("slot"),
                "start": starter,
                "sit": bench_player,
                "yahoo_edge": round(edge, 2),
                "yahoo_call": yahoo,
                "fantasypros": fp,
            }
        )

    decisions.sort(
        key=lambda item: item[
            "yahoo_edge"
        ]
    )

    return decisions

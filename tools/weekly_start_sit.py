from fantasy_calendar import current_fantasy_week
from weekly_engine import build_weekly_data
from weekly_evidence import build_start_sit_evidence


def _fmt_edge(value):
    if value is None:
        return "—"
    return f"{value:+.2f}"


def main():
    weekly = build_weekly_data()
    week = weekly.get("week") or current_fantasy_week(2026)

    decisions = build_start_sit_evidence(
        weekly["lineup"],
        weekly["bench"],
        week=week,
    )

    print(f"Busy Working start/sit review · Week {week}")
    print()

    if not decisions:
        print(
            "No unlocked bench player is within 3 Yahoo-projected points "
            "of an eligible starter."
        )
        return

    for decision in decisions:
        start = decision["start"]
        sit = decision["sit"]
        sleeper = decision["sleeper"]

        print(decision["recommendation"])
        print(
            f"  {start['name']} ({decision['slot']}) vs "
            f"{sit['name']} ({sit.get('position')})"
        )
        print(
            f"  Yahoo edge: {_fmt_edge(decision['yahoo_edge'])} "
            f"for {start['name']}"
        )

        if sleeper["edge"] is not None:
            print(
                f"  Sleeper edge: {_fmt_edge(sleeper['edge'])} "
                f"for {start['name']} "
                "(rescored to Busy Working Yahoo points)"
            )
            print(
                f"  Sources: {sleeper['agreement'].upper()}"
            )
        elif sleeper.get("error"):
            print(
                "  Sleeper: unavailable · "
                + sleeper["error"]
            )
        else:
            print("  Sleeper: projection unavailable for one or both players")

        print()


if __name__ == "__main__":
    main()

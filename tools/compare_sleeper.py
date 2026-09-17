import argparse

from database import load_season_roster
from fantasy_calendar import current_fantasy_week
from sleeper_compare import compare_players
from yahoo_provider import enrich_local_roster


def find_roster_player(roster, name):
    target = name.strip().lower()

    for player in roster:
        if (player.get("name") or "").strip().lower() == target:
            return player

    raise SystemExit(
        f"Player not found on local roster: {name}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compare roster players using Sleeper raw projections "
            "rescored with Busy Working Yahoo rules."
        )
    )
    parser.add_argument(
        "players",
        nargs="+",
        help="2-4 exact player names from My Team",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Fantasy week (defaults to current week)",
    )

    args = parser.parse_args()

    if not 2 <= len(args.players) <= 4:
        parser.error("provide 2 to 4 player names")

    week = (
        args.week
        if args.week is not None
        else current_fantasy_week(2026)
    )

    local_roster = load_season_roster(2026)
    roster = enrich_local_roster(local_roster)
    selected = [
        find_roster_player(roster, name)
        for name in args.players
    ]

    print(
        f"Sleeper comparison rescored for Busy Working · Week {week}"
    )
    print()

    results = compare_players(
        selected,
        week=week,
        season=2026,
    )

    for result in results:
        yahoo = result["yahoo_projection"]
        sleeper = result["sleeper_yahoo_projection"]

        if sleeper is None:
            sleeper_text = "no Sleeper projection found"
            delta_text = ""
        else:
            sleeper_text = f"{sleeper:.2f} Yahoo-equivalent pts"
            delta = sleeper - yahoo
            delta_text = f" · delta {delta:+.2f}"

        print(
            f"  {result['name']} · {result['position']} · "
            f"Yahoo {yahoo:.2f} · Sleeper {sleeper_text}{delta_text}"
        )

    print()
    print(
        "Sleeper generic half-PPR totals are fetched only as a diagnostic; "
        "the comparison above is recalculated from Sleeper raw stats using "
        "Busy Working's Yahoo scoring rules."
    )


if __name__ == "__main__":
    main()

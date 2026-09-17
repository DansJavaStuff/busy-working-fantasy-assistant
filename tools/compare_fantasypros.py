import argparse
import json

from database import load_season_roster
from fantasy_calendar import current_fantasy_week
from fantasypros_compare import fetch_targeted_comparison
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
            "Compare 2-4 roster players using targeted FantasyPros "
            "weekly projections and expert rankings."
        )
    )
    parser.add_argument(
        "position",
        help="QB, RB, WR, TE or FLEX",
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore a cached comparison and call FantasyPros again",
    )

    args = parser.parse_args()

    if not 2 <= len(args.players) <= 4:
        parser.error("provide 2 to 4 player names")

    position = args.position.upper()

    if position not in {"QB", "RB", "WR", "TE", "FLEX"}:
        parser.error("position must be QB, RB, WR, TE or FLEX")

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
        f"FantasyPros targeted comparison · Week {week} · {position}"
    )
    print()

    for player in selected:
        print(
            f"  {player['name']} · {player.get('position')} · "
            f"Yahoo projection {float(player.get('current_week_projection') or 0):.2f}"
        )

    print()
    print("Requesting/caching FantasyPros targeted data...")

    result = fetch_targeted_comparison(
        selected,
        week,
        position,
        force=args.force,
    )

    print()
    print("Resolved FantasyPros players:")
    for player in result.get("players", []):
        print(
            f"  {player.get('name')} · {player.get('position')} · "
            f"FantasyPros ID {player.get('id')}"
        )

    print()
    print("FantasyPros projections response:")
    print(
        json.dumps(
            result.get("projections"),
            indent=2,
        )
    )

    print()
    print("FantasyPros compare-players response:")
    print(
        json.dumps(
            result.get("comparison"),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

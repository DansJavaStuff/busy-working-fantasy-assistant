from fantasy_calendar import current_fantasy_week
from fantasypros_weekly import (
    POSITIONS,
    refresh_weekly_cache,
)


def main():
    week = current_fantasy_week(2026)

    print(
        f"Refreshing FantasyPros weekly ECR for Week {week}..."
    )

    cache = refresh_weekly_cache(
        week
    )

    print()
    print(
        f"Saved Week {cache['week']} weekly rankings."
    )

    for position in POSITIONS:
        print(
            f"  {position}: "
            f"{len(cache['feeds'].get(position, []))} players"
        )

    print()
    print(
        "This cache is separate from the draft/season FantasyPros cache."
    )


if __name__ == "__main__":
    main()

from database import replace_week_cant_cut


SEASON = 2026
WEEK = 4

CANT_CUT = [
    {
        "player_id": "30977",
        "player_name": "Josh Allen",
        "source": "confirmed_yahoo_screenshot",
    },
    {
        "player_id": "41791",
        "player_name": "Ashton Jeanty",
        "source": "confirmed_yahoo_screenshot",
    },
    {
        "player_id": "40168",
        "player_name": "Puka Nacua",
        "source": "confirmed_yahoo_screenshot",
    },
]


def main():
    count = replace_week_cant_cut(
        WEEK,
        CANT_CUT,
        season=SEASON,
        source="confirmed_yahoo_screenshot",
    )

    print(
        f"Stored Week {WEEK} Can't Cut list: "
        f"{count} player(s)"
    )

    for player in CANT_CUT:
        print(
            f"  {player['player_name']} "
            f"({player['player_id']})"
        )


if __name__ == "__main__":
    main()

import json
import re
import unicodedata
from pathlib import Path

from adp import load_adp
from fantasypros import load_players as load_fantasypros_players


DATABASE_FILE = Path("player_database.json")


def normalise_name(name):
    """
    Normalise names to improve matching between data sources.

    Examples:
        De'Von Achane -> devonachane
        Amon-Ra St. Brown -> amonrastbrown
    """

    if not name:
        return ""

    name = unicodedata.normalize("NFKD", name)

    name = "".join(
        char
        for char in name
        if not unicodedata.combining(char)
    )

    return re.sub(
        r"[^a-z0-9]",
        "",
        name.lower(),
    )


def build_database():
    adp_players = load_adp()
    fp_players = load_fantasypros_players()

    fp_by_name = {
        normalise_name(player["name"]): player
        for player in fp_players
    }

    players = []
    matched = 0
    unmatched = []

    for adp_player in adp_players:

        key = normalise_name(
            adp_player["name"]
        )

        fp_player = fp_by_name.get(key)

        player = dict(adp_player)

        if fp_player:
            matched += 1

            player.update({
                "id": fp_player["id"],
                "yahoo_id": fp_player.get("yahoo_id"),
                "fantasypros_ecr": fp_player.get("ecr"),
                "fantasypros_position_rank":
                    fp_player.get("position_rank"),
                "tier": fp_player.get("tier"),
                "rank_min": fp_player.get("rank_min"),
                "rank_max": fp_player.get("rank_max"),
                "rank_average":
                    fp_player.get("rank_average"),
            })

        else:
            # Give CSV-only players a stable local ID.
            player["id"] = (
                "adp-" +
                normalise_name(player["name"])
            )

            player["yahoo_id"] = None
            player["fantasypros_ecr"] = None
            player["fantasypros_position_rank"] = None
            player["tier"] = None
            player["rank_min"] = None
            player["rank_max"] = None
            player["rank_average"] = None

            unmatched.append(player["name"])

        players.append(player)

    database = {
        "count": len(players),
        "fantasypros_matches": matched,
        "fantasypros_unmatched": len(unmatched),
        "players": players,
    }

    DATABASE_FILE.write_text(
        json.dumps(database, indent=2)
    )

    print()
    print(f"Total ADP players: {len(players)}")
    print(f"FantasyPros matches: {matched}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print()
        print("First 20 unmatched:")
        for name in unmatched[:20]:
            print(" ", name)

    return database


def load_players():
    if not DATABASE_FILE.exists():
        build_database()

    data = json.loads(
        DATABASE_FILE.read_text()
    )

    return data["players"]


if __name__ == "__main__":
    build_database()

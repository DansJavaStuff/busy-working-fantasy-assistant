import csv
import re
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"

ADP_FILE = (
    DATA_DIR
    / "FantasyPros_2026_Overall_ADP_Rankings.csv"
)


def split_player(player_text):
    """
    Converts:
        Jahmyr Gibbs DET (6)

    into:
        ("Jahmyr Gibbs", "DET", 6)
    """

    match = re.match(
        r"^(.*?)\s+([A-Z]{2,3})\s+\((\d+)\)$",
        player_text.strip(),
    )

    if not match:
        return player_text.strip(), None, None

    name, team, bye = match.groups()

    return name.strip(), team, int(bye)


def split_position(position_text):
    """
    Converts RB12 -> ("RB", 12)
    """

    match = re.match(
        r"([A-Z]+)(\d+)",
        position_text.strip(),
    )

    if not match:
        return position_text.strip(), None

    position, rank = match.groups()

    return position, int(rank)


def number(value):
    """
    Safely converts CSV numbers to float.
    """

    if value is None:
        return None

    value = value.strip()

    if not value or value == "-":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def load_adp():
    players = []

    with ADP_FILE.open(
        newline="",
        encoding="utf-8-sig",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            name, team, bye = split_player(
                row["Player (Bye)"]
            )

            position, position_rank = split_position(
                row["POS"]
            )

            players.append(
                {
                    "adp_rank": int(row["Rank"]),
                    "name": name,
                    "team": team,
                    "bye": bye,
                    "position": position,
                    "position_rank": position_rank,

                    "yahoo_adp": number(
                        row.get("Yahoo")
                    ),

                    "sleeper_adp": number(
                        row.get("Sleeper")
                    ),

                    "rtsports_adp": number(
                        row.get("RTSports")
                    ),

                    "adp": number(
                        row.get("AVG")
                    ),
                }
            )

    return players


if __name__ == "__main__":

    players = load_adp()

    print(f"Loaded {len(players)} players")
    print()

    for player in players[:20]:
        print(
            f'{player["adp_rank"]:>3}',
            f'{player["name"]:<25}',
            f'{player["position"]:<3}',
            f'{player["team"] or "-":<3}',
            f'AVG {player["adp"]}',
            f'Yahoo {player["yahoo_adp"]}',
            f'Bye {player["bye"]}',
        )

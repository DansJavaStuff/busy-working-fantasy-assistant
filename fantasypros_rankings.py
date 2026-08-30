import csv
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"

POSITION_FILES = {
    "QB": DATA_DIR / "FantasyPros_2026_Draft_QB_Rankings.csv",
    "RB": DATA_DIR / "FantasyPros_2026_Draft_RB_Rankings.csv",
    "WR": DATA_DIR / "FantasyPros_2026_Draft_WR_Rankings.csv",
    "TE": DATA_DIR / "FantasyPros_2026_Draft_TE_Rankings.csv",
    "K": DATA_DIR / "FantasyPros_2026_Draft_K_Rankings.csv",
    "DST": DATA_DIR / "FantasyPros_2026_Draft_DST_Rankings.csv",
}


def integer(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value or value == "-":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def load_rankings():
    players = []

    for position, filename in POSITION_FILES.items():

        if not filename.exists():
            print(
                f"Warning: FantasyPros ranking file "
                f"missing: {filename}"
            )
            continue

        with filename.open(
            newline="",
            encoding="utf-8-sig",
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                name = (
                    row.get("PLAYER NAME")
                    or ""
                ).strip()

                team = (
                    row.get("TEAM")
                    or ""
                ).strip()

                # FantasyPros downloads can contain blank
                # rows at the bottom of the file.
                if not name:
                    continue

                players.append(
                    {
                        "name":
                            name,

                        "team":
                            team,

                        "position":
                            position,

                        "position_rank":
                            integer(row.get("RK")),

                        "tier":
                            integer(row.get("TIERS")),

                        "bye":
                            integer(
                                row.get("BYE WEEK")
                            ),

                        "ecr_vs_adp":
                            (
                                row.get("ECR VS. ADP")
                                or ""
                            ).strip(),

                        "source_file":
                            filename.name,
                    }
                )

    return players


if __name__ == "__main__":
    players = load_rankings()

    print(
        f"Loaded {len(players)} "
        f"FantasyPros positional rankings"
    )

    print()

    for player in players:
        if player["name"] == "Blake Grupe":
            print(player)

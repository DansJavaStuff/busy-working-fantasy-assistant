from pathlib import Path
import sys

from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from tools.import_yahoo_players import (
    DATA_DIR,
    clean_text,
)


def describe_cell(cell):
    return {
        "tag": cell.name,
        "class": cell.get("class"),
        "role": cell.get("role"),
        "text": clean_text(
            cell.get_text(
                " ",
                strip=True,
            )
        ),
    }


def inspect(path):
    print()
    print(path.name)
    print("=" * len(path.name))

    html = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    seen = set()
    shown = 0

    for link in soup.find_all(
        "a",
        attrs={
            "data-ys-playerid": True,
        },
    ):
        player_id = link.get(
            "data-ys-playerid"
        )

        if (
            not player_id
            or player_id in seen
        ):
            continue

        row = link.find_parent("tr")

        if row is None:
            continue

        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        player_cell = link.find_parent(
            ["th", "td"]
        )

        if (
            player_cell is None
            or player_cell not in cells
        ):
            continue

        seen.add(player_id)
        shown += 1

        print()
        print(
            f"Player {shown}: "
            f"id={player_id} "
            f"link_text={clean_text(link.get_text(' ', strip=True))!r}"
        )

        print(
            f"player_cell_index="
            f"{cells.index(player_cell)}"
        )

        for index, cell in enumerate(
            cells
        ):
            print(
                f"  cell[{index}]: "
                f"{describe_cell(cell)}"
            )

        if shown >= 15:
            break


def main():
    paths = sorted(
        DATA_DIR.glob(
            "Yahoo_MyTeam*week3*Actual*.html"
        )
    )

    if not paths:
        raise SystemExit(
            "No Week 3 Yahoo My Team actual HTML files found."
        )

    for path in paths:
        inspect(path)


if __name__ == "__main__":
    main()

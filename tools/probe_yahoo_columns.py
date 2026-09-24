from pathlib import Path

from bs4 import BeautifulSoup


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def main():
    candidates = sorted(
        DATA_DIR.glob(
            "Yahoo_MyTeam_*week3-Proj*.html"
        ),
        key=lambda path:
            path.stat().st_mtime_ns,
        reverse=True,
    )

    if not candidates:
        raise SystemExit(
            "No Week 3 My Team projection HTML found."
        )

    path = candidates[0]

    print(f"File: {path.name}")
    print()

    html = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    link = soup.find(
        "a",
        string=lambda value:
            value
            and "Josh Allen"
            in value,
    )

    if link is None:
        link = soup.find(
            "a",
            attrs={
                "data-ys-playerid": True,
            },
        )

    if link is None:
        raise SystemExit(
            "No Yahoo player row found."
        )

    row = link.find_parent("tr")
    table = row.find_parent("table")

    print("HEADER ROWS")
    print("===========")

    for number, header_row in enumerate(
        table.find_all("tr")
    ):
        if header_row is row:
            break

        cells = header_row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        print(f"Header row {number}:")

        for index, cell in enumerate(cells):
            print(
                f"  [{index:02}] "
                f"colspan={cell.get('colspan', '1')} "
                f"text={cell.get_text(' ', strip=True)!r}"
            )

    print()
    print("PLAYER ROW")
    print("==========")

    cells = row.find_all(
        ["th", "td"],
        recursive=False,
    )

    for index, cell in enumerate(cells):
        attrs = {
            key: value
            for key, value in cell.attrs.items()
            if key
            in {
                "class",
                "data-tst",
                "data-testid",
                "headers",
                "aria-label",
            }
        }

        print(
            f"[{index:02}] "
            f"text={cell.get_text(' ', strip=True)!r} "
            f"attrs={attrs}"
        )


if __name__ == "__main__":
    main()

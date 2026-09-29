import argparse

from bs4 import BeautifulSoup

from tools.import_yahoo_players import DATA_DIR, clean_text

DEFAULT_PLAYERS = (
    "Josh Allen",
    "Ashton Jeanty",
    "Puka Nacua",
    "David Montgomery",
    "Tee Higgins",
)

INTERESTING_ATTRIBUTES = (
    "aria-label",
    "class",
    "data-testid",
    "data-tst",
    "disabled",
    "role",
    "title",
)


def player_name(link):
    return clean_text(link.get_text(" ", strip=True))


def relevant_controls(row):
    controls = []

    for element in row.find_all(True):
        attributes = {
            name: element.get(name)
            for name in INTERESTING_ATTRIBUTES
            if element.has_attr(name)
        }
        href = element.get("href")

        if href and any(
            word in href.lower()
            for word in (
                "drop",
                "remove",
                "transaction",
            )
        ):
            attributes["href"] = href

        classes = " ".join(element.get("class", [])).lower()
        text = clean_text(element.get_text(" ", strip=True))

        is_control = element.name in {
            "button",
            "i",
            "svg",
            "use",
        }
        looks_relevant = any(
            word in f"{classes} {text} {attributes}".lower()
            for word in (
                "can't cut",
                "cant-cut",
                "cannot cut",
                "disabled",
                "drop",
                "lock",
                "no-drop",
                "remove",
                "undroppable",
            )
        )

        if not (is_control or looks_relevant or attributes):
            continue

        controls.append(
            {
                "tag": element.name,
                "text": text[:80],
                "attributes": attributes,
            }
        )

    return controls


def inspect_file(path, wanted):
    soup = BeautifulSoup(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        ),
        "html.parser",
    )
    found = {}

    for link in soup.find_all(
        "a",
        attrs={"data-ys-playerid": True},
    ):
        name = player_name(link)

        if name not in wanted or name in found:
            continue

        row = link.find_parent("tr")

        if row is None:
            continue

        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )
        found[name] = {
            "player_id": str(link.get("data-ys-playerid")),
            "row_attributes": {
                name: row.get(name)
                for name in INTERESTING_ATTRIBUTES
                if row.has_attr(name)
            },
            "cells": [
                {
                    "index": index,
                    "text": clean_text(
                        cell.get_text(
                            " ",
                            strip=True,
                        )
                    )[:100],
                    "attributes": {
                        name: cell.get(name)
                        for name in INTERESTING_ATTRIBUTES
                        if cell.has_attr(name)
                    },
                }
                for index, cell in enumerate(cells)
            ],
            "controls": relevant_controls(row),
        }

    return found


def latest_my_team_files():
    return sorted(
        DATA_DIR.glob("Yahoo_MyTeam_*.html"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compare Yahoo HTML markers for Can't Cut and ordinary roster players."
        )
    )
    parser.add_argument(
        "players",
        nargs="*",
        help=(
            "Player names to inspect. Defaults to the confirmed Week 4 "
            "Can't Cut players plus two droppable comparisons."
        ),
    )
    args = parser.parse_args()
    wanted = tuple(args.players) or DEFAULT_PLAYERS
    remaining = set(wanted)
    results = {}

    files = latest_my_team_files()

    if not files:
        raise SystemExit(f"No Yahoo_MyTeam_*.html files found in {DATA_DIR}")

    for path in files:
        found = inspect_file(path, remaining)

        for name, details in found.items():
            results[name] = {
                "file": path.name,
                **details,
            }
            remaining.discard(name)

        if not remaining:
            break

    print("Yahoo Can't Cut HTML probe")
    print("==========================")

    for name in wanted:
        details = results.get(name)
        print()
        print(name)
        print("-" * len(name))

        if details is None:
            print("Not found in saved My Team HTML.")
            continue

        print(f"File: {details['file']}")
        print(f"Yahoo player id: {details['player_id']}")
        print(f"Row attributes: {details['row_attributes']}")
        print("Cells:")

        for cell in details["cells"]:
            print(
                f"  [{cell['index']:02}] "
                f"text={cell['text']!r} "
                f"attrs={cell['attributes']}"
            )

        print("Relevant controls and markers:")

        if not details["controls"]:
            print("  None found")

        for control in details["controls"]:
            print(
                f"  <{control['tag']}> "
                f"text={control['text']!r} "
                f"attrs={control['attributes']}"
            )

    if remaining:
        print()
        print("Missing players: " + ", ".join(sorted(remaining)))


if __name__ == "__main__":
    main()

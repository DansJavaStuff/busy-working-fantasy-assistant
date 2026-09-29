from pathlib import Path
import re
import sys

from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

DATE_RE = re.compile(
    r"\b(Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2}),\s+"
    r"(\d{1,2}:\d{2})\s+"
    r"(am|pm)\b",
    re.IGNORECASE,
)

PLAYER_RE = re.compile(
    r"\b([A-Za-z]{2,3})\s*-\s*"
    r"(QB|RB|WR|TE|K|DEF|DST)\b",
    re.IGNORECASE,
)

PLAYER_HREF_RE = re.compile(
    r"/nfl/players/(\d+)"
)


def clean_text(value):
    return " ".join(
        value.split()
    )


def yahoo_player_id(link):
    player_id = link.get(
        "data-ys-playerid"
    )

    if player_id:
        return str(player_id)

    href = link.get("href") or ""
    match = PLAYER_HREF_RE.search(
        href
    )

    if match:
        return match.group(1)

    return None


def player_details(link):
    text = clean_text(
        link.parent.get_text(
            " ",
            strip=True,
        )
    )

    match = PLAYER_RE.search(
        text
    )

    team = None
    position = None

    if match:
        team = match.group(1).upper()
        position = match.group(2).upper()

        if position == "DEF":
            position = "DST"

    return {
        "player_id": yahoo_player_id(
            link
        ),
        "name": clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        ),
        "team": team,
        "position": position,
    }


def transaction_container(link):
    node = link

    while node is not None:
        node = node.parent

        if node is None:
            break

        text = clean_text(
            node.get_text(
                " ",
                strip=True,
            )
        )

        if (
            len(text) > 2500
            or not DATE_RE.search(text)
            or "Allen Wrench" not in text
        ):
            continue

        links = [
            item
            for item in node.find_all("a")
            if yahoo_player_id(item)
        ]

        ids = {
            yahoo_player_id(item)
            for item in links
            if yahoo_player_id(item)
        }

        if 1 <= len(ids) <= 2:
            return node

    return None


def parse_candidates(path):
    html = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    groups = {}

    candidate_links = [
        link
        for link in soup.find_all("a")
        if yahoo_player_id(link)
    ]

    for link in candidate_links:
        container = transaction_container(
            link
        )

        if container is None:
            continue

        text = clean_text(
            container.get_text(
                " ",
                strip=True,
            )
        )

        date_match = DATE_RE.search(
            text
        )

        if not date_match:
            continue

        player_links = []
        seen = set()

        for player_link in container.find_all("a"):
            player_id = yahoo_player_id(
                player_link
            )

            if (
                not player_id
                or player_id in seen
            ):
                continue

            seen.add(player_id)
            player_links.append(
                player_link
            )

        key = (
            date_match.group(0).lower(),
            tuple(
                yahoo_player_id(link)
                for link in player_links
            ),
        )

        groups[key] = {
            "date_text": date_match.group(0),
            "players": [
                player_details(
                    player_link
                )
                for player_link in player_links
            ],
            "text": text,
        }

    return list(
        groups.values()
    )


def main():
    filename = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Yahoo_MyTxns_SoFar.html"
    )

    path = DATA_DIR / filename

    if not path.exists():
        raise SystemExit(
            f"Transaction HTML not found: {path}"
        )

    candidates = parse_candidates(
        path
    )

    print(
        "YAHOO TRANSACTION PROBE"
    )
    print(
        "======================="
    )
    print(
        f"File: {path.name}"
    )
    print(
        f"Candidate groups: {len(candidates)}"
    )

    for index, item in enumerate(
        candidates,
        start=1,
    ):
        print()
        print(
            f"[{index}] {item['date_text']}"
        )

        for player in item[
            "players"
        ]:
            print(
                "  "
                f"{player['player_id']} | "
                f"{player['name']} | "
                f"{player['team']} | "
                f"{player['position']}"
            )

        print(
            "  TEXT: "
            + item["text"][:700]
        )


if __name__ == "__main__":
    main()

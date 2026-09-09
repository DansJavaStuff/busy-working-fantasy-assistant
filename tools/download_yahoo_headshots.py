from pathlib import Path
from urllib.parse import urljoin
import json
import re
import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = (
    PROJECT_ROOT
    / "static"
    / "player_headshots"
)

PLAYER_JSON = (
    DATA_DIR
    / "yahoo_available_players.json"
)


def clean_url(src):
    if not src:
        return None

    # Saved Yahoo HTML may contain escaped entities.
    return (
        src.replace("&amp;", "&")
        .strip()
    )


def collect_image_urls():
    image_urls = {}

    html_files = sorted(
        DATA_DIR.glob(
            "Yahoo_Player_list_*.html"
        )
    )

    for path in html_files:
        html = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        for link in soup.find_all(
            "a",
            attrs={
                "data-ys-playerid": True
            },
        ):
            player_id = link.get(
                "data-ys-playerid"
            )

            if not player_id:
                continue

            row = link.find_parent("tr")

            if row is None:
                continue

            image = row.find("img")

            if image is None:
                continue

            src = clean_url(
                image.get("src")
            )

            if not src:
                continue

            # We only want player cutout images here,
            # not team/DEF logos or unrelated page assets.
            if (
                "/nfl_cutout/players_l/"
                not in src
            ):
                continue

            if src.startswith("./"):
                # HTML-only saves should usually
                # preserve the original remote URL,
                # but skip local asset references.
                continue

            image_urls.setdefault(
                player_id,
                src,
            )

    return image_urls


def load_candidate_ids():
    players = json.loads(
        PLAYER_JSON.read_text(
            encoding="utf-8",
        )
    )

    return {
        str(player["yahoo_player_id"])
        for player in players
        if player["position"] != "DST"
    }


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_ids = load_candidate_ids()
    image_urls = collect_image_urls()

    print(
        "Candidate offensive/kicker players:",
        len(candidate_ids),
    )

    print(
        "Image URLs found in saved HTML:",
        len(image_urls),
    )

    downloaded = 0
    skipped = 0
    missing = []

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent":
                "Mozilla/5.0"
        }
    )

    for player_id in sorted(
        candidate_ids,
        key=int,
    ):
        url = image_urls.get(player_id)

        if not url:
            missing.append(player_id)
            continue

        destination = (
            OUTPUT_DIR
            / f"{player_id}.png"
        )

        if destination.exists():
            skipped += 1
            continue

        try:
            response = session.get(
                url,
                timeout=20,
            )

            response.raise_for_status()

            destination.write_bytes(
                response.content
            )

            downloaded += 1

            print(
                f"Downloaded "
                f"{player_id}"
            )

        except requests.RequestException as exc:
            print(
                f"FAILED "
                f"{player_id}: "
                f"{exc}"
            )

            missing.append(player_id)

    print()
    print("Downloaded:", downloaded)
    print("Already present:", skipped)
    print("Missing:", len(missing))

    if missing:
        print()
        print(
            "Missing Yahoo IDs:"
        )

        for player_id in missing:
            print(
                f"  {player_id}"
            )


if __name__ == "__main__":
    main()

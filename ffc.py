import json
import time
from pathlib import Path

import requests


FFC_URL = (
    "https://fantasyfootballcalculator.com/"
    "api/v1/adp/half-ppr"
)

CACHE_FILE = Path("ffc_cache.json")

CACHE_MAX_AGE = 6 * 60 * 60

PARAMS = {
    "position": "all",
    "teams": 12,
    "year": 2026,
}


def normalise_position(position):
    if position == "PK":
        return "K"

    if position == "DEF":
        return "DST"

    return position


def cache_is_fresh():
    if not CACHE_FILE.exists():
        return False

    age = (
        time.time()
        - CACHE_FILE.stat().st_mtime
    )

    return age < CACHE_MAX_AGE


def fetch_data():
    response = requests.get(
        FFC_URL,
        params=PARAMS,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "Success":
        raise RuntimeError(
            "Fantasy Football Calculator "
            "returned an unsuccessful response"
        )

    CACHE_FILE.write_text(
        json.dumps(
            data,
            indent=2,
        )
    )

    return data


def load_data(force_refresh=False):
    if (
        force_refresh
        or not cache_is_fresh()
    ):
        try:
            return fetch_data()

        except Exception:
            # Draft night resilience:
            # stale data is better than no data.
            if not CACHE_FILE.exists():
                raise

    return json.loads(
        CACHE_FILE.read_text()
    )


def load_players(force_refresh=False):
    data = load_data(
        force_refresh=force_refresh
    )

    players = []

    for raw in data.get(
        "players",
        [],
    ):
        players.append({
            "ffc_id":
                raw.get("player_id"),

            "name":
                raw.get("name"),

            "position":
                normalise_position(
                    raw.get("position")
                ),

            "team":
                raw.get("team"),

            "ffc_adp":
                raw.get("adp"),

            "ffc_high":
                raw.get("high"),

            "ffc_low":
                raw.get("low"),

            "ffc_stdev":
                raw.get("stdev"),

            "ffc_times_drafted":
                raw.get("times_drafted"),

            "bye":
                raw.get("bye"),
        })

    return players


def metadata(force_refresh=False):
    data = load_data(
        force_refresh=force_refresh
    )

    return data.get(
        "meta",
        {},
    )


if __name__ == "__main__":
    data = load_data(
        force_refresh=True
    )

    meta = data.get(
        "meta",
        {}
    )

    print(
        "Type:",
        meta.get("type"),
    )

    print(
        "Teams:",
        meta.get("teams"),
    )

    print(
        "Drafts:",
        meta.get("total_drafts"),
    )

    print(
        "Period:",
        meta.get("start_date"),
        "to",
        meta.get("end_date"),
    )

    players = load_players()

    print(
        "Players:",
        len(players),
    )

    print()

    for player in players[:10]:
        print(
            f'{player["name"]:<25} '
            f'{player["position"]:<3} '
            f'ADP {player["ffc_adp"]:>5} '
            f'±{player["ffc_stdev"]}'
        )

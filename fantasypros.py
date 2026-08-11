import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FANTASYPROS_API_KEY")

CACHE_FILE = Path("fantasypros_cache.json")

BASE_URL = (
    "https://api.fantasypros.com/public/v2/json/"
    "nfl/2026/consensus-rankings"
)


def fetch_rankings():
    if not API_KEY:
        raise RuntimeError(
            "FANTASYPROS_API_KEY missing from .env"
        )

    response = requests.get(
        BASE_URL,
        headers={
            "x-api-key": API_KEY,
        },
        params={
            "position": "OP",
            "scoring": "HALF",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def convert_player(player):
    return {
        "id": player["player_id"],
        "yahoo_id": player.get("player_yahoo_id"),

        "name": player["player_name"],
        "short_name": player.get("player_short_name"),

        "position": player["player_position_id"],
        "team": player.get("player_team_id") or "FA",

        "bye": player.get("player_bye_week"),

        # Overall FantasyPros ranking from OP feed
        "ecr": player.get("rank_ecr"),

        "position_rank": player.get("pos_rank"),
        "tier": player.get("tier"),

        "rank_min": player.get("rank_min"),
        "rank_max": player.get("rank_max"),
        "rank_average": player.get("rank_ave"),
    }


def refresh_cache():
    print("Downloading FantasyPros 2026 rankings...")

    data = fetch_rankings()

    players = [
        convert_player(player)
        for player in data.get("players", [])
    ]

    # Ignore unusual positions for now.
    wanted_positions = {
        "QB",
        "RB",
        "WR",
        "TE",
    }

    players = [
        player
        for player in players
        if player["position"] in wanted_positions
    ]

    players.sort(
        key=lambda player: (
            player["ecr"]
            if player["ecr"] is not None
            else 9999
        )
    )

    cache = {
        "season": 2026,
        "scoring": "HALF",
        "updated": datetime.now().isoformat(),
        "fantasypros_last_updated": data.get("last_updated"),
        "public_api_limited": data.get("public_api_limited"),
        "players": players,
    }

    CACHE_FILE.write_text(
        json.dumps(cache, indent=2)
    )

    print(
        f"Saved {len(players)} players "
        f"to {CACHE_FILE}"
    )

    return cache


def load_players():
    if not CACHE_FILE.exists():
        refresh_cache()

    cache = json.loads(
        CACHE_FILE.read_text()
    )

    return cache["players"]


if __name__ == "__main__":
    refresh_cache()

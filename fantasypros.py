import json
import os
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FANTASYPROS_API_KEY")

DAILY_LIMIT = int(
    os.getenv(
        "FANTASYPROS_DAILY_LIMIT",
        "50",
    )
)

USAGE_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "fantasypros_usage.json"
)

CACHE_FILE = Path("fantasypros_cache.json")

BASE_URL = (
    "https://api.fantasypros.com/public/v2/json/"
    "nfl/2026/consensus-rankings"
)

POSITIONS = [
    "QB",
    "RB",
    "WR",
    "TE",
]

def convert_player(player):
    return {
        "id": player["player_id"],
        "yahoo_id": player.get("player_yahoo_id"),

        "name": player["player_name"],
        "short_name": player.get("player_short_name"),

        "position": player["player_position_id"],
        "team": player.get("player_team_id") or "FA",

        "bye": player.get("player_bye_week"),

        # Position-specific FantasyPros ECR from the QB/RB/WR/TE feeds
        "ecr": player.get("rank_ecr"),

        "position_rank": player.get("pos_rank"),
        "tier": player.get("tier"),

        "rank_min": player.get("rank_min"),
        "rank_max": player.get("rank_max"),
        "rank_average": player.get("rank_ave"),
    }

def load_usage():
    today = date.today().isoformat()

    if not USAGE_FILE.exists():
        return {
            "date": today,
            "calls": 0,
            "last_call": None,
            "server_limit": None,
            "server_remaining": None,
        }

    try:
        usage = json.loads(
            USAGE_FILE.read_text()
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        usage = {}

    if usage.get("date") != today:
        return {
            "date": today,
            "calls": 0,
            "last_call": None,
            "server_limit": None,
            "server_remaining": None,
        }

    return usage


def record_api_call(response=None):
    usage = load_usage()

    usage["calls"] = (
        usage.get("calls", 0) + 1
    )

    usage["last_call"] = (
        datetime.now().isoformat()
    )

    if response is not None:
        headers = response.headers

        for name in (
            "x-ratelimit-limit",
            "ratelimit-limit",
            "x-rate-limit-limit",
        ):
            value = headers.get(name)

            if value is not None:
                usage["server_limit"] = value
                break

        for name in (
            "x-ratelimit-remaining",
            "ratelimit-remaining",
            "x-rate-limit-remaining",
        ):
            value = headers.get(name)

            if value is not None:
                usage["server_remaining"] = value
                break

    USAGE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    USAGE_FILE.write_text(
        json.dumps(
            usage,
            indent=2,
        )
    )

    return usage


def get_api_usage():
    usage = load_usage()

    calls = usage.get("calls", 0)
    remaining = max(
        DAILY_LIMIT - calls,
        0,
    )

    refresh_calls = len(POSITIONS)

    usage["limit"] = DAILY_LIMIT
    usage["remaining"] = remaining
    usage["refresh_calls"] = refresh_calls
    usage["can_refresh"] = (
        remaining >= refresh_calls
    )

    if remaining < refresh_calls:
        usage["status"] = "blocked"
        usage["status_class"] = "missing"

    elif remaining < (refresh_calls * 2):
        usage["status"] = "low"
        usage["status_class"] = "stale"

    else:
        usage["status"] = "ok"
        usage["status_class"] = "current"

    last_call = usage.get("last_call")

    if last_call:
        try:
            usage["last_call_display"] = (
                datetime.fromisoformat(
                    last_call
                ).strftime(
                    "%Y-%m-%d %H:%M"
                )
            )
        except ValueError:
            usage["last_call_display"] = (
                last_call
            )
    else:
        usage["last_call_display"] = (
            "None recorded today"
        )

    return usage

def refresh_cache():
    if not API_KEY:
        raise RuntimeError(
            "FANTASYPROS_API_KEY missing from .env"
        )

    players = []

    for position in POSITIONS:
        print(f"Downloading {position} rankings...")

        response = requests.get(
            BASE_URL,
            headers={
                "x-api-key": API_KEY,
            },
            params={
                "position": position,
                "scoring": "HALF",
            },
            timeout=30,
        )

        usage = record_api_call(
            response
        )

        print(
            f"  FantasyPros API usage: "
            f"{usage['calls']}/{DAILY_LIMIT} "
            f"calls today "
            f"({max(DAILY_LIMIT - usage['calls'], 0)} remaining)"
        )

        response.raise_for_status()
        data = response.json()

        print(
            f"  {data.get('count')} available, "
            f"{len(data.get('players', []))} returned"
        )

        for player in data.get("players", []):
            players.append(convert_player(player))

    # Deduplicate by FantasyPros ID
    unique = {
        player["id"]: player
        for player in players
    }

    players = list(unique.values())

    cache = {
        "season": 2026,
        "scoring": "HALF",
        "updated": datetime.now().isoformat(),
        "players": players,
    }

    CACHE_FILE.write_text(
        json.dumps(cache, indent=2)
    )

    print()
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

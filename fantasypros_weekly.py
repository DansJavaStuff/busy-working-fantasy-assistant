import json
from datetime import datetime
from pathlib import Path

import requests

from fantasypros import (
    API_KEY,
    BASE_URL,
    record_api_call,
)


SEASON = 2026
SCORING = "HALF"

# FLEX is included so RB/WR/TE choices can be compared across positions.
POSITIONS = [
    "QB",
    "RB",
    "WR",
    "TE",
    "FLEX",
]

CACHE_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "fantasypros_weekly.json"
)


def convert_player(player):
    return {
        "id": player.get("player_id"),
        "yahoo_id": player.get("player_yahoo_id"),
        "name": player.get("player_name"),
        "short_name": player.get("player_short_name"),
        "position": player.get("player_position_id"),
        "team": player.get("player_team_id") or "FA",
        "ecr": player.get("rank_ecr"),
        "position_rank": player.get("pos_rank"),
        "tier": player.get("tier"),
        "rank_min": player.get("rank_min"),
        "rank_max": player.get("rank_max"),
        "rank_average": player.get("rank_ave"),
    }


def refresh_weekly_cache(week):
    """Download current-week FantasyPros ECR into a separate in-season cache."""

    if not API_KEY:
        raise RuntimeError(
            "FANTASYPROS_API_KEY missing from .env"
        )

    feeds = {}

    for position in POSITIONS:
        response = requests.get(
            BASE_URL,
            headers={
                "x-api-key": API_KEY,
            },
            params={
                "position": position,
                "scoring": SCORING,
                "week": int(week),
            },
            timeout=30,
        )

        record_api_call(response)
        response.raise_for_status()

        data = response.json()

        feeds[position] = [
            convert_player(player)
            for player in data.get(
                "players",
                [],
            )
        ]

    cache = {
        "season": SEASON,
        "week": int(week),
        "scoring": SCORING,
        "updated": datetime.now().isoformat(),
        "feeds": feeds,
    }

    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CACHE_FILE.write_text(
        json.dumps(
            cache,
            indent=2,
        ),
        encoding="utf-8",
    )

    return cache


def load_weekly_cache(week=None):
    """Load cached weekly ECR without making an API call.

    A cache from another week is treated as stale and ignored. The Weekly page
    must never burn FantasyPros allowance merely because a user opened it.
    """

    if not CACHE_FILE.exists():
        return None

    try:
        cache = json.loads(
            CACHE_FILE.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if (
        week is not None
        and cache.get("week") != int(week)
    ):
        return None

    return cache

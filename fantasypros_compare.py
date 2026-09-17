import json
from datetime import datetime
from pathlib import Path

import requests

from fantasypros import (
    API_KEY,
    record_api_call,
)
from player_database import normalise_name


BASE_URL = "https://api.fantasypros.com/public/v2/json/nfl"
PLAYER_DATABASE_FILE = Path("player_database.json")
CACHE_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "fantasypros_comparisons.json"
)


def _normalise_position(position):
    value = (position or "").upper()
    return "DST" if value == "DEF" else value


def _load_player_database(path=None):
    path = path or PLAYER_DATABASE_FILE

    if not path.exists():
        return []

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return []

    if isinstance(data, dict):
        return data.get("players", [])

    if isinstance(data, list):
        return data

    return []


def resolve_fantasypros_player(
    player,
    database=None,
):
    """Resolve a Yahoo/local player to its FantasyPros player ID.

    The merged player database stores the FantasyPros player ID in ``id`` for
    matched records. Synthetic ``adp-``/``ffc-`` IDs are deliberately rejected.
    """

    database = (
        database
        if database is not None
        else _load_player_database()
    )

    target_name = normalise_name(
        player.get("name")
        or player.get("player_name")
    )
    target_position = _normalise_position(
        player.get("position")
    )
    target_team = (
        player.get("team")
        or ""
    ).upper()
    yahoo_id = str(
        player.get("yahoo_player_id")
        or player.get("yahoo_id")
        or ""
    )

    candidates = []

    for candidate in database:
        candidate_id = candidate.get("id")

        if candidate_id is None:
            continue

        candidate_id_text = str(candidate_id)

        if candidate_id_text.startswith(
            ("adp-", "ffc-")
        ):
            continue

        candidate_yahoo = str(
            candidate.get("yahoo_id")
            or ""
        )

        if (
            yahoo_id
            and candidate_yahoo
            and yahoo_id == candidate_yahoo
        ):
            return {
                "id": candidate_id_text,
                "name": candidate.get("name"),
                "position": _normalise_position(
                    candidate.get("position")
                ),
                "team": candidate.get("team"),
            }

        if normalise_name(
            candidate.get("name")
        ) != target_name:
            continue

        candidate_position = (
            _normalise_position(
                candidate.get("position")
            )
        )

        if (
            target_position
            and candidate_position
            and target_position
            != candidate_position
        ):
            continue

        candidates.append(candidate)

    if not candidates:
        return None

    if target_team:
        team_matches = [
            candidate
            for candidate in candidates
            if (
                candidate.get("team")
                or ""
            ).upper() == target_team
        ]

        if len(team_matches) == 1:
            candidates = team_matches

    if len(candidates) != 1:
        return None

    candidate = candidates[0]

    return {
        "id": str(candidate["id"]),
        "name": candidate.get("name"),
        "position": _normalise_position(
            candidate.get("position")
        ),
        "team": candidate.get("team"),
    }


def _load_cache():
    if not CACHE_FILE.exists():
        return {"comparisons": {}}

    try:
        data = json.loads(
            CACHE_FILE.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {"comparisons": {}}

    if not isinstance(data, dict):
        return {"comparisons": {}}

    data.setdefault("comparisons", {})
    return data


def _save_cache(cache):
    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2),
        encoding="utf-8",
    )


def _cache_key(week, position, player_ids):
    ordered = ":".join(
        sorted(str(value) for value in player_ids)
    )
    return f"{int(week)}|{position}|{ordered}"


def fetch_targeted_comparison(
    players,
    week,
    position,
    force=False,
):
    """Fetch/cache FantasyPros data for exactly two to four players.

    One call fetches HALF-PPR weekly projections for the requested players and
    one call fetches the expert weekly head-to-head rankings. Cached results are
    reused for the same fantasy week/player set.
    """

    if not API_KEY:
        raise RuntimeError(
            "FANTASYPROS_API_KEY missing from .env"
        )

    if not 2 <= len(players) <= 4:
        raise ValueError(
            "FantasyPros comparisons require 2 to 4 players"
        )

    resolved = []

    for player in players:
        match = resolve_fantasypros_player(
            player
        )
        if match is None:
            raise LookupError(
                "Could not resolve FantasyPros ID for "
                + str(
                    player.get("name")
                    or player.get("player_name")
                )
            )
        resolved.append(match)

    fp_ids = [
        player["id"]
        for player in resolved
    ]
    lookup_position = _normalise_position(
        position
    )
    cache = _load_cache()
    key = _cache_key(
        week,
        lookup_position,
        fp_ids,
    )

    if (
        not force
        and key in cache["comparisons"]
    ):
        return cache["comparisons"][key]

    ids_text = ":".join(fp_ids)

    projection_response = requests.get(
        f"{BASE_URL}/2026/projections",
        headers={"x-api-key": API_KEY},
        params={
            "week": int(week),
            "position": lookup_position,
            "scoring": "HALF",
            "players": ids_text,
        },
        timeout=30,
    )
    record_api_call(projection_response)
    projection_response.raise_for_status()

    compare_response = requests.get(
        f"{BASE_URL}/compare-players",
        headers={"x-api-key": API_KEY},
        params={
            "players": ids_text,
            "position": (
                "FLX"
                if lookup_position == "FLEX"
                else lookup_position
            ),
            "ranking_type": "weekly",
            "details": "players",
        },
        timeout=30,
    )
    record_api_call(compare_response)
    compare_response.raise_for_status()

    result = {
        "week": int(week),
        "position": lookup_position,
        "players": resolved,
        "updated": datetime.now().isoformat(),
        "projections": projection_response.json(),
        "comparison": compare_response.json(),
    }

    cache["comparisons"][key] = result
    _save_cache(cache)

    return result

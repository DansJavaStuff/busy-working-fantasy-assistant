import json
from datetime import datetime
from pathlib import Path

import requests

from fantasypros import API_KEY, record_api_call
from player_database import normalise_name


BASE_URL = "https://api.fantasypros.com/public/v2/json/nfl"
PLAYER_DATABASE_FILE = Path("player_database.json")
PLAYER_CATALOG_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "fantasypros_players.json"
)
CACHE_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "fantasypros_comparisons.json"
)


class FantasyProsLimitedAccessError(RuntimeError):
    """Raised when FantasyPros returns its limited/sample public dataset."""


def _limited_access_message(payload=None):
    payload = payload or {}
    tier = payload.get("tier")
    limit = payload.get("limit")

    detail = []
    if tier:
        detail.append(f"tier={tier}")
    if limit is not None:
        detail.append(f"limit={limit}")

    suffix = (
        " (" + ", ".join(detail) + ")"
        if detail
        else ""
    )

    return (
        "FantasyPros returned the limited public/sample player catalogue"
        + suffix
        + ". Targeted comparisons need full player metadata access, "
        "so arbitrary roster players cannot be resolved with this API key."
    )


def _normalise_position(position):
    if isinstance(position, list):
        position = position[0] if position else ""

    value = str(position or "").split(",")[0].strip().upper()
    return "DST" if value == "DEF" else value


def _first(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", []):
            return value
    return None


def _external_yahoo_id(candidate):
    direct = _first(
        candidate,
        "player_yahoo_id",
        "yahoo_id",
        "yahooid",
    )
    if direct is not None:
        return direct

    external = candidate.get("external_ids")
    if isinstance(external, dict):
        return _first(
            external,
            "yahoo",
            "yahoo_id",
            "player_yahoo_id",
        )

    return None


def _normalise_catalog_player(candidate, fallback_id=None):
    if not isinstance(candidate, dict):
        return None

    player_id = _first(
        candidate,
        "player_id",
        "fpid",
        "fantasypros_id",
        "fantasypros_player_id",
        "id",
    )
    if player_id is None:
        player_id = fallback_id

    name = _first(
        candidate,
        "player_name",
        "name",
        "full_name",
    )

    if player_id is None or not name:
        return None

    position = _first(
        candidate,
        "position_id",
        "player_position_id",
        "player_positions",
        "position",
        "primary_position",
        "positions",
    )

    team = _first(
        candidate,
        "team_id",
        "player_team_id",
        "team",
        "team_abbr",
        "team_code",
    )

    return {
        "id": str(player_id),
        "name": str(name),
        "position": _normalise_position(position),
        "team": str(team or "").upper(),
        "yahoo_id": (
            str(_external_yahoo_id(candidate))
            if _external_yahoo_id(candidate) is not None
            else ""
        ),
    }


def _extract_catalog_players(payload):
    """Walk an arbitrary FantasyPros response and extract player records."""

    players = []
    seen = set()

    def add(candidate, fallback_id=None):
        normalised = _normalise_catalog_player(
            candidate,
            fallback_id=fallback_id,
        )
        if not normalised:
            return

        key = (
            normalised["id"],
            normalise_name(normalised["name"]),
        )
        if key in seen:
            return

        seen.add(key)
        players.append(normalised)

    def walk(value, parent_key=None):
        if isinstance(value, list):
            for item in value:
                walk(item)
            return

        if not isinstance(value, dict):
            return

        add(
            value,
            fallback_id=(
                parent_key
                if parent_key is not None
                and str(parent_key).isdigit()
                else None
            ),
        )

        for key, child in value.items():
            if isinstance(child, (dict, list)):
                walk(child, parent_key=key)

    walk(payload)
    return players


def _load_json(path):
    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None


def _load_player_database():
    data = _load_json(PLAYER_DATABASE_FILE)
    if isinstance(data, dict):
        return data.get("players", [])
    if isinstance(data, list):
        return data
    return []


def _normalise_local_database(database):
    output = []

    for candidate in database:
        if not isinstance(candidate, dict):
            continue

        candidate_id = candidate.get("id")
        if candidate_id is None:
            continue

        candidate_id = str(candidate_id)
        if candidate_id.startswith(("adp-", "ffc-")):
            continue

        output.append(
            {
                "id": candidate_id,
                "name": candidate.get("name") or "",
                "position": _normalise_position(
                    candidate.get("position")
                ),
                "team": str(
                    candidate.get("team") or ""
                ).upper(),
                "yahoo_id": str(
                    candidate.get("yahoo_id") or ""
                ),
            }
        )

    return output


def load_player_catalog():
    data = _load_json(PLAYER_CATALOG_FILE)
    if data is None:
        return []

    if (
        isinstance(data, dict)
        and data.get("public_api_limited") is True
    ):
        raise FantasyProsLimitedAccessError(
            _limited_access_message(data)
        )

    if isinstance(data, dict) and isinstance(
        data.get("players"), list
    ):
        raw = data["players"]
    else:
        raw = data

    normalized = []
    for candidate in raw if isinstance(raw, list) else []:
        if (
            isinstance(candidate, dict)
            and "id" in candidate
            and "name" in candidate
        ):
            normalized.append(candidate)
        else:
            item = _normalise_catalog_player(candidate)
            if item:
                normalized.append(item)

    if normalized:
        return normalized

    return _extract_catalog_players(data)


def refresh_player_catalog():
    if not API_KEY:
        raise RuntimeError(
            "FANTASYPROS_API_KEY missing from .env"
        )

    response = requests.get(
        f"{BASE_URL}/players",
        headers={"x-api-key": API_KEY},
        timeout=30,
    )
    record_api_call(response)
    response.raise_for_status()

    payload = response.json()
    players = _extract_catalog_players(payload)

    PLAYER_CATALOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    limited = (
        isinstance(payload, dict)
        and payload.get("public_api_limited") is True
    )

    cache = {
        "updated": datetime.now().isoformat(),
        "count": len(players),
        "players": players,
        "public_api_limited": limited,
        "tier": (
            payload.get("tier")
            if isinstance(payload, dict)
            else None
        ),
        "limit": (
            payload.get("limit")
            if isinstance(payload, dict)
            else None
        ),
    }

    PLAYER_CATALOG_FILE.write_text(
        json.dumps(cache, indent=2),
        encoding="utf-8",
    )

    if limited:
        raise FantasyProsLimitedAccessError(
            _limited_access_message(payload)
        )

    return players


def _resolve_from_candidates(player, candidates):
    target_name = normalise_name(
        player.get("name")
        or player.get("player_name")
    )
    target_position = _normalise_position(
        player.get("position")
    )
    target_team = str(
        player.get("team") or ""
    ).upper()
    yahoo_id = str(
        player.get("yahoo_player_id")
        or player.get("yahoo_id")
        or ""
    )

    if yahoo_id:
        for candidate in candidates:
            if str(candidate.get("yahoo_id") or "") == yahoo_id:
                return candidate

    matches = [
        candidate
        for candidate in candidates
        if normalise_name(candidate.get("name")) == target_name
    ]

    if target_position:
        positional = [
            candidate
            for candidate in matches
            if _normalise_position(
                candidate.get("position")
            ) == target_position
        ]
        if positional:
            matches = positional

    if target_team:
        team_matches = [
            candidate
            for candidate in matches
            if str(candidate.get("team") or "").upper()
            == target_team
        ]
        if len(team_matches) == 1:
            matches = team_matches

    return matches[0] if len(matches) == 1 else None


def _resolve_players(players):
    local = _normalise_local_database(
        _load_player_database()
    )
    catalog = load_player_catalog()

    resolved = []
    unresolved = []

    for player in players:
        match = _resolve_from_candidates(player, local)
        if match is None:
            match = _resolve_from_candidates(player, catalog)

        if match is None:
            unresolved.append(player)
        else:
            resolved.append((player, match))

    if unresolved:
        catalog = refresh_player_catalog()
        still_unresolved = []

        for player in unresolved:
            match = _resolve_from_candidates(player, catalog)
            if match is None:
                still_unresolved.append(player)
            else:
                resolved.append((player, match))

        unresolved = still_unresolved

    if unresolved:
        names = ", ".join(
            str(
                player.get("name")
                or player.get("player_name")
            )
            for player in unresolved
        )
        raise LookupError(
            "Could not resolve FantasyPros ID for: " + names
        )

    by_name = {
        normalise_name(
            original.get("name")
            or original.get("player_name")
        ): match
        for original, match in resolved
    }

    return [
        by_name[
            normalise_name(
                player.get("name")
                or player.get("player_name")
            )
        ]
        for player in players
    ]


def _load_cache():
    data = _load_json(CACHE_FILE)
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
    ids = ":".join(
        sorted(str(value) for value in player_ids)
    )
    return f"{int(week)}|{position}|{ids}"


def fetch_targeted_comparison(
    players,
    week,
    position,
    force=False,
):
    if not API_KEY:
        raise RuntimeError(
            "FANTASYPROS_API_KEY missing from .env"
        )

    if not 2 <= len(players) <= 4:
        raise ValueError(
            "FantasyPros comparisons require 2 to 4 players"
        )

    resolved = _resolve_players(players)
    fp_ids = [player["id"] for player in resolved]
    lookup_position = _normalise_position(position)

    cache = _load_cache()
    key = _cache_key(week, lookup_position, fp_ids)

    if not force and key in cache["comparisons"]:
        return cache["comparisons"][key]

    ids_text = ":".join(fp_ids)
    projection_params = {
        "week": int(week),
        "scoring": "HALF",
        "players": ids_text,
    }

    if lookup_position == "FLEX":
        projection_params["positions"] = "RB:WR:TE"
    else:
        projection_params["position"] = lookup_position

    projection_response = requests.get(
        f"{BASE_URL}/2026/projections",
        headers={"x-api-key": API_KEY},
        params=projection_params,
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

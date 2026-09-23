import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from sleeper_compare import (
    _projection_player,
    _projection_stats,
    score_offense_for_yahoo,
)


BASE_URL = "https://api.sleeper.com"
SEASON = 2026

PROJECT_ROOT = Path(__file__).resolve().parent
CACHE_FILE = (
    PROJECT_ROOT
    / "data"
    / "sleeper_matchups.json"
)

POSITIONS = (
    "QB",
    "RB",
    "WR",
    "TE",
)

CACHE_VERSION = 1


def _normal_team(value):
    return (
        str(value or "")
        .upper()
        .replace("LA", "LAR")
        if str(value or "").upper() == "LA"
        else str(value or "").upper()
    )


def _row_position(row):
    player = _projection_player(row)

    return str(
        player.get("position")
        or row.get("position")
        or ""
    ).upper()


def _row_opponent(row):
    stats = _projection_stats(row)

    return _normal_team(
        row.get("opponent")
        or stats.get("opponent")
    )


def _rows(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        rows = []

        for player_id, value in payload.items():
            if not isinstance(value, dict):
                continue

            row = dict(value)
            row.setdefault(
                "player_id",
                player_id,
            )
            rows.append(row)

        return rows

    return []


def fetch_week_position_stats(
    position,
    week,
    season=SEASON,
):
    response = requests.get(
        f"{BASE_URL}/stats/nfl/{int(season)}/{int(week)}",
        params={
            "season_type": "regular",
            "position": position,
            "order_by": "pts_half_ppr",
        },
        timeout=30,
    )
    response.raise_for_status()

    return _rows(
        response.json()
    )


def allowed_for_week_position(
    rows,
    position,
):
    totals = {}

    for row in rows:
        row_position = (
            _row_position(row)
        )

        if (
            row_position
            and row_position != position
        ):
            continue

        opponent = _row_opponent(row)

        if not opponent:
            continue

        score = score_offense_for_yahoo(
            _projection_stats(row)
        )

        totals[opponent] = (
            totals.get(
                opponent,
                0.0,
            )
            + float(score)
        )

    return {
        team: round(
            points,
            2,
        )
        for team, points
        in totals.items()
    }


def load_cache():
    if not CACHE_FILE.exists():
        return {
            "version":
                CACHE_VERSION,
            "season":
                SEASON,
            "weeks": {},
        }

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
        return {
            "version":
                CACHE_VERSION,
            "season":
                SEASON,
            "weeks": {},
        }

    if (
        cache.get("version")
        != CACHE_VERSION
    ):
        return {
            "version":
                CACHE_VERSION,
            "season":
                SEASON,
            "weeks": {},
        }

    return cache


def save_cache(cache):
    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CACHE_FILE.write_text(
        json.dumps(
            cache,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def refresh_matchup_cache(
    current_week,
    season=SEASON,
    fetcher=fetch_week_position_stats,
):
    """Fetch completed weeks and persist fantasy points allowed by position."""

    cache = load_cache()

    if cache.get("season") != season:
        cache = {
            "version":
                CACHE_VERSION,
            "season":
                season,
            "weeks": {},
        }

    weeks = cache.setdefault(
        "weeks",
        {},
    )

    completed_through = max(
        0,
        int(current_week) - 1,
    )

    fetched = 0

    for week in range(
        1,
        completed_through + 1,
    ):
        week_key = str(week)

        if week_key in weeks:
            continue

        week_data = {}

        for position in POSITIONS:
            rows = fetcher(
                position,
                week,
                season=season,
            )

            week_data[position] = (
                allowed_for_week_position(
                    rows,
                    position,
                )
            )

        weeks[week_key] = week_data
        fetched += 1

    cache[
        "generated_at"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    cache[
        "completed_through"
    ] = completed_through

    save_cache(cache)

    return {
        "fetched_weeks": fetched,
        "completed_through":
            completed_through,
    }


def _position_samples(
    cache,
    position,
):
    samples = {}

    for week_data in (
        cache.get(
            "weeks",
            {},
        ).values()
    ):
        teams = week_data.get(
            position,
            {},
        )

        for team, points in (
            teams.items()
        ):
            samples.setdefault(
                team,
                [],
            ).append(
                float(points)
            )

    return samples


def matchup_context(
    player,
    cache=None,
):
    position = str(
        player.get("position")
        or ""
    ).upper()

    if position not in POSITIONS:
        return None

    opponent = _normal_team(
        player.get("opponent")
    )

    if not opponent:
        return None

    if cache is None:
        cache = load_cache()

    samples = _position_samples(
        cache,
        position,
    )

    opponent_samples = samples.get(
        opponent,
        [],
    )

    all_values = [
        value
        for values in samples.values()
        for value in values
    ]

    if (
        not opponent_samples
        or not all_values
    ):
        return None

    opponent_average = (
        sum(opponent_samples)
        / len(opponent_samples)
    )

    league_average = (
        sum(all_values)
        / len(all_values)
    )

    if league_average <= 0:
        return None

    delta_pct = (
        (
            opponent_average
            / league_average
        )
        - 1.0
    ) * 100.0

    if delta_pct >= 10:
        label = "FAVOURABLE"
    elif delta_pct <= -10:
        label = "TOUGH"
    else:
        label = "NEUTRAL"

    return {
        "position": position,
        "opponent": opponent,
        "games": len(
            opponent_samples
        ),
        "allowed_average":
            round(
                opponent_average,
                2,
            ),
        "league_average":
            round(
                league_average,
                2,
            ),
        "delta_pct":
            round(
                delta_pct,
                1,
            ),
        "label": label,
    }

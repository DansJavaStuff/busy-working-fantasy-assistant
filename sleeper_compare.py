import requests

from league_settings import OFFENSE_SCORING
from player_database import normalise_name


BASE_URL = "https://api.sleeper.com"
SEASON = 2026


SLEEPER_TO_YAHOO = {
    "pass_td": ("passing_touchdown", 1.0),
    "pass_int": ("interception", 1.0),
    "rush_td": ("rushing_touchdown", 1.0),
    "rec": ("reception", 1.0),
    "rec_td": ("receiving_touchdown", 1.0),
    "fum_lost": ("fumble_lost", 1.0),
}


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def score_offense_for_yahoo(stats):
    """Score a Sleeper projected stat line using Busy Working Yahoo rules."""

    stats = stats or {}
    score = 0.0

    score += _number(stats.get("pass_yd")) / float(
        OFFENSE_SCORING["passing_yards_per_point"]
    )
    score += _number(stats.get("rush_yd")) / float(
        OFFENSE_SCORING["rushing_yards_per_point"]
    )
    score += _number(stats.get("rec_yd")) / float(
        OFFENSE_SCORING["receiving_yards_per_point"]
    )

    for sleeper_key, (yahoo_key, multiplier) in SLEEPER_TO_YAHOO.items():
        score += (
            _number(stats.get(sleeper_key))
            * float(OFFENSE_SCORING[yahoo_key])
            * multiplier
        )

    two_point_total = sum(
        _number(stats.get(key))
        for key in ("pass_2pt", "rush_2pt", "rec_2pt")
    )
    score += (
        two_point_total
        * float(OFFENSE_SCORING["two_point_conversion"])
    )

    return_td_total = sum(
        _number(stats.get(key))
        for key in (
            "ret_td",
            "kr_td",
            "pr_td",
        )
    )
    score += (
        return_td_total
        * float(OFFENSE_SCORING["return_touchdown"])
    )

    fumble_return_td = _number(
        stats.get("fum_rec_td")
    )
    score += (
        fumble_return_td
        * float(
            OFFENSE_SCORING[
                "offensive_fumble_return_touchdown"
            ]
        )
    )

    return round(score, 2)


def _projection_stats(row):
    stats = row.get("stats")
    if isinstance(stats, dict):
        return stats
    return row


def _projection_player(row):
    player = row.get("player")
    return player if isinstance(player, dict) else {}


def _row_name(row):
    player = _projection_player(row)
    return (
        player.get("full_name")
        or player.get("player_name")
        or player.get("name")
        or ""
    )


def _row_team(row):
    player = _projection_player(row)
    return str(
        player.get("team")
        or player.get("team_abbr")
        or row.get("team")
        or ""
    ).upper()


def fetch_week_position(position, week, season=SEASON):
    response = requests.get(
        f"{BASE_URL}/projections/nfl/{int(season)}/{int(week)}",
        params={
            "season_type": "regular",
            "position": position,
            "order_by": "pts_half_ppr",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def find_projection(rows, player):
    target_name = normalise_name(player.get("name"))
    target_team = str(player.get("team") or "").upper()

    matches = [
        row
        for row in rows
        if normalise_name(_row_name(row)) == target_name
    ]

    if target_team:
        team_matches = [
            row for row in matches
            if _row_team(row) == target_team
        ]
        if len(team_matches) == 1:
            matches = team_matches

    return matches[0] if len(matches) == 1 else None


def compare_players(players, week, season=SEASON):
    """Return Sleeper projections rescored in Busy Working Yahoo points."""

    positions = sorted(
        {
            str(player.get("position") or "").upper()
            for player in players
            if str(player.get("position") or "").upper()
            in {"QB", "RB", "WR", "TE"}
        }
    )

    feeds = {
        position: fetch_week_position(
            position,
            week,
            season=season,
        )
        for position in positions
    }

    results = []

    for player in players:
        position = str(
            player.get("position") or ""
        ).upper()
        row = find_projection(
            feeds.get(position, []),
            player,
        )

        if row is None:
            results.append(
                {
                    "name": player.get("name"),
                    "position": position,
                    "team": player.get("team"),
                    "yahoo_projection": _number(
                        player.get("current_week_projection")
                    ),
                    "sleeper_yahoo_projection": None,
                    "sleeper_generic_half_ppr": None,
                    "raw_stats": None,
                }
            )
            continue

        stats = _projection_stats(row)
        results.append(
            {
                "name": player.get("name"),
                "position": position,
                "team": player.get("team"),
                "yahoo_projection": round(
                    _number(
                        player.get("current_week_projection")
                    ),
                    2,
                ),
                "sleeper_yahoo_projection": (
                    score_offense_for_yahoo(stats)
                ),
                "sleeper_generic_half_ppr": (
                    stats.get("pts_half_ppr")
                ),
                "raw_stats": stats,
            }
        )

    return results

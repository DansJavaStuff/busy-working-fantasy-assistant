import math
from datetime import UTC, datetime
from time import monotonic

import requests

from league_settings import DEFENSE_SCORING, KICKER_SCORING, OFFENSE_SCORING
from player_database import normalise_name, normalise_name_without_suffix


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


def score_stream_for_yahoo(stats, position):
    """Rescore supplied projection components; never use preset fantasy totals."""
    def value(key):
        number = float(stats[key])
        if not math.isfinite(number) or number < 0:
            raise ValueError("Invalid projected statistic: " + key)
        return number

    try:
        if position == "K":
            # All sub-40-yard kicks earn two points in this league. Use the
            # total rather than summing short bands, which can be incomplete.
            total = value("fgm")
            medium = value("fgm_40_49")
            long = value("fgm_50p")
            short = total - medium - long
            if short < -0.02:
                raise ValueError("Field-goal bands exceed the total")
            score = (
                max(0, short) * KICKER_SCORING["field_goal_0_19"]
                + medium * KICKER_SCORING["field_goal_40_49"]
                + long * KICKER_SCORING["field_goal_50_plus"]
                + value("xpm") * KICKER_SCORING["pat_made"]
            )
            note = "Rescored estimate; short field goals derived from total makes."
        else:
            bands = {
                "pts_allow_0": "points_allowed_0",
                "pts_allow_1_6": "points_allowed_1_6",
                "pts_allow_7_13": "points_allowed_7_13",
                "pts_allow_14_20": "points_allowed_14_20",
                "pts_allow_21_27": "points_allowed_21_27",
                "pts_allow_28_34": "points_allowed_28_34",
                "pts_allow_35p": "points_allowed_35_plus",
            }
            supplied = [key for key in bands if key in stats]
            if not supplied or abs(sum(value(key) for key in supplied) - 1) > 0.05:
                raise ValueError("Missing or incomplete points-allowed bands")
            score = sum(value(key) * DEFENSE_SCORING[bands[key]] for key in supplied)
            # Aggregate defensive TDs already contain interception/fumble TDs.
            mapping = {
                "sack": "sack", "int": "interception",
                "fum_rec": "fumble_recovery", "def_td": "touchdown",
                "safe": "safety", "blk_kick": "blocked_kick",
                "st_td": "kickoff_punt_return_touchdown",
                "def_2pt": "extra_point_returned",
            }
            for key in ("sack", "int", "fum_rec", "def_td"):
                value(key)  # Require core fields; omitted rare events are zero.
            score += sum(value(key) * DEFENSE_SCORING[target]
                         for key, target in mapping.items() if key in stats)
            if "st_td" not in stats:
                score += sum(value(key) for key in ("def_kr_td", "def_pr_td") if key in stats) * DEFENSE_SCORING["kickoff_punt_return_touchdown"]
            note = "Rescored estimate using provider points-allowed bands, not outcome probabilities."
        return round(score, 2), note
    except (KeyError, TypeError, ValueError) as exc:
        return None, "Cannot rescore safely: " + str(exc)


_FEED_CACHE = {}


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

    explicit = (
        player.get("full_name")
        or player.get("player_name")
        or player.get("name")
    )
    if explicit:
        return explicit

    parts = [
        str(value).strip()
        for value in (
            player.get("first_name"),
            player.get("last_name"),
        )
        if value
    ]
    return " ".join(parts)


def _team_key(team):
    team = str(team or "").upper()
    return {"JAC": "JAX", "LA": "LAR", "WSH": "WAS"}.get(team, team)


def _row_team(row):
    player = _projection_player(row)
    return _team_key(
        player.get("team")
        or player.get("team_abbr")
        or row.get("team")
        or ""
    )


def fetch_week_position(position, week, season=SEASON):
    cache_key = (position, int(week), int(season))
    cached = _FEED_CACHE.get(cache_key)
    if cached and monotonic() - cached[0] < 900:
        return cached[1]
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
    rows = payload if isinstance(payload, list) else []
    _FEED_CACHE[cache_key] = (monotonic(), rows)
    return rows


def find_projection(rows, player):
    if player.get("position") in {"DST", "DEF"}:
        team = _team_key(player.get("team"))
        matches = [row for row in rows if team and _row_team(row) == team]
        return matches[0] if len(matches) == 1 else None
    target_name = normalise_name(player.get("name"))
    target_team = _team_key(player.get("team"))

    matches = [
        row
        for row in rows
        if normalise_name(_row_name(row)) == target_name
        and (not _projection_player(row).get("position")
             or _projection_player(row)["position"] == player.get("position"))
    ]

    if matches:
        if target_team:
            matches = [row for row in matches if _row_team(row) == target_team]
        return matches[0] if len(matches) == 1 else None

    # Only relax a missing suffix when team and position establish a unique
    # identity. Never use a fuzzy surname match or choose one ambiguous row.
    target_base = normalise_name_without_suffix(player.get("name"))
    if not target_team or not target_base:
        return None
    matches = [
        row for row in rows
        if normalise_name_without_suffix(_row_name(row)) == target_base
        and _row_team(row) == target_team
        and str(_projection_player(row).get("position") or "").upper()
        == str(player.get("position") or "").upper()
    ]
    return matches[0] if len(matches) == 1 else None


def compare_players(players, week, season=SEASON):
    """Return Sleeper projections rescored in Busy Working Yahoo points."""

    positions = sorted(
        {
            "DEF" if player.get("position") in {"DST", "DEF"}
            else str(player.get("position") or "").upper()
            for player in players
            if str(player.get("position") or "").upper()
            in {"QB", "RB", "WR", "TE", "K", "DST", "DEF"}
        }
    )

    feeds, errors = {}, {}
    for position in positions:
        try:
            feeds[position] = fetch_week_position(position, week, season=season)
        except Exception as exc:
            feeds[position] = []
            errors[position] = "Sleeper feed unavailable: " + str(exc)

    results = []

    for player in players:
        position = str(
            player.get("position") or ""
        ).upper()
        feed_position = "DEF" if position in {"DST", "DEF"} else position
        row = find_projection(
            feeds.get(feed_position, []),
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
                    "coverage_note": errors.get(feed_position, "No matching weekly projection."),
                    "source": "Sleeper",
                    "provider": None,
                    "updated_at": None,
                }
            )
            continue

        stats = _projection_stats(row)
        updated_at = row.get("updated_at") or row.get("last_modified")
        try:
            updated_display = datetime.fromtimestamp(float(updated_at) / 1000, UTC).strftime("%d %b %Y %H:%M UTC")
        except (ValueError, TypeError, OverflowError, OSError):
            updated_display = "Not supplied"
        if position in {"K", "DST", "DEF"}:
            rescored, coverage_note = score_stream_for_yahoo(stats, position)
        else:
            rescored, coverage_note = score_offense_for_yahoo(stats), "Rescored to league rules."
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
                    rescored
                ),
                "sleeper_generic_half_ppr": (
                    stats.get("pts_half_ppr")
                ),
                "raw_stats": stats,
                "coverage_note": coverage_note,
                "source": "Sleeper",
                "provider": row.get("company"),
                "updated_at": updated_at,
                "updated_display": updated_display,
            }
        )

    return results


def stream_move_evidence(move, results):
    """Compare both sides of a stream without changing Yahoo's move score."""
    def lookup(player):
        return next((r for r in results if r.get("position") == player.get("position")
                     and normalise_name(r.get("name")) == normalise_name(player.get("name"))
                     and r.get("team") == player.get("team")), {})
    add = lookup(move["add"])
    drop = lookup(move["drop"])
    incoming, outgoing = add.get("sleeper_yahoo_projection"), drop.get("sleeper_yahoo_projection")
    edge = round(incoming - outgoing, 2) if incoming is not None and outgoing is not None else None
    verdict = ("SECOND SOURCE UNAVAILABLE" if edge is None else
               "SECOND SOURCE FAVOURS ADD" if edge >= 0.5 else
               "SOURCES DISAGREE" if edge <= -0.5 else "SECOND SOURCE TOO CLOSE TO CALL")
    return {"add": add, "drop": drop, "edge": edge, "verdict": verdict}


def attach_stream_evidence(moves, week, sleeper_fetch=compare_players):
    streams = [move for move in moves if move.get("streaming")]
    if not streams:
        return moves
    players = [player for move in streams for player in (move["add"], move["drop"])]
    try:
        results = sleeper_fetch(players, week=week)
    except Exception:
        results = []
    return [{**move, "source_comparison": stream_move_evidence(move, results)}
            if move.get("streaming") else move for move in moves]

from pathlib import Path
import json
import re
import shutil
import sys

from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from database import (
    load_season_roster,
    replace_week_cant_cut,
)
from fantasy_calendar import current_fantasy_week
from roster_manager import replace_roster_player

DATA_DIR = PROJECT_ROOT / "data"

HEADSHOT_DIR = (
    PROJECT_ROOT
    / "static"
    / "player_headshots"
)

OUTPUT_FILE = (
    DATA_DIR
    / "yahoo_available_players.json"
)

MY_TEAM_OUTPUT_FILE = (
    DATA_DIR
    / "yahoo_my_team.json"
)

PARSE_CACHE_FILE = (
    DATA_DIR
    / "yahoo_html_store.json"
)

PARSE_CACHE_VERSION = 5

SEASON = 2026
MY_TEAM_NAME = "Allen Wrench"

PLAYER_SOURCE_PREFIX = (
    "Yahoo_Player_list_"
)

MY_TEAM_SOURCE_PREFIX = (
    "Yahoo_MyTeam_"
)

GAME_FIELDS = (
    "game_display",
    "game_day",
    "game_time",
    "opponent",
    "home_away",
)

CANT_CUT_CLASSES = {
    "noactioncc-cantcut",
    "T-action-icon-cantcut",
}

DROP_ACTION_CLASS = "T-action-icon-drop"

CANT_CUT_ELIGIBLE_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
}

MIN_CANT_CUT_ACTION_COVERAGE = 0.8


def clean_text(value):
    return " ".join(
        value.split()
    )


def _normalise_player_name(value):
    return clean_text(
        value or ""
    ).casefold()


def parse_cant_cut_actions(path):
    """Return Yahoo drop-action observations from one saved My Team page."""

    soup = BeautifulSoup(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        ),
        "html.parser",
    )

    observations = {}

    for link in soup.find_all(
        "a",
        attrs={
            "data-ys-playerid": True,
        },
    ):
        player_id = str(
            link.get(
                "data-ys-playerid"
            )
        )

        if player_id in observations:
            continue

        row = link.find_parent("tr")

        if row is None:
            continue

        name = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if not name:
            continue

        player_cell = link.find_parent(
            ["th", "td"]
        )
        team = None
        position = None

        if player_cell is not None:
            team, position = (
                extract_team_position(
                    player_cell
                )
            )

        action = None

        for control in row.find_all(
            ["a", "button"],
        ):
            classes = set(
                control.get(
                    "class",
                    [],
                )
            )
            title = clean_text(
                control.get(
                    "title",
                    "",
                )
            ).casefold()

            if (
                classes
                & CANT_CUT_CLASSES
                or title
                == "player is on can't cut list"
            ):
                action = "cant_cut"
                break

            if (
                DROP_ACTION_CLASS
                in classes
                or title == "drop player"
            ):
                action = "drop"

        observations[player_id] = {
            "player_id": player_id,
            "player_name": name,
            "team": team,
            "position": position,
            "action": action,
        }

    return observations


def parse_number(value):
    value = value.strip()

    if value in {"", "-", "—"}:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value):
    number = parse_number(value)

    if number is None:
        return None

    return int(number)


def parse_percentage(value):
    value = value.strip()

    if not value.endswith("%"):
        return None

    try:
        return float(
            value.rstrip("%")
        )
    except ValueError:
        return None


def extract_team_position(cell):
    text = clean_text(
        cell.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\b([A-Za-z]{2,3})\s*-\s*"
        r"(QB|RB|WR|TE|K|DEF|DST)\b",
        text,
    )

    if not match:
        return None, None

    team = match.group(1).upper()
    position = match.group(2).upper()

    if position == "DEF":
        position = "DST"

    return team, position


def extract_status(cell):
    status = cell.select_one(
        ".ysf-player-status"
    )

    if not status:
        return None

    value = clean_text(
        status.get_text(
            " ",
            strip=True,
        )
    )

    return value or None


def extract_headshot(
    cell,
    player_id,
):
    image = cell.find(
        "img",
        alt=True,
    )

    if not image:
        return None

    src = image.get("src")

    if not src:
        return None

    html_relative = Path(
        src.replace("./", "")
    )

    source = (
        DATA_DIR
        / html_relative
    )

    if not source.exists():
        return None

    suffix = source.suffix.lower()

    destination = (
        HEADSHOT_DIR
        / f"{player_id}{suffix}"
    )

    HEADSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    return (
        "player_headshots/"
        f"{destination.name}"
    )


def _normal_header(value):
    value = (
        clean_text(value)
        .lower()
        .replace("% rostered", "% ros")
        .replace("% started", "% start")
        .replace("roster status", "status")
    )

    # Yahoo decorates some column labels with icon glyphs from its private
    # font (for example "Fan Pts \ue002").  Those glyphs are visual only and
    # must not be part of the semantic header name used by the importer.
    value = re.sub(
        r"[^a-z0-9%]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def _expanded_header_cells(row):
    labels = []

    for cell in row.find_all(
        ["th", "td"],
        recursive=False,
    ):
        label = _normal_header(
            cell.get_text(
                " ",
                strip=True,
            )
        )

        try:
            colspan = int(
                cell.get(
                    "colspan",
                    1,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            colspan = 1

        labels.extend(
            [label] * max(
                1,
                colspan,
            )
        )

    return labels


def column_indexes(row):
    """Map Yahoo's visible leaf headers to row-cell indexes."""

    table = row.find_parent(
        "table"
    )

    if table is None:
        return {}

    candidates = []

    for header_row in table.find_all(
        "tr"
    ):
        if header_row is row:
            break

        labels = (
            _expanded_header_cells(
                header_row
            )
        )

        if not labels:
            continue

        recognised = sum(
            1
            for label in labels
            if label in {
                "pos",
                "offense",
                "player",
                "status",
                "gp",
                "bye",
                "fan pts",
                "proj pts",
                "% start",
                "% ros",
            }
        )

        if recognised:
            candidates.append(
                (
                    recognised,
                    labels,
                )
            )

    if not candidates:
        return {}

    labels = max(
        candidates,
        key=lambda item:
            item[0],
    )[1]

    indexes = {}

    for index, label in enumerate(
        labels
    ):
        if (
            label
            and label not in indexes
        ):
            indexes[label] = index

    return indexes


def _cell_text(
    cells,
    indexes,
    label,
    fallback=None,
):
    index = indexes.get(
        label,
        fallback,
    )

    if (
        index is None
        or index < 0
        or index >= len(cells)
    ):
        return ""

    return cells[index].get_text(
        " ",
        strip=True,
    )


def extract_offense_stats(
    cells,
    position,
):
    """
    Yahoo offense stat columns after % rostered:

    10 pass yards
    11 pass TD
    12 interceptions
    13 rush attempts
    14 rush yards
    15 rush TD
    16 targets
    17 receptions
    18 receiving yards
    19 receiving TD
    20 return TD
    21 two-point conversions
    22 fumbles lost
    """

    if position not in {
        "QB",
        "RB",
        "WR",
        "TE",
    }:
        return None

    if len(cells) < 23:
        return None

    return {
        "pass_yards":
            parse_number(
                cells[10].get_text(
                    strip=True
                )
            ),

        "pass_td":
            parse_number(
                cells[11].get_text(
                    strip=True
                )
            ),

        "interceptions":
            parse_number(
                cells[12].get_text(
                    strip=True
                )
            ),

        "rush_attempts":
            parse_number(
                cells[13].get_text(
                    strip=True
                )
            ),

        "rush_yards":
            parse_number(
                cells[14].get_text(
                    strip=True
                )
            ),

        "rush_td":
            parse_number(
                cells[15].get_text(
                    strip=True
                )
            ),

        "targets":
            parse_number(
                cells[16].get_text(
                    strip=True
                )
            ),

        "receptions":
            parse_number(
                cells[17].get_text(
                    strip=True
                )
            ),

        "receiving_yards":
            parse_number(
                cells[18].get_text(
                    strip=True
                )
            ),

        "receiving_td":
            parse_number(
                cells[19].get_text(
                    strip=True
                )
            ),

        "return_td":
            parse_number(
                cells[20].get_text(
                    strip=True
                )
            ),

        "two_point":
            parse_number(
                cells[21].get_text(
                    strip=True
                )
            ),

        "fumbles_lost":
            parse_number(
                cells[22].get_text(
                    strip=True
                )
            ),
    }


def extract_game_info(
    player_cell,
):
    """
    Extract Yahoo matchup text such as:

        Sun 1:00 pm @ Hou
        Thu 8:20 pm vs NE
    """

    text = " ".join(
        player_cell.stripped_strings
    )

    match = re.search(
        r"\b"
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
        r"\s+"
        r"(\d{1,2}:\d{2})"
        r"\s*"
        r"(am|pm)"
        r"\s+"
        r"(@|vs\.?)"
        r"\s+"
        r"([A-Za-z]{2,4})"
        r"\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return {
            "game_display": None,
            "game_day": None,
            "game_time": None,
            "opponent": None,
            "home_away": None,
        }

    day = match.group(1).title()
    clock = match.group(2)
    meridiem = (
        match.group(3).lower()
    )
    marker = (
        match.group(4).lower()
    )
    opponent = (
        match.group(5).upper()
    )

    home_away = (
        "away"
        if marker == "@"
        else "home"
    )

    return {
        "game_display": (
            f"{day} {clock} "
            f"{meridiem} "
            f"{marker} {opponent}"
        ),
        "game_day": day,
        "game_time": (
            f"{clock} {meridiem}"
        ),
        "opponent": opponent,
        "home_away": home_away,
    }


def parse_page(path):
    html = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    players = {}

    links = soup.find_all(
        "a",
        attrs={
            "data-ys-playerid": True,
        },
    )

    seen = set()

    is_actual_snapshot = (
        "-actual"
        in path.name.lower()
    )

    for link in links:
        player_id = link.get(
            "data-ys-playerid"
        )

        if not player_id:
            continue

        if player_id in seen:
            continue

        row = link.find_parent("tr")

        if row is None:
            continue

        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        link_cell = link.find_parent(
            ["th", "td"]
        )

        if (
            link_cell is None
            or link_cell not in cells
        ):
            continue

        player_cell = link_cell
        player_index = cells.index(
            player_cell
        )

        indexes = column_indexes(
            row
        )

        name = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        (
            team,
            position,
        ) = extract_team_position(
            player_cell
        )

        if not name:
            continue

        if (
            not team
            or not position
        ):
            continue

        game_info = (
            extract_game_info(
                player_cell
            )
        )

        roster_status = (
            _cell_text(
                cells,
                indexes,
                "status",
            )
        )

        if (
            not roster_status
            and not indexes
            and player_index + 1
            < len(cells)
        ):
            roster_status = clean_text(
                cells[
                    player_index + 1
                ].get_text(
                    " ",
                    strip=True,
                )
            )

        status = extract_status(
            player_cell
        )

        if indexes:
            bye_text = _cell_text(
                cells,
                indexes,
                "bye",
            )

            points_label = (
                "fan pts"
                if is_actual_snapshot
                else "proj pts"
            )

            points_text = _cell_text(
                cells,
                indexes,
                points_label,
            )

            # Some historical Yahoo captures only expose one fantasy-points
            # column. Fall back to the other named points column, never to a
            # positional cell that could actually be Bye.
            if not points_text:
                alternate = (
                    "proj pts"
                    if points_label
                    == "fan pts"
                    else "fan pts"
                )
                points_text = _cell_text(
                    cells,
                    indexes,
                    alternate,
                )

            games_played_text = (
                _cell_text(
                    cells,
                    indexes,
                    "gp",
                )
            )

            rostered_text = (
                _cell_text(
                    cells,
                    indexes,
                    "% ros",
                )
            )
        else:
            # Legacy saved layouts from before Yahoo added separate Fan Pts /
            # Proj Pts columns.
            games_played_text = (
                cells[4].get_text(
                    strip=True,
                )
                if len(cells) > 4
                else ""
            )

            bye_text = (
                cells[5].get_text(
                    strip=True,
                )
                if len(cells) > 5
                else ""
            )

            points_text = (
                cells[6].get_text(
                    strip=True,
                )
                if len(cells) > 6
                else ""
            )

            rostered_text = (
                cells[9].get_text(
                    strip=True,
                )
                if len(cells) > 9
                else ""
            )

        players[player_id] = {
            "yahoo_player_id":
                player_id,

            "name":
                name,

            "team":
                team,

            "position":
                position,

            "status":
                status,

            "roster_status":
                roster_status,

            "games_played":
                parse_int(
                    games_played_text
                ),

            "bye_week":
                parse_int(
                    bye_text
                ),

            "projection":
                parse_number(
                    points_text
                ),

            "preseason_rank":
                None,

            "actual_rank":
                None,

            "rostered_pct":
                parse_percentage(
                    rostered_text
                ),

            "headshot_source":
                extract_headshot(
                    player_cell,
                    player_id,
                ),

            "projection_stats":
                (
                    extract_offense_stats(
                        cells,
                        position,
                    )
                    if not indexes
                    else None
                ),
        }

        for field in GAME_FIELDS:
            players[
                player_id
            ][field] = (
                game_info[field]
            )

        seen.add(player_id)

    return players


def _normalise_lineup_slot(value):
    value = clean_text(
        value or ""
    ).upper()

    aliases = {
        "W/R/T": "FLEX",
        "W/R": "FLEX",
        "R/W/T": "FLEX",
        "DST": "DEF",
    }

    value = aliases.get(
        value,
        value,
    )

    if value in {
        "QB",
        "RB",
        "WR",
        "TE",
        "FLEX",
        "K",
        "DEF",
        "BN",
        "IR",
    }:
        return value

    return None


def parse_my_team_lineup_page(path):
    """Extract Yahoo submitted roster slots from one saved My Team page."""

    html = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    players = {}
    slot_counts = {}
    seen = set()

    for link in soup.find_all(
        "a",
        attrs={
            "data-ys-playerid": True,
        },
    ):
        player_id = link.get(
            "data-ys-playerid"
        )

        if (
            not player_id
            or player_id in seen
        ):
            continue

        row = link.find_parent("tr")

        if row is None:
            continue

        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        player_cell = link.find_parent(
            ["th", "td"]
        )

        if (
            player_cell is None
            or player_cell not in cells
        ):
            continue

        indexes = column_indexes(
            row
        )

        # Yahoo My Team layouts have varied over time. Prefer the
        # semantic Pos column when available, but fall back to scanning cells
        # before the player-name cell for a recognised roster slot.
        slot_candidates = []

        semantic_slot = _cell_text(
            cells,
            indexes,
            "pos",
        )

        if semantic_slot:
            slot_candidates.append(
                semantic_slot
            )

        player_index = cells.index(
            player_cell
        )

        for cell in cells[:player_index]:
            text_value = clean_text(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )

            if text_value:
                slot_candidates.append(
                    text_value
                )

        lineup_slot = next(
            (
                slot
                for slot in (
                    _normalise_lineup_slot(
                        candidate
                    )
                    for candidate
                    in slot_candidates
                )
                if slot is not None
            ),
            None,
        )

        if lineup_slot is None:
            continue

        name = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if not name:
            # Yahoo's note icon can carry the player id but no visible name.
            # Fall back to the first player link in the same cell.
            candidate = (
                player_cell.find(
                    "a",
                    href=re.compile(
                        r"/nfl/(?:players|teams)/"
                    ),
                )
            )

            if candidate:
                name = clean_text(
                    candidate.get_text(
                        " ",
                        strip=True,
                    )
                )

        team, position = (
            extract_team_position(
                player_cell
            )
        )

        if (
            not name
            or not position
        ):
            continue

        slot_counts[lineup_slot] = (
            slot_counts.get(
                lineup_slot,
                0,
            )
            + 1
        )

        players[str(player_id)] = {
            "player_id": str(
                player_id
            ),
            "player_name": name,
            "position": position,
            "team": team,
            "lineup_slot":
                lineup_slot,
            "slot_index":
                slot_counts[
                    lineup_slot
                ],
            "source":
                "yahoo_my_team",
        }

        seen.add(
            player_id
        )

    return players


def file_signature(path):
    stat = path.stat()

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def load_parse_cache():
    if not PARSE_CACHE_FILE.exists():
        return {
            "version": PARSE_CACHE_VERSION,
            "files": {},
        }

    try:
        cache = json.loads(
            PARSE_CACHE_FILE.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {
            "version": PARSE_CACHE_VERSION,
            "files": {},
        }

    if (
        cache.get("version")
        != PARSE_CACHE_VERSION
        or not isinstance(
            cache.get("files"),
            dict,
        )
    ):
        return {
            "version": PARSE_CACHE_VERSION,
            "files": {},
        }

    return cache


def save_parse_cache(cache):
    PARSE_CACHE_FILE.write_text(
        json.dumps(
            {
                "version":
                    PARSE_CACHE_VERSION,
                "files":
                    cache.get(
                        "files",
                        {},
                    ),
            },
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )


def parse_page_cached(
    path,
    cache,
):
    signature = file_signature(
        path
    )
    cache_key = path.name

    entry = (
        cache.get(
            "files",
            {},
        ).get(cache_key)
    )

    if (
        entry
        and entry.get("size")
        == signature["size"]
        and entry.get("mtime_ns")
        == signature["mtime_ns"]
        and isinstance(
            entry.get("players"),
            dict,
        )
    ):
        return (
            entry["players"],
            True,
        )

    players = parse_page(path)

    existing = (
        cache.setdefault(
            "files",
            {},
        ).get(cache_key)
        or {}
    )

    cache["files"][cache_key] = {
        **existing,
        **signature,
        "players": players,
    }

    return players, False


def snapshot_name_from_filename(
    path,
    prefix,
):
    """
    Convert a saved Yahoo HTML filename into
    the provider field it contains.

    Pagination suffixes are deliberately ignored, so
    week2-Proj.html, week2-Proj2.html and similar files
    all merge into one Week 2 snapshot.
    """

    name = path.name

    if (
        not name.startswith(prefix)
        or not name.lower().endswith(
            ".html"
        )
    ):
        return None

    detail = name[
        len(prefix):-5
    ]

    detail = re.sub(
        r"^(?:K|DEF)_",
        "",
        detail,
        flags=re.IGNORECASE,
    )

    if re.match(
        r"^4week-Proj",
        detail,
        re.IGNORECASE,
    ):
        return (
            "next_4_weeks_projection"
        )

    match = re.match(
        r"^week(\d+)-"
        r"(Proj|Actual)",
        detail,
        re.IGNORECASE,
    )

    if not match:
        return None

    week = int(
        match.group(1)
    )

    kind = (
        match.group(2)
        .lower()
    )

    suffix = (
        "projection"
        if kind == "proj"
        else "actual"
    )

    return (
        f"week_{week}_{suffix}"
    )


def discover_source_files(
    prefix,
):
    discovered = {}

    for path in sorted(
        DATA_DIR.glob(
            f"{prefix}*.html"
        )
    ):
        snapshot_name = (
            snapshot_name_from_filename(
                path,
                prefix,
            )
        )

        if snapshot_name is None:
            continue

        discovered.setdefault(
            snapshot_name,
            [],
        ).append(path)

    return discovered


def merge_source_maps(*source_maps):
    """Combine Yahoo snapshot files regardless of which page supplied them."""

    merged = {}

    for source_map in source_maps:
        for snapshot_name, paths in source_map.items():
            merged.setdefault(
                snapshot_name,
                [],
            ).extend(paths)

    for paths in merged.values():
        paths.sort(
            key=lambda path: (
                path.stat().st_mtime_ns,
                path.name,
            )
        )

    return merged


def _my_team_page_kind(path):
    name = path.name

    if name.startswith(
        f"{MY_TEAM_SOURCE_PREFIX}K_"
    ):
        return "K"

    if name.startswith(
        f"{MY_TEAM_SOURCE_PREFIX}DEF_"
    ):
        return "DST"

    return "OFFENSE"


def freshest_my_team_pages(my_team_sources):
    """Return the newest saved My Team page for offense, kicker and DST."""

    newest_by_kind = {}

    for paths in my_team_sources.values():
        for path in paths:
            kind = _my_team_page_kind(
                path
            )
            current = newest_by_kind.get(
                kind
            )

            if (
                current is None
                or path.stat().st_mtime_ns
                > current.stat().st_mtime_ns
            ):
                newest_by_kind[kind] = path

    return newest_by_kind


def _observation_matches_local(
    observation,
    local_player,
):
    if (
        _normalise_player_name(
            observation.get(
                "player_name"
            )
        )
        == _normalise_player_name(
            local_player.get(
                "player_name"
            )
        )
    ):
        return True

    return (
        local_player.get(
            "position"
        )
        in {"DEF", "DST"}
        and observation.get(
            "position"
        )
        in {"DEF", "DST"}
        and _normalise_player_name(
            observation.get(
                "team"
            )
        )
        == _normalise_player_name(
            local_player.get(
                "team"
            )
        )
    )


def sync_cant_cut_from_my_team(
    my_team_sources,
    local_roster,
    week=None,
):
    """Persist Can't Cut players only from a complete, actionable roster."""

    newest_pages = freshest_my_team_pages(
        my_team_sources
    )

    if not newest_pages:
        print(
            "Can't Cut auto-sync skipped: "
            "no saved My Team pages."
        )
        return False

    observations = {}

    for path in newest_pages.values():
        observations.update(
            parse_cant_cut_actions(
                path
            )
        )

    eligible_roster = [
        player
        for player in local_roster
        if player.get(
            "position"
        )
        in CANT_CUT_ELIGIBLE_POSITIONS
    ]

    matched = []

    for local_player in eligible_roster:
        match = next(
            (
                observation
                for observation
                in observations.values()
                if _observation_matches_local(
                    observation,
                    local_player,
                )
            ),
            None,
        )

        if match is not None:
            matched.append(match)

    if len(matched) != len(eligible_roster):
        print(
            "Can't Cut auto-sync skipped: "
            "newest My Team pages cover "
            f"{len(matched)} of "
            f"{len(eligible_roster)} eligible "
            "offensive roster players."
        )
        return False

    unclassified = [
        player
        for player in matched
        if player.get(
            "action"
        )
        not in {
            "cant_cut",
            "drop",
        }
    ]

    recognised_count = (
        len(matched)
        - len(unclassified)
    )
    action_coverage = (
        recognised_count
        / len(matched)
        if matched
        else 0.0
    )

    if (
        action_coverage
        < MIN_CANT_CUT_ACTION_COVERAGE
    ):
        print(
            "Can't Cut auto-sync skipped: "
            "Yahoo's drop action was recognised for "
            f"{recognised_count} of {len(matched)} "
            "eligible offensive roster players "
            f"({action_coverage:.0%})."
        )

        if unclassified:
            print(
                "  Unrecognised: "
                + ", ".join(
                    sorted(
                        player[
                            "player_name"
                        ]
                        for player
                        in unclassified
                    )
                )
            )

        return False

    if unclassified:
        print(
            "Can't Cut auto-sync: "
            f"{len(unclassified)} player action(s) "
            "were unrecognised but semantic action coverage "
            f"was sufficient ({action_coverage:.0%})."
        )
        print(
            "  Unrecognised: "
            + ", ".join(
                sorted(
                    player[
                        "player_name"
                    ]
                    for player
                    in unclassified
                )
            )
        )

    if week is None:
        week = current_fantasy_week(
            SEASON
        )

    cant_cut = [
        {
            "player_id":
                player["player_id"],
            "player_name":
                player["player_name"],
            "source":
                "yahoo_html",
        }
        for player in matched
        if player[
            "action"
        ] == "cant_cut"
    ]

    replace_week_cant_cut(
        week,
        cant_cut,
        season=SEASON,
        source="yahoo_html",
    )

    print()
    print("YAHOO CAN'T CUT")
    print("===============")
    print(
        f"Stored Week {week} Can't Cut list: "
        f"{len(cant_cut)} player(s)"
    )

    for player in sorted(
        cant_cut,
        key=lambda item:
            item["player_name"],
    ):
        print(
            f"  {player['player_name']} "
            f"({player['player_id']})"
        )

    return True


def freshest_current_my_team_players(
    my_team_sources,
    parse_cache,
):
    """Return membership from the freshest current-week My Team pages.

    My Team is small enough to be represented by offense, K and DST pages.
    When duplicate browser downloads exist, only the newest file for each page
    kind is authoritative for roster membership.
    """

    week = current_fantasy_week(
        SEASON
    )

    snapshot_name = (
        f"week_{week}_projection"
    )

    paths = my_team_sources.get(
        snapshot_name,
        [],
    )

    if not paths:
        return {}

    newest_by_kind = {}

    for path in paths:
        kind = _my_team_page_kind(
            path
        )

        current = newest_by_kind.get(
            kind
        )

        if (
            current is None
            or path.stat().st_mtime_ns
            > current.stat().st_mtime_ns
        ):
            newest_by_kind[kind] = path

    players = {}

    for path in newest_by_kind.values():
        page_players, _ = (
            parse_page_cached(
                path,
                parse_cache,
            )
        )

        players.update(
            page_players
        )

    return players


def _same_roster_player(
    local_player,
    yahoo_player,
):
    if (
        local_player.get(
            "player_name",
            "",
        ).lower()
        == yahoo_player.get(
            "name",
            "",
        ).lower()
    ):
        return True

    return (
        local_player.get(
            "position"
        ) in {"DEF", "DST"}
        and yahoo_player.get(
            "position"
        ) == "DST"
        and local_player.get(
            "team"
        )
        == yahoo_player.get(
            "team"
        )
    )


def reconcile_local_roster_from_yahoo(
    local_roster,
    yahoo_roster,
):
    """Apply unambiguous same-position Yahoo roster changes to SQLite."""

    snapshot_players = list(
        yahoo_roster.values()
    )

    if (
        not snapshot_players
        or len(snapshot_players)
        != len(local_roster)
    ):
        print(
            "Roster auto-sync skipped: "
            "fresh My Team snapshot size "
            f"{len(snapshot_players)} != local "
            f"{len(local_roster)}."
        )
        return False

    removed = [
        local
        for local in local_roster
        if not any(
            _same_roster_player(
                local,
                yahoo,
            )
            for yahoo in snapshot_players
        )
    ]

    added = [
        yahoo
        for yahoo in snapshot_players
        if not any(
            _same_roster_player(
                local,
                yahoo,
            )
            for local in local_roster
        )
    ]

    if not removed and not added:
        return False

    def normal_position(value):
        return (
            "DST"
            if value in {"DEF", "DST"}
            else value
        )

    removed_by_position = {}
    added_by_position = {}

    for player in removed:
        removed_by_position.setdefault(
            normal_position(
                player.get(
                    "position"
                )
            ),
            [],
        ).append(player)

    for player in added:
        added_by_position.setdefault(
            normal_position(
                player.get(
                    "position"
                )
            ),
            [],
        ).append(player)

    if (
        set(removed_by_position)
        != set(added_by_position)
        or any(
            len(
                removed_by_position[
                    position
                ]
            )
            != len(
                added_by_position[
                    position
                ]
            )
            for position
            in removed_by_position
        )
    ):
        print(
            "Roster auto-sync skipped: "
            "Yahoo/local changes are not an "
            "unambiguous same-position swap."
        )
        return False

    for position in sorted(
        removed_by_position
    ):
        outgoing = sorted(
            removed_by_position[
                position
            ],
            key=lambda player:
                player.get(
                    "player_name",
                    "",
                ),
        )

        incoming = sorted(
            added_by_position[
                position
            ],
            key=lambda player:
                player.get(
                    "name",
                    "",
                ),
        )

        for dropped, added_player in zip(
            outgoing,
            incoming,
        ):
            local_id = (
                added_player["name"]
                .lower()
                .replace("'", "")
                .replace(".", "")
                .replace(" ", "-")
            )

            replace_roster_player(
                dropped[
                    "player_id"
                ],
                {
                    "player_id":
                        local_id,
                    "player_name":
                        added_player[
                            "name"
                        ],
                    "position":
                        added_player[
                            "position"
                        ],
                    "team":
                        added_player.get(
                            "team"
                        ),
                    "bye_week":
                        added_player.get(
                            "bye_week"
                        ),
                    "status":
                        added_player.get(
                            "status"
                        ),
                    "source":
                        "yahoo_html_sync",
                },
                season=SEASON,
            )

            print(
                "Roster auto-sync: "
                f"{dropped['player_name']} "
                "-> "
                f"{added_player['name']}"
            )

    return True


def snapshot_sort_key(
    snapshot_name,
):
    match = re.fullmatch(
        r"week_(\d+)_"
        r"(projection|actual)",
        snapshot_name,
    )

    if match:
        return (
            int(match.group(1)),
            (
                0
                if match.group(2)
                == "projection"
                else 1
            ),
        )

    if (
        snapshot_name
        == "next_4_weeks_projection"
    ):
        return (999, 0)

    return (1000, snapshot_name)


def merge_projection_sources(
    source_files,
    parse_cache=None,
    cache_stats=None,
):
    merged = {}

    for (
        projection_name,
        paths,
    ) in sorted(
        source_files.items(),
        key=lambda item:
            snapshot_sort_key(
                item[0]
            ),
    ):
        projection_players = {}

        print()
        print(projection_name)
        print(
            "-"
            * len(projection_name)
        )

        for path in paths:
            if parse_cache is None:
                print(
                    f"Reading "
                    f"{path.name}"
                )

                page_players = (
                    parse_page(path)
                )
                cache_hit = False
            else:
                (
                    page_players,
                    cache_hit,
                ) = parse_page_cached(
                    path,
                    parse_cache,
                )

                print(
                    (
                        "Cached "
                        if cache_hit
                        else "Reading "
                    )
                    + path.name
                )

                if cache_stats is not None:
                    key = (
                        "hits"
                        if cache_hit
                        else "misses"
                    )
                    cache_stats[key] = (
                        cache_stats.get(
                            key,
                            0,
                        )
                        + 1
                    )

            print(
                f"  Found "
                f"{len(page_players)} "
                f"players"
            )

            projection_players.update(
                page_players
            )

        print(
            f"  Unique players: "
            f"{len(projection_players)}"
        )

        for (
            player_id,
            player,
        ) in (
            projection_players
            .items()
        ):
            transient_fields = {
                "projection",
                "projection_stats",
                *GAME_FIELDS,
            }

            existing = (
                merged.setdefault(
                    player_id,
                    {
                        key: value
                        for (
                            key,
                            value,
                        )
                        in player.items()
                        if key
                        not in transient_fields
                    },
                )
            )

            existing[
                projection_name
            ] = player.get(
                "projection"
            )

            existing[
                f"{projection_name}_stats"
            ] = player.get(
                "projection_stats"
            )

            week_match = (
                re.fullmatch(
                    r"(week_\d+)_"
                    r"(projection|actual)",
                    projection_name,
                )
            )

            if week_match:
                week_prefix = (
                    week_match.group(1)
                )

                for field in (
                    GAME_FIELDS
                ):
                    value = (
                        player.get(field)
                    )

                    if (
                        value is not None
                        or f"{week_prefix}_{field}"
                        not in existing
                    ):
                        existing[
                            f"{week_prefix}_{field}"
                        ] = value

            for key in (
                "games_played",
                "bye_week",
                "preseason_rank",
                "actual_rank",
                "rostered_pct",
                "headshot_source",
            ):
                value = (
                    player.get(key)
                )

                if value is not None:
                    existing[key] = value

            if player.get(
                "status"
            ):
                existing["status"] = (
                    player["status"]
                )

            roster_status = (
                player.get(
                    "roster_status"
                )
            )

            if roster_status:
                # Ownership is maintained by the local roster layer. Yahoo's
                # roster-status field is informational only, so the newest
                # parsed snapshot is allowed to replace an older value.
                existing[
                    "roster_status"
                ] = roster_status

    return merged


def merge_player_data(
    target,
    supplement,
):
    for (
        player_id,
        player,
    ) in supplement.items():
        existing = target.get(
            player_id
        )

        if existing is None:
            target[player_id] = (
                dict(player)
            )
            continue

        for key, value in (
            player.items()
        ):
            if value is None:
                continue

            if (
                key
                == "roster_status"
                and existing.get(key)
                == MY_TEAM_NAME
                and value
                != MY_TEAM_NAME
            ):
                continue

            existing[key] = value


def write_players(
    merged,
    output_file,
):
    players = sorted(
        merged.values(),
        key=lambda item: (
            item["position"],
            item["name"],
        ),
    )

    output_file.write_text(
        json.dumps(
            players,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        f"Wrote "
        f"{len(players)} players"
    )

    print(
        f"Output: "
        f"{output_file}"
    )

    return players


def main():
    print(
        "COMBINED YAHOO PLAYER SNAPSHOT"
    )
    print(
        "============================="
    )

    player_sources = (
        discover_source_files(
            PLAYER_SOURCE_PREFIX
        )
    )

    my_team_sources = (
        discover_source_files(
            MY_TEAM_SOURCE_PREFIX
        )
    )

    sources = merge_source_maps(
        player_sources,
        my_team_sources,
    )

    if not sources:
        raise SystemExit(
            "No Yahoo player HTML files found in data/"
        )

    print()
    print("DISCOVERED YAHOO SNAPSHOTS")
    print("==========================")

    for snapshot_name in sorted(
        sources,
        key=snapshot_sort_key,
    ):
        print(
            f"{snapshot_name}: "
            f"{len(sources[snapshot_name])} "
            "file(s)"
        )

    parse_cache = (
        load_parse_cache()
    )
    cache_stats = {
        "hits": 0,
        "misses": 0,
    }

    combined = (
        merge_projection_sources(
            sources,
            parse_cache=parse_cache,
            cache_stats=cache_stats,
        )
    )

    local_roster = (
        load_season_roster(
            SEASON
        )
    )

    sync_cant_cut_from_my_team(
        my_team_sources,
        local_roster,
    )

    # Projection/stat imports never mutate roster ownership. The local roster
    # is the authority; Yahoo pages only contribute player observations.
    local_names = {
        player[
            "player_name"
        ].lower()
        for player
        in local_roster
    }

    local_dst_teams = {
        player.get("team")
        for player
        in local_roster
        if player.get(
            "position"
        )
        in {"DEF", "DST"}
    }

    def is_local_roster_player(
        player,
    ):
        return (
            player.get(
                "name",
                "",
            ).lower()
            in local_names
            or (
                player.get(
                    "position"
                )
                == "DST"
                and player.get(
                    "team"
                )
                in local_dst_teams
            )
        )

    my_team = {
        player_id: {
            **player,
            "roster_status": MY_TEAM_NAME,
        }
        for (
            player_id,
            player,
        ) in combined.items()
        if is_local_roster_player(
            player
        )
    }

    available = {
        player_id: {
            **player,
            "roster_status": (
                None
                if player.get(
                    "roster_status"
                )
                == MY_TEAM_NAME
                else player.get(
                    "roster_status"
                )
            ),
        }
        for (
            player_id,
            player,
        ) in combined.items()
        if not is_local_roster_player(
            player
        )
    }

    print()
    print("AVAILABLE PLAYERS")
    print("=================")

    write_players(
        available,
        OUTPUT_FILE,
    )

    print()
    print("MY TEAM ENRICHMENT")
    print("==================")

    write_players(
        my_team,
        MY_TEAM_OUTPUT_FILE,
    )

    print()
    print(
        f"Combined players: "
        f"{len(combined)}"
    )

    print(
        f"My team: "
        f"{len(my_team)}"
    )

    print(
        f"Available: "
        f"{len(available)}"
    )

    save_parse_cache(
        parse_cache
    )

    print()
    print("HTML PARSE CACHE")
    print("================")

    print(
        f"Reused:      "
        f"{cache_stats['hits']} file(s)"
    )

    print(
        f"Reparsed:    "
        f"{cache_stats['misses']} file(s)"
    )

    print(
        f"Cache file:  "
        f"{PARSE_CACHE_FILE}"
    )

    print()
    print(
        f"Headshots: "
        f"{HEADSHOT_DIR}"
    )


if __name__ == "__main__":
    main()

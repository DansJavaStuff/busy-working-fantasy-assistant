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

from database import load_season_roster

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

PARSE_CACHE_VERSION = 1

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


def clean_text(value):
    return " ".join(
        value.split()
    )


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
            ["th", "td"]
        )

        # Yahoo rows currently contain:
        # 0 action
        # 1 watch list
        # 2 player
        # 3 roster status
        # 4 GP
        # 5 bye
        # 6 fantasy points
        # 7 pre-season rank
        # 8 actual rank
        # 9 rostered %
        # 10+ projected/actual stats
        if len(cells) < 10:
            continue

        player_cell = cells[2]

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

        roster_status = clean_text(
            cells[3].get_text(
                " ",
                strip=True,
            )
        )

        status = extract_status(
            player_cell
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
                    cells[4].get_text(
                        strip=True,
                    )
                ),

            "bye_week":
                parse_int(
                    cells[5].get_text(
                        strip=True,
                    )
                ),

            "projection":
                parse_number(
                    cells[6].get_text(
                        strip=True,
                    )
                ),

            "preseason_rank":
                parse_int(
                    cells[7].get_text(
                        strip=True,
                    )
                ),

            "actual_rank":
                parse_int(
                    cells[8].get_text(
                        strip=True,
                    )
                ),

            "rostered_pct":
                parse_percentage(
                    cells[9].get_text(
                        strip=True,
                    )
                ),

            "headshot_source":
                extract_headshot(
                    player_cell,
                    player_id,
                ),

            "projection_stats":
                extract_offense_stats(
                    cells,
                    position,
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
                # Some Yahoo stat views can briefly disagree
                # after a transaction. If any snapshot says
                # the player is ours, do not let a stale
                # FA/waiver view overwrite that.
                if (
                    roster_status
                    == MY_TEAM_NAME
                    or existing.get(
                        "roster_status"
                    )
                    != MY_TEAM_NAME
                ):
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

    if not player_sources:
        raise SystemExit(
            "No Yahoo player-list HTML "
            "files found in data/"
        )

    print()
    print("DISCOVERED PLAYER SNAPSHOTS")
    print("===========================")

    for snapshot_name in sorted(
        player_sources,
        key=snapshot_sort_key,
    ):
        print(
            f"{snapshot_name}: "
            f"{len(player_sources[snapshot_name])} "
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
            player_sources,
            parse_cache=parse_cache,
            cache_stats=cache_stats,
        )
    )

    my_team = {
        player_id: dict(player)
        for (
            player_id,
            player,
        ) in combined.items()
        if player.get(
            "roster_status"
        )
        == MY_TEAM_NAME
    }

    my_team_sources = (
        discover_source_files(
            MY_TEAM_SOURCE_PREFIX
        )
    )

    print()
    print("MY TEAM SUPPLEMENT")
    print("==================")

    if my_team_sources:
        for snapshot_name in sorted(
            my_team_sources,
            key=snapshot_sort_key,
        ):
            print(
                f"{snapshot_name}: "
                f"{len(my_team_sources[snapshot_name])} "
                "file(s)"
            )

        supplement = (
            merge_projection_sources(
                my_team_sources,
                parse_cache=parse_cache,
                cache_stats=cache_stats,
            )
        )

        merge_player_data(
            my_team,
            supplement,
        )

    else:
        print(
            "No My Team HTML pages found; "
            "using player-list ownership "
            "data only."
        )

    local_roster = (
        load_season_roster(
            SEASON
        )
    )

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
        player_id: player
        for (
            player_id,
            player,
        ) in my_team.items()
        if is_local_roster_player(
            player
        )
    }

    available = {
        player_id: player
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

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

MY_TEAM_NAME = "Allen Wrench"


SOURCE_PATTERNS = {
    "week_1_projection": [
        "Yahoo_Player_list_week1-Proj*.html",
        "Yahoo_Player_list_K_week1-Proj.html",
        "Yahoo_Player_list_DEF_week1-Proj.html",
    ],

    "week_1_actual": [
        "Yahoo_Player_list_week1-Actual*.html",
        "Yahoo_Player_list_K_week1-Actual.html",
        "Yahoo_Player_list_DEF_week1-Actual.html",
    ],

    "week_2_projection": [
        "Yahoo_Player_list_week2-Proj*.html",
        "Yahoo_Player_list_K_week2-Proj.html",
        "Yahoo_Player_list_DEF_week2-Proj.html",
    ],

    "next_4_weeks_projection": [
        "Yahoo_Player_list_4week-Proj*.html",
        "Yahoo_Player_list_K_4week-Proj.html",
        "Yahoo_Player_list_DEF_4week-Proj.html",
    ],
}


MY_TEAM_SOURCE_PATTERNS = {
    "week_1_projection": [
        "Yahoo_MyTeam_week1-Proj.html",
        "Yahoo_MyTeam_K_week1-Proj.html",
        "Yahoo_MyTeam_DEF_week1-Proj.html",
    ],

    "week_1_actual": [
        "Yahoo_MyTeam_week1-Actual.html",
        "Yahoo_MyTeam_K_week1-Actual.html",
        "Yahoo_MyTeam_DEF_week1-Actual.html",
    ],

    "week_2_projection": [
        "Yahoo_MyTeam_week2-Proj.html",
        "Yahoo_MyTeam_K_week2-Proj.html",
        "Yahoo_MyTeam_DEF_week2-Proj.html",
    ],

    "next_4_weeks_projection": [
        "Yahoo_MyTeam_4week-Proj.html",
        "Yahoo_MyTeam_K_4week-Proj.html",
        "Yahoo_MyTeam_DEF_4week-Proj.html",
    ],
}


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


def extract_headshot(cell, player_id):
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

    source = DATA_DIR / html_relative

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
        f"player_headshots/"
        f"{destination.name}"
    )


def extract_offense_stats(cells, position):
    """
    Yahoo offense projection columns after % rostered:

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
        "pass_yards": parse_number(
            cells[10].get_text(strip=True)
        ),
        "pass_td": parse_number(
            cells[11].get_text(strip=True)
        ),
        "interceptions": parse_number(
            cells[12].get_text(strip=True)
        ),
        "rush_attempts": parse_number(
            cells[13].get_text(strip=True)
        ),
        "rush_yards": parse_number(
            cells[14].get_text(strip=True)
        ),
        "rush_td": parse_number(
            cells[15].get_text(strip=True)
        ),
        "targets": parse_number(
            cells[16].get_text(strip=True)
        ),
        "receptions": parse_number(
            cells[17].get_text(strip=True)
        ),
        "receiving_yards": parse_number(
            cells[18].get_text(strip=True)
        ),
        "receiving_td": parse_number(
            cells[19].get_text(strip=True)
        ),
        "return_td": parse_number(
            cells[20].get_text(strip=True)
        ),
        "two_point": parse_number(
            cells[21].get_text(strip=True)
        ),
        "fumbles_lost": parse_number(
            cells[22].get_text(strip=True)
        ),
    }



def extract_game_info(player_cell):
    """
    Extract Yahoo's matchup text, for example:

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
    meridiem = match.group(3).lower()
    marker = match.group(4).lower()
    opponent = match.group(5).upper()

    home_away = (
        "away"
        if marker == "@"
        else "home"
    )

    return {
        "game_display": (
            f"{day} {clock} {meridiem} "
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
        # 10+ projected stats
        if len(cells) < 10:
            continue

        player_cell = cells[2]

        name = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        team, position = (
            extract_team_position(
                player_cell
            )
        )

        game_info = extract_game_info(
            player_cell
        )

        if not name:
            continue

        if not team or not position:
            continue

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

            "game_display":
                game_info[
                    "game_display"
                ],

            "game_day":
                game_info[
                    "game_day"
                ],

            "game_time":
                game_info[
                    "game_time"
                ],

            "opponent":
                game_info[
                    "opponent"
                ],

            "home_away":
                game_info[
                    "home_away"
                ],

            "projection_stats":
                extract_offense_stats(
                    cells,
                    position,
                ),
        }

        seen.add(player_id)

    return players


def merge_projection_sources(source_patterns):
    merged = {}

    for (
        projection_name,
        patterns,
    ) in source_patterns.items():

        paths = []

        for pattern in patterns:
            paths.extend(
                DATA_DIR.glob(pattern)
            )

        paths = sorted(
            set(paths)
        )

        if not paths:
            raise SystemExit(
                f"No source files found for "
                f"{projection_name}"
            )

        projection_players = {}

        print()
        print(projection_name)
        print("-" * len(projection_name))

        for path in paths:
            print(
                f"Reading "
                f"{path.name}"
            )

            page_players = parse_page(
                path
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
        ) in projection_players.items():

            existing = merged.setdefault(
                player_id,
                {
                    key: value
                    for key, value
                    in player.items()
                    if key not in {
                        "projection",
                        "projection_stats",
                    }
                },
            )

            existing[
                projection_name
            ] = player["projection"]

            existing[
                f"{projection_name}_stats"
            ] = player.get(
                "projection_stats"
            )

            if player["status"]:
                existing["status"] = (
                    player["status"]
                )

            if player["roster_status"]:
                # Ownership can disagree between Yahoo
                # stat views after a recent transaction.
                # If any current snapshot identifies a
                # player as ours, do not let a stale
                # FA/waiver view overwrite that.
                if (
                    player["roster_status"]
                    == MY_TEAM_NAME
                    or existing.get(
                        "roster_status"
                    ) != MY_TEAM_NAME
                ):
                    existing[
                        "roster_status"
                    ] = player[
                        "roster_status"
                    ]

    return merged



def write_players(
    merged,
    output_file,
):
    players = sorted(
        merged.values(),
        key=lambda item: (
            item["position"],
            -(
                item.get(
                    "week_1_projection"
                )
                or 0
            ),
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
    print("COMBINED YAHOO PLAYER SNAPSHOT")
    print("=============================")

    combined = merge_projection_sources(
        SOURCE_PATTERNS
    )

    my_team = {
        player_id: player
        for player_id, player
        in combined.items()
        if player.get("roster_status")
        == MY_TEAM_NAME
    }

    print()
    print("MY TEAM SUPPLEMENT")
    print("==================")

    my_team_supplement = (
        merge_projection_sources(
            MY_TEAM_SOURCE_PATTERNS
        )
    )

    for (
        player_id,
        player,
    ) in my_team_supplement.items():
        existing = my_team.get(
            player_id
        )

        if existing is None:
            my_team[player_id] = player
            continue

        for key, value in player.items():
            if (
                existing.get(key) is None
                and value is not None
            ):
                existing[key] = value

    local_roster = load_season_roster(
        2026
    )

    local_names = {
        player["player_name"].lower()
        for player in local_roster
    }

    local_dst_teams = {
        player.get("team")
        for player in local_roster
        if player.get("position")
        in {"DEF", "DST"}
    }

    my_team = {
        player_id: player
        for player_id, player
        in my_team.items()
        if (
            player.get(
                "name",
                "",
            ).lower()
            in local_names
            or (
                player.get("position")
                == "DST"
                and player.get("team")
                in local_dst_teams
            )
        )
    }

    available = {
        player_id: player
        for player_id, player
        in combined.items()
        if not (
            player.get(
                "name",
                "",
            ).lower()
            in local_names
            or (
                player.get("position")
                == "DST"
                and player.get("team")
                in local_dst_teams
            )
        )
    }

    print()
    print("AVAILABLE PLAYERS")
    print("=================")

    write_players(
        available,
        OUTPUT_FILE,
    )

    my_team_output = (
        DATA_DIR
        / "yahoo_my_team.json"
    )

    print()
    print("MY TEAM ENRICHMENT")
    print("==================")

    write_players(
        my_team,
        my_team_output,
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

    print()
    print(
        f"Headshots: "
        f"{HEADSHOT_DIR}"
    )


if __name__ == "__main__":
    main()

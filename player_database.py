import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from adp import load_adp
from fantasypros import (
    load_players as load_fantasypros_players,
)
from ffc import (
    load_players as load_ffc_players,
)

DATABASE_FILE = Path("player_database.json")
PLAYER_DATA_SEASON = 2026

def normalise_name(name):
    """
    Normalise names to improve matching between data sources.

    Examples:
        De'Von Achane -> devonachane
        Amon-Ra St. Brown -> amonrastbrown
    """

    if not name:
        return ""

    name = unicodedata.normalize(
        "NFKD",
        name,
    )

    name = "".join(
        char
        for char in name
        if not unicodedata.combining(char)
    )

    return re.sub(
        r"[^a-z0-9]",
        "",
        name.lower(),
    )


SUFFIX_RE = re.compile(
    r"\b(jr|sr|ii|iii|iv)\.?\s*$",
    re.IGNORECASE,
)


def normalise_name_without_suffix(name):
    """
    Allow harmless differences such as:

        Kenneth Walker
            <-> Kenneth Walker III

        Patrick Mahomes
            <-> Patrick Mahomes II

        Brian Robinson
            <-> Brian Robinson Jr.
    """

    if not name:
        return ""

    name = SUFFIX_RE.sub(
        "",
        name,
    ).strip()

    return normalise_name(name)


# FantasyPros represents team defences using the franchise
# name, while FFC uses names such as "Denver Defense" and
# supplies the actual team code separately.
#
# Convert the FantasyPros franchise name to that team code.
DST_TEAM_CODES = {
    "arizonacardinals": "ARI",
    "atlantafalcons": "ATL",
    "baltimoreravens": "BAL",
    "buffalobills": "BUF",
    "carolinapanthers": "CAR",
    "chicagobears": "CHI",
    "cincinnatibengals": "CIN",
    "clevelandbrowns": "CLE",
    "dallascowboys": "DAL",
    "denverbroncos": "DEN",
    "detroitlions": "DET",
    "greenbaypackers": "GB",
    "houstontexans": "HOU",
    "indianapoliscolts": "IND",
    "jacksonvillejaguars": "JAX",
    "kansascitychiefs": "KC",
    "lasvegasraiders": "LV",
    "lachargers": "LAC",
    "losangeleschargers": "LAC",
    "larams": "LAR",
    "losangelesrams": "LAR",
    "miamidolphins": "MIA",
    "minnesotavikings": "MIN",
    "newenglandpatriots": "NE",
    "neworleanssaints": "NO",
    "nygiants": "NYG",
    "newyorkgiants": "NYG",
    "nyjets": "NYJ",
    "newyorkjets": "NYJ",
    "philadelphiaeagles": "PHI",
    "pittsburghsteelers": "PIT",
    "sanfrancisco49ers": "SF",
    "seattleseahawks": "SEA",
    "tampabaybuccaneers": "TB",
    "tennesseetitans": "TEN",
    "washingtoncommanders": "WAS",
}


def dst_team_code(name):
    return DST_TEAM_CODES.get(
        normalise_name(name)
    )


def ffc_identity(player):
    """
    Stable identity for tracking whether an FFC record has
    already been merged.
    """

    return (
        str(player.get("ffc_id")),
        player.get("name"),
        player.get("position"),
        player.get("team"),
    )


def add_ffc_fields(
    player,
    ffc_player,
):
    """
    Add FFC human mock-draft data to a player.
    """

    if not ffc_player:
        player.update({
            "ffc_adp": None,
            "ffc_high": None,
            "ffc_low": None,
            "ffc_stdev": None,
            "ffc_times_drafted": None,
        })
        return

    player.update({
        "ffc_adp":
            ffc_player.get("ffc_adp"),

        "ffc_high":
            ffc_player.get("ffc_high"),

        "ffc_low":
            ffc_player.get("ffc_low"),

        "ffc_stdev":
            ffc_player.get("ffc_stdev"),

        "ffc_times_drafted":
            ffc_player.get(
                "ffc_times_drafted"
            ),
    })


def ffc_position_ranks(ffc_players):
    """
    Derive a positional rank from FFC ADP.

    This is mainly useful when we need to create an FFC-only
    player who is absent from the FantasyPros ADP backbone.
    """

    ranks = {}

    positions = {
        player["position"]
        for player in ffc_players
    }

    for position in positions:
        position_players = [
            player
            for player in ffc_players
            if player["position"] == position
            and player.get("ffc_adp") is not None
        ]

        position_players.sort(
            key=lambda player:
                float(player["ffc_adp"])
        )

        for rank, player in enumerate(
            position_players,
            start=1,
        ):
            ranks[
                ffc_identity(player)
            ] = rank

    return ranks


def make_ffc_only_player(
    ffc_player,
    position_ranks,
):
    """
    Create a complete local player record when FFC contains a
    draftable player that is absent from our FantasyPros ADP
    backbone.

    Until Yahoo Fantasy API access is approved we won't have
    a Yahoo player ID or Yahoo ADP for these players.
    """

    ffc_adp = ffc_player.get(
        "ffc_adp"
    )

    if ffc_adp is None:
        adp_rank = 999
        adp = 999.0
    else:
        adp_rank = int(
            round(float(ffc_adp))
        )
        adp = float(ffc_adp)

    player = {
        "id":
            "ffc-"
            + normalise_name(
                ffc_player["name"]
            ),

        "adp_rank":
            adp_rank,

        "name":
            ffc_player["name"],

        "team":
            ffc_player.get("team"),

        "bye":
            ffc_player.get("bye"),

        "position":
            ffc_player["position"],

        "position_rank":
            position_ranks.get(
                ffc_identity(ffc_player)
            ),

        "yahoo_adp": None,
        "sleeper_adp": None,
        "rtsports_adp": None,

        # FFC becomes consensus fallback for a player that
        # FantasyPros omitted.
        "adp":
            adp,

        "yahoo_id": None,
        "fantasypros_ecr": None,
        "fantasypros_position_rank": None,
        "tier": None,
        "rank_min": None,
        "rank_max": None,
        "rank_average": None,
    }

    add_ffc_fields(
        player,
        ffc_player,
    )

    return player


def build_database():
    adp_players = load_adp()

    fp_players = (
        load_fantasypros_players()
    )

    ffc_players = (
        load_ffc_players()
    )

    fp_by_name = {
        normalise_name(
            player["name"]
        ): player
        for player in fp_players
    }

    ffc_by_name = {
        normalise_name(
            player["name"]
        ): player
        for player in ffc_players
    }

    ffc_by_suffix = {
        (
            normalise_name_without_suffix(
                player["name"]
            ),
            player["position"],
            player.get("team"),
        ): player
        for player in ffc_players
        if player["position"] != "DST"
    }

    ffc_dst_by_team = {
        player.get("team"): player
        for player in ffc_players
        if player["position"] == "DST"
    }

    position_ranks = (
        ffc_position_ranks(
            ffc_players
        )
    )

    players = []

    matched_fp = 0
    unmatched_fp = []

    matched_ffc = set()

    for adp_player in adp_players:

        key = normalise_name(
            adp_player["name"]
        )

        fp_player = fp_by_name.get(
            key
        )

        player = dict(
            adp_player
        )

        # -----------------------------------------------------
        # FantasyPros API enrichment.
        # -----------------------------------------------------

        if fp_player:
            matched_fp += 1

            player.update({
                "id":
                    fp_player["id"],

                "yahoo_id":
                    fp_player.get(
                        "yahoo_id"
                    ),

                "fantasypros_ecr":
                    fp_player.get(
                        "ecr"
                    ),

                "fantasypros_position_rank":
                    fp_player.get(
                        "position_rank"
                    ),

                "tier":
                    fp_player.get(
                        "tier"
                    ),

                "rank_min":
                    fp_player.get(
                        "rank_min"
                    ),

                "rank_max":
                    fp_player.get(
                        "rank_max"
                    ),

                "rank_average":
                    fp_player.get(
                        "rank_average"
                    ),
            })

        else:
            player["id"] = (
                "adp-"
                + normalise_name(
                    player["name"]
                )
            )

            player["yahoo_id"] = None
            player["fantasypros_ecr"] = None
            player[
                "fantasypros_position_rank"
            ] = None
            player["tier"] = None
            player["rank_min"] = None
            player["rank_max"] = None
            player["rank_average"] = None

            unmatched_fp.append(
                player["name"]
            )

        # -----------------------------------------------------
        # Fantasy Football Calculator human-mock enrichment.
        # -----------------------------------------------------

        ffc_player = ffc_by_name.get(
            key
        )

        if not ffc_player:

            position = adp_player[
                "position"
            ]

            if position in (
                "DEF",
                "DST",
            ):
                team_code = (
                    dst_team_code(
                        adp_player["name"]
                    )
                )

                if team_code:
                    ffc_player = (
                        ffc_dst_by_team.get(
                            team_code
                        )
                    )

            else:
                suffix_key = (
                    normalise_name_without_suffix(
                        adp_player["name"]
                    ),
                    position,
                    adp_player.get("team"),
                )

                ffc_player = (
                    ffc_by_suffix.get(
                        suffix_key
                    )
                )

        if ffc_player:
            matched_ffc.add(
                ffc_identity(
                    ffc_player
                )
            )

        add_ffc_fields(
            player,
            ffc_player,
        )

        players.append(
            player
        )

    # ---------------------------------------------------------
    # FFC players absent from FantasyPros ADP.
    #
    # We retain them so a valid late Yahoo selection doesn't
    # make our local draft impossible to keep in sync.
    # ---------------------------------------------------------

    ffc_only = [
        player
        for player in ffc_players
        if ffc_identity(player)
        not in matched_ffc
    ]

    for ffc_player in ffc_only:
        players.append(
            make_ffc_only_player(
                ffc_player,
                position_ranks,
            )
        )

    # Keep one stable overall ordering.
    players.sort(
        key=lambda player:
            float(
                player.get(
                    "adp",
                    999,
                )
            )
    )

    database = {
        "season":
            PLAYER_DATA_SEASON,

        "built_at":
            datetime.now().isoformat(),

        "count":
            len(players),

        "fantasypros_matches":
            matched_fp,

        "fantasypros_unmatched":
            len(unmatched_fp),

        "ffc_merged":
            len(matched_ffc),

        "ffc_only":
            len(ffc_only),

        "ffc_total":
            len(ffc_players),

        "players":
            players,
    }

    DATABASE_FILE.write_text(
        json.dumps(
            database,
            indent=2,
        )
    )

    print()
    print(
        f"Total players: "
        f"{len(players)}"
    )

    print(
        f"FantasyPros matches: "
        f"{matched_fp}"
    )

    print(
        f"FantasyPros unmatched: "
        f"{len(unmatched_fp)}"
    )

    print()

    print(
        f"FFC merged: "
        f"{len(matched_ffc)}"
    )

    print(
        f"FFC-only added: "
        f"{len(ffc_only)}"
    )

    print(
        f"FFC coverage: "
        f"{len(matched_ffc) + len(ffc_only)}"
        f"/{len(ffc_players)}"
    )

    if ffc_only:
        print()
        print("FFC-only players:")

        for player in ffc_only:
            print(
                " ",
                player["position"],
                player["name"],
                player.get("team") or "-",
            )

    if unmatched_fp:
        print()
        print(
            "First 20 FantasyPros "
            "API-unmatched:"
        )

        for name in unmatched_fp[:20]:
            print(
                " ",
                name,
            )

    return database


def load_players():
    if not DATABASE_FILE.exists():
        build_database()

    data = json.loads(
        DATABASE_FILE.read_text()
    )

    return data["players"]


if __name__ == "__main__":
    build_database()

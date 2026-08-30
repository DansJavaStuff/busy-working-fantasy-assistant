import json
from datetime import datetime, timedelta

from adp import ADP_FILE
from fantasypros import (
    CACHE_FILE as FANTASYPROS_CACHE_FILE,
)
from fantasypros_rankings import (
    POSITION_FILES as FANTASYPROS_RANKING_FILES,
)
from ffc import (
    CACHE_FILE as FFC_CACHE_FILE,
)
from player_database import (
    DATABASE_FILE,
    PLAYER_DATA_SEASON,
)


FANTASYPROS_MAX_AGE = timedelta(days=7)
FANTASYPROS_RANKINGS_MAX_AGE = timedelta(days=7)
ADP_MAX_AGE = timedelta(days=7)
FFC_MAX_AGE = timedelta(hours=6)


def _load_json(path):
    if not path.exists():
        return {}

    try:
        return json.loads(
            path.read_text()
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}


def _modified(path):
    if not path.exists():
        return None

    return datetime.fromtimestamp(
        path.stat().st_mtime
    )


def _parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value
        )
    except ValueError:
        return None


def _display_time(value):
    if value is None:
        return "Missing"

    return value.strftime(
        "%Y-%m-%d %H:%M"
    )


def _freshness(updated, max_age):
    if updated is None:
        return "missing"

    if datetime.now() - updated <= max_age:
        return "fresh"

    return "stale"


def get_data_status():
    fp_cache = _load_json(
        FANTASYPROS_CACHE_FILE
    )

    ffc_cache = _load_json(
        FFC_CACHE_FILE
    )

    player_database = _load_json(
        DATABASE_FILE
    )

    fp_updated = (
        _parse_datetime(
            fp_cache.get("updated")
        )
        or _modified(
            FANTASYPROS_CACHE_FILE
        )
    )

    adp_updated = _modified(
        ADP_FILE
    )

    ranking_files = list(
        FANTASYPROS_RANKING_FILES.values()
    )

    ranking_times = [
        _modified(path)
        for path in ranking_files
    ]

    ranking_missing = [
        path
        for path, updated in zip(
            ranking_files,
            ranking_times,
        )
        if updated is None
    ]

    if ranking_missing:
        rankings_updated = None
        rankings_status = "missing"
    else:
        # Show/check the oldest file because all six
        # positional ranking files need to be current.
        rankings_updated = min(
            ranking_times
        )

        rankings_status = (
            "fresh"
            if all(
                _freshness(
                    updated,
                    FANTASYPROS_RANKINGS_MAX_AGE,
                ) == "fresh"
                for updated in ranking_times
            )
            else "stale"
        )

    ffc_updated = _modified(
        FFC_CACHE_FILE
    )

    database_built = (
        _parse_datetime(
            player_database.get(
                "built_at"
            )
        )
        or _modified(
            DATABASE_FILE
        )
    )

    fp_status = _freshness(
        fp_updated,
        FANTASYPROS_MAX_AGE,
    )

    adp_status = _freshness(
        adp_updated,
        ADP_MAX_AGE,
    )

    ffc_status = _freshness(
        ffc_updated,
        FFC_MAX_AGE,
    )

    source_times = [
        value
        for value in (
            fp_updated,
            adp_updated,
            ffc_updated,
            *ranking_times,
        )
        if value is not None
    ]

    needs_rebuild = (
        database_built is None
        or any(
            updated > database_built
            for updated in source_times
        )
    )

    if database_built is None:
        database_status = "missing"
    elif needs_rebuild:
        database_status = "stale"
    else:
        database_status = "current"

    ffc_meta = ffc_cache.get(
        "meta",
        {},
    )

    sources = [
        {
            "key": "fantasypros",
            "label": "FantasyPros API",
            "status": fp_status,
            "updated": _display_time(
                fp_updated
            ),
            "detail": (
                f"{len(fp_cache.get('players', []))} "
                "players"
            ),
        },
        {
            "key": "adp",
            "label": "FantasyPros Overall ADP",
            "status": adp_status,
            "updated": _display_time(
                adp_updated
            ),
            "detail": ADP_FILE.name,
        },
        {
            "key": "fantasypros_rankings",
            "label": "FantasyPros Positional Rankings",
            "status": rankings_status,
            "updated": _display_time(
                rankings_updated
            ),
            "detail": (
                f"{len(ranking_files) - len(ranking_missing)}"
                f"/{len(ranking_files)} files · "
                f"{player_database.get('fantasypros_rankings_total', 0)} "
                "rankings"
            ),
        },
        {
            "key": "ffc",
            "label": (
                "Fantasy Football Calculator"
            ),
            "status": ffc_status,
            "updated": _display_time(
                ffc_updated
            ),
            "detail": (
                f"{ffc_meta.get('total_drafts', 0)} "
                "drafts · "
                f"{ffc_meta.get('start_date', '?')} "
                "to "
                f"{ffc_meta.get('end_date', '?')}"
            ),
        },
    ]

    ready = (
        all(
            source["status"] == "fresh"
            for source in sources
        )
        and database_status == "current"
    )

    return {
        "ready": ready,
        "season": player_database.get(
            "season",
            PLAYER_DATA_SEASON,
        ),
        "sources": sources,
        "database": {
            "status": database_status,
            "built_at": _display_time(
                database_built
            ),
            "players": player_database.get(
                "count",
                0,
            ),
        },
    }


def print_status():
    status = get_data_status()

    print(
        "Player data:",
        (
            "READY"
            if status["ready"]
            else "NEEDS REFRESH"
        ),
    )

    print()

    for source in status["sources"]:
        print(
            f'{source["label"]}: '
            f'{source["status"].upper()}'
        )
        print(
            "  Updated:",
            source["updated"],
        )
        print(
            "  Detail:",
            source["detail"],
        )

    print()

    database = status["database"]

    print(
        "Merged player database:",
        database["status"].upper(),
    )

    print(
        "  Built:",
        database["built_at"],
    )

    print(
        "  Players:",
        database["players"],
    )


if __name__ == "__main__":
    print_status()

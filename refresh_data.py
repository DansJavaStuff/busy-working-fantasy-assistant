from data_status import (
    get_data_status,
    print_status,
)
from fantasypros import refresh_cache
from ffc import load_data as load_ffc_data
from player_database import build_database


def refresh_all():
    print()
    print(
        "=== Refreshing FantasyPros API ==="
    )

    refresh_cache()

    print()
    print(
        "=== Refreshing FFC mock data ==="
    )

    load_ffc_data(
        force_refresh=True
    )

    print()
    print(
        "=== Rebuilding player database ==="
    )

    build_database()

    print()
    print(
        "=== Final data status ==="
    )

    print_status()

    print()
    print(
        "NOTE: FantasyPros Overall ADP CSV "
        "must still be updated manually."
    )

    return get_data_status()

if __name__ == "__main__":
    refresh_all()

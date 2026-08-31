from data_status import (
    get_data_status,
    print_status,
)
from fantasypros import refresh_cache
from ffc import load_data as load_ffc_data
from player_database import build_database


def rebuild_database():
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

    return get_data_status()


def refresh_ffc():
    print()
    print(
        "=== Refreshing FFC mock data ==="
    )

    load_ffc_data(
        force_refresh=True
    )

    return rebuild_database()


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

    return rebuild_database()


if __name__ == "__main__":
    refresh_all()

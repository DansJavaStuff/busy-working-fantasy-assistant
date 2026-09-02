import json
import sqlite3
import subprocess
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from data_status import get_data_status
from fantasypros import get_api_usage


BASE_DIR = Path(__file__).resolve().parents[1]
DB_FILE = BASE_DIR / "fantasy_assistant.db"
BACKUP_DIR = BASE_DIR / "backups"

HEALTH_URL = "http://127.0.0.1:8080/health"

EXPECTED_SEASON = 2026
EXPECTED_TEAMS = 12
EXPECTED_SLOT = 8


def check_git():
    try:
        result = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        clean = not result.stdout.strip()

        return {
            "ok": clean,
            "detail": (
                "clean"
                if clean
                else "uncommitted changes"
            ),
        }

    except Exception as exc:
        return {
            "ok": False,
            "detail": str(exc),
        }


def check_health():
    try:
        with urlopen(
            HEALTH_URL,
            timeout=5,
        ) as response:
            body = json.loads(
                response.read().decode("utf-8")
            )

        ok = (
            response.status == 200
            and body.get("status") == "ok"
        )

        return {
            "ok": ok,
            "detail": (
                "healthy"
                if ok
                else f"unexpected response: {body}"
            ),
        }

    except (
        URLError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return {
            "ok": False,
            "detail": str(exc),
        }


def load_draft():
    if not DB_FILE.exists():
        return None

    connection = sqlite3.connect(
        f"file:{DB_FILE}?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    try:
        row = connection.execute(
            """
            SELECT
                s.season,
                ds.session_type,
                ds.teams,
                ds.your_slot,
                ds.current_pick
            FROM draft_sessions ds
            JOIN seasons s
              ON s.id = ds.season_id
            WHERE ds.is_active = 1
            """
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def latest_backup():
    if not BACKUP_DIR.exists():
        return None

    backups = sorted(
        BACKUP_DIR.glob(
            "fantasy_assistant_*.db"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not backups:
        return None

    return backups[0]


def show(label, ok, detail):
    marker = "OK" if ok else "CHECK"

    print(
        f"{label:<26}"
        f"{marker:<8}"
        f"{detail}"
    )


def main():
    print(
        "Busy Working — Pre-Draft Check"
    )
    print("=" * 49)
    print()

    results = []

    git = check_git()
    show(
        "Git working tree",
        git["ok"],
        git["detail"],
    )
    results.append(git["ok"])

    health = check_health()
    show(
        "Application health",
        health["ok"],
        health["detail"],
    )
    results.append(health["ok"])

    player_data = get_data_status()

    data_ok = player_data["ready"]

    show(
        "Player data",
        data_ok,
        (
            "READY"
            if data_ok
            else "NEEDS REFRESH"
        ),
    )
    results.append(data_ok)

    draft = load_draft()

    if draft is None:
        show(
            "Active draft",
            False,
            "not found",
        )

        results.append(False)

    else:
        season_ok = (
            draft["season"]
            == EXPECTED_SEASON
        )

        show(
            "Season",
            season_ok,
            str(draft["season"]),
        )
        results.append(season_ok)

        teams_ok = (
            draft["teams"]
            == EXPECTED_TEAMS
        )

        show(
            "League size",
            teams_ok,
            f'{draft["teams"]} teams',
        )
        results.append(teams_ok)

        slot_ok = (
            draft["your_slot"]
            == EXPECTED_SLOT
        )

        show(
            "Your draft slot",
            slot_ok,
            f'pick {draft["your_slot"]}',
        )
        results.append(slot_ok)

        mode_ok = (
            draft["session_type"]
            == "mock"
        )

        show(
            "Draft mode",
            mode_ok,
            draft["session_type"].upper(),
        )
        results.append(mode_ok)

        pick_ok = (
            draft["current_pick"]
            == 1
        )

        show(
            "Current pick",
            pick_ok,
            str(draft["current_pick"]),
        )
        results.append(pick_ok)

    usage = get_api_usage()

    allowance_ok = usage["can_refresh"]

    show(
        "FantasyPros allowance",
        allowance_ok,
        (
            f'{usage["remaining"]} remaining '
            f'· full refresh needs '
            f'{usage["refresh_calls"]}'
        ),
    )
    results.append(allowance_ok)

    backup = latest_backup()

    backup_ok = (
        backup is not None
        and backup.stat().st_size > 0
    )

    show(
        "Backup directory",
        backup_ok,
        (
            backup.name
            if backup
            else "no backups found"
        ),
    )
    results.append(backup_ok)

    print()
    print("=" * 49)

    if all(results):
        print(
            "DRAFT NIGHT: READY"
        )
        return 0

    print(
        "DRAFT NIGHT: CHECK ITEMS ABOVE"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

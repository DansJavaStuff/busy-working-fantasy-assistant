from pathlib import Path
import argparse
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import import_yahoo_players as importer
from tools.html_fallback_import import classify_snapshot


NORMALIZED_FILE = importer.DATA_DIR / "yahoo_normalized.json"


def parsed_player(path, player_name):
    players = importer.parse_page(path)
    target = player_name.strip().lower()

    for player in players.values():
        if (player.get("name") or "").strip().lower() == target:
            return player

    return None


def normalized_player(player_name, week):
    if not NORMALIZED_FILE.exists():
        return None

    dataset = json.loads(NORMALIZED_FILE.read_text(encoding="utf-8"))
    target = player_name.strip().lower()

    for player in dataset.get("players", {}).values():
        if (player.get("name") or "").strip().lower() == target:
            week_data = player.get("weeks", {}).get(str(week), {})
            return {
                "projection": week_data.get("projection"),
                "actual": week_data.get("actual"),
                "game": week_data.get("game"),
                "next_4_weeks_projection": player.get("next_4_weeks_projection"),
            }

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Show how saved Yahoo HTML is parsed for one player/week."
    )
    parser.add_argument("player", nargs="?", default="Josh Allen")
    parser.add_argument("--week", type=int, default=2)
    args = parser.parse_args()

    wanted = f"week_{args.week}_projection"

    print(f"Yahoo import diagnostic · {args.player} · Week {args.week}")
    print()

    patterns = [
        "Yahoo_MyTeam_*.html",
        "Yahoo_Player_list_*.html",
    ]

    matched_any = False

    for pattern in patterns:
        for path in sorted(importer.DATA_DIR.glob(pattern)):
            prefix = (
                importer.MY_TEAM_SOURCE_PREFIX
                if path.name.startswith(importer.MY_TEAM_SOURCE_PREFIX)
                else importer.PLAYER_SOURCE_PREFIX
            )
            classification = classify_snapshot(path, prefix)
            snapshot = classification.get("snapshot_name")

            if snapshot not in {wanted, "next_4_weeks_projection"}:
                continue

            player = parsed_player(path, args.player)
            if player is None:
                continue

            matched_any = True
            print(path.name)
            print(f"  classified: {snapshot} ({classification.get('source')})")
            metadata = classification.get("metadata") or {}
            print(f"  selected label: {metadata.get('selected_label')}")
            print(f"  projection column parsed: {player.get('projection')}")
            print(f"  game: {player.get('game_display')}")
            print()

    if not matched_any:
        print("No matching parsed rows found in saved HTML.")
        print()

    print("Normalized dataset:")
    print(json.dumps(normalized_player(args.player, args.week), indent=2))


if __name__ == "__main__":
    main()

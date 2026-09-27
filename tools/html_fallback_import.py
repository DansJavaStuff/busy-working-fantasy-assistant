from pathlib import Path
import json
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import import_yahoo_players as importer
from tools.yahoo_html_metadata import inspect_path
from yahoo_normalizer import (
    build_dataset,
    preserve_locked_projections,
)
from database import (
    replace_week_lineup,
    upsert_player_week_history,
)


NORMALIZED_OUTPUT_FILE = (
    importer.DATA_DIR
    / "yahoo_normalized.json"
)


def classify_snapshot(path, prefix):
    """Classify a saved Yahoo page, preferring Yahoo's own metadata.

    The saved filename is deliberately only a fallback.  This keeps the
    emergency HTML path forgiving: useful Yahoo pages do not need to be
    renamed to one of our September 2026 conventions before importing.
    """
    metadata = inspect_path(path)
    html_snapshot = metadata.get("snapshot_name")

    filename_snapshot = importer.snapshot_name_from_filename(
        path,
        prefix,
    )

    if html_snapshot:
        return {
            "snapshot_name": html_snapshot,
            "source": "html",
            "metadata": metadata,
            "filename_snapshot": filename_snapshot,
            "metadata_mismatch": (
                filename_snapshot is not None
                and filename_snapshot != html_snapshot
            ),
        }

    if filename_snapshot:
        return {
            "snapshot_name": filename_snapshot,
            "source": "filename_fallback",
            "metadata": metadata,
            "filename_snapshot": filename_snapshot,
            "metadata_mismatch": False,
        }

    return {
        "snapshot_name": None,
        "source": "unknown",
        "metadata": metadata,
        "filename_snapshot": filename_snapshot,
        "metadata_mismatch": False,
    }


def discover_source_files(prefix):
    discovered = {}
    diagnostics = {
        "html": 0,
        "filename_fallback": 0,
        "unknown": 0,
        "unknown_files": [],
        "classification_reused": 0,
        "classification_read": 0,
        "metadata_mismatches": [],
    }
    store = importer.load_parse_cache()
    files = store.setdefault("files", {})

    for path in sorted(
        importer.DATA_DIR.glob(f"{prefix}*.html")
    ):
        signature = importer.file_signature(path)
        entry = files.get(path.name) or {}

        if (
            entry.get("size") == signature["size"]
            and entry.get("mtime_ns") == signature["mtime_ns"]
            and isinstance(
                entry.get("classification"),
                dict,
            )
        ):
            result = entry["classification"]
            diagnostics["classification_reused"] += 1
        else:
            result = classify_snapshot(path, prefix)
            diagnostics["classification_read"] += 1

            # A changed file invalidates the old parsed rows.  Keep only the
            # fresh signature/classification; the player parser will rebuild
            # the rows later in this same import.
            files[path.name] = {
                **signature,
                "classification": result,
            }

        source = result["source"]
        snapshot_name = result["snapshot_name"]

        diagnostics[source] += 1

        if result.get("metadata_mismatch"):
            diagnostics["metadata_mismatches"].append(
                {
                    "filename": path.name,
                    "filename_snapshot": result.get(
                        "filename_snapshot"
                    ),
                    "html_snapshot": snapshot_name,
                }
            )

        if snapshot_name is None:
            diagnostics["unknown_files"].append(path.name)
            continue

        discovered.setdefault(snapshot_name, []).append(path)

    importer.save_parse_cache(store)

    # The legacy merger applies files in list order and later rows win.
    # Browsers often save a newly-downloaded Yahoo page as "... (1).html";
    # filename sorting can therefore put the older base file last and make a
    # refresh appear stale.  Sort each snapshot oldest -> newest by mtime so
    # the most recently downloaded page is authoritative.
    for paths in discovered.values():
        paths.sort(
            key=lambda path: (
                path.stat().st_mtime_ns,
                path.name,
            )
        )

    return discovered, diagnostics


def print_diagnostics(label, diagnostics):
    print()
    print(label)
    print("=" * len(label))
    print(
        "Yahoo HTML metadata: "
        f"{diagnostics['html']} file(s)"
    )
    print(
        "Filename fallback:   "
        f"{diagnostics['filename_fallback']} file(s)"
    )
    print(
        "Unclassified:        "
        f"{diagnostics['unknown']} file(s)"
    )
    print(
        "Metadata reused:     "
        f"{diagnostics['classification_reused']} file(s)"
    )
    print(
        "Metadata read:       "
        f"{diagnostics['classification_read']} file(s)"
    )

    for filename in diagnostics["unknown_files"]:
        print(f"  WARNING: could not classify {filename}")

    for item in diagnostics["metadata_mismatches"]:
        print(
            "  WARNING: filename/HTML mismatch: "
            f"{item['filename']} looks like "
            f"{item['filename_snapshot']} by filename, "
            f"but Yahoo metadata says {item['html_snapshot']}."
        )


def html_first_discovery(prefix):
    discovered, diagnostics = discover_source_files(prefix)

    label = (
        "PLAYER-LIST CLASSIFICATION"
        if prefix == importer.PLAYER_SOURCE_PREFIX
        else "MY TEAM CLASSIFICATION"
    )
    print_diagnostics(label, diagnostics)

    return discovered


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_normalized_dataset():
    previous_dataset = None

    if NORMALIZED_OUTPUT_FILE.exists():
        previous_dataset = load_json(
            NORMALIZED_OUTPUT_FILE
        )

    roster = load_json(
        importer.MY_TEAM_OUTPUT_FILE
    )
    available = load_json(
        importer.OUTPUT_FILE
    )

    dataset = build_dataset(
        roster,
        available,
        source="manual_html",
    )

    if previous_dataset:
        dataset = preserve_locked_projections(
            previous_dataset,
            dataset,
        )

    NORMALIZED_OUTPUT_FILE.write_text(
        json.dumps(
            dataset,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    history_rows = upsert_player_week_history(
        dataset.get(
            "players",
            {},
        ),
        season=2026,
        source="manual_html",
    )

    week_numbers = sorted(
        {
            int(week)
            for player in dataset[
                "players"
            ].values()
            for week in player.get(
                "weeks",
                {},
            )
        }
    )

    print()
    print("NORMALIZED YAHOO DATASET")
    print("========================")
    print(
        f"Players:    "
        f"{len(dataset['players'])}"
    )
    print(
        f"My Team:    "
        f"{len(dataset['my_team_ids'])}"
    )
    print(
        f"Available:  "
        f"{len(dataset['available_ids'])}"
    )
    print(
        "Weeks:      "
        + (
            ", ".join(
                str(week)
                for week in week_numbers
            )
            if week_numbers
            else "none"
        )
    )
    print(
        f"Output:     "
        f"{NORMALIZED_OUTPUT_FILE}"
    )
    print(
        f"History:    "
        f"{history_rows} player/week row(s) persisted"
    )

    return dataset


def persist_submitted_lineups():
    """Persist Yahoo's actual submitted lineup from saved My Team pages."""

    sources, _ = discover_source_files(
        importer.MY_TEAM_SOURCE_PREFIX
    )

    total_rows = 0

    for snapshot_name, paths in sorted(
        sources.items()
    ):
        match = re.fullmatch(
            r"week_(\d+)_actual",
            snapshot_name,
        )

        if not match:
            continue

        week = int(
            match.group(1)
        )

        players = {}

        for path in paths:
            page_players = (
                importer
                .parse_my_team_lineup_page(
                    path
                )
            )

            players.update(
                page_players
            )

        if not players:
            print(
                f"Lineup Week {week}: "
                "no submitted slots parsed"
            )
            continue

        rows = list(
            players.values()
        )

        replace_week_lineup(
            week,
            rows,
            season=2026,
            source="yahoo_my_team_actual",
        )

        total_rows += len(
            rows
        )

        print(
            f"Lineup Week {week}: "
            f"{len(rows)} submitted slot(s) persisted"
        )

    if total_rows:
        print(
            f"Submitted lineup history: "
            f"{total_rows} row(s) persisted"
        )

    return total_rows


def main():
    # Reuse the already-tested row parser/merger/output path, replacing only
    # source discovery.  Legacy JSON outputs are retained temporarily while
    # Weekly/Transactions migrate to the common normalized weeks{} model.
    importer.discover_source_files = html_first_discovery
    importer.main()
    write_normalized_dataset()
    persist_submitted_lineups()


if __name__ == "__main__":
    main()

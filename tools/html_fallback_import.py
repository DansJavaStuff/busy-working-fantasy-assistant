from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import import_yahoo_players as importer
from tools.yahoo_html_metadata import inspect_path
from yahoo_normalizer import build_dataset


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

    if html_snapshot:
        return {
            "snapshot_name": html_snapshot,
            "source": "html",
            "metadata": metadata,
        }

    filename_snapshot = importer.snapshot_name_from_filename(
        path,
        prefix,
    )

    if filename_snapshot:
        return {
            "snapshot_name": filename_snapshot,
            "source": "filename_fallback",
            "metadata": metadata,
        }

    return {
        "snapshot_name": None,
        "source": "unknown",
        "metadata": metadata,
    }


def discover_source_files(prefix):
    discovered = {}
    diagnostics = {
        "html": 0,
        "filename_fallback": 0,
        "unknown": 0,
        "unknown_files": [],
    }

    for path in sorted(
        importer.DATA_DIR.glob(f"{prefix}*.html")
    ):
        result = classify_snapshot(path, prefix)
        source = result["source"]
        snapshot_name = result["snapshot_name"]

        diagnostics[source] += 1

        if snapshot_name is None:
            diagnostics["unknown_files"].append(path.name)
            continue

        discovered.setdefault(snapshot_name, []).append(path)

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

    for filename in diagnostics["unknown_files"]:
        print(f"  WARNING: could not classify {filename}")


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

    NORMALIZED_OUTPUT_FILE.write_text(
        json.dumps(
            dataset,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
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

    return dataset


def main():
    # Reuse the already-tested row parser/merger/output path, replacing only
    # source discovery.  Legacy JSON outputs are retained temporarily while
    # Weekly/Transactions migrate to the common normalized weeks{} model.
    importer.discover_source_files = html_first_discovery
    importer.main()
    write_normalized_dataset()


if __name__ == "__main__":
    main()

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.import_yahoo_players import (
    MY_TEAM_SOURCE_PREFIX,
    PLAYER_SOURCE_PREFIX,
    snapshot_name_from_filename,
)
from tools.yahoo_html_metadata import inspect_path


DATA_DIR = PROJECT_ROOT / "data"


def filename_classification(path):
    for prefix in (
        PLAYER_SOURCE_PREFIX,
        MY_TEAM_SOURCE_PREFIX,
    ):
        result = snapshot_name_from_filename(
            path,
            prefix,
        )
        if result:
            return result
    return None


def main():
    paths = sorted(DATA_DIR.glob("Yahoo_*.html"))

    if not paths:
        raise SystemExit(
            "No Yahoo_*.html files found in data/"
        )

    print("YAHOO HTML METADATA INVENTORY")
    print("=============================")
    print(f"Files found: {len(paths)}")

    matched = 0
    disagreements = 0
    unknown = 0

    for path in paths:
        meta = inspect_path(path)
        html_class = meta["snapshot_name"]
        file_class = filename_classification(path)

        if html_class and html_class == file_class:
            status = "MATCH"
            matched += 1
        elif html_class and file_class:
            status = "DIFF"
            disagreements += 1
        else:
            status = "UNKNOWN"
            unknown += 1

        print()
        print(path.name)
        print(f"  status:    {status}")
        print(f"  html:      {html_class}")
        print(f"  filename:  {file_class}")
        print(
            "  selected:  "
            f"{meta['selected_value']!r} / "
            f"{meta['selected_label']!r}"
        )
        print(f"  stat1:     {meta['stat1']!r}")
        print(f"  fteam:     {meta['fteam']!r}")
        print(f"  myteam:    {meta['myteam']!r}")

    print()
    print("SUMMARY")
    print("=======")
    print(f"HTML agrees with filename: {matched}")
    print(f"HTML/filename disagreements: {disagreements}")
    print(f"Unclassified/partial: {unknown}")

    if disagreements:
        print()
        print(
            "Do not switch the importer to HTML-first "
            "classification until the DIFF entries are "
            "understood."
        )


if __name__ == "__main__":
    main()

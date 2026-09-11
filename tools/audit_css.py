from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CSS_FILE = (
    PROJECT_ROOT
    / "static"
    / "style.css"
)

SOURCE_SUFFIXES = {
    ".html",
    ".py",
    ".js",
}

IGNORED_DIRS = {
    ".git",
    "venv",
    "__pycache__",
    "data",
    "backups",
}

CLASS_RE = re.compile(
    r"(?<![\w-])\.([A-Za-z_][\w-]*)"
)

ID_RE = re.compile(
    r"(?<![\w-])#([A-Za-z_][\w-]*)"
)

HTML_CLASS_RE = re.compile(
    r'''class\s*=\s*["']([^"']+)["']''',
    re.IGNORECASE,
)

HTML_ID_RE = re.compile(
    r'''id\s*=\s*["']([^"']+)["']''',
    re.IGNORECASE,
)

# A leaf rule has no nested braces in its body.
# That means this safely sees ordinary CSS rules
# inside or outside @media blocks without trying
# to remove the @media wrapper itself.
LEAF_RULE_RE = re.compile(
    r"([^{}]+)\{([^{}]*)\}",
    re.MULTILINE,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Audit style.css against project source "
            "files."
        )
    )

    parser.add_argument(
        "--delete-unused",
        action="store_true",
        help=(
            "Show CSS rules that can be "
            "conservatively removed."
        ),
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Actually modify style.css. "
            "Requires --delete-unused."
        ),
    )

    return parser.parse_args()


def source_files():
    files = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(
            PROJECT_ROOT
        )

        if any(
            part in IGNORED_DIRS
            for part in relative.parts
        ):
            continue

        if path == CSS_FILE:
            continue

        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue

        files.append(path)

    return sorted(files)


def read_sources(paths):
    chunks = []

    for path in paths:
        try:
            chunks.append(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
        except OSError:
            pass

    return "\n".join(chunks)


def extract_css_names(css):
    classes = set()
    ids = set()

    # Only inspect selectors. Scanning the full
    # stylesheet would mistake colour values such
    # as #fff7e6 for HTML IDs.
    for block in selector_blocks(css):
        block_classes, block_ids = (
            selector_names(
                block["selector"]
            )
        )

        classes.update(
            block_classes
        )

        ids.update(
            block_ids
        )

    return classes, ids


def extract_markup_names(text):
    classes = set()
    ids = set()

    for match in HTML_CLASS_RE.finditer(text):
        value = match.group(1)

        # Remove Jinja statements/expressions before
        # splitting the literal class attribute.
        # Otherwise:
        #
        # class="{% block main_class %}container..."
        #
        # incorrectly produces classes named
        # "block", "main_class" and "endblock".
        value = re.sub(
            r"\{\{.*?\}\}|\{%.*?%\}",
            " ",
            value,
            flags=re.DOTALL,
        )

        for token in value.split():
            if re.fullmatch(
                r"[A-Za-z_][\w-]*",
                token,
            ):
                classes.add(token)

    for match in HTML_ID_RE.finditer(text):
        value = match.group(1)

        value = re.sub(
            r"\{\{.*?\}\}|\{%.*?%\}",
            " ",
            value,
            flags=re.DOTALL,
        ).strip()

        if re.fullmatch(
            r"[A-Za-z_][\w-]*",
            value,
        ):
            ids.add(value)

    return classes, ids


def name_used(name, source_text):
    pattern = re.compile(
        r"(?<![\w-])"
        + re.escape(name)
        + r"(?![\w-])"
    )

    return bool(
        pattern.search(source_text)
    )


def normalise_selector(selector):
    selector = re.sub(
        r"/\*.*?\*/",
        "",
        selector,
        flags=re.DOTALL,
    )

    selector = " ".join(
        selector.split()
    )

    return selector.strip()


def selector_blocks(css):
    blocks = []

    for match in LEAF_RULE_RE.finditer(css):
        selector = normalise_selector(
            match.group(1)
        )

        if not selector:
            continue

        # Avoid interpreting declaration fragments
        # or at-rules as ordinary selectors.
        if selector.startswith("@"):
            continue

        blocks.append(
            {
                "selector": selector,
                "body": match.group(2),
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0),
            }
        )

    return blocks


def selector_names(selector):
    classes = set(
        CLASS_RE.findall(selector)
    )

    ids = set(
        ID_RE.findall(selector)
    )

    return classes, ids


def safe_delete_candidate(
    block,
    unused_classes,
    unused_ids,
):
    selector = block["selector"]

    classes, ids = selector_names(
        selector
    )

    names_present = bool(
        classes or ids
    )

    if not names_present:
        return False

    # A rule is only automatically removable when
    # every class/id it depends upon is unused.
    if any(
        name not in unused_classes
        for name in classes
    ):
        return False

    if any(
        name not in unused_ids
        for name in ids
    ):
        return False

    return True


def print_group(title, values):
    print()
    print(title)
    print("-" * len(title))

    if not values:
        print("None")
        return

    for value in values:
        print(f"  {value}")


def main():
    args = parse_args()

    if args.yes and not args.delete_unused:
        raise SystemExit(
            "--yes requires --delete-unused"
        )

    if not CSS_FILE.exists():
        raise SystemExit(
            f"CSS file not found: {CSS_FILE}"
        )

    css = CSS_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    files = source_files()
    source_text = read_sources(files)

    css_classes, css_ids = (
        extract_css_names(css)
    )

    markup_classes, markup_ids = (
        extract_markup_names(source_text)
    )

    unused_classes = sorted(
        name
        for name in css_classes
        if not name_used(
            name,
            source_text,
        )
    )

    unused_ids = sorted(
        name
        for name in css_ids
        if not name_used(
            name,
            source_text,
        )
    )

    missing_classes = sorted(
        markup_classes
        - css_classes
    )

    missing_ids = sorted(
        markup_ids
        - css_ids
    )

    blocks = selector_blocks(css)

    selector_counts = Counter(
        block["selector"]
        for block in blocks
    )

    duplicates = sorted(
        selector
        for selector, count
        in selector_counts.items()
        if count > 1
    )

    delete_candidates = [
        block
        for block in blocks
        if safe_delete_candidate(
            block,
            set(unused_classes),
            set(unused_ids),
        )
    ]

    print("CSS AUDIT")
    print("=========")
    print(
        f"Stylesheet: {CSS_FILE}"
    )
    print(
        f"Source files scanned: {len(files)}"
    )
    print(
        f"CSS classes defined: {len(css_classes)}"
    )
    print(
        f"CSS IDs defined: {len(css_ids)}"
    )
    print(
        f"Leaf CSS rules: {len(blocks)}"
    )

    print_group(
        "Possibly unused CSS classes",
        [
            f".{name}"
            for name in unused_classes
        ],
    )

    print_group(
        "Possibly unused CSS IDs",
        [
            f"#{name}"
            for name in unused_ids
        ],
    )

    print_group(
        "Classes used in markup/code "
        "with no CSS class rule",
        [
            f".{name}"
            for name in missing_classes
        ],
    )

    print_group(
        "IDs used in markup/code "
        "with no CSS ID rule",
        [
            f"#{name}"
            for name in missing_ids
        ],
    )

    print_group(
        "Repeated selector blocks — review only",
        [
            (
                f"{selector} "
                f"({selector_counts[selector]} times)"
            )
            for selector in duplicates
        ],
    )

    print_group(
        "Conservative delete candidates",
        [
            block["selector"]
            for block in delete_candidates
        ],
    )

    if not args.delete_unused:
        print()
        print(
            "Report only. No files changed."
        )
        print(
            "Preview deletion candidates with:"
        )
        print(
            "  python tools/audit_css.py "
            "--delete-unused"
        )
        return

    if not delete_candidates:
        print()
        print(
            "No conservative deletion "
            "candidates found."
        )
        return

    if not args.yes:
        print()
        print(
            f"Would remove "
            f"{len(delete_candidates)} rule(s)."
        )
        print(
            "No files changed."
        )
        print()
        print(
            "To apply:"
        )
        print(
            "  python tools/audit_css.py "
            "--delete-unused --yes"
        )
        return

    updated = css

    # Work backwards so recorded offsets remain
    # valid while deleting rules.
    for block in sorted(
        delete_candidates,
        key=lambda item: item["start"],
        reverse=True,
    ):
        updated = (
            updated[:block["start"]]
            + updated[block["end"]:]
        )

    CSS_FILE.write_text(
        updated,
        encoding="utf-8",
    )

    print()
    print(
        f"Removed "
        f"{len(delete_candidates)} rule(s)."
    )
    print(
        f"Updated: {CSS_FILE}"
    )
    print()
    print(
        "Review with:"
    )
    print(
        "  git diff -- static/style.css"
    )


if __name__ == "__main__":
    main()

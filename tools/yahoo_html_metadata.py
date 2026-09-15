import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


def clean_text(value):
    return " ".join((value or "").split())


def snapshot_name_from_label(label):
    """Classify Yahoo's selected stat label.

    Examples seen in saved Yahoo pages include labels such as
    ``Week 2 (proj)`` and ``Next 4 Weeks (proj)``.  A plain
    ``Week N`` label is treated as actual/scored fantasy points.

    Return None when the label is not specific enough; callers can
    then fall back to other metadata or the saved filename.
    """
    label = clean_text(label)

    if not label:
        return None

    if re.search(
        r"\bnext\s+4\s+weeks?\b",
        label,
        re.IGNORECASE,
    ):
        if re.search(
            r"\bproj(?:ected|ection)?\b|\(proj\)",
            label,
            re.IGNORECASE,
        ):
            return "next_4_weeks_projection"
        return None

    match = re.search(
        r"\bweek\s*(\d+)\b",
        label,
        re.IGNORECASE,
    )

    if not match:
        return None

    week = int(match.group(1))

    if re.search(
        r"\bproj(?:ected|ection)?\b|\(proj\)",
        label,
        re.IGNORECASE,
    ):
        return f"week_{week}_projection"

    # Yahoo's non-projection Week N view is the scored/actual view.
    return f"week_{week}_actual"


def selected_stat_option(soup):
    """Return Yahoo's selected statistics option, if present."""
    candidates = []

    for option in soup.find_all("option"):
        value = option.get("value")
        text = clean_text(option.get_text(" ", strip=True))

        if not value:
            continue

        # Yahoo stat selector values are normally S_*.
        if not str(value).startswith("S_"):
            continue

        if option.has_attr("selected"):
            return {
                "value": str(value),
                "label": text,
            }

        candidates.append(
            {
                "value": str(value),
                "label": text,
            }
        )

    # Do not guess purely because a page only happens to contain one
    # S_* option; absence of an explicit selection is useful evidence.
    return None


def canonical_metadata(soup):
    """Extract useful Yahoo query metadata from the canonical URL."""
    canonical = soup.find("link", rel="canonical")

    if canonical is None:
        return {
            "url": None,
            "stat1": None,
            "fteam": None,
            "myteam": None,
        }

    url = canonical.get("href")

    if not url:
        return {
            "url": None,
            "stat1": None,
            "fteam": None,
            "myteam": None,
        }

    params = parse_qs(urlparse(url).query)

    def first(name):
        values = params.get(name) or []
        return values[0] if values else None

    return {
        "url": url,
        "stat1": first("stat1"),
        "fteam": first("fteam"),
        "myteam": first("myteam"),
    }


def inspect_html(html):
    """Inspect one saved Yahoo HTML document without parsing players."""
    soup = BeautifulSoup(html, "html.parser")
    selected = selected_stat_option(soup)
    canonical = canonical_metadata(soup)

    snapshot_name = None
    source = None

    if selected:
        snapshot_name = snapshot_name_from_label(
            selected.get("label")
        )
        if snapshot_name:
            source = "selected_option"

    return {
        "snapshot_name": snapshot_name,
        "classification_source": source,
        "selected_value": (
            selected.get("value") if selected else None
        ),
        "selected_label": (
            selected.get("label") if selected else None
        ),
        "canonical_url": canonical["url"],
        "stat1": canonical["stat1"],
        "fteam": canonical["fteam"],
        "myteam": canonical["myteam"],
    }


def inspect_path(path):
    return inspect_html(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )

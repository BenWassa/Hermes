"""Canada-national coverage and bounded scheduled-event recall.

This module is deliberately small and deterministic. It gives the ordinary
Daily a Canada-national intake lane without creating a new visible section or
a second model call, and it protects a few known high-significance scheduled
events from being crowded out of the bounded curation input.

Official/public authority is used only to seed an event identity and date.
Journalistic coverage remains the ordinary editorial material; an event seed
never forces a story into the finished paper.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable

CANADA_COVERAGE_LANE = "canada-national"

# Keep the Perigon request count flat: this query replaces the old mixed
# US/GB/CA world query. Guardian + NYT remain the broad world inputs while
# Perigon now contributes a dedicated Canadian national lane.
CANADA_PERIGON_QUERY = {
    "label": "canada",
    "hint": "world",
    "coverage_lane": CANADA_COVERAGE_LANE,
    "params": {
        "country": ["ca"],
        "category": ["Politics", "General", "Business", "Finance"],
    },
}

# One high-signal national journalism feed complements the aggregator without
# creating publisher sprawl or additional paid quota pressure.
CANADA_RSS = [
    {
        "name": "CBC Canada",
        "url": "https://www.cbc.ca/webfeed/rss/rss-canada",
        "hint": "world",
        "coverage_lane": CANADA_COVERAGE_LANE,
    },
]

# Small deterministic reservations inside the existing CURATE_MAX_INPUT bound.
# These are ceilings, not quotas: quiet Canadian days do not manufacture filler.
CANADA_CURATE_RESERVE = 8
MAJOR_EVENT_CURATE_RESERVE = 3

# Manual, bounded seeds for exceptional scheduled national events. Entries are
# inert outside their monitor window and can be removed after the event. The
# authority URL is provenance for the schedule only; it is not fetched or sent
# to Gemini and cannot become a story by itself.
MAJOR_NEWS_EVENTS = (
    {
        "id": "canada-investment-summit-2026",
        "title": "Canada Investment Summit 2026",
        "monitor_start": "2026-09-08",
        "monitor_end": "2026-09-16",
        "authority_url": "https://www.canada.ca/en/campaign/canada-investment-summit-2026.html",
        "term_groups": (
            ("canada investment summit",),
            ("investment summit", "carney"),
            ("investment summit", "canada"),
            ("1 trillion", "investment", "canada"),
            ("$1 trillion", "canada"),
        ),
    },
)

EDITORIAL_INSTRUCTION = """

CANADA-NATIONAL EDITORIAL PRIORITY
The Daily is Toronto-based, but it must reliably cover major Canadian national
political and economic developments. A nationally consequential Canadian story
may be Front Page even when it is not narrowly local. Cross-desk developments
such as major investment, fiscal, central-bank or federal-policy news may belong
on Front Page or Business. Do not force Canadian representation on a quiet day;
importance still governs the finished paper.
"""

_SPACE_RE = re.compile(r"\s+")


def perigon_queries(base_queries: Iterable[dict]) -> list[dict]:
    """Replace the legacy mixed world query with the dedicated Canada query.

    The number of Perigon requests is intentionally unchanged. If the legacy
    query is ever removed, prepend Canada once rather than silently losing the
    national lane.
    """
    out: list[dict] = []
    replaced = False
    for query in base_queries:
        if query.get("label") == "world" and not replaced:
            out.append(dict(CANADA_PERIGON_QUERY))
            replaced = True
        else:
            out.append(query)
    if not replaced:
        out.insert(0, dict(CANADA_PERIGON_QUERY))
    return out


def _date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def active_major_events(today: dt.date) -> tuple[dict, ...]:
    """Return configured events whose bounded monitoring window includes today."""
    return tuple(
        event
        for event in MAJOR_NEWS_EVENTS
        if _date(event["monitor_start"]) <= today <= _date(event["monitor_end"])
    )


def _search_text(story: dict) -> str:
    text = f"{story.get('title', '')} {story.get('description', '')}".casefold()
    text = text.replace("c$", "$")
    return _SPACE_RE.sub(" ", text).strip()


def matching_major_event_ids(story: dict, today: dt.date) -> tuple[str, ...]:
    """Return active scheduled-event ids supported by public story metadata."""
    text = _search_text(story)
    if not text:
        return ()

    matches: list[str] = []
    for event in active_major_events(today):
        for group in event["term_groups"]:
            if all(term.casefold() in text for term in group):
                matches.append(event["id"])
                break
    return tuple(matches)


def is_canada_national(story: dict) -> bool:
    """Whether a normalized story came through the Canada-national intake lane."""
    return story.get("coverage_lane") == CANADA_COVERAGE_LANE

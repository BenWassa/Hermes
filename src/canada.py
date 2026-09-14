"""Canada-national coverage and bounded scheduled-event recall.

This module is deliberately small and deterministic. It gives the ordinary
Daily a Canada-national intake lane without creating a new visible section or
a second model call. Known high-significance scheduled events are protected
through both bounded candidate recall and a transient curation-boundary
priority marker so the editor can distinguish them from ordinary candidates.

Official/public authority is used only to seed event identity and dates.
Journalistic coverage remains the editorial material; an event seed by itself
never becomes a story.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable

CANADA_COVERAGE_LANE = "canada-national"

# Keep the Perigon request count flat. The generic markets query overlaps the
# existing Business/Finance query, so Canada replaces that lane while the broad
# world query remains intact alongside Guardian + NYT world coverage.
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

_MAJOR_EVENT_INSTRUCTION = """

ACTIVE SCHEDULED MAJOR EVENTS
Some input records may carry an `editorial_priority` field naming an active
scheduled major event that Hermes deliberately protected from candidate
crowd-out. Treat that marker as a strong editorial recall signal, not as source
content and not as permission to invent facts.

When credible current journalistic reporting carries this marker, normally
include at least one distinct treatment of that event in Front Page or the
appropriate desk. It is reasonable to omit all marked treatments only when the
reporting is clearly stale, duplicates a stronger included treatment of the
same event, is too weak to summarize safely, or the event has materially failed
to occur / ceased to be newsworthy. Do not create a story from the event seed
itself, and do not manufacture Canadian filler.
"""

_SPACE_RE = re.compile(r"\s+")


def perigon_queries(base_queries: Iterable[dict]) -> list[dict]:
    """Replace generic markets with Canada while preserving request count.

    Canada runs first so if an article also appears in a generic Business query,
    the first normalized copy carries the national-lane marker before exact
    canonical dedupe. Broad world and business coverage remain unchanged.
    """
    base = list(base_queries)
    without_markets = [query for query in base if query.get("label") != "markets"]
    if len(without_markets) == len(base):
        # Current config is expected to contain the replaceable markets lane.
        # Preserve the configured request budget rather than silently adding a
        # fourth request if that contract changes later.
        return base
    return [dict(CANADA_PERIGON_QUERY), *without_markets]


def _date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def active_major_events(today: dt.date) -> tuple[dict, ...]:
    """Return configured events whose bounded monitoring window includes today."""
    return tuple(
        event
        for event in MAJOR_NEWS_EVENTS
        if _date(event["monitor_start"]) <= today <= _date(event["monitor_end"])
    )


def _event_by_id(event_id: str) -> dict | None:
    return next((event for event in MAJOR_NEWS_EVENTS if event["id"] == event_id), None)


def _search_text(story: dict) -> str:
    # Input stories use title/description. Finished model stories use
    # headline/sub/summary. Supporting both shapes lets final-selection
    # observability recognize a stronger duplicate treatment even when it comes
    # from a different source URL.
    text = " ".join(
        str(story.get(key, "") or "")
        for key in ("title", "description", "headline", "sub", "summary")
    ).casefold()
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


def editorial_priority(story: dict, today: dt.date) -> str:
    """Transient model-only priority for a real article matching an active event."""
    titles = []
    for event_id in matching_major_event_ids(story, today):
        event = _event_by_id(event_id)
        if event:
            titles.append(event["title"])
    if not titles:
        return ""
    return "active scheduled major event: " + "; ".join(titles)


def editorial_instruction(today: dt.date) -> str:
    """Single-call editorial contract, with event pressure only while active."""
    instruction = EDITORIAL_INSTRUCTION
    if active_major_events(today):
        instruction += _MAJOR_EVENT_INSTRUCTION
    return instruction


def final_event_coverage(
    sections: list[dict], input_stories: list[dict], today: dt.date
) -> dict[str, dict]:
    """Summarize whether protected event candidates survived final selection.

    Exact input links prove survival directly. Event-text matching on final
    cards also counts a stronger duplicate treatment from another source, so
    observability never pressures the editor to publish a second redundant item.
    """
    active = active_major_events(today)
    if not active:
        return {}

    coverage: dict[str, dict] = {}
    for event in active:
        event_id = event["id"]
        matched_inputs = [
            story for story in input_stories if event_id in matching_major_event_ids(story, today)
        ]
        if not matched_inputs:
            continue
        input_links = {str(story.get("link") or "") for story in matched_inputs if story.get("link")}
        selected_sections: list[str] = []
        selected_count = 0
        for section in sections:
            for story in section.get("stories", []):
                exact = bool(story.get("link")) and str(story.get("link")) in input_links
                semantic = event_id in matching_major_event_ids(story, today)
                if exact or semantic:
                    selected_count += 1
                    label = str(section.get("id") or section.get("label") or "unknown")
                    if label not in selected_sections:
                        selected_sections.append(label)
        coverage[event_id] = {
            "title": event["title"],
            "input": len(matched_inputs),
            "selected": selected_count,
            "sections": selected_sections,
        }
    return coverage


def is_canada_national(story: dict) -> bool:
    """Whether a normalized story came through the Canada-national intake lane."""
    return story.get("coverage_lane") == CANADA_COVERAGE_LANE

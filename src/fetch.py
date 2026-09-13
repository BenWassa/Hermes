"""Task 2 (part 1) - Fetch.

Pull raw stories from the Guardian API, the NYT Top Stories API, the Perigon
News API, and bounded RSS feeds. Each source is wrapped so a failure (missing
key, dead feed, network error) logs a warning and returns an empty list rather
than crashing the run.

Each returned item is a source-native-ish dict carrying helper keys the
normalizer relies on: ``_src`` (guardian|nyt|perigon|rss), ``_section_hint``
and, for national Canadian intake, optional ``_coverage_lane``.
"""

from __future__ import annotations

import logging
import os

import feedparser
import requests

from . import canada, config

log = logging.getLogger("the-daily.fetch")

GUARDIAN_URL = "https://content.guardianapis.com/search"
NYT_URL = "https://api.nytimes.com/svc/topstories/v2/{section}.json"
PERIGON_URL = "https://api.perigon.io/v1/all"

_TIMEOUT = 20


def fetch_guardian(page_size: int = 10) -> list[dict]:
    """Guardian Content API across the configured sections."""
    key = os.environ.get("GUARDIAN_API_KEY")
    if not key:
        log.warning("GUARDIAN_API_KEY not set; skipping Guardian")
        return []

    items: list[dict] = []
    for section, hint in config.GUARDIAN_SECTIONS.items():
        try:
            resp = requests.get(
                GUARDIAN_URL,
                params={
                    "section": section,
                    "show-fields": "thumbnail,trailText,byline",
                    # Contributor tags are the Guardian's stable per-writer
                    # identity, and they ride along on the same request, so
                    # followed-Voice attribution costs nothing extra here.
                    "show-tags": "contributor",
                    "order-by": "newest",
                    "page-size": page_size,
                    "api-key": key,
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json().get("response", {}).get("results", [])
            for r in results:
                r["_src"] = "guardian"
                r["_section_hint"] = hint
            items.extend(results)
        except Exception as exc:  # graceful per-section
            log.warning("Guardian section %s failed: %s", section, exc)
    return items


def fetch_nyt() -> list[dict]:
    """NYT Top Stories API across the configured sections."""
    key = os.environ.get("NYT_API_KEY")
    if not key:
        log.warning("NYT_API_KEY not set; skipping NYT")
        return []

    items: list[dict] = []
    for section, hint in config.NYT_SECTIONS.items():
        try:
            resp = requests.get(
                NYT_URL.format(section=section),
                params={"api-key": key},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            for r in results:
                r["_src"] = "nyt"
                r["_section_hint"] = hint
            items.extend(results)
        except Exception as exc:
            log.warning("NYT section %s failed: %s", section, exc)
    return items


def fetch_perigon(size: int = 10) -> list[dict]:
    """Perigon News API across the bounded ordinary-news queries.

    The legacy mixed US/GB/CA world query is replaced at runtime by one
    dedicated Canada query, keeping the total Perigon request count unchanged.
    Guardian and NYT remain the broad world inputs while Perigon guarantees a
    small national Canadian candidate lane.
    """
    key = os.environ.get("PERIGON_API_KEY")
    if not key:
        log.warning("PERIGON_API_KEY not set; skipping Perigon")
        return []

    items: list[dict] = []
    for query in canada.perigon_queries(config.PERIGON_QUERIES):
        try:
            params: dict = {
                "apiKey": key,
                "size": size,
                "sortBy": "date",
                "language": "en",
                "showReprints": "false",
            }
            params.update(query.get("params", {}))
            resp = requests.get(PERIGON_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            results = resp.json().get("articles", [])
            for r in results:
                r["_src"] = "perigon"
                r["_section_hint"] = query["hint"]
                if query.get("coverage_lane"):
                    r["_coverage_lane"] = query["coverage_lane"]
            items.extend(results)
        except Exception as exc:  # graceful per-query
            log.warning("Perigon query %s failed: %s", query.get("label"), exc)
    return items


_RSS_HEADERS = {"User-Agent": "TheDaily/2.0 (+https://github.com/BenWassa/Hermes)"}


def _fetch_rss_feeds(
    feeds: list[dict], *, default_hint: str, default_coverage_lane: str | None = None
) -> list[dict]:
    """Fetch a bounded set of RSS feeds with shared timeout/failure behavior."""
    items: list[dict] = []
    for feed in feeds:
        try:
            resp = requests.get(feed["url"], headers=_RSS_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if parsed.bozo and not parsed.entries:
                log.warning("RSS feed %s looks dead (%s)", feed["name"], parsed.bozo_exception)
                continue
            for entry in parsed.entries:
                entry["_src"] = "rss"
                entry["_section_hint"] = feed.get("hint", default_hint)
                entry["_source_name"] = feed["name"]
                lane = feed.get("coverage_lane", default_coverage_lane)
                if lane:
                    entry["_coverage_lane"] = lane
            items.extend(parsed.entries)
        except Exception as exc:
            log.warning("RSS feed %s failed: %s", feed["name"], exc)
    return items


def fetch_canada_rss() -> list[dict]:
    """High-signal national Canadian journalism, independent of Toronto-local RSS."""
    return _fetch_rss_feeds(
        canada.CANADA_RSS,
        default_hint="world",
        default_coverage_lane=canada.CANADA_COVERAGE_LANE,
    )


def fetch_toronto_rss() -> list[dict]:
    """Toronto local RSS feeds; failures remain local to the affected feed."""
    return _fetch_rss_feeds(config.TORONTO_RSS, default_hint="toronto")


def fetch_all() -> list[dict]:
    """All ordinary-news sources concatenated into one raw list."""
    return (
        fetch_guardian()
        + fetch_nyt()
        + fetch_perigon()
        + fetch_canada_rss()
        + fetch_toronto_rss()
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from .normalize import normalize

    raw = fetch_all()
    stories = normalize(raw)

    breakdown: dict[str, int] = {}
    for s in stories:
        breakdown[s["source"]] = breakdown.get(s["source"], 0) + 1

    print(f"Normalized stories: {len(stories)}")
    for src, n in sorted(breakdown.items()):
        print(f"  {src}: {n}")

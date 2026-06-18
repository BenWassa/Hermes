"""Task 2 (part 1) - Fetch.

Pull raw stories from the Guardian API, the NYT Top Stories API, and Toronto
RSS feeds. Each source is wrapped so a failure (missing key, dead feed, network
error) logs a warning and returns an empty list rather than crashing the run.

Each returned item is a source-native-ish dict carrying two helper keys the
normalizer relies on: ``_src`` (guardian|nyt|rss) and ``_section_hint``.
"""

from __future__ import annotations

import logging
import os

import feedparser
import requests

from . import config

log = logging.getLogger("the-daily.fetch")

GUARDIAN_URL = "https://content.guardianapis.com/search"
NYT_URL = "https://api.nytimes.com/svc/topstories/v2/{section}.json"

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


_RSS_HEADERS = {"User-Agent": "TheDaily/2.0 (+https://github.com/BenWassa/Hermes)"}


def fetch_toronto_rss() -> list[dict]:
    """Toronto local RSS feeds. A dead feed is skipped with a warning.

    The feed bytes are fetched with ``requests`` (with a timeout) and handed to
    feedparser, because ``feedparser.parse(url)`` has no timeout and can hang on
    a slow or unreachable host.
    """
    items: list[dict] = []
    for feed in config.TORONTO_RSS:
        try:
            resp = requests.get(feed["url"], headers=_RSS_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if parsed.bozo and not parsed.entries:
                log.warning("RSS feed %s looks dead (%s)", feed["name"], parsed.bozo_exception)
                continue
            for entry in parsed.entries:
                entry["_src"] = "rss"
                entry["_section_hint"] = "toronto"
                entry["_source_name"] = feed["name"]
            items.extend(parsed.entries)
        except Exception as exc:
            log.warning("RSS feed %s failed: %s", feed["name"], exc)
    return items


def fetch_all() -> list[dict]:
    """All sources concatenated into one raw list."""
    return fetch_guardian() + fetch_nyt() + fetch_toronto_rss()


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

"""Deterministic source identity and Toronto clock labels for ordinary Daily cards.

The model composes prose and chooses editorial order, but it is not an authority
for article URLs or publication clocks. Use the *actual post-trim model input*
as the only article identity source. Never infer another publisher's article
from headline similarity or invent a source timestamp.
"""
from __future__ import annotations

import datetime as dt
import logging
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .voices.urls import canonical_url

log = logging.getLogger("the-daily.source-integrity")
TORONTO = ZoneInfo("America/Toronto")
_FUZZY_MIN = 0.975
_FUZZY_MARGIN = 0.05


def _canonical(value: object) -> str:
    return canonical_url(value) if isinstance(value, str) else ""


def _safe_source_link(candidate: dict) -> str:
    return _canonical(candidate.get("canonical_url") or candidate.get("link"))


def _reader_url(candidate: dict) -> str:
    # Keep the publisher-stated destination: the comparable canonical form
    # may normalize away host/addressing details essential to navigation.
    original = candidate.get("link")
    if isinstance(original, str) and _canonical(original):
        return original
    return _safe_source_link(candidate)


def _unique_exact(link: str, candidates: list[dict]) -> dict | None:
    identity = _canonical(link)
    if not identity:
        return None
    matches = [c for c in candidates if identity in {
        _canonical(c.get("link")), _canonical(c.get("canonical_url"))
    }]
    return matches[0] if len(matches) == 1 else None


def _unique_minor_slug_drift(link: str, candidates: list[dict]) -> dict | None:
    """Recover minor punctuation/spelling changes, never cross-host/date.

    A high similarity score alone cannot identify an article. Exact host plus
    all pre-slug path segments and an unambiguous margin are also required.
    """
    identity = _canonical(link)
    if not identity:
        return None
    output = urlsplit(identity)
    host = (output.hostname or "").removeprefix("www.")
    segments = output.path.strip("/").split("/")
    if len(segments) < 3:
        return None

    scored: list[tuple[float, dict]] = []
    for candidate in candidates:
        source = _safe_source_link(candidate)
        if not source:
            continue
        parts = urlsplit(source)
        if (parts.hostname or "").removeprefix("www.") != host:
            continue
        source_parts = parts.path.strip("/").split("/")
        if len(source_parts) != len(segments) or source_parts[:-1] != segments[:-1]:
            continue
        similarity = SequenceMatcher(None, source_parts[-1], segments[-1]).ratio()
        if similarity >= _FUZZY_MIN:
            scored.append((similarity, candidate))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored or (len(scored) > 1 and scored[0][0] - scored[1][0] < _FUZZY_MARGIN):
        return None
    return scored[0][1]


def _toronto_time(value: object, today: dt.date) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        try:
            when = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            when = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if when.tzinfo is None:
        return None
    local = when.astimezone(TORONTO)
    if local.date() == today:
        return local.strftime("%-I:%M %p")
    if local.date() == today - dt.timedelta(days=1):
        return "Yesterday"
    return None


def restore_source_metadata(sections: list[dict], model_input: list[dict], today: dt.date) -> dict:
    """Correct matched ordinary cards in place; leave unproven identities alone.

    Unknown model URLs remain visible with a warning instead of assigning an
    arbitrary source. Another separately owned decision can reject those cards.
    Toronto backfill, Sports and Following own their independent source paths.
    """
    repaired_links = adjusted_times = unmatched = 0
    for section in sections:
        for card in section.get("stories", []):
            if card.get("backfill"):
                continue
            supplied = str(card.get("link") or "")
            source = _unique_exact(supplied, model_input) or _unique_minor_slug_drift(supplied, model_input)
            if source is None:
                unmatched += 1
                continue
            authoritative = _reader_url(source)
            if authoritative and supplied != authoritative:
                card["link"] = authoritative
                repaired_links += 1
            corrected_time = _toronto_time(source.get("pub_date"), today)
            if card.get("time") != corrected_time:
                card["time"] = corrected_time
                adjusted_times += 1
    stats = {"repaired_links": repaired_links, "adjusted_times": adjusted_times, "unmatched": unmatched}
    if any(stats.values()):
        log.info("source-integrity links=%d times=%d unmatched=%d",
                 repaired_links, adjusted_times, unmatched)
    return stats

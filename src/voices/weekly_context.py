"""Bounded public source context for weekly Voice screening.

This is deliberately a weekly source-family pass, not an article-body fetcher.
It reuses the same generic adapters, authorship evidence, canonical identity,
request budgets and paywall boundaries as normal Voice discovery.  Descriptions
are public feed/archive metadata and may be incomplete; callers must never
pretend they are full article text.
"""

from __future__ import annotations

import datetime as dt
import logging

from .. import config
from .adapters import FetchWindow
from .dedupe import syndication_keys_for
from .discover import plan_requests, resolve_observations, run_requests
from .http import RequestBudget, VoiceHttp
from .names import clean_text
from .registry import Registry
from .roundup import WeeklyPeriod, core_registry, roundup_budget
from .window import EditionWindow

log = logging.getLogger("the-daily.voices.weekly-context")

MAX_DESCRIPTION_CHARS = 1600


def _clip_description(value: object) -> str:
    text = clean_text(str(value or ""))
    if len(text) <= MAX_DESCRIPTION_CHARS:
        return text
    return text[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"


def _prefer_description(existing: str, candidate: str) -> str:
    """Deterministically prefer the richer public excerpt."""
    values = {value for value in (existing, candidate) if value}
    if not values:
        return ""
    return min(values, key=lambda value: (-len(value), value.casefold(), value))


def weekly_public_descriptions(
    registry: Registry,
    period: WeeklyPeriod,
    *,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
) -> dict[str, str]:
    """Return canonical/identity-key -> public source description for a week.

    One bounded request plan is executed across distinct Core sources.  Partial
    source failure remains local.  If every source fails, an empty mapping is
    returned so the weekly screen can degrade conservatively without inventing
    content or trying article URLs individually.
    """
    core = core_registry(registry)
    window = EditionWindow(
        since=period.start,
        until=period.cutoff,
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )
    fetch_window = FetchWindow(since=window.since, until=window.until)
    planned = plan_requests(core, fetch_window)
    if not planned:
        return {}

    client = http or VoiceHttp(budget=budget or roundup_budget())
    observations, statuses = run_requests(planned, client, fetch_window)
    if statuses and not any(status.ok for status in statuses):
        log.warning("voice weekly context: all planned Core sources failed")
        return {}

    result = resolve_observations(core, observations, window)
    descriptions: dict[str, str] = {}
    for article in result.fresh:
        description = _clip_description(article.description)
        if not description:
            continue
        keys = {
            article.key,
            *article.identity_keys,
            *syndication_keys_for(article),
        }
        for key in keys:
            if not key:
                continue
            descriptions[key] = _prefer_description(
                descriptions.get(key, ""), description
            )
    return descriptions


def description_for_item(item, descriptions: dict[str, str]) -> str:
    """Resolve a stored roundup item back to the richest weekly public excerpt."""
    candidates = [
        descriptions.get(key, "")
        for key in (item.key, *item.keys)
        if key
    ]
    candidates = [value for value in candidates if value]
    if not candidates:
        return ""
    return min(candidates, key=lambda value: (-len(value), value.casefold(), value))

"""Production assembly for the deterministic Sports V2 morning desk.

This is the only Sports orchestration layer used by the Daily build. Provider
adapters remain independently testable; this module coordinates them, records
request/news/model-budget telemetry, and produces the stable #38 presentation
payload. No Sports item is sent to Gemini.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from src import config
from src.voices.urls import canonical_url

from .budget import headline_budget_metrics
from .event_news import EventArticle, fetch_guardian_event_articles
from .headlines import (
    fetch_guardian_team_candidates,
    qualify,
    select_team_winners,
    sports_model_payload,
)
from .major_events import build_major_events
from .models import SeasonPhase, TeamSnapshot, TORONTO, UTC
from .presentation import build_sports_payload
from .providers import BLUE_JAYS, LEAFS, RAPTORS
from .toronto import build_toronto_snapshots

_WORD_RE = re.compile(r"[a-z0-9]+")
_TITLE_STOP = {
    "the", "a", "an", "to", "of", "and", "for", "in", "on", "with", "at",
    "from", "after", "before", "as", "is", "are", "be", "by",
}


@dataclass(frozen=True)
class SportsBuildResult:
    payload: dict
    metrics: dict


class CountingSession:
    """Small requests-compatible proxy that counts attempted requests by host."""

    def __init__(self, delegate: requests.Session | None = None):
        self._delegate = delegate or requests.Session()
        self.counts: Counter[str] = Counter()

    def get(self, url, *args, **kwargs):
        self.counts[_provider_name(str(url))] += 1
        return self._delegate.get(url, *args, **kwargs)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _provider_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host == "api-web.nhle.com":
        return "nhl"
    if host == "statsapi.mlb.com":
        return "mlb"
    if host == "site.api.espn.com":
        return "espn"
    if host == "content.guardianapis.com":
        return "guardian"
    return host or "other"


def _aware_now(value: dt.datetime | None) -> dt.datetime:
    value = value or dt.datetime.now(UTC)
    if value.tzinfo is None:
        raise ValueError("Sports build time must be timezone-aware")
    return value.astimezone(UTC)


def _flatten_event_articles(
    grouped: dict[str, tuple[EventArticle, ...]],
) -> tuple[EventArticle, ...]:
    items = [article for group in grouped.values() for article in group]
    items.sort(key=lambda article: (article.published_at, article.title), reverse=True)
    return tuple(items)


def build_sports_desk(
    *,
    now: dt.datetime | None = None,
    structured_session: requests.Session | None = None,
    news_session: requests.Session | None = None,
) -> SportsBuildResult:
    """Build one finite Sports payload and inspectable budget metrics."""
    now_utc = _aware_now(now)
    structured_http = CountingSession(structured_session)
    news_http = CountingSession(news_session)

    teams = build_toronto_snapshots(now=now_utc, session=structured_http)
    events = build_major_events(now=now_utc, session=structured_http)

    lookback = dt.timedelta(hours=config.SPORTS_NEWS_LOOKBACK_HOURS)
    since = now_utc - lookback
    raw_team_news = fetch_guardian_team_candidates(
        since=since,
        until=now_utc,
        session=news_http,
    )
    qualified_team_news = qualify(raw_team_news)
    team_winners = select_team_winners(raw_team_news, now=now_utc)

    event_groups = fetch_guardian_event_articles(
        on_date=now_utc.astimezone(TORONTO).date(),
        since=since,
        until=now_utc,
        session=news_http,
    )
    event_articles = _flatten_event_articles(event_groups)

    model_payload = sports_model_payload(team_winners)
    if model_payload:
        raise RuntimeError("Sports V2 model boundary violated: Gemini payload is not empty")

    payload = build_sports_payload(
        teams,
        team_headlines=team_winners,
        major_events=events,
        major_headlines=event_articles,
    )

    metrics = headline_budget_metrics(
        raw_candidates=raw_team_news,
        qualified_candidates=qualified_team_news,
        winners=team_winners,
        model_payload=model_payload,
    )
    metrics.update(
        {
            "team_news_rejected": len(raw_team_news) - len(qualified_team_news),
            "event_news_selected": len(event_articles),
            "structured_requests": structured_http.total,
            "news_requests": news_http.total,
            "structured_requests_by_provider": dict(sorted(structured_http.counts.items())),
            "news_requests_by_provider": dict(sorted(news_http.counts.items())),
            "teams_available": sum(1 for snapshot in teams if snapshot.available),
            "active_structured_events": len(events.snapshots),
            "event_mode": int(events.event_mode),
        }
    )
    return SportsBuildResult(payload=payload, metrics=metrics)


def unavailable_sports_result(
    *,
    now: dt.datetime | None = None,
    error: str = "sports_build_unavailable",
) -> SportsBuildResult:
    """Fail-soft payload for an unexpected Sports-stage failure.

    Provider failures should already be isolated inside their adapters. This is
    the final Daily-publication guard: a Sports bug/outage is visible as three
    unavailable rows but cannot suppress the newspaper itself.
    """
    now_utc = _aware_now(now)
    teams = [
        TeamSnapshot(
            team=team,
            phase=SeasonPhase.OFFSEASON,
            source=source,
            fetched_at=now_utc,
            available=False,
            error=error,
        )
        for team, source in (
            (LEAFS, "NHL"),
            (RAPTORS, "ESPN"),
            (BLUE_JAYS, "MLB Stats API"),
        )
    ]
    payload = build_sports_payload(teams)
    return SportsBuildResult(
        payload=payload,
        metrics={
            "raw_candidates": 0,
            "qualified_candidates": 0,
            "winners": 0,
            "model_records": 0,
            "model_chars": 0,
            "approx_model_tokens": 0,
            "team_news_rejected": 0,
            "event_news_selected": 0,
            "structured_requests": 0,
            "news_requests": 0,
            "structured_requests_by_provider": {},
            "news_requests_by_provider": {},
            "teams_available": 0,
            "active_structured_events": 0,
            "event_mode": 0,
            "build_degraded": 1,
        },
    )


def _title_tokens(value: str) -> set[str]:
    return {word for word in _WORD_RE.findall(value.lower()) if word not in _TITLE_STOP}


def _similar_title(a: str, b: str) -> bool:
    left, right = _title_tokens(a), _title_tokens(b)
    if not left or not right:
        return False
    return len(left & right) / len(left | right) >= 0.75


def _sports_editorial_refs(payload: dict) -> tuple[set[str], list[str]]:
    urls: set[str] = set()
    titles: list[str] = []
    for row in payload.get("toronto", []):
        headline = row.get("headline") or {}
        if headline.get("url"):
            urls.add(canonical_url(str(headline["url"])))
        if headline.get("headline"):
            titles.append(str(headline["headline"]))
    for headline in payload.get("major_headlines", []):
        if headline.get("url"):
            urls.add(canonical_url(str(headline["url"])))
        if headline.get("headline"):
            titles.append(str(headline["headline"]))
    urls.discard("")
    return urls, titles


def suppress_sports_editorial_duplicates(
    stories: Iterable[dict],
    sports_payload: dict,
) -> tuple[list[dict], int]:
    """Keep deterministic Sports ownership out of the Gemini story pool.

    Explicit legacy `section_hint=sports` records are always removed. The
    remaining general/local streams are checked against selected Sports
    headlines by canonical URL and conservative title similarity so the same
    development cannot appear once as deterministic Sports and again as an
    ordinary Toronto/Front Page card.
    """
    urls, titles = _sports_editorial_refs(sports_payload)
    kept: list[dict] = []
    removed = 0
    for story in stories:
        if story.get("section_hint") == "sports":
            removed += 1
            continue
        story_url = canonical_url(str(story.get("canonical_url") or story.get("link") or ""))
        story_title = str(story.get("title") or "")
        if (story_url and story_url in urls) or any(
            _similar_title(story_title, title) for title in titles
        ):
            removed += 1
            continue
        kept.append(story)
    return kept, removed

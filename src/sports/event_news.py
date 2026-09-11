"""Targeted zero-model article exceptions for active Sports major events."""

from __future__ import annotations

import datetime as dt
import html
import os
import re
from dataclasses import dataclass
from typing import Iterable

import requests

from src.voices.urls import canonical_url

from .events import EventSpec, active_event_specs
from .headlines import GUARDIAN_SEARCH_URL
from .models import UTC

_TIMEOUT = 15
_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class EventArticle:
    event_key: str
    title: str
    description: str
    url: str
    source: str
    published_at: dt.datetime

    def __post_init__(self) -> None:
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")

    def to_dict(self) -> dict:
        return {
            "event_key": self.event_key,
            "headline": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }


def _clean(value: str | None) -> str:
    return " ".join(html.unescape(_TAG_RE.sub(" ", value or "")).split())


def _fold(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.lower()))


def _parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def qualifies_event_article(spec: EventSpec, article: EventArticle) -> bool:
    """Apply event-specific deterministic significance triggers."""
    text = _fold(f"{article.title} {article.description}")

    if spec.key.startswith("fifa-world-cup"):
        return any(
            token in text
            for token in (
                "canada",
                "final",
                "semi final",
                "semifinal",
                "quarter final",
                "quarterfinal",
                "knockout",
                "eliminated",
                "advances",
                "champion",
                "world record",
            )
        )
    if spec.key.startswith("summer-olympics"):
        return (
            ("canada" in text and any(token in text for token in ("medal", "gold", "silver", "bronze", "final", "record")))
            or "world record" in text
            or "olympic record" in text
            or ("final" in text and any(token in text for token in ("wins", "gold", "champion")))
        )
    if spec.key == "nfl-postseason":
        return any(
            token in text
            for token in (
                "super bowl",
                "afc championship",
                "nfc championship",
                "conference championship",
                "eliminated",
                "advances to",
                "clinches",
            )
        )
    if spec.key.startswith("rugby-world-cup"):
        return any(
            token in text
            for token in (
                "final",
                "semi final",
                "semifinal",
                "quarter final",
                "quarterfinal",
                "knockout",
                "champion",
                "eliminated",
            )
        )
    return False


def _title_tokens(title: str) -> set[str]:
    stop = {"the", "a", "an", "to", "of", "and", "for", "in", "on", "with", "world", "cup", "olympic", "olympics"}
    return {word for word in _WORD_RE.findall(title.lower()) if word not in stop}


def _same_story(a: EventArticle, b: EventArticle) -> bool:
    if a.event_key != b.event_key:
        return False
    au, bu = canonical_url(a.url), canonical_url(b.url)
    if au and au == bu:
        return True
    at, bt = _title_tokens(a.title), _title_tokens(b.title)
    if not at or not bt:
        return False
    return len(at & bt) / len(at | bt) >= 0.75


def select_event_articles(
    spec: EventSpec,
    articles: Iterable[EventArticle],
    *,
    limit: int = 2,
) -> tuple[EventArticle, ...]:
    """Deduplicate and keep a tiny recent exception set for one event."""
    eligible = [article for article in articles if article.event_key == spec.key and qualifies_event_article(spec, article)]
    eligible.sort(key=lambda article: (article.published_at, article.title), reverse=True)
    selected: list[EventArticle] = []
    for article in eligible:
        if any(_same_story(article, prior) for prior in selected):
            continue
        selected.append(article)
        if len(selected) >= min(limit, 2):
            break
    return tuple(selected)


def fetch_guardian_event_articles(
    *,
    on_date: dt.date,
    since: dt.datetime,
    until: dt.datetime,
    session: requests.Session | None = None,
) -> dict[str, tuple[EventArticle, ...]]:
    """Query only active registry events that explicitly enable discovery."""
    key = os.environ.get("GUARDIAN_API_KEY")
    if not key:
        return {}
    http = session or requests.Session()
    output: dict[str, tuple[EventArticle, ...]] = {}

    for spec in active_event_specs(on_date):
        if not spec.article_discovery or not spec.article_queries:
            continue
        raw: list[EventArticle] = []
        for query in spec.article_queries:
            try:
                response = http.get(
                    GUARDIAN_SEARCH_URL,
                    params={
                        "q": query,
                        "section": "sport",
                        "from-date": since.astimezone(UTC).date().isoformat(),
                        "to-date": until.astimezone(UTC).date().isoformat(),
                        "order-by": "newest",
                        "page-size": 6,
                        "show-fields": "trailText",
                        "api-key": key,
                    },
                    timeout=_TIMEOUT,
                )
                response.raise_for_status()
                for row in response.json().get("response", {}).get("results", []):
                    published = _parse_time(row.get("webPublicationDate"))
                    if published is None or published < since or published > until:
                        continue
                    raw.append(
                        EventArticle(
                            event_key=spec.key,
                            title=_clean(row.get("webTitle")),
                            description=_clean((row.get("fields") or {}).get("trailText")),
                            url=str(row.get("webUrl") or ""),
                            source="The Guardian",
                            published_at=published,
                        )
                    )
            except Exception:
                continue
        selected = select_event_articles(spec, raw)
        if selected:
            output[spec.key] = selected
    return output

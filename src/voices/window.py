"""The edition window: what counts as "new" this morning.

The morning build should carry work published since the last edition, not
"whatever a feed happens to be serving". Feeds re-emit old entries, archives
list years of back catalogue, and timestamps are occasionally missing, wrong,
or in the future. Each of those has one documented decision here rather than
being buried in a prompt or an adapter.

Some public indexes publish only a calendar date. Treating ``2026-09-05`` as
an exact midnight timestamp would invent precision and can wrongly make a
current article stale late the next day. For those records the whole UTC day
is the publication interval; the item is fresh when that interval intersects
the edition window. Exact timestamps retain the existing exact behavior.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from enum import Enum

from .model import VoiceArticle

UTC = dt.timezone.utc
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class WindowVerdict(str, Enum):
    FRESH = "fresh"        # inside the window; eligible for Following
    STALE = "stale"        # published before the window opened
    FUTURE = "future"      # timestamp beyond tolerated clock skew
    UNDATED = "undated"    # no usable timestamp


@dataclass(frozen=True)
class EditionWindow:
    """The time range one build treats as new.

    ``since`` is normally the previous successful edition's cutoff minus
    ``lookback`` overlap, so a piece indexed late still arrives. Overlap is
    safe because article identity already prevents a repeat.
    """

    since: dt.datetime
    until: dt.datetime
    future_skew: dt.timedelta = dt.timedelta(hours=2)

    @classmethod
    def ending_now(cls, lookback: dt.timedelta, now: dt.datetime | None = None,
                   future_skew: dt.timedelta = dt.timedelta(hours=2)) -> "EditionWindow":
        now = now or dt.datetime.now(UTC)
        return cls(since=now - lookback, until=now, future_skew=future_skew)

    def classify(self, published_at: dt.datetime | None) -> WindowVerdict:
        if published_at is None:
            return WindowVerdict.UNDATED
        moment = published_at.astimezone(UTC)
        return self.classify_interval(moment, moment)

    def classify_interval(self, earliest: dt.datetime, latest: dt.datetime) -> WindowVerdict:
        """Classify an imprecise publication time without inventing precision.

        An interval is stale only when its latest possible instant predates
        the window, and future only when its earliest possible instant is
        beyond tolerated clock skew. Any overlap is fresh.
        """
        earliest = earliest.astimezone(UTC)
        latest = latest.astimezone(UTC)
        if earliest > self.until + self.future_skew:
            return WindowVerdict.FUTURE
        if latest < self.since:
            return WindowVerdict.STALE
        return WindowVerdict.FRESH


def _date_only_interval(article: VoiceArticle) -> tuple[dt.datetime, dt.datetime] | None:
    """Return the article's full-day interval when its chosen date is day-only.

    ``merge_observations`` preserves every underlying observation. Restrict the
    check to observations that supplied the article's chosen ``published_at``;
    if any such observation carried a precise timestamp, precision wins and
    normal exact classification remains in force.
    """
    if article.published_at is None:
        return None
    matches = [o for o in article.observations if o.published_at == article.published_at]
    if not matches:
        return None
    raw_values = [str(o.raw_published or "").strip() for o in matches]
    if not raw_values or not all(_DATE_ONLY_RE.fullmatch(raw) for raw in raw_values):
        return None
    try:
        days = {dt.date.fromisoformat(raw) for raw in raw_values}
    except ValueError:
        return None
    if len(days) != 1:
        return None
    day = next(iter(days))
    return (
        dt.datetime.combine(day, dt.time.min, tzinfo=UTC),
        dt.datetime.combine(day, dt.time.max, tzinfo=UTC),
    )


def classify_article(article: VoiceArticle, window: EditionWindow) -> WindowVerdict:
    """Classify one article using the precision its source actually supplied."""
    if article.published_at is None:
        return WindowVerdict.UNDATED
    interval = _date_only_interval(article)
    if interval is not None:
        return window.classify_interval(*interval)
    return window.classify(article.published_at)


def partition(articles: list[VoiceArticle], window: EditionWindow) -> dict[str, list[VoiceArticle]]:
    """Split articles by window verdict.

    Only ``fresh`` is eligible for Following. An undated item is *not*
    promoted on the assumption that it is new: a feed that stops emitting
    dates would otherwise republish its whole back catalogue every morning.
    Date-only items are evaluated as calendar-day intervals rather than fake
    midnight timestamps. The other buckets are returned rather than discarded
    so the reason a piece did not appear stays visible in diagnostics.
    """
    buckets: dict[str, list[VoiceArticle]] = {v.value: [] for v in WindowVerdict}
    for article in articles:
        buckets[classify_article(article, window).value].append(article)
    return buckets

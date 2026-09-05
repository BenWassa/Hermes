"""The edition window: what counts as "new" this morning.

The morning build should carry work published since the last edition, not
"whatever a feed happens to be serving". Feeds re-emit old entries, archives
list years of back catalogue, and timestamps are occasionally missing, wrong,
or in the future. Each of those has one documented decision here rather than
being buried in a prompt or an adapter.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from .model import VoiceArticle

UTC = dt.timezone.utc


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
        if moment > self.until + self.future_skew:
            return WindowVerdict.FUTURE
        if moment < self.since:
            return WindowVerdict.STALE
        return WindowVerdict.FRESH


def partition(articles: list[VoiceArticle], window: EditionWindow) -> dict[str, list[VoiceArticle]]:
    """Split articles by window verdict.

    Only ``fresh`` is eligible for Following. An undated item is *not*
    promoted on the assumption that it is new: a feed that stops emitting
    dates would otherwise republish its whole back catalogue every morning.
    The other buckets are returned rather than discarded so the reason a piece
    did not appear stays visible in diagnostics.
    """
    buckets: dict[str, list[VoiceArticle]] = {v.value: [] for v in WindowVerdict}
    for article in articles:
        buckets[window.classify(article.published_at).value].append(article)
    return buckets

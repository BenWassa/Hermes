"""Tolerant publication-timestamp parsing.

Every source states time differently: Guardian and Perigon send ISO-8601, RSS
sends RFC-2822, and the NYT Top Stories API sends ISO-8601 with a *single
digit* hour offset ("2026-09-05T00:00:00-5:00") that ``fromisoformat``
rejects. Feeds also send blank strings, dates with no time, and occasional
garbage. Parsing returns ``None`` rather than raising, and callers decide what
an unparseable date means.
"""

from __future__ import annotations

import datetime as dt
import re
from email.utils import parsedate_to_datetime

UTC = dt.timezone.utc

# "-5:00" / "+5:30" -> "-05:00" / "+05:30"
_SHORT_OFFSET_RE = re.compile(r"([+-])(\d):(\d{2})$")
# "+0000" -> "+00:00"
_COMPACT_OFFSET_RE = re.compile(r"([+-])(\d{2})(\d{2})$")


def parse_timestamp(value) -> dt.datetime | None:
    """Best-effort parse of a publication timestamp into aware UTC.

    Accepts ISO-8601 (with ``Z``, compact, or single-digit offsets),
    RFC-2822, a bare date, an epoch number, a ``time.struct_time`` as produced
    by feedparser, and an existing ``datetime``. Returns ``None`` for anything
    else. Naive results are interpreted as UTC.
    """
    if value is None:
        return None

    if isinstance(value, dt.datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day, tzinfo=UTC)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return dt.datetime.fromtimestamp(float(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if hasattr(value, "tm_year"):  # time.struct_time from feedparser
        try:
            import calendar

            return dt.datetime.fromtimestamp(calendar.timegm(value), tz=UTC)
        except (OverflowError, OSError, ValueError, TypeError):
            return None

    text = str(value).strip()
    if not text:
        return None

    iso = text.replace("Z", "+00:00").replace("z", "+00:00")
    iso = _SHORT_OFFSET_RE.sub(lambda m: f"{m.group(1)}0{m.group(2)}:{m.group(3)}", iso)
    iso = _COMPACT_OFFSET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}:{m.group(3)}", iso)
    if " " in iso and "T" not in iso and re.match(r"^\d{4}-\d{2}-\d{2} ", iso):
        iso = iso.replace(" ", "T", 1)
    try:
        parsed = dt.datetime.fromisoformat(iso)
    except ValueError:
        parsed = None
    if parsed is None:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            parsed = None
    if parsed is None:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def to_iso(value: dt.datetime | None) -> str | None:
    """Render an aware datetime as a compact UTC ISO string."""
    if value is None:
        return None
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_key(value: dt.datetime | None) -> str | None:
    """UTC calendar day of a timestamp, used by fallback identity keys."""
    if value is None:
        return None
    return value.astimezone(UTC).strftime("%Y-%m-%d")

"""Toronto favourite-team snapshot assembly.

The three team adapters are intentionally independent: one provider failure
produces one quiet unavailable row, never a failed morning edition.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable, Mapping

import requests

from .models import SeasonPhase, TeamRef, TeamSnapshot, UTC
from .providers import (
    BLUE_JAYS,
    LEAFS,
    RAPTORS,
    fetch_blue_jays_snapshot,
    fetch_leafs_snapshot,
    fetch_raptors_snapshot,
)

log = logging.getLogger("the-daily.sports")

SnapshotFetcher = Callable[..., TeamSnapshot]

_TEAM_ORDER: tuple[tuple[TeamRef, str, SnapshotFetcher], ...] = (
    (LEAFS, "NHL", fetch_leafs_snapshot),
    (RAPTORS, "ESPN", fetch_raptors_snapshot),
    (BLUE_JAYS, "MLB Stats API", fetch_blue_jays_snapshot),
)


def _aware_utc(value: dt.datetime | None) -> dt.datetime:
    value = value or dt.datetime.now(UTC)
    if value.tzinfo is None:
        raise ValueError("sports build time must be timezone-aware")
    return value.astimezone(UTC)


def build_toronto_snapshots(
    *,
    now: dt.datetime | None = None,
    fetched_at: dt.datetime | None = None,
    session: requests.Session | None = None,
    fetchers: Mapping[str, SnapshotFetcher] | None = None,
) -> list[TeamSnapshot]:
    """Return Leafs, Raptors, Jays snapshots in fixed reader-priority order.

    ``fetchers`` exists for deterministic tests and controlled replacement of a
    provider adapter. Keys are team keys (``leafs``, ``raptors``, ``blue-jays``).
    Raw provider exceptions are logged but never serialized into the edition.
    """
    now_utc = _aware_utc(now)
    fetched_utc = _aware_utc(fetched_at) if fetched_at else dt.datetime.now(UTC)
    http = session or requests.Session()
    overrides = dict(fetchers or {})

    snapshots: list[TeamSnapshot] = []
    for team, source, default_fetcher in _TEAM_ORDER:
        fetcher = overrides.get(team.key, default_fetcher)
        try:
            snapshot = fetcher(now=now_utc, fetched_at=fetched_utc, session=http)
        except Exception as exc:
            log.warning("sports: %s source unavailable: %s", team.key, exc)
            snapshot = TeamSnapshot(
                team=team,
                phase=SeasonPhase.OFFSEASON,
                source=source,
                fetched_at=fetched_utc,
                available=False,
                error="source_unavailable",
            )
        snapshots.append(snapshot)

    return snapshots

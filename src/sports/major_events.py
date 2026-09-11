"""Assembly for the deterministic Sports V2 Major Events desk."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

import requests

from .espn_events import fetch_espn_event_snapshot
from .events import (
    EventHighlight,
    EventProvider,
    EventSnapshot,
    MajorEventsDesk,
    active_event_specs,
    build_major_events_desk,
    select_olympic_highlights,
)
from .models import TORONTO, UTC


def build_major_event_snapshots(
    *,
    now: dt.datetime | None = None,
    session: requests.Session | None = None,
    olympic_highlights: Iterable[EventHighlight] = (),
) -> tuple[EventSnapshot, ...]:
    """Build only the active structured event snapshots.

    ESPN-backed competitions fetch independently. Olympics is intentionally a
    window-only seam: until a Games-time source is configured, the active
    snapshot says so explicitly rather than creating a permanent year-round
    provider dependency. Headline-only NFL/rugby specs are handled by targeted
    article discovery and do not become scoreboards.
    """
    now = now or dt.datetime.now(UTC)
    fetched_at = now.astimezone(UTC)
    on_date = now.astimezone(TORONTO).date()
    highlights = tuple(olympic_highlights)
    snapshots: list[EventSnapshot] = []

    for spec in active_event_specs(on_date):
        if spec.provider == EventProvider.ESPN_SOCCER:
            snapshots.append(fetch_espn_event_snapshot(spec, now=now, session=session))
            continue
        if spec.provider == EventProvider.OLYMPICS_WINDOW:
            selected = select_olympic_highlights(highlights, spec=spec)
            snapshots.append(
                EventSnapshot(
                    spec=spec,
                    fetched_at=fetched_at,
                    source="event-window source" if selected else "unconfigured",
                    highlights=selected,
                    available=bool(selected),
                    error=None if selected else "event_source_unavailable",
                )
            )
            continue
        # HEADLINE_ONLY specs intentionally add no persistent score state.

    return tuple(snapshots)


def build_major_events(
    *,
    now: dt.datetime | None = None,
    session: requests.Session | None = None,
    olympic_highlights: Iterable[EventHighlight] = (),
) -> MajorEventsDesk:
    now = now or dt.datetime.now(UTC)
    snapshots = build_major_event_snapshots(
        now=now,
        session=session,
        olympic_highlights=olympic_highlights,
    )
    return build_major_events_desk(snapshots, on_date=now.astimezone(TORONTO).date())

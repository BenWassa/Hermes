"""Presentation-only Sports V2 payload assembly.

This module does no fetching, ranking, or model work. It combines the stable
#35/#36/#37 domain objects into the dedicated shape consumed by the Sports
renderer. Production ownership is wired by #39.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .event_news import EventArticle
from .events import MajorEventsDesk
from .headlines import QualifiedHeadline
from .models import TeamSnapshot

SPORTS_PAYLOAD_VERSION = 1
TEAM_ORDER = ("leafs", "raptors", "blue-jays")
MAX_MAJOR_HEADLINES = 4


def _headline_dict(value: QualifiedHeadline | Mapping[str, object]) -> dict:
    if isinstance(value, QualifiedHeadline):
        return value.to_dict()
    return dict(value)


def _event_article_dict(value: EventArticle | Mapping[str, object]) -> dict:
    if isinstance(value, EventArticle):
        return value.to_dict()
    return dict(value)


def build_sports_payload(
    team_snapshots: Iterable[TeamSnapshot],
    *,
    team_headlines: Mapping[str, QualifiedHeadline | Mapping[str, object]] | None = None,
    major_events: MajorEventsDesk | None = None,
    major_headlines: Iterable[EventArticle | Mapping[str, object]] = (),
) -> dict:
    """Build the finite UI payload without duplicating domain state.

    The three Toronto teams are required and always emitted in reader-priority
    order. A provider outage is represented by an unavailable TeamSnapshot, not
    by omitting the team. Qualified team headlines stay attached to their team;
    event/global exceptions live in the separate Major Headlines layer.
    """
    snapshots = list(team_snapshots)
    by_key: dict[str, TeamSnapshot] = {}
    for snapshot in snapshots:
        key = snapshot.team.key
        if key not in TEAM_ORDER:
            raise ValueError(f"unexpected Toronto team key: {key}")
        if key in by_key:
            raise ValueError(f"duplicate Toronto team snapshot: {key}")
        by_key[key] = snapshot

    missing = [key for key in TEAM_ORDER if key not in by_key]
    if missing:
        raise ValueError(f"missing permanent Toronto team snapshots: {', '.join(missing)}")

    headline_map = team_headlines or {}
    unexpected_headlines = set(headline_map) - set(TEAM_ORDER)
    if unexpected_headlines:
        raise ValueError(
            "unexpected favourite-team headline keys: "
            + ", ".join(sorted(unexpected_headlines))
        )

    toronto = []
    for key in TEAM_ORDER:
        row = {"snapshot": by_key[key].to_dict(), "headline": None}
        headline = headline_map.get(key)
        if headline is not None:
            payload = _headline_dict(headline)
            if payload.get("team_key") not in (None, key):
                raise ValueError(f"headline team mismatch for {key}")
            row["headline"] = payload
        toronto.append(row)

    event_payload = (
        major_events.to_dict()
        if major_events is not None
        else {"event_mode": False, "max_items": 6, "events": []}
    )

    global_headlines = [_event_article_dict(item) for item in major_headlines]
    global_headlines.sort(
        key=lambda item: (str(item.get("published_at") or ""), str(item.get("headline") or "")),
        reverse=True,
    )
    global_headlines = global_headlines[:MAX_MAJOR_HEADLINES]

    return {
        "version": SPORTS_PAYLOAD_VERSION,
        "toronto": toronto,
        "major_events": event_payload,
        "major_headlines": global_headlines,
    }

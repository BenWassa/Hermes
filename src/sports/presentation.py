"""Presentation-only Sports V2 payload assembly.

This module does no fetching, ranking, or model work. It combines the stable
#35/#36/#37 domain objects into the dedicated shape consumed by the Sports
renderer and owns the build-time navigation shell for the dedicated desk.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from src import config

from .event_news import EventArticle
from .events import MajorEventsDesk
from .headlines import QualifiedHeadline
from .identity import TORONTO_TEAM_MARKS, trusted_asset_url
from .models import TeamSnapshot

SPORTS_PAYLOAD_VERSION = 2
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


def _team_mark(key: str) -> dict | None:
    raw = TORONTO_TEAM_MARKS.get(key)
    if not raw:
        return None
    light = trusted_asset_url(raw.get("light"))
    dark = trusted_asset_url(raw.get("dark"))
    if not light:
        return None
    mark = {"light": light, "fallback": str(raw.get("fallback") or "")}
    if dark:
        mark["dark"] = dark
    return mark


def build_sports_payload(
    team_snapshots: Iterable[TeamSnapshot],
    *,
    team_headlines: Mapping[str, QualifiedHeadline | Mapping[str, object]] | None = None,
    major_events: MajorEventsDesk | None = None,
    major_headlines: Iterable[EventArticle | Mapping[str, object]] = (),
) -> dict:
    """Build the finite UI payload without duplicating domain state."""
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
        row = {
            "snapshot": by_key[key].to_dict(),
            "headline": None,
            "mark": _team_mark(key),
        }
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


def attach_sports_to_edition(edition: dict, sports_payload: dict) -> dict:
    """Attach Sports V2 while keeping Sports as a build-owned navigation tab."""
    by_id = {
        section.get("id"): section
        for section in edition.get("sections", [])
        if section.get("id") != "sports"
    }
    sections: list[dict] = []
    for spec in config.SECTIONS:
        if spec["id"] == "sports":
            sections.append({"id": "sports", "label": spec["label"], "stories": []})
            continue
        section = by_id.get(spec["id"])
        if section is not None:
            sections.append(section)

    edition["sections"] = sections
    edition["sports"] = sports_payload
    return edition

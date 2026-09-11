"""Deterministic Sports V2 major-event registry and domain.

Only explicitly configured competitions can enter the morning paper. The
registry is intentionally small; there is no generic all-sports fallback.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Iterable

from .models import TORONTO, UTC


class EventPriority(IntEnum):
    SELECTIVE = 50
    HIGH = 80
    EVENT_MODE = 100


class EventProvider(StrEnum):
    ESPN_SOCCER = "espn_soccer"
    OLYMPICS_WINDOW = "olympics_window"
    HEADLINE_ONLY = "headline_only"


@dataclass(frozen=True)
class DateWindow:
    start: dt.date
    end: dt.date

    def contains(self, value: dt.date) -> bool:
        return self.start <= value <= self.end


@dataclass(frozen=True)
class EventSpec:
    key: str
    label: str
    sport: str
    priority: EventPriority
    provider: EventProvider
    provider_code: str | None = None
    windows: tuple[DateWindow, ...] = ()
    active_months: frozenset[int] = frozenset()
    max_items: int = 4
    event_mode: bool = False
    canada_promote: bool = False
    include_standings: bool = False
    article_discovery: bool = False
    article_queries: tuple[str, ...] = ()
    fallback: str = "quiet_unavailable"

    def active_on(self, date: dt.date) -> bool:
        return any(window.contains(date) for window in self.windows) or date.month in self.active_months


# Official known tournament windows are pinned rather than guessed. Champions
# League activation covers the main September-May competition rather than
# summer qualification, keeping the morning product focused on the high-value
# competition phase.
EVENT_REGISTRY: tuple[EventSpec, ...] = (
    EventSpec(
        key="fifa-world-cup-2030",
        label="FIFA World Cup",
        sport="soccer",
        priority=EventPriority.EVENT_MODE,
        provider=EventProvider.ESPN_SOCCER,
        provider_code="fifa.world",
        windows=(DateWindow(dt.date(2030, 6, 8), dt.date(2030, 7, 21)),),
        max_items=8,
        event_mode=True,
        canada_promote=True,
        include_standings=True,
        article_discovery=True,
        article_queries=("FIFA World Cup Canada", "FIFA World Cup"),
    ),
    EventSpec(
        key="summer-olympics-2028",
        label="Los Angeles 2028",
        sport="olympics",
        priority=EventPriority.EVENT_MODE,
        provider=EventProvider.OLYMPICS_WINDOW,
        windows=(DateWindow(dt.date(2028, 7, 14), dt.date(2028, 7, 30)),),
        max_items=8,
        event_mode=True,
        canada_promote=True,
        article_discovery=True,
        article_queries=("Olympics Canada medal", "Olympic Games final record"),
        fallback="event_window_source_required",
    ),
    EventSpec(
        key="champions-league",
        label="UEFA Champions League",
        sport="soccer",
        priority=EventPriority.HIGH,
        provider=EventProvider.ESPN_SOCCER,
        provider_code="uefa.champions",
        active_months=frozenset({1, 2, 3, 4, 5, 9, 10, 11, 12}),
        max_items=6,
        include_standings=True,
        article_discovery=False,
    ),
    EventSpec(
        key="rugby-world-cup-2027",
        label="Rugby World Cup",
        sport="rugby",
        priority=EventPriority.SELECTIVE,
        provider=EventProvider.HEADLINE_ONLY,
        windows=(DateWindow(dt.date(2027, 10, 1), dt.date(2027, 11, 13)),),
        max_items=3,
        article_discovery=True,
        article_queries=("Rugby World Cup final", "Rugby World Cup knockout"),
    ),
    EventSpec(
        key="nfl-postseason",
        label="NFL Playoffs",
        sport="football",
        priority=EventPriority.SELECTIVE,
        provider=EventProvider.HEADLINE_ONLY,
        active_months=frozenset({1, 2}),
        max_items=2,
        article_discovery=True,
        article_queries=("NFL playoffs", "Super Bowl"),
    ),
)


class EventMatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    FINAL = "final"
    LIVE = "live"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class EventMatch:
    provider_id: str
    start_time_utc: dt.datetime
    home_team: str
    away_team: str
    status: EventMatchStatus
    stage: str | None = None
    home_score: int | None = None
    away_score: int | None = None
    detail: str | None = None
    canada_involved: bool = False

    def __post_init__(self) -> None:
        if self.start_time_utc.tzinfo is None:
            raise ValueError("start_time_utc must be timezone-aware")

    @property
    def start_time_toronto(self) -> dt.datetime:
        return self.start_time_utc.astimezone(TORONTO)

    def to_dict(self) -> dict:
        return {
            "id": self.provider_id,
            "start_time_utc": self.start_time_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "start_time_toronto": self.start_time_toronto.isoformat(),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "status": self.status.value,
            "stage": self.stage,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "detail": self.detail,
            "canada_involved": self.canada_involved,
        }


@dataclass(frozen=True)
class EventStandingRow:
    position: int
    team: str
    played: int | None = None
    points: int | None = None
    goal_difference: int | None = None
    canada: bool = False

    def to_dict(self) -> dict:
        return {
            "position": self.position,
            "team": self.team,
            "played": self.played,
            "points": self.points,
            "goal_difference": self.goal_difference,
            "canada": self.canada,
        }


@dataclass(frozen=True)
class EventTable:
    label: str
    rows: tuple[EventStandingRow, ...]

    def to_dict(self) -> dict:
        return {"label": self.label, "rows": [row.to_dict() for row in self.rows]}


@dataclass(frozen=True)
class EventHighlight:
    label: str
    detail: str
    occurred_at: dt.datetime | None = None
    canada: bool = False
    world_record: bool = False
    final: bool = False

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "detail": self.detail,
            "occurred_at": self.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z") if self.occurred_at else None,
            "canada": self.canada,
            "world_record": self.world_record,
            "final": self.final,
        }


@dataclass(frozen=True)
class EventSnapshot:
    spec: EventSpec
    fetched_at: dt.datetime
    source: str
    matches: tuple[EventMatch, ...] = ()
    standings: EventTable | None = None
    highlights: tuple[EventHighlight, ...] = ()
    available: bool = True
    error: str | None = None

    def __post_init__(self) -> None:
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")
        if not self.available and not self.error:
            raise ValueError("unavailable event snapshots require an error code")
        if len(self.matches) + len(self.highlights) > self.spec.max_items:
            raise ValueError("event snapshot exceeds configured item cap")

    def to_dict(self) -> dict:
        return {
            "key": self.spec.key,
            "label": self.spec.label,
            "priority": int(self.spec.priority),
            "event_mode": self.spec.event_mode,
            "available": self.available,
            "error": self.error,
            "source": self.source,
            "fetched_at": self.fetched_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "matches": [match.to_dict() for match in self.matches],
            "standings": self.standings.to_dict() if self.standings else None,
            "highlights": [item.to_dict() for item in self.highlights],
        }


@dataclass(frozen=True)
class MajorEventsDesk:
    snapshots: tuple[EventSnapshot, ...]
    event_mode: bool
    max_items: int

    def __post_init__(self) -> None:
        if sum(len(s.matches) + len(s.highlights) for s in self.snapshots) > self.max_items:
            raise ValueError("major-events desk exceeds global item cap")

    def to_dict(self) -> dict:
        return {
            "event_mode": self.event_mode,
            "max_items": self.max_items,
            "events": [snapshot.to_dict() for snapshot in self.snapshots],
        }


def active_event_specs(on_date: dt.date) -> tuple[EventSpec, ...]:
    active = [spec for spec in EVENT_REGISTRY if spec.active_on(on_date)]
    active.sort(key=lambda spec: (-int(spec.priority), spec.key))
    return tuple(active)


def event_article_queries(on_date: dt.date) -> tuple[str, ...]:
    queries: list[str] = []
    for spec in active_event_specs(on_date):
        if spec.article_discovery:
            queries.extend(spec.article_queries)
    return tuple(dict.fromkeys(queries))


def select_event_matches(
    matches: Iterable[EventMatch],
    *,
    spec: EventSpec,
    now: dt.datetime,
) -> tuple[EventMatch, ...]:
    """Select previous-day results and next fixtures within the event cap.

    Canada is promoted ahead of otherwise equivalent World Cup matches. The
    selector retains both result and next-fixture utility where available.
    """
    now_utc = now.astimezone(UTC)
    toronto_today = now.astimezone(TORONTO).date()
    yesterday = toronto_today - dt.timedelta(days=1)

    finished = [
        match for match in matches
        if match.status == EventMatchStatus.FINAL and match.start_time_toronto.date() >= yesterday
        and match.start_time_utc <= now_utc
    ]
    upcoming = [
        match for match in matches
        if match.status in {EventMatchStatus.SCHEDULED, EventMatchStatus.LIVE, EventMatchStatus.POSTPONED}
        and match.start_time_utc >= now_utc - dt.timedelta(hours=3)
    ]

    finished.sort(key=lambda m: (m.canada_involved if spec.canada_promote else False, m.start_time_utc), reverse=True)
    upcoming.sort(key=lambda m: (not (m.canada_involved and spec.canada_promote), m.start_time_utc, m.home_team, m.away_team))

    result_cap = min(len(finished), max(1, spec.max_items // 2)) if finished else 0
    chosen = finished[:result_cap]
    chosen.extend(upcoming[: spec.max_items - len(chosen)])
    if len(chosen) < spec.max_items:
        chosen.extend(finished[result_cap : result_cap + spec.max_items - len(chosen)])
    return tuple(chosen[: spec.max_items])


def select_olympic_highlights(
    highlights: Iterable[EventHighlight],
    *,
    spec: EventSpec,
) -> tuple[EventHighlight, ...]:
    """Deterministically prioritize Canadian medals/results, finals and records."""
    def score(item: EventHighlight) -> tuple[int, float, str]:
        priority = (100 if item.canada else 0) + (40 if item.world_record else 0) + (20 if item.final else 0)
        when = item.occurred_at.timestamp() if item.occurred_at else 0.0
        return priority, when, item.label

    return tuple(sorted(highlights, key=score, reverse=True)[: spec.max_items])


def build_major_events_desk(
    snapshots: Iterable[EventSnapshot],
    *,
    on_date: dt.date,
) -> MajorEventsDesk:
    active_keys = {spec.key for spec in active_event_specs(on_date)}
    eligible = [snapshot for snapshot in snapshots if snapshot.spec.key in active_keys]
    eligible.sort(key=lambda snapshot: (-int(snapshot.spec.priority), snapshot.spec.key))

    event_mode = any(snapshot.spec.event_mode for snapshot in eligible)
    global_cap = 12 if event_mode else 6
    kept: list[EventSnapshot] = []
    used = 0
    for snapshot in eligible:
        items = len(snapshot.matches) + len(snapshot.highlights)
        if used >= global_cap:
            break
        if used + items <= global_cap:
            kept.append(snapshot)
            used += items
            continue
        remaining = global_cap - used
        if remaining <= 0:
            break
        kept.append(
            EventSnapshot(
                spec=snapshot.spec,
                fetched_at=snapshot.fetched_at,
                source=snapshot.source,
                matches=snapshot.matches[:remaining],
                standings=snapshot.standings,
                highlights=snapshot.highlights[: max(0, remaining - len(snapshot.matches[:remaining]))],
                available=snapshot.available,
                error=snapshot.error,
            )
        )
        used = global_cap
    return MajorEventsDesk(tuple(kept), event_mode=event_mode, max_items=global_cap)

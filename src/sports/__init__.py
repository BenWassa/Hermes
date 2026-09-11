"""Deterministic Sports V2 domain API."""

from .budget import headline_budget_metrics
from .event_news import EventArticle, fetch_guardian_event_articles, select_event_articles
from .events import (
    EVENT_REGISTRY,
    EventHighlight,
    EventMatch,
    EventMatchStatus,
    EventSnapshot,
    EventSpec,
    EventStandingRow,
    EventTable,
    MajorEventsDesk,
    active_event_specs,
    event_article_queries,
)
from .headlines import (
    QualifiedHeadline,
    Significance,
    SportsHeadlineCandidate,
    fetch_guardian_team_candidates,
    qualify,
    select_team_winners,
    sports_model_payload,
)
from .major_events import build_major_event_snapshots, build_major_events
from .models import (
    GameStatus,
    GameSummary,
    RecordSummary,
    SeasonPhase,
    StandingSummary,
    TeamRef,
    TeamSnapshot,
)
from .providers import BLUE_JAYS, LEAFS, RAPTORS
from .toronto import build_toronto_snapshots

__all__ = [
    "BLUE_JAYS",
    "EVENT_REGISTRY",
    "LEAFS",
    "RAPTORS",
    "EventArticle",
    "EventHighlight",
    "EventMatch",
    "EventMatchStatus",
    "EventSnapshot",
    "EventSpec",
    "EventStandingRow",
    "EventTable",
    "GameStatus",
    "GameSummary",
    "MajorEventsDesk",
    "QualifiedHeadline",
    "RecordSummary",
    "SeasonPhase",
    "Significance",
    "SportsHeadlineCandidate",
    "StandingSummary",
    "TeamRef",
    "TeamSnapshot",
    "active_event_specs",
    "build_major_event_snapshots",
    "build_major_events",
    "build_toronto_snapshots",
    "event_article_queries",
    "fetch_guardian_event_articles",
    "fetch_guardian_team_candidates",
    "headline_budget_metrics",
    "qualify",
    "select_event_articles",
    "select_team_winners",
    "sports_model_payload",
]

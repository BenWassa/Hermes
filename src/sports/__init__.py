"""Deterministic Sports V2 domain API."""

from .budget import headline_budget_metrics
from .headlines import (
    QualifiedHeadline,
    Significance,
    SportsHeadlineCandidate,
    fetch_guardian_team_candidates,
    qualify,
    select_team_winners,
    sports_model_payload,
)
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
    "LEAFS",
    "RAPTORS",
    "GameStatus",
    "GameSummary",
    "QualifiedHeadline",
    "RecordSummary",
    "SeasonPhase",
    "Significance",
    "SportsHeadlineCandidate",
    "StandingSummary",
    "TeamRef",
    "TeamSnapshot",
    "build_toronto_snapshots",
    "fetch_guardian_team_candidates",
    "headline_budget_metrics",
    "qualify",
    "select_team_winners",
    "sports_model_payload",
]

"""Provider-independent domain objects for the deterministic Sports desk."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
UTC = dt.timezone.utc


class SeasonPhase(StrEnum):
    PRESEASON = "preseason"
    REGULAR = "regular"
    POSTSEASON = "postseason"
    OFFSEASON = "offseason"


class GameStatus(StrEnum):
    SCHEDULED = "scheduled"
    FINAL = "final"
    LIVE = "live"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TeamRef:
    key: str
    name: str
    league: str
    abbreviation: str
    provider_id: str


@dataclass(frozen=True)
class GameSummary:
    provider_game_id: str
    start_time_utc: dt.datetime
    opponent: str
    opponent_abbreviation: str
    home_away: str
    status: GameStatus
    phase: SeasonPhase
    team_score: int | None = None
    opponent_score: int | None = None
    result: str | None = None

    def __post_init__(self) -> None:
        if self.start_time_utc.tzinfo is None:
            raise ValueError("start_time_utc must be timezone-aware")

    @property
    def start_time_toronto(self) -> dt.datetime:
        return self.start_time_utc.astimezone(TORONTO)

    def to_dict(self) -> dict:
        return {
            "id": self.provider_game_id,
            "start_time_utc": self.start_time_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "start_time_toronto": self.start_time_toronto.isoformat(),
            "opponent": self.opponent,
            "opponent_abbreviation": self.opponent_abbreviation,
            "home_away": self.home_away,
            "status": self.status.value,
            "phase": self.phase.value,
            "team_score": self.team_score,
            "opponent_score": self.opponent_score,
            "result": self.result,
        }


@dataclass(frozen=True)
class RecordSummary:
    wins: int
    losses: int
    display: str
    overtime_losses: int | None = None

    def to_dict(self) -> dict:
        return {
            "wins": self.wins,
            "losses": self.losses,
            "overtime_losses": self.overtime_losses,
            "display": self.display,
        }


@dataclass(frozen=True)
class StandingSummary:
    label: str
    rank: int | None = None
    scope: str | None = None
    games_back: str | None = None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "rank": self.rank,
            "scope": self.scope,
            "games_back": self.games_back,
        }


@dataclass(frozen=True)
class TeamSnapshot:
    team: TeamRef
    phase: SeasonPhase
    source: str
    fetched_at: dt.datetime
    last_game: GameSummary | None = None
    record: RecordSummary | None = None
    standing: StandingSummary | None = None
    next_game: GameSummary | None = None
    available: bool = True
    error: str | None = None

    def __post_init__(self) -> None:
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")
        if not self.available and not self.error:
            raise ValueError("unavailable snapshots require an error code")

    def to_dict(self) -> dict:
        return {
            "team": {
                "key": self.team.key,
                "name": self.team.name,
                "league": self.team.league,
                "abbreviation": self.team.abbreviation,
            },
            "phase": self.phase.value,
            "available": self.available,
            "error": self.error,
            "source": self.source,
            "fetched_at": self.fetched_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "last_game": self.last_game.to_dict() if self.last_game else None,
            "record": self.record.to_dict() if self.record else None,
            "standing": self.standing.to_dict() if self.standing else None,
            "next_game": self.next_game.to_dict() if self.next_game else None,
        }

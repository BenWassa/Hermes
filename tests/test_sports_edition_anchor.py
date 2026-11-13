"""Issue #67: edition-date Sports horizons must not drift with late GitHub builds."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from src.sports import desk as desk_mod
from src.sports.desk import sports_edition_anchor
from src.sports.events import MajorEventsDesk
from src.sports.headlines import fetch_guardian_team_candidates

UTC = dt.timezone.utc


def at(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


@pytest.mark.parametrize("now,expected", [
    ("2026-09-16T09:10:00Z", "2026-09-16T09:00:00Z"),
    ("2026-09-16T20:00:00Z", "2026-09-16T09:00:00Z"),
    ("2026-11-10T10:15:00Z", "2026-11-10T10:00:00Z"),
    ("2026-11-10T22:30:00Z", "2026-11-10T10:00:00Z"),
    ("2026-03-08T09:30:00Z", "2026-03-08T09:00:00Z"),  # EDT begins
    ("2026-11-01T10:30:00Z", "2026-11-01T10:00:00Z"),  # EST begins
    ("2026-11-11T02:30:00Z", "2026-11-10T10:00:00Z"),  # Toronto previous day
    ("2026-11-11T10:20:00Z", "2026-11-11T10:00:00Z"),
    ("2026-09-16T08:30:00Z", "2026-09-16T08:30:00Z"),  # early manual dispatch
])
def test_edition_anchor_uses_toronto_0500_floor_without_future_clock(now, expected):
    assert sports_edition_anchor(at(now)) == at(expected)


def test_edition_anchor_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        sports_edition_anchor(dt.datetime(2026, 9, 16, 10, 0))


def test_recovery_and_morning_build_share_bounded_horizons_and_zero_ai(monkeypatch):
    attempts = []

    def team_news(*, since, until, session):
        attempts.append(("teams", since, until))
        return []

    def event_news(*, on_date, since, until, session):
        attempts.append(("events", on_date, since, until))
        return {}

    def structured_events(*, now, session):
        attempts.append(("major", now))
        return MajorEventsDesk((), event_mode=False, max_items=6)

    monkeypatch.setattr(desk_mod, "build_toronto_snapshots", lambda **kwargs: [])
    monkeypatch.setattr(desk_mod, "build_major_events", structured_events)
    monkeypatch.setattr(desk_mod, "fetch_guardian_team_candidates", team_news)
    monkeypatch.setattr(desk_mod, "fetch_guardian_event_articles", event_news)
    monkeypatch.setattr(desk_mod, "build_sports_payload", lambda *args, **kwargs: {})

    early = desk_mod.build_sports_desk(now=at("2026-09-16T09:15:00Z"))
    early_calls = attempts[:]
    attempts.clear()
    late = desk_mod.build_sports_desk(now=at("2026-09-16T20:00:00Z"))

    assert attempts == early_calls
    assert early.metrics["edition_date_toronto"] == "2026-09-16"
    assert late.metrics["edition_time_anchor_utc"] == "2026-09-16T09:00:00Z"
    assert early.metrics["team_news_horizon_since"] == late.metrics["team_news_horizon_since"]
    assert early.metrics["team_news_horizon_until"] == late.metrics["team_news_horizon_until"]
    assert early.metrics["news_requests"] == late.metrics["news_requests"] == 0
    assert early.metrics["model_records"] == late.metrics["model_records"] == 0


class _GuardianResponse:
    def raise_for_status(self): pass
    def json(self):
        return {"response": {"results": [
            {
                "id": "pre-cutoff",
                "webTitle": "Toronto Maple Leafs trade star",
                "webUrl": "https://theguardian.com/sport/leafs-trade",
                "webPublicationDate": "2026-09-16T08:55:00Z",
                "fields": {"trailText": "Confirmed deal"},
            },
            {
                "id": "post-cutoff",
                "webTitle": "Toronto Maple Leafs trade another star",
                "webUrl": "https://theguardian.com/sport/leafs-second",
                "webPublicationDate": "2026-09-16T09:30:00Z",
                "fields": {"trailText": "Later deal"},
            },
        ]}}


class _GuardianSession:
    def __init__(self): self.calls = 0
    def get(self, *args, **kwargs):
        self.calls += 1
        return _GuardianResponse()


def test_real_guardian_adapter_excludes_news_after_edition_anchor(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "offline-fixture")
    cutoff = sports_edition_anchor(at("2026-09-16T20:00:00Z"))
    session = _GuardianSession()
    candidates = fetch_guardian_team_candidates(
        since=cutoff - dt.timedelta(hours=36), until=cutoff, session=session
    )
    assert session.calls == 3  # original bounded request volume
    assert len(candidates) == 3  # each team query yields one eligible row
    assert all(candidate.provider_id == "pre-cutoff" for candidate in candidates)

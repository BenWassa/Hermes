import datetime as dt

from src.sports.budget import headline_budget_metrics
from src.sports.headlines import (
    GUARDIAN_TEAM_QUERIES,
    SportsHeadlineCandidate,
    fetch_guardian_team_candidates,
    qualify,
    select_team_winners,
    sports_model_payload,
)

UTC = dt.timezone.utc
SINCE = dt.datetime(2026, 9, 10, 0, tzinfo=UTC)
UNTIL = dt.datetime(2026, 9, 11, 23, tzinfo=UTC)


class _Response:
    def __init__(self, payload, *, fail=False):
        self.payload = payload
        self.fail = fail

    def raise_for_status(self):
        if self.fail:
            raise RuntimeError("boom")

    def json(self):
        return self.payload


class _Session:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        query = params["q"]
        if query == GUARDIAN_TEAM_QUERIES["raptors"]:
            return _Response({}, fail=True)
        team = "Maple Leafs" if query == GUARDIAN_TEAM_QUERIES["leafs"] else "Blue Jays"
        return _Response(
            {
                "response": {
                    "results": [
                        {
                            "id": f"sport/{team.lower().replace(' ', '-')}",
                            "webTitle": f"{team} sign star to five-year contract",
                            "webUrl": f"https://www.theguardian.com/sport/{team.lower().replace(' ', '-')}",
                            "webPublicationDate": "2026-09-11T12:00:00Z",
                            "fields": {"trailText": "A major roster move was completed."},
                        }
                    ]
                }
            }
        )


def test_guardian_discovery_is_three_targeted_team_queries(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    session = _Session()
    candidates = fetch_guardian_team_candidates(
        since=SINCE,
        until=UNTIL,
        session=session,
    )

    assert len(session.calls) == 3
    assert {call[1]["q"] for call in session.calls} == set(GUARDIAN_TEAM_QUERIES.values())
    assert all(call[1]["section"] == "sport" for call in session.calls)
    assert all(call[1]["page-size"] == 8 for call in session.calls)
    assert {candidate.team_key for candidate in candidates} == {"leafs", "blue-jays"}


def test_one_failed_targeted_query_does_not_hide_other_teams(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    candidates = fetch_guardian_team_candidates(
        since=SINCE,
        until=UNTIL,
        session=_Session(),
    )
    winners = select_team_winners(candidates, now=UNTIL)
    assert set(winners) == {"leafs", "blue-jays"}


def test_missing_guardian_key_costs_zero_requests(monkeypatch):
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)
    session = _Session()
    assert fetch_guardian_team_candidates(since=SINCE, until=UNTIL, session=session) == []
    assert session.calls == []


def test_budget_metrics_make_zero_gemini_contract_inspectable():
    raw = [
        SportsHeadlineCandidate(
            title="Raptors star to undergo surgery and miss three months",
            description="",
            url="https://example.com/raptors",
            source="The Guardian",
            published_at=UNTIL - dt.timedelta(hours=2),
        )
    ]
    qualified = qualify(raw)
    winners = select_team_winners(raw, now=UNTIL)
    payload = sports_model_payload(winners)
    metrics = headline_budget_metrics(
        raw_candidates=raw,
        qualified_candidates=qualified,
        winners=winners,
        model_payload=payload,
    )
    assert metrics == {
        "raw_candidates": 1,
        "qualified_candidates": 1,
        "winners": 1,
        "model_records": 0,
        "model_chars": 0,
        "approx_model_tokens": 0,
    }

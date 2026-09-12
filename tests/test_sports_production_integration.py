import datetime as dt
from types import SimpleNamespace

from src import build as build_mod
from src import config
from src.sports import desk as desk_mod
from src.sports.desk import (
    CountingSession,
    SportsBuildResult,
    build_sports_desk,
    suppress_sports_editorial_duplicates,
    unavailable_sports_result,
)
from src.sports.events import MajorEventsDesk
from src.sports.headlines import SportsHeadlineCandidate
from src.sports.models import SeasonPhase, TeamSnapshot, UTC
from src.sports.presentation import attach_sports_to_edition
from src.sports.providers import BLUE_JAYS, LEAFS, RAPTORS


def _snapshot(team, *, available=True):
    return TeamSnapshot(
        team=team,
        phase=SeasonPhase.REGULAR,
        source="fixture",
        fetched_at=dt.datetime(2026, 9, 11, 9, tzinfo=UTC),
        available=available,
        error=None if available else "source_unavailable",
    )


def _headline(team_key="leafs"):
    return SportsHeadlineCandidate(
        title="Leafs clinch a playoff berth after major roster move",
        description="Toronto clinches after a confirmed major change.",
        url="https://example.com/leafs-major?utm_source=x",
        source="The Guardian",
        published_at=dt.datetime(2026, 9, 11, 8, tzinfo=UTC),
        team_key=team_key,
    )


def test_navigation_and_gemini_section_authority_are_separate():
    assert [section["id"] for section in config.SECTIONS] == [
        "front", "toronto", "world", "sports", "business", "opinion"
    ]
    assert [section["id"] for section in config.CURATION_SECTIONS] == [
        "front", "toronto", "world", "business", "opinion"
    ]
    prompt = config.build_curate_system_prompt(dt.date(2026, 9, 11))
    assert '"sports" (Sports' not in prompt
    assert '"toronto" (Toronto' in prompt
    assert "sport" not in config.GUARDIAN_SECTIONS


def test_attach_sports_discards_any_model_sports_and_inserts_clean_shell():
    edition = {
        "sections": [
            {"id": "front", "label": "Front Page", "stories": [{"id": "f1"}]},
            {"id": "sports", "label": "Sports", "stories": [{"id": "model-sports"}]},
            {"id": "business", "label": "Business", "stories": [{"id": "b1"}]},
        ]
    }
    payload = {"version": 1, "toronto": [], "major_events": {}, "major_headlines": []}
    attach_sports_to_edition(edition, payload)

    assert [section["id"] for section in edition["sections"]] == ["front", "sports", "business"]
    sports = next(section for section in edition["sections"] if section["id"] == "sports")
    assert sports == {"id": "sports", "label": "Sports", "stories": []}
    assert edition["sports"] is payload


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {}


class _Delegate:
    def get(self, *args, **kwargs):
        return _Response()


def test_request_telemetry_counts_provider_attempts_without_content_access():
    session = CountingSession(_Delegate())
    session.get("https://api-web.nhle.com/v1/standings/now")
    session.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/tor")
    session.get("https://statsapi.mlb.com/api/v1/schedule")
    session.get("https://content.guardianapis.com/search")

    assert session.total == 4
    assert session.counts == {"nhl": 1, "espn": 1, "mlb": 1, "guardian": 1}


def test_production_desk_keeps_three_teams_and_zero_model_records(monkeypatch):
    monkeypatch.setattr(
        desk_mod,
        "build_toronto_snapshots",
        lambda **kwargs: [_snapshot(BLUE_JAYS), _snapshot(LEAFS), _snapshot(RAPTORS)],
    )
    monkeypatch.setattr(
        desk_mod,
        "build_major_events",
        lambda **kwargs: MajorEventsDesk((), event_mode=False, max_items=6),
    )
    monkeypatch.setattr(
        desk_mod,
        "fetch_guardian_team_candidates",
        lambda **kwargs: [_headline("leafs")],
    )
    monkeypatch.setattr(desk_mod, "fetch_guardian_event_articles", lambda **kwargs: {})

    result = build_sports_desk(now=dt.datetime(2026, 9, 11, 10, tzinfo=UTC))

    assert [row["snapshot"]["team"]["key"] for row in result.payload["toronto"]] == [
        "leafs", "raptors", "blue-jays"
    ]
    assert result.metrics["raw_candidates"] == 1
    assert result.metrics["winners"] == 1
    assert result.metrics["model_records"] == 0
    assert result.metrics["model_chars"] == 0
    assert result.metrics["approx_model_tokens"] == 0
    assert result.metrics["structured_requests"] == 0
    assert result.metrics["news_requests"] == 0


def test_editorial_duplicate_suppression_removes_legacy_sports_and_selected_story():
    payload = unavailable_sports_result(
        now=dt.datetime(2026, 9, 11, 10, tzinfo=UTC)
    ).payload
    payload["toronto"][0]["headline"] = {
        "team_key": "leafs",
        "headline": "Leafs clinch a playoff berth after major roster move",
        "url": "https://example.com/leafs-major",
    }
    stories = [
        {
            "title": "Routine sport pool story",
            "link": "https://example.com/routine",
            "canonical_url": "https://example.com/routine",
            "section_hint": "sports",
        },
        {
            "title": "Leafs clinch a playoff berth after major roster move",
            "link": "https://other.example/leafs-copy",
            "canonical_url": "https://other.example/leafs-copy",
            "section_hint": "toronto",
        },
        {
            "title": "City council approves housing changes",
            "link": "https://example.com/city",
            "canonical_url": "https://example.com/city",
            "section_hint": "toronto",
        },
    ]

    kept, removed = suppress_sports_editorial_duplicates(stories, payload)
    assert removed == 2
    assert [story["title"] for story in kept] == ["City council approves housing changes"]


def test_fail_soft_payload_preserves_all_three_rows_and_zero_model_budget():
    result = unavailable_sports_result(now=dt.datetime(2026, 9, 11, 10, tzinfo=UTC))
    assert [row["snapshot"]["team"]["key"] for row in result.payload["toronto"]] == [
        "leafs", "raptors", "blue-jays"
    ]
    assert all(not row["snapshot"]["available"] for row in result.payload["toronto"])
    assert result.metrics["model_records"] == 0
    assert result.metrics["build_degraded"] == 1


class _Registry:
    def for_tiers(self, tiers):
        return self


def test_daily_build_publishes_when_sports_stage_raises(monkeypatch, tmp_path):
    raw = [{"unused": True}]
    normalized = [
        {
            "title": "World story",
            "description": "description",
            "source": "Fixture",
            "section_hint": "world",
            "pub_date": "2026-09-11T08:00:00Z",
            "image": None,
            "link": "https://example.com/world",
            "canonical_url": "https://example.com/world",
        }
    ]
    fallback = unavailable_sports_result(now=dt.datetime(2026, 9, 11, 10, tzinfo=UTC))
    rendered = {}

    monkeypatch.setattr(build_mod.weather_mod, "get_weather", lambda: {})
    monkeypatch.setattr(build_mod, "fetch_all", lambda: raw)
    monkeypatch.setattr(build_mod, "normalize", lambda value: normalized)
    monkeypatch.setattr(build_mod, "load_registry", lambda path: _Registry())
    monkeypatch.setattr(build_mod, "discover", lambda registry, pool: SimpleNamespace(fresh=[]))
    monkeypatch.setattr(build_mod, "select_following", lambda *args, **kwargs: [])
    monkeypatch.setattr(build_mod, "following_seeds", lambda *args, **kwargs: [])
    monkeypatch.setattr(build_mod, "editorial_without_following", lambda stories, following: stories)
    monkeypatch.setattr(build_mod, "build_sports_desk", lambda: (_ for _ in ()).throw(RuntimeError("sports down")))
    monkeypatch.setattr(build_mod, "unavailable_sports_result", lambda: fallback)
    monkeypatch.setattr(
        build_mod,
        "curate",
        lambda stories, weather, following: {
            "date": "Friday, September 11, 2026",
            "weather": {},
            "sections": [
                {"id": "front", "label": "Front Page", "stories": []},
                {"id": "world", "label": "World", "stories": []},
            ],
        },
    )
    monkeypatch.setattr(build_mod, "resolve_images", lambda edition: edition)

    def fake_render(edition):
        rendered.update(edition)
        return tmp_path / "index.html"

    monkeypatch.setattr(build_mod, "render", fake_render)

    assert build_mod.main() == 0
    assert rendered["sports"]["version"] == 1
    assert next(section for section in rendered["sections"] if section["id"] == "sports")["stories"] == []
    assert all(not row["snapshot"]["available"] for row in rendered["sports"]["toronto"])

"""Discovery orchestration: batching, budgets, failure isolation, provenance."""

from __future__ import annotations

import datetime as dt

import pytest

from src.voices.adapters import FetchWindow
from src.voices.discover import (
    default_budget,
    discover,
    observations_from_pool,
    plan_requests,
    resolve_observations,
)
from src.voices.http import RequestBudget
from src.voices.window import EditionWindow, WindowVerdict
from tests.conftest import NOW, FakeHttp, FakeResponse, fixture_bytes, fixture_json, fixture_text


@pytest.fixture(autouse=True)
def provider_keys(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")


def all_routes(**overrides):
    routes = {
        "afterbabel.com": FakeResponse(content=fixture_bytes("rss", "multi_author_publication.xml")),
        "drjordanbpeterson.substack.com": FakeResponse(
            content=fixture_bytes("rss", "personal_newsletter.xml")),
        "guardianapis.com": FakeResponse(payload=fixture_json("guardian", "contributor_search.json")),
        "perigon.io": FakeResponse(payload=fixture_json("perigon", "journalist_articles.json")),
        "nysun.com": FakeResponse(text=fixture_text("author_pages", "jsonld_author_archive.html")),
        "example-herald.com": FakeResponse(
            text=fixture_text("author_pages", "structural_author_archive.html")),
    }
    routes.update(overrides)
    return routes


def run(registry, window, *, routes=None, pool=None, budget=None):
    http = FakeHttp(all_routes(**(routes or {})), budget=budget or default_budget())
    return discover(registry, pool=pool or [], window=window, http=http)


# --- batching and budget --------------------------------------------------

def test_request_count_does_not_scale_with_voices(acceptance_registry, window):
    """Seven Voices and six sources must not become seven provider calls."""
    planned = plan_requests(acceptance_registry, FetchWindow(since=window.since, until=window.until))
    per_provider: dict[str, int] = {}
    for request in planned:
        from src.voices.adapters import get_adapter

        provider = get_adapter(request.adapter).provider
        per_provider[provider] = per_provider.get(provider, 0) + 1

    assert per_provider["guardian"] == 1, "all contributor tags belong in one query"
    assert per_provider["perigon"] == 1, "all journalist ids belong in one query"
    assert per_provider["rss"] == 2, "one request per distinct feed"
    assert per_provider["author_page"] == 2


def test_the_pool_costs_no_requests(acceptance_registry, window):
    pool = [{
        "title": "The Quiet Part of the Bargain",
        "link": "https://www.nytimes.com/2026/09/05/opinion/the-quiet-part.html",
        "provider": "nyt", "source": "The New York Times",
        "byline": "By David Brooks", "authors": [{"name": "David Brooks"}],
        "pub_date": "2026-09-05T14:00:00Z", "source_article_id": "nyt://article/1",
        "canonical_url": "https://nytimes.com/2026/09/05/opinion/the-quiet-part.html",
    }]
    result = discover(acceptance_registry, pool=pool, window=window, fetch=False)
    assert result.budget == {}
    assert [a.voice_ids for a in result.fresh] == [["david-brooks"]]


def test_the_perigon_budget_is_one_request_per_run(acceptance_registry, window):
    budget = default_budget()
    run(acceptance_registry, window, budget=budget)
    assert budget.spent["perigon"] == 1
    assert budget.limits["perigon"] == 1


def test_exceeding_a_budget_degrades_that_provider_only(acceptance_registry, window):
    budget = RequestBudget(limits={"rss": 1, "guardian": 5, "perigon": 5, "author_page": 5})
    result = run(acceptance_registry, window, budget=budget)
    failures = [s for s in result.statuses if not s.ok]
    assert len(failures) == 1 and failures[0].adapter == "rss"
    assert any(s.ok and s.adapter == "guardian_contributor" for s in result.statuses)


# --- failure isolation ----------------------------------------------------

def test_one_dead_source_does_not_stop_the_others(acceptance_registry, window):
    result = run(acceptance_registry, window, routes={"afterbabel.com": RuntimeError("HTTP 502")})

    failed = [s for s in result.statuses if not s.ok]
    assert [s.adapter for s in failed] == ["rss"]
    assert "502" in failed[0].error
    # Everything else still produced work.
    assert {v for a in result.articles for v in a.voice_ids} >= {
        "jordan-peterson", "conrad-black", "george-monbiot"}


def test_a_source_that_raises_an_unexpected_error_is_still_local(acceptance_registry, window):
    class Exploding(FakeResponse):
        def json(self):
            raise ValueError("not json at all")

    result = run(acceptance_registry, window, routes={"guardianapis.com": Exploding(text="{}")})
    assert any(not s.ok and s.adapter == "guardian_contributor" for s in result.statuses)
    assert result.articles, "the run continued"


def test_every_source_failing_still_returns_a_result(acceptance_registry, window):
    routes = {key: RuntimeError("down") for key in all_routes()}
    result = run(acceptance_registry, window, routes=routes)
    assert result.articles == []
    assert result.fresh == []
    assert len(result.failures) == len(result.statuses) > 0


# --- window ---------------------------------------------------------------

def test_stale_future_and_undated_items_are_excluded_but_explained(acceptance_registry, window):
    result = run(acceptance_registry, window)
    titles = {v: {a.title for a in items} for v, items in result.buckets.items()}

    assert "An Archive Piece From 2019" in titles[WindowVerdict.STALE.value]
    assert "A Post Dated Next Year" in titles[WindowVerdict.FUTURE.value]
    assert "A Post With An Unparseable Date" in titles[WindowVerdict.UNDATED.value]
    fresh_titles = {a.title for a in result.fresh}
    assert fresh_titles.isdisjoint({
        "An Archive Piece From 2019", "A Post Dated Next Year", "A Post With An Unparseable Date"})
    # Older archive entries on the author pages are stale for the same reason.
    assert titles[WindowVerdict.STALE.value] == {
        "An Archive Piece From 2019",
        "Canada's Constitutional Drift",
        "What the Inquiry Will Not Ask",
    }
    assert result.diagnostics()["dropped"] == {"stale": 3, "future": 1, "undated": 1}


def test_window_classification_boundaries():
    now = NOW
    window = EditionWindow(since=now - dt.timedelta(hours=36), until=now,
                           future_skew=dt.timedelta(hours=2))
    assert window.classify(now - dt.timedelta(hours=1)) is WindowVerdict.FRESH
    assert window.classify(now - dt.timedelta(hours=36)) is WindowVerdict.FRESH
    assert window.classify(now - dt.timedelta(hours=37)) is WindowVerdict.STALE
    assert window.classify(now + dt.timedelta(hours=1)) is WindowVerdict.FRESH
    assert window.classify(now + dt.timedelta(hours=3)) is WindowVerdict.FUTURE
    assert window.classify(None) is WindowVerdict.UNDATED


# --- provenance -----------------------------------------------------------

def test_every_article_can_explain_its_attribution(acceptance_registry, window):
    result = run(acceptance_registry, window)
    assert result.articles
    for article in result.articles:
        for voice_id in article.voice_ids:
            evidence = article.evidence_for(voice_id)
            assert evidence is not None
            assert evidence.evidence in {"provider_author_id", "source_scope", "byline_alias"}
            assert evidence.detail
            assert evidence.source_key or evidence.adapter


def test_diagnostics_are_json_serialisable(acceptance_registry, window):
    import json

    result = run(acceptance_registry, window)
    payload = json.dumps(result.diagnostics())
    assert "requests" in payload and "sources" in payload


def test_an_article_records_every_observation_behind_it(acceptance_registry, window):
    """The Atlantic piece arrives via Perigon; add a pool sighting of the same URL."""
    pool = [{
        "title": "Attention and the Commons",
        "link": "https://www.theatlantic.com/ideas/archive/2026/09/attention-and-the-commons/687001/?utm_source=x",
        "provider": "perigon", "source": "The Atlantic",
        "byline": "Jonathan Haidt",
        "authors": [{"name": "Jonathan Haidt", "source_author_id": "perigon-jhaidt-001",
                     "source_author_provider": "perigon"}],
        "pub_date": "2026-09-05T10:15:00Z",
        "source_article_id": "0a1b2c3d4e5f60718293a4b5c6d7e8f9",
    }]
    result = run(acceptance_registry, window, pool=pool)
    article = next(a for a in result.articles if "theatlantic.com" in a.canonical_url)
    assert len(article.observations) == 2
    assert set(article.discovered_via) == {"perigon_journalist:perigon-jhaidt-001", "pool:perigon"}


def test_rejected_near_misses_are_reported(acceptance_registry, window):
    pool = [{
        "title": "A guest essay elsewhere",
        "link": "https://www.example-news.com/2026/09/05/guest",
        "provider": "perigon", "source": "Example News",
        "byline": "Jonathan Haidt", "authors": [{"name": "Jonathan Haidt"}],
        "pub_date": "2026-09-05T12:00:00Z",
    }]
    result = discover(acceptance_registry, pool=pool, window=window, fetch=False)
    assert result.articles == []
    assert [r.reason for r in result.rejections] == ["byline_out_of_scope"]
    assert "example-news.com" not in str(result.articles)


# --- pool conversion ------------------------------------------------------

def test_pool_conversion_preserves_provider_author_ids():
    stories = [{
        "title": "Rivers", "link": "https://www.theguardian.com/commentisfree/2026/sep/05/rivers",
        "provider": "guardian", "source": "The Guardian", "byline": "George Monbiot",
        "authors": [{"name": "George Monbiot", "source_author_id": "profile/georgemonbiot",
                     "source_author_provider": "guardian"}],
        "pub_date": "2026-09-05T06:00:00Z",
    }]
    observation = observations_from_pool(stories)[0]
    assert observation.authors[0].provider_id == "profile/georgemonbiot"
    assert observation.source_key == "pool:guardian"


def test_pool_conversion_skips_records_without_a_link_or_title():
    assert observations_from_pool([{"title": "x"}, {"link": "https://a.com/b"}, {}]) == []


def test_resolve_observations_ignores_unattributed_noise(acceptance_registry, window):
    noise = observations_from_pool([{
        "title": "Council approves the transit levy",
        "link": "https://municipal-notes.example.org/2026/09/05/transit-levy",
        "provider": "rss", "byline": "John Smith", "authors": [{"name": "John Smith"}],
        "pub_date": "2026-09-05T10:00:00Z",
    }])
    result = resolve_observations(acceptance_registry, noise, window)
    assert result.articles == []

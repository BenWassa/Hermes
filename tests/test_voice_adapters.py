"""Adapters, exercised against recorded provider fixtures.

No network. Each adapter is driven through its real ``plan`` and ``fetch`` with
a fake HTTP client, so batching, parsing, and failure handling are all the code
the live build runs.
"""

from __future__ import annotations

import datetime as dt

import pytest

from src.voices.adapters import FetchWindow, get_adapter
from src.voices.adapters.base import AdapterError
from src.voices.http import RequestBudget
from src.voices.registry import validate
from tests.conftest import NOW, FakeHttp, FakeResponse, fixture_bytes, fixture_json, fixture_text


@pytest.fixture
def fetch_window():
    return FetchWindow(since=NOW - dt.timedelta(hours=36), until=NOW)


def sources_for(data: dict):
    registry, problems = validate(data)
    assert problems == [], problems
    return [(voice, source) for voice in registry.active for source in voice.enabled_sources]


# --- RSS ------------------------------------------------------------------

RSS_VOICE = {
    "version": 1,
    "voices": [{
        "id": "jonathan-haidt", "name": "Jonathan Haidt",
        "sources": [{"id": "after-babel", "type": "rss", "url": "https://www.afterbabel.com/feed",
                     "publication": "After Babel", "authorship": "byline"}],
    }],
}


def test_rss_entries_carry_their_own_authors(fetch_window):
    adapter = get_adapter("rss")
    request = adapter.plan(sources_for(RSS_VOICE), fetch_window)[0]
    http = FakeHttp({"afterbabel.com": FakeResponse(
        content=fixture_bytes("rss", "multi_author_publication.xml"))})

    observations = adapter.fetch(request, http, fetch_window)

    by_title = {o.title: o for o in observations}
    assert by_title["Treasure Your Attention"].authors[0].name == "Jonathan Haidt"
    # A coauthored entry keeps both, in order.
    assert [a.name for a in by_title["The Phone-Based Childhood, Two Years On"].authors] == [
        "Zach Rausch", "Jonathan Haidt"]
    # A different writer on the same feed is reported as themselves.
    assert [a.name for a in by_title["Girls, Friendship, and the Feed"].authors] == ["Freya India"]
    # An entry with no creator element gets no invented author.
    assert by_title["An Untitled Draft With No Author"].authors == ()


def test_rss_authors_have_no_provider_ids(fetch_window):
    adapter = get_adapter("rss")
    request = adapter.plan(sources_for(RSS_VOICE), fetch_window)[0]
    http = FakeHttp({"afterbabel.com": FakeResponse(
        content=fixture_bytes("rss", "multi_author_publication.xml"))})
    for observation in adapter.fetch(request, http, fetch_window):
        assert all(not author.provider_id for author in observation.authors)


def test_rss_strips_tracking_parameters_into_the_canonical_url(fetch_window):
    adapter = get_adapter("rss")
    request = adapter.plan(sources_for(RSS_VOICE), fetch_window)[0]
    http = FakeHttp({"afterbabel.com": FakeResponse(
        content=fixture_bytes("rss", "multi_author_publication.xml"))})
    observation = adapter.fetch(request, http, fetch_window)[0]
    assert "utm_source" in observation.url
    assert observation.canonical_url == "https://afterbabel.com/p/treasure-your-attention"


def test_rss_keeps_bad_timestamps_as_missing_rather_than_guessing(fetch_window):
    adapter = get_adapter("rss")
    request = adapter.plan(sources_for(RSS_VOICE), fetch_window)[0]
    http = FakeHttp({"afterbabel.com": FakeResponse(
        content=fixture_bytes("rss", "multi_author_publication.xml"))})
    bad = next(o for o in adapter.fetch(request, http, fetch_window) if o.title.endswith("Unparseable Date"))
    assert bad.published_at is None
    assert bad.raw_published == "sometime last week"


def test_one_feed_shared_by_two_voices_is_fetched_once(fetch_window):
    data = {"version": 1, "voices": [
        {"id": "one", "name": "Writer One", "sources": [
            {"type": "rss", "url": "https://www.afterbabel.com/feed", "authorship": "byline"}]},
        {"id": "two", "name": "Writer Two", "sources": [
            {"type": "rss", "url": "https://www.afterbabel.com/feed", "authorship": "byline"}]},
    ]}
    registry, problems = validate(data)
    assert problems == []
    from src.voices.discover import plan_requests

    assert len(plan_requests(registry, fetch_window)) == 1


def test_a_dead_feed_raises_an_adapter_error(fetch_window):
    adapter = get_adapter("rss")
    request = adapter.plan(sources_for(RSS_VOICE), fetch_window)[0]
    http = FakeHttp({"afterbabel.com": RuntimeError("HTTP 503")})
    with pytest.raises(AdapterError):
        adapter.fetch(request, http, fetch_window)


def test_malformed_feed_content_raises_rather_than_returning_junk(fetch_window):
    adapter = get_adapter("rss")
    request = adapter.plan(sources_for(RSS_VOICE), fetch_window)[0]
    http = FakeHttp({"afterbabel.com": FakeResponse(content=fixture_bytes("rss", "malformed.xml"))})
    with pytest.raises(AdapterError):
        adapter.fetch(request, http, fetch_window)


# --- Guardian -------------------------------------------------------------

GUARDIAN_VOICES = {
    "version": 1,
    "voices": [
        {"id": "george-monbiot", "name": "George Monbiot",
         "provider_ids": [{"provider": "guardian", "id": "profile/georgemonbiot"}],
         "sources": [{"type": "guardian_contributor", "tag": "profile/georgemonbiot",
                      "authorship": "provider_id"}]},
        {"id": "amelia-hargreaves", "name": "Amelia Hargreaves",
         "provider_ids": [{"provider": "guardian", "id": "profile/ameliahargreaves"}],
         "sources": [{"type": "guardian_contributor", "tag": "profile/ameliahargreaves",
                      "authorship": "provider_id"}]},
    ],
}


def test_every_guardian_contributor_rides_in_one_request(fetch_window, monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    adapter = get_adapter("guardian_contributor")
    planned = adapter.plan(sources_for(GUARDIAN_VOICES), fetch_window)
    assert len(planned) == 1
    assert planned[0].payload["tags"] == ["profile/ameliahargreaves", "profile/georgemonbiot"]

    http = FakeHttp({"guardianapis.com": FakeResponse(
        payload=fixture_json("guardian", "contributor_search.json"))},
        budget=RequestBudget())
    adapter.fetch(planned[0], http, fetch_window)

    url, params = http.calls[0]
    assert params["tag"] == "profile/ameliahargreaves|profile/georgemonbiot"
    assert params["show-tags"] == "contributor"
    assert http.budget.spent == {"guardian": 1}


def test_guardian_contributor_tags_become_provider_ids(fetch_window, monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    adapter = get_adapter("guardian_contributor")
    planned = adapter.plan(sources_for(GUARDIAN_VOICES), fetch_window)
    http = FakeHttp({"guardianapis.com": FakeResponse(
        payload=fixture_json("guardian", "contributor_search.json"))})
    observations = adapter.fetch(planned[0], http, fetch_window)

    solo = next(o for o in observations if o.title == "Rivers and the public realm")
    assert [(a.name, a.provider, a.provider_id) for a in solo.authors] == [
        ("George Monbiot", "guardian", "profile/georgemonbiot")]
    assert solo.byline == "George Monbiot"
    assert solo.provider_article_id == "commentisfree/2026/sep/05/rivers-and-the-public-realm"


def test_guardian_keyword_tags_are_not_authors(fetch_window, monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    adapter = get_adapter("guardian_contributor")
    planned = adapter.plan(sources_for(GUARDIAN_VOICES), fetch_window)
    http = FakeHttp({"guardianapis.com": FakeResponse(
        payload=fixture_json("guardian", "contributor_search.json"))})
    joint = next(o for o in adapter.fetch(planned[0], http, fetch_window)
                 if o.title == "Two authors on water")
    assert [a.provider_id for a in joint.authors] == [
        "profile/georgemonbiot", "profile/ameliahargreaves"]


def test_guardian_results_for_unrequested_contributors_are_dropped(fetch_window, monkeypatch):
    """A piece merely *about* a followed writer must not enter as their work."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    adapter = get_adapter("guardian_contributor")
    planned = adapter.plan(sources_for(GUARDIAN_VOICES), fetch_window)
    http = FakeHttp({"guardianapis.com": FakeResponse(
        payload=fixture_json("guardian", "contributor_search.json"))})
    titles = {o.title for o in adapter.fetch(planned[0], http, fetch_window)}
    assert "What George Monbiot gets wrong about rivers" not in titles


def test_guardian_without_a_key_fails_locally(fetch_window, monkeypatch):
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)
    adapter = get_adapter("guardian_contributor")
    planned = adapter.plan(sources_for(GUARDIAN_VOICES), fetch_window)
    with pytest.raises(AdapterError):
        adapter.fetch(planned[0], FakeHttp({}), fetch_window)


# --- Perigon --------------------------------------------------------------

PERIGON_VOICE = {
    "version": 1,
    "voices": [{
        "id": "jonathan-haidt", "name": "Jonathan Haidt",
        "provider_ids": [{"provider": "perigon", "id": "perigon-jhaidt-001"}],
        "sources": [{"type": "perigon_journalist", "journalist_id": "perigon-jhaidt-001",
                     "authorship": "provider_id"}],
    }],
}


def test_every_perigon_journalist_rides_in_one_request(fetch_window, monkeypatch):
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")
    adapter = get_adapter("perigon_journalist")
    planned = adapter.plan(sources_for(PERIGON_VOICE), fetch_window)
    assert len(planned) == 1

    http = FakeHttp({"perigon.io": FakeResponse(
        payload=fixture_json("perigon", "journalist_articles.json"))})
    adapter.fetch(planned[0], http, fetch_window)
    _url, params = http.calls[0]
    assert params["journalistId"] == ["perigon-jhaidt-001"]
    assert http.budget.spent == {"perigon": 1}


def test_perigon_journalist_identity_survives(fetch_window, monkeypatch):
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")
    adapter = get_adapter("perigon_journalist")
    planned = adapter.plan(sources_for(PERIGON_VOICE), fetch_window)
    http = FakeHttp({"perigon.io": FakeResponse(
        payload=fixture_json("perigon", "journalist_articles.json"))})
    observations = adapter.fetch(planned[0], http, fetch_window)

    original = next(o for o in observations if "theatlantic.com" in o.url)
    assert original.authors[0].provider == "perigon"
    assert original.authors[0].provider_id == "perigon-jhaidt-001"
    assert original.publication == "The Atlantic"
    assert original.provider_article_id == "0a1b2c3d4e5f60718293a4b5c6d7e8f9"


def test_perigon_reprints_are_kept_and_flagged(fetch_window, monkeypatch):
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")
    adapter = get_adapter("perigon_journalist")
    planned = adapter.plan(sources_for(PERIGON_VOICE), fetch_window)
    http = FakeHttp({"perigon.io": FakeResponse(
        payload=fixture_json("perigon", "journalist_articles.json"))})
    reprint = next(o for o in adapter.fetch(planned[0], http, fetch_window)
                   if "nationalpost.com" in o.url)
    assert reprint.reprint is True
    assert reprint.reprint_group_id == "reprint-group-attention-commons"


def test_perigon_people_mentioned_are_not_authors(fetch_window, monkeypatch):
    monkeypatch.setenv("PERIGON_API_KEY", "test-key")
    adapter = get_adapter("perigon_journalist")
    planned = adapter.plan(sources_for(PERIGON_VOICE), fetch_window)
    http = FakeHttp({"perigon.io": FakeResponse(
        payload=fixture_json("perigon", "journalist_articles.json"))})
    titles = {o.title for o in adapter.fetch(planned[0], http, fetch_window)}
    assert "Schools debate the Haidt thesis" not in titles


# --- author pages ---------------------------------------------------------

AUTHOR_PAGE_VOICE = {
    "version": 1,
    "voices": [{
        "id": "conrad-black", "name": "Conrad Black",
        "sources": [{"type": "author_page", "url": "https://www.nysun.com/author/conrad-black-2",
                     "publication": "The New York Sun", "link_prefix": "/article/",
                     "paywalled": True, "authorship": "scope"}],
    }],
}

STRUCTURAL_VOICE = {
    "version": 1,
    "voices": [{
        "id": "amelia-hargreaves", "name": "Amelia Hargreaves",
        "sources": [{"type": "author_page", "url": "https://www.example-herald.com/authors/amelia-hargreaves",
                     "publication": "The Example Herald", "link_prefix": "/article/",
                     "structural": True, "authorship": "scope"}],
    }],
}


def test_author_page_reads_jsonld(fetch_window):
    adapter = get_adapter("author_page")
    request = adapter.plan(sources_for(AUTHOR_PAGE_VOICE), fetch_window)[0]
    http = FakeHttp({"nysun.com": FakeResponse(
        text=fixture_text("author_pages", "jsonld_author_archive.html"))})
    observations = adapter.fetch(request, http, fetch_window)

    titles = [o.title for o in observations]
    assert "The Long Retreat of the Administrative State" in titles
    assert observations[0].publication == "The New York Sun"
    assert observations[0].author_scoped is True


def test_author_page_drops_off_site_and_non_article_links(fetch_window):
    adapter = get_adapter("author_page")
    request = adapter.plan(sources_for(AUTHOR_PAGE_VOICE), fetch_window)[0]
    http = FakeHttp({"nysun.com": FakeResponse(
        text=fixture_text("author_pages", "jsonld_author_archive.html"))})
    urls = [o.canonical_url for o in adapter.fetch(request, http, fetch_window)]
    assert not any("partner-example.com" in u for u in urls)
    assert not any("/subscribe" in u for u in urls)


def test_author_page_canonicalizes_its_links(fetch_window):
    adapter = get_adapter("author_page")
    request = adapter.plan(sources_for(AUTHOR_PAGE_VOICE), fetch_window)[0]
    http = FakeHttp({"nysun.com": FakeResponse(
        text=fixture_text("author_pages", "jsonld_author_archive.html"))})
    drift = next(o for o in adapter.fetch(request, http, fetch_window)
                 if "constitutional-drift" in o.canonical_url)
    assert drift.canonical_url == "https://nysun.com/article/canadas-constitutional-drift"


def test_structural_parsing_is_opt_in_and_bounded(fetch_window):
    adapter = get_adapter("author_page")
    request = adapter.plan(sources_for(STRUCTURAL_VOICE), fetch_window)[0]
    http = FakeHttp({"example-herald.com": FakeResponse(
        text=fixture_text("author_pages", "structural_author_archive.html"))})
    observations = adapter.fetch(request, http, fetch_window)

    assert [o.title for o in observations] == [
        "The Water Companies and the Regulator", "What the Inquiry Will Not Ask"]
    assert all("example-herald.com" in o.canonical_url for o in observations)


def test_a_redesigned_page_fails_closed(fetch_window):
    """No recognisable structure must produce nothing, never invented items."""
    adapter = get_adapter("author_page")
    request = adapter.plan(sources_for(STRUCTURAL_VOICE), fetch_window)[0]
    http = FakeHttp({"example-herald.com": FakeResponse(
        text=fixture_text("author_pages", "redesigned_no_structure.html"))})
    with pytest.raises(AdapterError):
        adapter.fetch(request, http, fetch_window)


def test_structural_parsing_disabled_means_jsonld_or_nothing(fetch_window):
    adapter = get_adapter("author_page")
    request = adapter.plan(sources_for(AUTHOR_PAGE_VOICE), fetch_window)[0]
    http = FakeHttp({"nysun.com": FakeResponse(
        text=fixture_text("author_pages", "structural_author_archive.html"))})
    with pytest.raises(AdapterError):
        adapter.fetch(request, http, fetch_window)

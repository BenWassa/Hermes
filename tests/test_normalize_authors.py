"""Authorship survives fetch and normalization, and curation is unchanged.

The pipeline used to discard the Guardian byline it had already paid to fetch,
and never read the NYT or Perigon ones. These tests pin the correction, and
pin that the editor model's input did not change as a side effect.
"""

from __future__ import annotations

import feedparser

from src import config
from src.normalize import CURATION_KEYS, curation_view, normalize
from tests.conftest import fixture_bytes, fixture_json


def guardian_items():
    items = fixture_json("guardian", "contributor_search.json")["response"]["results"]
    for item in items:
        item["_src"] = "guardian"
        item["_section_hint"] = "opinion"
    return items


def nyt_items():
    items = fixture_json("nyt", "opinion_top_stories.json")["results"]
    for item in items:
        item["_src"] = "nyt"
        item["_section_hint"] = "opinion"
    return items


def perigon_items():
    items = fixture_json("perigon", "journalist_articles.json")["articles"]
    for item in items:
        item["_src"] = "perigon"
        item["_section_hint"] = "world"
    return items


def rss_items():
    parsed = feedparser.parse(fixture_bytes("rss", "multi_author_publication.xml"))
    for entry in parsed.entries:
        entry["_src"] = "rss"
        entry["_section_hint"] = "opinion"
        entry["_source_name"] = "After Babel"
    return list(parsed.entries)


# --- the original contract still holds ------------------------------------

def test_the_original_seven_keys_are_unchanged():
    for story in normalize(guardian_items() + nyt_items() + perigon_items() + rss_items()):
        for key in CURATION_KEYS:
            assert key in story
        assert story["title"] and story["link"]


def test_items_without_a_title_or_link_are_still_dropped():
    assert normalize([{"_src": "guardian", "webTitle": "", "webUrl": "https://x.com/a"}]) == []
    assert normalize([{"_src": "guardian", "webTitle": "T", "webUrl": ""}]) == []


def test_the_editor_prompt_receives_exactly_the_fields_it_always_did():
    stories = normalize(guardian_items())
    view = curation_view(stories)
    assert all(set(item) == set(CURATION_KEYS) for item in view)
    # Authorship is Hermes' business, not the model's.
    assert all(key not in item for item in view
               for key in ("authors", "byline", "provider", "voice_ids", "canonical_url"))
    # And the projection did not mutate the underlying stories.
    assert stories[0]["authors"]


# --- authorship is preserved ----------------------------------------------

def test_guardian_byline_is_no_longer_discarded():
    story = normalize(guardian_items())[0]
    assert story["byline"] == "George Monbiot"


def test_guardian_contributor_tags_become_stable_author_ids():
    story = normalize(guardian_items())[0]
    assert story["authors"] == [{
        "name": "George Monbiot",
        "source_author_id": "profile/georgemonbiot",
        "source_author_provider": "guardian",
    }]


def test_guardian_keyword_tags_are_not_treated_as_authors():
    joint = normalize(guardian_items())[1]
    assert [a["source_author_id"] for a in joint["authors"]] == [
        "profile/georgemonbiot", "profile/ameliahargreaves"]


def test_nyt_byline_is_retained_and_parsed():
    stories = normalize(nyt_items())
    solo, joint = stories[0], stories[1]
    assert solo["byline"] == "By David Brooks"
    assert solo["authors"] == [{"name": "David Brooks"}]
    assert [a["name"] for a in joint["authors"]] == ["David Brooks", "Marisol Vega"]


def test_nyt_people_mentioned_never_become_authors():
    critique = next(s for s in normalize(nyt_items()) if "Haidt" in s["title"])
    assert [a["name"] for a in critique["authors"]] == ["Nadia Okonjo"]
    assert not any("Haidt" in a["name"] for a in critique["authors"])


def test_an_unsigned_editorial_has_no_authors():
    editorial = next(s for s in normalize(nyt_items()) if "Editorial Board" in s["byline"])
    assert editorial["authors"] == []
    assert editorial["byline"] == "By The Editorial Board"


def test_perigon_journalist_identity_is_retained():
    story = normalize(perigon_items())[0]
    assert story["byline"] == "Jonathan Haidt"
    assert story["authors"][0]["source_author_id"] == "perigon-jhaidt-001"
    assert story["source_article_id"] == "0a1b2c3d4e5f60718293a4b5c6d7e8f9"
    assert story["paywalled"] is True


def test_rss_dc_creator_is_retained():
    stories = normalize(rss_items())
    assert stories[0]["byline"] == "Jonathan Haidt"
    assert [a["name"] for a in stories[1]["authors"]] == ["Zach Rausch", "Jonathan Haidt"]
    assert stories[3]["authors"] == []


def test_every_story_carries_its_provider_and_canonical_url():
    for story in normalize(guardian_items() + nyt_items() + perigon_items() + rss_items()):
        assert story["provider"] in {"guardian", "nyt", "perigon", "rss"}
        assert story["canonical_url"].startswith("https://")
        assert "utm_" not in story["canonical_url"]


def test_an_opaque_feed_guid_is_not_treated_as_an_article_id():
    parsed = feedparser.parse(fixture_bytes("rss", "personal_newsletter.xml"))
    entries = list(parsed.entries)
    for entry in entries:
        entry["_src"] = "rss"
        entry["_section_hint"] = "opinion"
    assert all(story["source_article_id"] == "" for story in normalize(entries))


# --- fetch configuration --------------------------------------------------

def test_guardian_fetch_requests_contributor_tags():
    import inspect

    from src import fetch

    assert '"show-tags": "contributor"' in inspect.getsource(fetch.fetch_guardian)


def test_nyt_opinion_is_fetched_so_a_followed_columnist_costs_nothing_extra():
    assert config.NYT_SECTIONS.get("opinion") == "opinion"

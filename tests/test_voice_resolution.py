"""Attribution: which Voice, if any, wrote this.

The important half of this file is the rejections. Hermes is allowed to miss a
piece; it is not allowed to put someone else's writing under a followed
Voice's name.
"""

from __future__ import annotations

import datetime as dt

from src.voices.model import (
    EVIDENCE_BYLINE_ALIAS,
    EVIDENCE_PROVIDER_ID,
    EVIDENCE_SOURCE_SCOPE,
    Author,
    Observation,
)
from src.voices.resolve import VoiceResolver
from tests.conftest import NOW


def observation(**kwargs) -> Observation:
    base = dict(
        adapter="rss",
        source_key="rss:https://afterbabel.com/feed",
        provider="rss",
        title="An Essay",
        url="https://www.afterbabel.com/p/an-essay",
        canonical_url="https://afterbabel.com/p/an-essay",
        published_at=NOW - dt.timedelta(hours=2),
    )
    base.update(kwargs)
    return Observation(**base)


def voices_of(resolver, obs):
    attributions, _ = resolver.attribute(obs)
    return sorted(a.voice_id for a in attributions)


# --- provider-id evidence -------------------------------------------------

def test_a_registered_contributor_id_attributes_anywhere(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:guardian", provider="guardian",
        url="https://www.theguardian.com/commentisfree/2026/sep/05/rivers",
        canonical_url="https://theguardian.com/commentisfree/2026/sep/05/rivers",
        byline="George Monbiot",
        authors=(Author(name="George Monbiot", provider="guardian", provider_id="profile/georgemonbiot"),),
    )
    attributions, _ = resolver.attribute(obs)
    assert [a.voice_id for a in attributions] == ["george-monbiot"]
    assert attributions[0].evidence == EVIDENCE_PROVIDER_ID
    assert attributions[0].detail == "guardian:profile/georgemonbiot"


def test_provider_id_matching_is_case_insensitive(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        provider="guardian", source_key="pool:guardian",
        authors=(Author(name="G M", provider="guardian", provider_id="PROFILE/GeorgeMonbiot"),),
    )
    assert voices_of(resolver, obs) == ["george-monbiot"]


def test_an_unregistered_provider_id_attributes_nothing(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        provider="guardian", source_key="pool:guardian",
        authors=(Author(name="Rachel Vaughan", provider="guardian", provider_id="profile/rachelvaughan"),),
    )
    assert voices_of(resolver, obs) == []


# --- source-scope evidence ------------------------------------------------

def test_a_personal_newsletter_attributes_by_scope(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        source_key="rss:https://drjordanbpeterson.substack.com/feed",
        title="On Responsibility and Order",
        url="https://drjordanbpeterson.substack.com/p/on-responsibility-and-order",
        canonical_url="https://drjordanbpeterson.substack.com/p/on-responsibility-and-order",
        byline="", authors=(),
    )
    attributions, _ = resolver.attribute(obs)
    assert [a.voice_id for a in attributions] == ["jordan-peterson"]
    assert attributions[0].evidence == EVIDENCE_SOURCE_SCOPE


def test_an_author_archive_attributes_by_scope(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="author_page",
        source_key="author_page:https://nysun.com/author/conrad-black-2",
        provider="nysun.com",
        title="The Long Retreat of the Administrative State",
        url="https://www.nysun.com/article/the-long-retreat",
        canonical_url="https://nysun.com/article/the-long-retreat",
        author_scoped=True,
    )
    assert voices_of(resolver, obs) == ["conrad-black"]


# --- byline evidence, and its scope ---------------------------------------

def test_a_byline_on_a_registered_multi_author_feed_attributes(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(byline="Jonathan Haidt", authors=(Author(name="Jonathan Haidt"),))
    attributions, _ = resolver.attribute(obs)
    assert [a.voice_id for a in attributions] == ["jonathan-haidt"]
    assert attributions[0].evidence == EVIDENCE_BYLINE_ALIAS


def test_an_alias_spelling_attributes(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(byline="Jon Haidt", authors=(Author(name="Jon Haidt"),))
    assert voices_of(resolver, obs) == ["jonathan-haidt"]


def test_another_writer_on_the_same_feed_is_not_the_followed_voice(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(byline="Freya India", authors=(Author(name="Freya India"),))
    assert voices_of(resolver, obs) == []


def test_a_coauthored_piece_attributes_the_followed_author_only(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        byline="Zach Rausch and Jonathan Haidt",
        authors=(Author(name="Zach Rausch"), Author(name="Jonathan Haidt")),
    )
    assert voices_of(resolver, obs) == ["jonathan-haidt"]


def test_the_followed_author_is_found_in_any_byline_position(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    for byline in ("Jonathan Haidt, A B and C D", "A B, Jonathan Haidt and C D", "A B, C D and Jonathan Haidt"):
        obs = observation(byline=byline, authors=())
        assert voices_of(resolver, obs) == ["jonathan-haidt"], byline


def test_a_byline_outside_the_voices_scope_is_rejected(acceptance_registry):
    """The same name on a source the operator never registered is not proof."""
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:perigon", provider="perigon",
        url="https://www.example-news.com/2026/09/05/an-essay",
        canonical_url="https://example-news.com/2026/09/05/an-essay",
        byline="Jonathan Haidt", authors=(Author(name="Jonathan Haidt"),),
    )
    attributions, rejections = resolver.attribute(obs)
    assert attributions == []
    assert [r.reason for r in rejections] == ["byline_out_of_scope"]


def test_a_declared_publication_puts_the_pool_in_scope(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:nyt", provider="nyt",
        url="https://www.nytimes.com/2026/09/05/opinion/the-quiet-part.html",
        canonical_url="https://nytimes.com/2026/09/05/opinion/the-quiet-part.html",
        byline="By David Brooks", authors=(Author(name="David Brooks"),),
    )
    attributions, _ = resolver.attribute(obs)
    assert [a.voice_id for a in attributions] == ["david-brooks"]
    assert "nytimes.com" in attributions[0].detail


def test_a_declared_publication_does_not_extend_to_other_hosts(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:perigon", provider="perigon",
        url="https://www.other-paper.com/opinion/x",
        canonical_url="https://other-paper.com/opinion/x",
        byline="By David Brooks", authors=(Author(name="David Brooks"),),
    )
    assert voices_of(resolver, obs) == []


# --- the ambiguity guard --------------------------------------------------

def test_a_common_name_is_never_attributed_on_a_byline(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:rss",
        url="https://municipal-notes.example.org/2026/09/05/transit-levy",
        canonical_url="https://municipal-notes.example.org/2026/09/05/transit-levy",
        byline="John Smith", authors=(Author(name="John Smith"),),
    )
    attributions, rejections = resolver.attribute(obs)
    assert attributions == []
    assert any(r.reason == "requires_provider_id" for r in rejections)


def test_a_common_name_is_attributed_on_its_registered_id(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:guardian", provider="guardian",
        byline="John Smith",
        authors=(Author(name="John Smith", provider="guardian", provider_id="profile/johnsmith-economics"),),
    )
    assert voices_of(resolver, obs) == ["john-smith"]


# --- what is never evidence -----------------------------------------------

def test_a_name_in_the_title_is_not_authorship(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="pool", source_key="pool:nyt", provider="nyt",
        title="What Jonathan Haidt Missed About Phones",
        url="https://www.nytimes.com/2026/09/05/opinion/haidt-phones-critique.html",
        canonical_url="https://nytimes.com/2026/09/05/opinion/haidt-phones-critique.html",
        byline="By Nadia Okonjo", authors=(Author(name="Nadia Okonjo"),),
    )
    assert voices_of(resolver, obs) == []


def test_a_name_in_the_description_is_not_authorship(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        description="Jonathan Haidt is cited throughout this piece.",
        byline="Priya Raman", authors=(Author(name="Priya Raman"),),
    )
    assert voices_of(resolver, obs) == []


def test_a_missing_byline_attributes_nothing_on_a_byline_source(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(byline="", authors=())
    assert voices_of(resolver, obs) == []


def test_an_organisation_byline_attributes_nothing(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(byline="Reuters", authors=(Author(name="Reuters"),))
    assert voices_of(resolver, obs) == []


def test_a_disabled_voice_is_never_attributed():
    from src.voices.registry import validate

    registry, problems = validate({"version": 1, "voices": [{
        "id": "jonathan-haidt", "name": "Jonathan Haidt", "enabled": False,
        "sources": [{"type": "rss", "url": "https://www.afterbabel.com/feed", "authorship": "byline"}],
    }]})
    assert problems == []
    resolver = VoiceResolver(registry)
    obs = observation(byline="Jonathan Haidt", authors=(Author(name="Jonathan Haidt"),))
    assert voices_of(resolver, obs) == []


def test_a_disabled_source_stops_scoping_its_bylines():
    from src.voices.registry import validate

    registry, problems = validate({"version": 1, "voices": [{
        "id": "jonathan-haidt", "name": "Jonathan Haidt",
        "byline_publications": ["theatlantic.com"],
        "sources": [{"id": "after-babel", "type": "rss", "url": "https://www.afterbabel.com/feed",
                     "authorship": "byline", "enabled": False}],
    }]})
    assert problems == []
    resolver = VoiceResolver(registry)
    obs = observation(byline="Jonathan Haidt", authors=(Author(name="Jonathan Haidt"),))
    assert voices_of(resolver, obs) == []


# --- evidence strength ----------------------------------------------------

def test_the_strongest_evidence_wins_per_voice(acceptance_registry):
    resolver = VoiceResolver(acceptance_registry)
    obs = observation(
        adapter="perigon_journalist",
        source_key="perigon_journalist:perigon-jhaidt-001",
        provider="perigon",
        url="https://www.theatlantic.com/ideas/archive/2026/09/attention/687001/",
        canonical_url="https://theatlantic.com/ideas/archive/2026/09/attention/687001",
        byline="Jonathan Haidt",
        authors=(Author(name="Jonathan Haidt", provider="perigon", provider_id="perigon-jhaidt-001"),),
    )
    attributions, _ = resolver.attribute(obs)
    assert len(attributions) == 1
    assert attributions[0].evidence == EVIDENCE_PROVIDER_ID

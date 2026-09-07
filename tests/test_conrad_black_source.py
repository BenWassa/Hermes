"""Issue #17: Conrad Black through a production-reachable generic author index."""

from __future__ import annotations

import datetime as dt

from src import config
from src.voices.adapters import FetchWindow, get_adapter
from src.voices.discover import discover
from src.voices.following import select_following
from src.voices.model import Author, Observation, VoiceArticle
from src.voices.resolve import VoiceResolver
from src.voices.watch import MODE_FREQUENT, discover_for_watch, notifiable_voice_ids, plan_for_mode
from src.voices.window import EditionWindow, WindowVerdict, classify_article
from tests.conftest import FakeHttp, FakeResponse, fixture_text, registry_from

UTC = dt.timezone.utc
AUDIT_NOW = dt.datetime(2026, 9, 6, 16, 36, 0, tzinfo=UTC)


CONRAD_VOICE = {
    "id": "conrad-black",
    "name": "Conrad Black",
    "enabled": True,
    "notify": True,
    "require_evidence": "provider_id",
    "aliases": ["Conrad M. Black"],
    "provider_ids": [
        {"provider": "nationalnewswatch.com", "id": "/author/conrad-black"},
    ],
    "sources": [
        {
            "id": "national-newswatch-conrad",
            "type": "author_page",
            "url": "https://www.nationalnewswatch.com/author/conrad-black",
            "structural": True,
            "item_tag": "div",
            "item_class": "article",
            "author_path": "/author/conrad-black",
            "allow_external_links": True,
            "authorship": "provider_id",
        }
    ],
}


def registry():
    return registry_from([CONRAD_VOICE])


def http():
    return FakeHttp({
        "nationalnewswatch.com": FakeResponse(
            text=fixture_text("author_pages", "external_author_index.html")
        )
    })


def fetch_window():
    return FetchWindow(since=AUDIT_NOW - dt.timedelta(hours=36), until=AUDIT_NOW)


def edition_window():
    return EditionWindow(since=AUDIT_NOW - dt.timedelta(hours=36), until=AUDIT_NOW)


def watcher_window():
    return EditionWindow(since=AUDIT_NOW - dt.timedelta(hours=24), until=AUDIT_NOW)


def test_external_author_index_uses_stable_author_identity_not_name_matching():
    reg = registry()
    adapter = get_adapter("author_page")
    request = adapter.plan([(reg.active[0], reg.active[0].enabled_sources[0])], fetch_window())[0]
    client = http()

    observations = adapter.fetch(request, client, fetch_window())

    assert len(observations) == 2, "the tracked duplicate collapses and the other author is rejected"
    current = next(o for o in observations if "example-one" in o.canonical_url)
    assert current.canonical_url == "https://nationalpost.com/opinion/example-one"
    assert current.publication == "National Post"
    assert current.byline == "Conrad Black"
    assert [(a.provider, a.provider_id, a.name) for a in current.authors] == [
        ("nationalnewswatch.com", "/author/conrad-black", "Conrad Black")
    ]
    assert current.reprint is False and current.reprint_group_id == ""
    assert client.budget.report() == {"author_page": 1}


def test_wrong_author_block_and_name_only_pool_record_do_not_attribute():
    reg = registry()
    resolver = VoiceResolver(reg)
    name_only = Observation(
        adapter="pool",
        source_key="pool:perigon",
        provider="perigon",
        title="A name-only record",
        url="https://example.com/opinion/name-only",
        canonical_url="https://example.com/opinion/name-only",
        byline="Conrad Black",
        authors=(Author(name="Conrad Black"),),
        published_at=AUDIT_NOW,
    )

    attributions, rejections = resolver.attribute(name_only)

    assert attributions == []
    assert [r.reason for r in rejections] == ["requires_provider_id"]


def test_date_only_publication_intersects_window_without_inventing_midnight():
    reg = registry()
    result = discover(reg, window=edition_window(), http=http())

    current = next(a for a in result.articles if "example-one" in a.canonical_url)
    assert current.published_at == dt.datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    assert current.observations[0].raw_published == "2026-09-05"
    assert classify_article(current, edition_window()) is WindowVerdict.FRESH
    assert current in result.fresh

    older = next(a for a in result.articles if "older-column" in a.canonical_url)
    assert classify_article(older, edition_window()) is WindowVerdict.STALE


def test_exact_midnight_timestamp_keeps_exact_precision():
    exact = dt.datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    observation = Observation(
        adapter="pool",
        source_key="pool:test",
        provider="test",
        title="Exact midnight publication",
        url="https://example.com/exact-midnight",
        canonical_url="https://example.com/exact-midnight",
        published_at=exact,
        raw_published="2026-09-05T00:00:00Z",
    )
    article = VoiceArticle(
        key="url:https://example.com/exact-midnight",
        title=observation.title,
        canonical_url=observation.canonical_url,
        published_at=exact,
        observations=[observation],
    )

    assert classify_article(article, edition_window()) is WindowVerdict.STALE


def test_conrad_source_flows_through_following_and_watcher_contracts():
    reg = registry()
    result = discover(reg, window=edition_window(), http=http())

    assert result.budget == {"author_page": 1}
    assert len(result.articles) == 2
    current = next(a for a in result.articles if "example-one" in a.canonical_url)
    assert current.voice_ids == ["conrad-black"]
    assert current.evidence_for("conrad-black").evidence == "provider_author_id"
    assert current.syndication_group == "" and current.syndication_primary is True

    chosen = select_following(
        result.fresh,
        cap=config.VOICE_FOLLOWING_CAP,
        per_voice=config.VOICE_MAX_PER_VOICE,
    )
    assert [a.key for a in chosen] == [current.key]
    assert notifiable_voice_ids(current, reg) == ["conrad-black"]

    planned = plan_for_mode(reg, fetch_window(), MODE_FREQUENT)
    assert len(planned) == 1
    assert planned[0].adapter == "author_page"

    watch_result, planned_count = discover_for_watch(
        reg,
        window=watcher_window(),
        mode=MODE_FREQUENT,
        http=http(),
    )
    assert planned_count == 1
    assert watch_result.budget == {"author_page": 1}
    assert [a.voice_ids for a in watch_result.fresh] == [["conrad-black"]]

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

from tests.conftest import FakeHttp, FakeResponse, FakeStore, registry_from, rss_feed
from src.voices.model import Attribution, EVIDENCE_SOURCE_SCOPE, VoiceArticle
from src.voices.notify import RecordingNotifier
from src.voices.release import (
    GeminiSummaryProvider,
    PagePublisher,
    ReleasePreparer,
    ReleaseSummary,
    SummaryProvider,
    article_page_path,
    article_page_url,
    source_material,
)
from src.voices.release_runtime import ReleaseNotifier, core_alert_registry
from src.voices.state import WatchState
from src.voices.watch import run_watch

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
CORE_FEED = "https://core.example/feed"
SELECTIVE_FEED = "https://selective.example/feed"


class FixedSummary(SummaryProvider):
    def __init__(self):
        self.calls = 0

    def summarize(self, article, *, writers):
        self.calls += 1
        return ReleaseSummary(
            thesis="The writer argues that institutional trust depends on visible accountability.",
            takeaways=(
                "Accountability has to be observable, not merely promised.",
                "Institutional incentives shape whether reforms endure.",
                "The proposed remedy emphasizes transparent feedback loops.",
            ),
            why_it_matters="The argument connects institutional design to public confidence.",
        )


class RaisingSummary(SummaryProvider):
    def summarize(self, article, *, writers):
        raise RuntimeError("simulated model outage")


class MemoryPublisher(PagePublisher):
    def __init__(self, *, succeed=True):
        self.succeed = succeed
        self.pages: dict[str, str] = {}
        self.calls = 0

    def publish(self, path, page_html, message):
        self.calls += 1
        if self.succeed:
            self.pages[str(path)] = page_html
        return self.succeed


def article(*, description="A public description with enough detail to support a cautious summary. " * 3,
            paywalled=False):
    return VoiceArticle(
        key="url:https://publisher.example/essay",
        title="Why Institutions Need Visible Accountability",
        canonical_url="https://publisher.example/essay",
        url="https://www.publisher.example/essay",
        publication="Example Review",
        description=description,
        published_at=NOW - dt.timedelta(hours=1),
        paywalled=paywalled,
        identity_keys=frozenset({"url:https://publisher.example/essay"}),
        attributions=[Attribution(
            voice_id="core-writer", evidence=EVIDENCE_SOURCE_SCOPE, detail="test"
        )],
    )


def registry():
    return registry_from([{
        "id": "core-writer",
        "name": "Core Writer",
        "tier": "core",
        "notify": False,
        "sources": [{
            "id": "core-feed", "type": "rss", "url": CORE_FEED,
            "publication": "Example Review", "authorship": "scope",
        }],
    }])


def seeded_store():
    return FakeStore(WatchState(last_reconcile_at=NOW, updated_at=NOW).dumps())


def test_release_preparer_builds_stable_hermes_page_and_restrained_alert(monkeypatch):
    monkeypatch.setattr("src.voices.release.config.SITE_URL", "https://example.github.io/Hermes/")
    reg = registry()
    item = article()
    summarizer = FixedSummary()
    publisher = MemoryPublisher()
    preparer = ReleasePreparer(summarizer=summarizer, publisher=publisher)

    prepared = preparer.prepare(item, reg, voice_ids=("core-writer",))

    assert summarizer.calls == 1
    assert prepared.page_published is True
    assert prepared.alert.title == "Core Writer — Why Institutions Need Visible Accountability"
    assert prepared.alert.message == "Accountability has to be observable, not merely promised."
    assert prepared.alert.click == article_page_url(item)
    assert "/voices/articles/" in prepared.alert.click
    assert prepared.alert.as_payload("topic")["priority"] == 3
    assert prepared.alert.as_payload("topic")["tags"] == ["memo"]

    page = publisher.pages[str(article_page_path(item))]
    assert "Core Writer" in page
    assert "Example Review" in page
    assert "Why Institutions Need Visible Accountability" in page
    assert "Key takeaways" in page
    assert "Why it matters" in page
    assert "Read original" in page
    assert 'href="https://www.publisher.example/essay"' in page


def test_model_failure_renders_honest_metadata_fallback_instead_of_losing_alert(monkeypatch):
    monkeypatch.setattr("src.voices.release.config.SITE_URL", "https://example.github.io/Hermes/")
    publisher = MemoryPublisher()
    prepared = ReleasePreparer(
        summarizer=RaisingSummary(), publisher=publisher
    ).prepare(article(), registry(), voice_ids=("core-writer",))

    assert prepared.summary_fallback is True
    assert prepared.page_published is True
    assert "/voices/articles/" in prepared.alert.click
    page = publisher.pages[str(article_page_path(article()))]
    assert "Model summary generation was unavailable" in page
    assert "Read original" in page


def test_render_failure_falls_back_to_original_publisher_link_without_raising():
    def broken_renderer(*args, **kwargs):
        raise RuntimeError("template broke")

    publisher = MemoryPublisher()
    prepared = ReleasePreparer(
        summarizer=FixedSummary(), publisher=publisher, renderer=broken_renderer
    ).prepare(article(), registry(), voice_ids=("core-writer",))

    assert prepared.page_published is False
    assert prepared.alert.click == "https://www.publisher.example/essay"
    assert publisher.calls == 0


def test_page_publish_failure_falls_back_to_original_link():
    prepared = ReleasePreparer(
        summarizer=FixedSummary(), publisher=MemoryPublisher(succeed=False)
    ).prepare(article(), registry(), voice_ids=("core-writer",))
    assert prepared.page_published is False
    assert prepared.alert.click == "https://www.publisher.example/essay"


def test_limited_paywalled_metadata_skips_gemini_and_degrades_honestly():
    class ExplodingModels:
        def generate_content(self, **kwargs):
            raise AssertionError("Gemini must not be called for thin metadata")

    provider = GeminiSummaryProvider(client=SimpleNamespace(models=ExplodingModels()))
    item = article(description="Short public deck.", paywalled=True)
    material, rich = source_material(item)
    summary = provider.summarize(item, writers="Core Writer")

    assert material == "Short public deck."
    assert rich is False
    assert "publisher-provided description metadata" in summary.limitation
    assert summary.takeaways == ()


def test_rich_metadata_causes_one_logical_gemini_generation():
    calls = []

    class Models:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=json.dumps({
                "thesis": "A concise thesis grounded in the supplied description.",
                "takeaways": ["First supported point.", "Second supported point."],
                "why_it_matters": "It clarifies the policy trade-off.",
            }))

    provider = GeminiSummaryProvider(
        client=SimpleNamespace(models=Models()), model="gemini-2.5-flash", retries=0
    )
    summary = provider.summarize(article(), writers="Core Writer")

    assert len(calls) == 1
    assert summary.takeaways == ("First supported point.", "Second supported point.")
    supplied = json.loads(calls[0]["contents"])
    assert "available_public_description_material" in supplied
    assert "body" not in supplied


def test_core_tier_is_release_authority_even_when_legacy_notify_values_disagree():
    reg = registry_from([
        {
            "id": "core-writer", "name": "Core Writer", "tier": "core", "notify": False,
            "sources": [{"id": "core", "type": "rss", "url": CORE_FEED,
                         "publication": "Core", "authorship": "scope"}],
        },
        {
            "id": "selective-writer", "name": "Selective Writer", "tier": "selective", "notify": True,
            "sources": [{"id": "selective", "type": "rss", "url": SELECTIVE_FEED,
                         "publication": "Selective", "authorship": "scope"}],
        },
        {
            "id": "discovery-writer", "name": "Discovery Writer", "tier": "discovery", "notify": True,
            "dormant": True,
        },
    ])
    release_reg = core_alert_registry(reg)
    assert [voice.id for voice in release_reg.voices] == ["core-writer"]
    assert release_reg.voices[0].notify is True  # compatibility only, after tier filter


def test_one_core_article_produces_one_page_and_at_most_once_alert(monkeypatch):
    monkeypatch.setattr("src.voices.release.config.SITE_URL", "https://example.github.io/Hermes/")
    release_reg = core_alert_registry(registry())
    summarizer = FixedSummary()
    publisher = MemoryPublisher()
    downstream = RecordingNotifier()
    notifier = ReleaseNotifier(
        delegate=downstream,
        preparer=ReleasePreparer(summarizer=summarizer, publisher=publisher),
        registry=release_reg,
    )
    feed = rss_feed([{
        "title": "Why Institutions Need Visible Accountability",
        "link": "https://www.publisher.example/essay",
        "published": "Thu, 10 Sep 2026 14:00:00 +0000",
    }], title="Example Review")
    store = seeded_store()

    kwargs = dict(
        store=store, notifier=notifier, now=NOW, quiet_hours=None,
        lookback=dt.timedelta(hours=24), retention=dt.timedelta(days=14),
        max_entries=500, max_alerts=5, reconcile_every=dt.timedelta(hours=24),
        push_attempts=3,
    )
    first = run_watch(
        release_reg, http=FakeHttp({CORE_FEED: FakeResponse(text=feed)}), **kwargs
    )
    second = run_watch(
        release_reg, http=FakeHttp({CORE_FEED: FakeResponse(text=feed)}), **kwargs
    )

    assert first.delivered == 1
    assert second.delivered == 0
    assert summarizer.calls == 1
    assert publisher.calls == 1
    assert len(downstream.sent) == 1
    assert "/voices/articles/" in downstream.sent[0].click


def test_gemini_and_page_work_never_start_when_claim_cannot_be_persisted():
    release_reg = core_alert_registry(registry())
    summarizer = FixedSummary()
    publisher = MemoryPublisher()
    downstream = RecordingNotifier()
    notifier = ReleaseNotifier(
        delegate=downstream,
        preparer=ReleasePreparer(summarizer=summarizer, publisher=publisher),
        registry=release_reg,
    )
    feed = rss_feed([{
        "title": "Why Institutions Need Visible Accountability",
        "link": "https://www.publisher.example/essay",
        "published": "Thu, 10 Sep 2026 14:00:00 +0000",
    }])
    store = FakeStore(seeded_store().content, reject=99)

    outcome = run_watch(
        release_reg, store=store, notifier=notifier,
        http=FakeHttp({CORE_FEED: FakeResponse(text=feed)}), now=NOW,
        quiet_hours=None, lookback=dt.timedelta(hours=24), retention=dt.timedelta(days=14),
        max_entries=500, max_alerts=5, reconcile_every=dt.timedelta(hours=24), push_attempts=3,
    )

    assert outcome.persisted is False
    assert summarizer.calls == 0
    assert publisher.calls == 0
    assert downstream.sent == []

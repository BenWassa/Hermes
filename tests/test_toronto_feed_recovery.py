"""Offline source-availability tests for the conditional Toronto journalism fallback."""
from __future__ import annotations

from src import config, fetch


def test_toronto_fallback_not_requested_when_a_primary_feed_has_articles(monkeypatch):
    calls = []
    primary = [{"title": "Toronto council announces transit plan"}]

    def fake(feeds, *, default_hint, default_coverage_lane=None):
        calls.append((feeds, default_hint))
        return primary

    monkeypatch.setattr(fetch, "_fetch_rss_feeds", fake)
    assert fetch.fetch_toronto_rss() is primary
    assert calls == [(config.TORONTO_RSS, "toronto")]


def test_toronto_fallback_only_on_empty_primary_and_is_bounded(monkeypatch):
    calls = []
    fallback = [{"title": f"Toronto report {i}"} for i in range(40)]

    def fake(feeds, *, default_hint, default_coverage_lane=None):
        calls.append((feeds, default_hint))
        return [] if feeds is config.TORONTO_RSS else fallback

    monkeypatch.setattr(fetch, "_fetch_rss_feeds", fake)
    result = fetch.fetch_toronto_rss()
    assert len(result) == 25
    assert calls == [
        (config.TORONTO_RSS, "toronto"),
        ([config.TORONTO_FALLBACK_RSS], "toronto"),
    ]


def test_toronto_fallback_failure_is_safe_and_does_not_invent_articles(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_rss_feeds", lambda *args, **kwargs: [])
    assert fetch.fetch_toronto_rss() == []

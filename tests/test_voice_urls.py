"""Canonical URLs and article identity keys."""

from __future__ import annotations

import pytest

from src.voices.urls import canonical_url, fingerprint_key, syndication_key, title_slug, url_host


@pytest.mark.parametrize("raw,expected", [
    ("https://www.theguardian.com/commentisfree/2026/sep/05/a-piece?CMP=share_btn_url",
     "https://theguardian.com/commentisfree/2026/sep/05/a-piece"),
    ("https://www.afterbabel.com/p/attention?utm_source=substack&utm_medium=email&utm_campaign=x",
     "https://afterbabel.com/p/attention"),
    ("http://theguardian.com/commentisfree/2026/sep/05/a-piece",
     "https://theguardian.com/commentisfree/2026/sep/05/a-piece"),
    ("https://amp.theguardian.com/commentisfree/2026/sep/05/a-piece/amp/",
     "https://theguardian.com/commentisfree/2026/sep/05/a-piece"),
    ("https://www.nytimes.com/2026/09/05/opinion/x.html?smid=tw-share#comments",
     "https://nytimes.com/2026/09/05/opinion/x.html"),
    ("https://m.example.com//double//slash/",
     "https://example.com/double/slash"),
])
def test_noise_is_removed(raw, expected):
    assert canonical_url(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "not a url", "ftp://example.com/x", "/relative/path", "javascript:void(0)"])
def test_non_urls_are_rejected(raw):
    assert canonical_url(raw) == ""


def test_meaningful_query_parameters_survive():
    # Paginated and id-bearing URLs are genuinely different pages.
    assert canonical_url("https://example.com/archive?page=3") == "https://example.com/archive?page=3"
    assert canonical_url("https://example.com/story?id=42&utm_source=x") == "https://example.com/story?id=42"


def test_distinct_articles_stay_distinct():
    a = canonical_url("https://example.com/2026/09/05/one")
    b = canonical_url("https://example.com/2026/09/05/two")
    assert a != b


def test_different_hosts_never_collapse():
    assert canonical_url("https://nysun.com/article/x") != canonical_url("https://partner.com/article/x")


def test_short_host_prefix_is_not_stripped_from_a_two_label_domain():
    # "m.co" style two-label hosts must not lose their first label.
    assert url_host("https://www.bbc.co.uk/news/x") == "bbc.co.uk"


def test_fingerprint_requires_all_three_components():
    assert fingerprint_key("https://example.com/a", "A Title", "2026-09-05")
    assert fingerprint_key("https://example.com/a", "A Title", None) == ""
    assert fingerprint_key("https://example.com/a", "", "2026-09-05") == ""
    assert fingerprint_key("", "A Title", "2026-09-05") == ""


def test_fingerprint_is_host_scoped():
    left = fingerprint_key("https://a.example.com/x", "Same Headline", "2026-09-05")
    right = fingerprint_key("https://b.example.com/x", "Same Headline", "2026-09-05")
    assert left != right


def test_syndication_key_requires_an_author():
    assert syndication_key("A Title", "voice:x", "2026-09-05")
    assert syndication_key("A Title", "", "2026-09-05") == ""


def test_title_slug_is_bounded():
    slug = title_slug("one two three four five six seven eight nine ten eleven twelve thirteen")
    assert slug.count("-") == 11

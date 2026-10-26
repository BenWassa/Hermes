"""Source identity/time regression coverage for #96 (no live network)."""
from __future__ import annotations

import datetime as dt

from src.editorial_integrity import _toronto_time, restore_source_metadata

TODAY = dt.date(2026, 10, 25)


def _source(slug: str, pub_date: str = "2026-10-25T08:00:58Z", *, title: str = "Source"):
    return {
        "title": title,
        "link": f"https://www.theguardian.com/world/2026/oct/24/{slug}",
        "canonical_url": f"https://theguardian.com/world/2026/oct/24/{slug}",
        "pub_date": pub_date,
    }


def _card(link: str, time: str = "8:00 AM"):
    return {"headline": "Composed headline", "summary": "Sourced analysis",
            "link": link, "time": time, "lead": True}


def test_exact_source_identity_restores_publisher_navigation_and_toronto_clock():
    src = _source("ukraine-live")
    card = _card("https://theguardian.com/world/2026/oct/24/ukraine-live", "8:00 AM")
    sections = [{"id": "front", "stories": [card]}]
    stats = restore_source_metadata(sections, [src], TODAY)

    assert card["link"] == src["link"]  # original publisher destination, not normalized host
    assert card["time"] == "4:00 AM"  # 08:00Z is 04:00 EDT
    assert stats == {"repaired_links": 1, "adjusted_times": 1, "unmatched": 0}


def test_minor_source_slug_drift_corrected_only_inside_unique_same_host_and_date():
    src = _source("israel-soldiers-raze-west-bank-neighbourhood-hebron-families-from-homes")
    card = _card(src["link"].replace("neighbourhood", "neighborhood"))
    stats = restore_source_metadata([{"id": "world", "stories": [card]}], [src], TODAY)
    assert card["link"] == src["link"]
    assert stats["repaired_links"] == 1


def test_minor_slug_punctuation_drift_is_recoverable_without_title_guessing():
    src = _source("ukraine-war-briefing-russian-diesel-tankers-headed-for-north-america-says-moscow-as-us-tries-to-revive-peace-talks")
    card = _card(src["link"].replace("briefing-", "briefing:"))
    restore_source_metadata([{"id": "world", "stories": [card]}], [src], TODAY)
    assert card["link"] == src["link"]


def test_ambiguous_near_identical_slugs_never_pick_arbitrary_source():
    a = _source("same-long-date-slug-report-alpha")
    b = _source("same-long-date-slug-report-alphb")
    link = "https://www.theguardian.com/world/2026/oct/24/same-long-date-slug-report-alphc"
    card = _card(link)
    stats = restore_source_metadata([{"id": "front", "stories": [card]}], [a, b], TODAY)
    assert card["link"] == link
    assert stats["unmatched"] == 1


def test_cross_host_and_date_do_not_fuzzy_link_to_unrelated_article():
    src = _source("long-interesting-report-of-the-day")
    altered = [
        "https://another.example/world/2026/oct/24/long-interesting-report-of-the-day",
        "https://www.theguardian.com/world/2026/oct/25/long-interesting-report-of-the-day",
        "https://www.theguardian.com/world/2026/oct/24/different-topic-altogether",
    ]
    for link in altered:
        card = _card(link)
        stats = restore_source_metadata([{"id": "front", "stories": [card]}], [src], TODAY)
        assert stats["unmatched"] == 1
        assert card["link"] == link


def test_time_display_is_deterministic_across_toronto_dst_and_day_rollover():
    assert _toronto_time("2026-10-25T08:00:58Z", TODAY) == "4:00 AM"
    assert _toronto_time("2026-10-26T10:56:31Z", dt.date(2026, 10, 26)) == "6:56 AM"
    assert _toronto_time("2026-10-26T01:00:00Z", TODAY) == "9:00 PM"
    assert _toronto_time("2026-10-25T01:00:00Z", TODAY) == "Yesterday"
    assert _toronto_time("2026-11-01T06:30:00Z", dt.date(2026, 11, 1)) == "1:30 AM"
    assert _toronto_time("2026-03-08T07:30:00Z", dt.date(2026, 3, 8)) == "3:30 AM"
    assert _toronto_time("2026-10-25T08:00:58", TODAY) is None
    assert _toronto_time("not a timestamp", TODAY) is None


def test_unmatched_and_deterministic_toronto_backfill_are_not_rewritten():
    unknown = _card("https://unmatched.example/article")
    source_created = dict(_card("https://theguardian.com/world/2026/oct/24/news"), backfill=True)
    stats = restore_source_metadata(
        [{"id": "toronto", "stories": [unknown, source_created]}],
        [_source("news")], TODAY,
    )
    assert stats["unmatched"] == 1
    assert unknown["link"] == "https://unmatched.example/article"
    assert source_created["time"] == "8:00 AM"

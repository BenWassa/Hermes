from __future__ import annotations

import datetime as dt

from src import canada
from src.curate import _trim_input
from src.normalize import curation_view, normalize


def _story(
    index: int,
    *,
    section: str = "world",
    title: str | None = None,
    description: str = "",
    coverage_lane: str = "",
    canonical_url: str | None = None,
) -> dict:
    return {
        "title": title or f"Routine story {index}",
        "description": description,
        "source": "Fixture Wire",
        "section_hint": section,
        "pub_date": "2026-09-13T08:00:00Z",
        "image": None,
        "link": f"https://example.com/{index}",
        "canonical_url": canonical_url or f"https://example.com/{index}",
        "coverage_lane": coverage_lane,
    }


def test_perigon_canada_lane_replaces_redundant_markets_without_more_requests():
    base = [
        {"label": "world", "hint": "world", "params": {"country": ["us", "gb", "ca"]}},
        {"label": "business", "hint": "business", "params": {"category": ["Business"]}},
        {"label": "markets", "hint": "business", "params": {"q": "markets"}},
    ]

    queries = canada.perigon_queries(base)

    assert len(queries) == len(base)
    assert [query["label"] for query in queries] == ["world", "business", "canada"]
    assert queries[-1]["params"]["country"] == ["ca"]
    assert queries[-1]["coverage_lane"] == canada.CANADA_COVERAGE_LANE


def test_cbc_national_feed_is_single_bounded_journalism_source():
    assert canada.CANADA_RSS == [
        {
            "name": "CBC Canada",
            "url": "https://www.cbc.ca/webfeed/rss/rss-canada",
            "hint": "world",
            "coverage_lane": canada.CANADA_COVERAGE_LANE,
        }
    ]


def test_normalize_preserves_coverage_lane_but_model_view_does_not():
    raw = [
        {
            "_src": "rss",
            "_section_hint": "world",
            "_coverage_lane": canada.CANADA_COVERAGE_LANE,
            "_source_name": "CBC Canada",
            "title": "Canada announces major industrial policy",
            "summary": "National economic policy with material investment consequences.",
            "link": "https://www.cbc.ca/news/canada/example",
            "published": "2026-09-13T08:00:00Z",
        }
    ]

    story = normalize(raw)[0]

    assert story["coverage_lane"] == canada.CANADA_COVERAGE_LANE
    assert "coverage_lane" not in curation_view([story])[0]


def test_busy_global_pool_cannot_crow_out_canada_national_candidate():
    stories = []
    for index in range(12):
        stories.append(_story(index, section="world"))
        stories.append(_story(100 + index, section="business"))

    canada_story = _story(
        999,
        section="world",
        title="Ottawa unveils nationally significant productivity package",
        coverage_lane=canada.CANADA_COVERAGE_LANE,
    )
    stories.append(canada_story)

    selected = _trim_input(stories, total=8, today=dt.date(2026, 9, 13))

    assert len(selected) == 8
    assert canada_story in selected


def test_investment_summit_regression_survives_without_lane_tag():
    stories = []
    for index in range(15):
        stories.append(_story(index, section="world"))
        stories.append(_story(100 + index, section="business"))

    summit = _story(
        999,
        section="business",
        title="Carney pitches Canada to global capital at investment summit",
        description=(
            "The Canada Investment Summit in Toronto aims to catalyse $1 trillion "
            "of investment over five years."
        ),
    )
    stories.append(summit)

    selected = _trim_input(stories, total=10, today=dt.date(2026, 9, 13))

    assert summit in selected
    assert canada.matching_major_event_ids(summit, dt.date(2026, 9, 13)) == (
        "canada-investment-summit-2026",
    )


def test_major_event_seed_expires_and_does_not_force_stale_priority():
    stories = []
    for index in range(10):
        stories.append(_story(index, section="world"))
        stories.append(_story(100 + index, section="business"))

    stale_summit = _story(
        999,
        section="business",
        title="Carney pitches Canada to global capital at investment summit",
        description="Canada Investment Summit follow-up.",
    )
    stories.append(stale_summit)

    selected = _trim_input(stories, total=6, today=dt.date(2026, 9, 17))

    assert canada.matching_major_event_ids(stale_summit, dt.date(2026, 9, 17)) == ()
    assert stale_summit not in selected


def test_exact_canonical_duplicate_does_not_consume_two_bounded_slots():
    duplicate_a = _story(
        1,
        title="Canada Investment Summit draws global investors",
        coverage_lane=canada.CANADA_COVERAGE_LANE,
        canonical_url="https://example.com/summit",
    )
    duplicate_b = _story(
        2,
        title="Canada Investment Summit draws global investors",
        coverage_lane=canada.CANADA_COVERAGE_LANE,
        canonical_url="https://example.com/summit",
    )
    others = [_story(10 + index, section="business") for index in range(5)]

    selected = _trim_input(
        [duplicate_a, duplicate_b, *others],
        total=6,
        today=dt.date(2026, 9, 13),
    )

    duplicates = [story for story in selected if story["canonical_url"] == "https://example.com/summit"]
    assert len(duplicates) == 1

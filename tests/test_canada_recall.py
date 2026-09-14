from __future__ import annotations

import datetime as dt
import logging

from src import canada
from src.curate import _curation_view, _log_major_event_coverage, _trim_input
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


def _summit(index: int = 999) -> dict:
    return _story(
        index,
        section="business",
        title="Carney pitches Canada to global capital at investment summit",
        description=(
            "The Canada Investment Summit in Toronto aims to catalyse $1 trillion "
            "of investment over five years."
        ),
    )


def test_perigon_canada_lane_replaces_redundant_markets_without_more_requests():
    base = [
        {"label": "world", "hint": "world", "params": {"country": ["us", "gb", "ca"]}},
        {"label": "business", "hint": "business", "params": {"category": ["Business"]}},
        {"label": "markets", "hint": "business", "params": {"q": "markets"}},
    ]

    queries = canada.perigon_queries(base)

    assert len(queries) == len(base)
    assert [query["label"] for query in queries] == ["canada", "world", "business"]
    assert queries[0]["params"]["country"] == ["ca"]
    assert queries[0]["coverage_lane"] == canada.CANADA_COVERAGE_LANE


def test_perigon_query_shape_never_adds_a_request_when_replaceable_lane_is_absent():
    base = [
        {"label": "world", "hint": "world", "params": {}},
        {"label": "business", "hint": "business", "params": {}},
    ]

    assert canada.perigon_queries(base) == base


def test_cbc_national_feed_is_single_bounded_journalism_source():
    assert canada.CANADA_RSS == [
        {
            "name": "CBC Canada",
            "url": "https://www.cbc.ca/webfeed/rss/rss-canada",
            "hint": "world",
            "coverage_lane": canada.CANADA_COVERAGE_LANE,
        }
    ]


def test_normalize_preserves_coverage_lane_but_standard_model_view_does_not():
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

    summit = _summit()
    stories.append(summit)

    selected = _trim_input(stories, total=10, today=dt.date(2026, 9, 13))

    assert summit in selected
    assert canada.matching_major_event_ids(summit, dt.date(2026, 9, 13)) == (
        "canada-investment-summit-2026",
    )


def test_active_event_match_gets_transient_priority_and_ordinary_canada_does_not():
    today = dt.date(2026, 9, 14)
    summit = _summit()
    ordinary_canada = _story(
        1000,
        title="Ottawa updates a routine federal program",
        coverage_lane=canada.CANADA_COVERAGE_LANE,
    )

    model_view = _curation_view([summit, ordinary_canada], today)

    assert len(model_view) == 2
    assert model_view[0]["editorial_priority"] == (
        "active scheduled major event: Canada Investment Summit 2026"
    )
    assert "editorial_priority" not in model_view[1]
    assert "coverage_lane" not in model_view[0]
    assert "coverage_lane" not in model_view[1]


def test_transient_priority_does_not_change_bounded_input_count():
    today = dt.date(2026, 9, 14)
    selected = _trim_input(
        [_story(i) for i in range(20)] + [_summit()],
        total=8,
        today=today,
    )
    view = _curation_view(selected, today)

    assert len(selected) == 8
    assert len(view) == 8
    assert sum("editorial_priority" in item for item in view) == 1


def test_active_event_instruction_sets_explicit_but_not_unconditional_editorial_expectation():
    instruction = canada.editorial_instruction(dt.date(2026, 9, 14))

    assert "editorial_priority" in instruction
    assert "normally\ninclude at least one distinct treatment" in instruction
    assert "Do not create a story from the event seed" in instruction
    assert "do not manufacture Canadian filler" in instruction


def test_major_event_seed_expires_and_removes_recall_and_editorial_priority():
    stories = []
    for index in range(10):
        stories.append(_story(index, section="world"))
        stories.append(_story(100 + index, section="business"))

    stale_summit = _summit()
    stories.append(stale_summit)
    expired = dt.date(2026, 9, 17)

    selected = _trim_input(stories, total=6, today=expired)

    assert canada.matching_major_event_ids(stale_summit, expired) == ()
    assert canada.editorial_priority(stale_summit, expired) == ""
    assert "ACTIVE SCHEDULED MAJOR EVENTS" not in canada.editorial_instruction(expired)
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


def test_final_event_coverage_recognizes_exact_selected_input():
    today = dt.date(2026, 9, 14)
    summit = _summit()
    sections = [
        {
            "id": "business",
            "stories": [
                {
                    "headline": "Canada investment summit opens in Toronto",
                    "summary": "Carney is courting global capital.",
                    "link": summit["link"],
                }
            ],
        }
    ]

    status = canada.final_event_coverage(sections, [summit], today)[
        "canada-investment-summit-2026"
    ]

    assert status["input"] == 1
    assert status["selected"] == 1
    assert status["sections"] == ["business"]


def test_stronger_duplicate_treatment_counts_as_event_coverage_without_same_link():
    today = dt.date(2026, 9, 14)
    summit = _summit()
    sections = [
        {
            "id": "front",
            "stories": [
                {
                    "headline": "Carney opens Canada Investment Summit with global capital pitch",
                    "summary": "The summit is aimed at major investment commitments.",
                    "link": "https://stronger.example/reporting",
                }
            ],
        }
    ]

    status = canada.final_event_coverage(sections, [summit], today)[
        "canada-investment-summit-2026"
    ]

    assert status["input"] == 1
    assert status["selected"] == 1
    assert status["sections"] == ["front"]


def test_final_selection_observability_reports_an_omitted_protected_event(caplog):
    today = dt.date(2026, 9, 14)
    summit = _summit()

    with caplog.at_level(logging.INFO, logger="the-daily.curate"):
        _log_major_event_coverage(
            [{"id": "business", "stories": [_story(42)]}],
            [summit],
            today,
        )

    assert (
        "major-event final id=canada-investment-summit-2026 input=1 "
        "selected=0 sections=none"
    ) in caplog.text

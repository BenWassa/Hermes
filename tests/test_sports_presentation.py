import datetime as dt

import pytest

from src.sports import BLUE_JAYS, LEAFS, RAPTORS
from src.sports.event_news import EventArticle
from src.sports.headlines import QualifiedHeadline, Significance, SportsHeadlineCandidate
from src.sports.models import SeasonPhase, TeamSnapshot, UTC
from src.sports.presentation import MAX_MAJOR_HEADLINES, TEAM_ORDER, build_sports_payload


def snapshot(team, *, available=True):
    return TeamSnapshot(
        team=team,
        phase=SeasonPhase.REGULAR,
        source="fixture",
        fetched_at=dt.datetime(2026, 9, 11, 10, tzinfo=UTC),
        available=available,
        error=None if available else "source_unavailable",
    )


def qualified(team_key):
    candidate = SportsHeadlineCandidate(
        title="Toronto makes a material roster move",
        description="A verified major development.",
        url="https://example.com/team-update",
        source="The Guardian",
        published_at=dt.datetime(2026, 9, 11, 8, tzinfo=UTC),
        team_key=team_key,
    )
    return QualifiedHeadline(candidate, team_key, Significance.MAJOR_TRANSACTION)


def event_article(index):
    return EventArticle(
        event_key="nfl-postseason",
        title=f"Major event headline {index}",
        description="A selective event exception.",
        url=f"https://example.com/event-{index}",
        source="The Guardian",
        published_at=dt.datetime(2026, 1, 20, 12, index, tzinfo=UTC),
    )


def test_payload_preserves_permanent_reader_order_and_attaches_team_headline_once():
    payload = build_sports_payload(
        [snapshot(BLUE_JAYS), snapshot(LEAFS), snapshot(RAPTORS)],
        team_headlines={"raptors": qualified("raptors")},
    )

    assert [row["snapshot"]["team"]["key"] for row in payload["toronto"]] == list(TEAM_ORDER)
    assert payload["toronto"][0]["headline"] is None
    assert payload["toronto"][1]["headline"]["team_key"] == "raptors"
    assert payload["toronto"][2]["headline"] is None
    assert payload["major_headlines"] == []
    assert payload["major_events"] == {"event_mode": False, "max_items": 6, "events": []}


def test_payload_keeps_unavailable_team_instead_of_dropping_row():
    payload = build_sports_payload(
        [snapshot(LEAFS, available=False), snapshot(RAPTORS), snapshot(BLUE_JAYS)]
    )
    leafs = payload["toronto"][0]["snapshot"]
    assert leafs["team"]["key"] == "leafs"
    assert leafs["available"] is False
    assert leafs["error"] == "source_unavailable"


def test_payload_rejects_missing_duplicate_or_mismatched_team_state():
    with pytest.raises(ValueError, match="missing permanent"):
        build_sports_payload([snapshot(LEAFS), snapshot(RAPTORS)])

    with pytest.raises(ValueError, match="duplicate"):
        build_sports_payload(
            [snapshot(LEAFS), snapshot(LEAFS), snapshot(RAPTORS), snapshot(BLUE_JAYS)]
        )

    with pytest.raises(ValueError, match="headline team mismatch"):
        build_sports_payload(
            [snapshot(LEAFS), snapshot(RAPTORS), snapshot(BLUE_JAYS)],
            team_headlines={"leafs": qualified("raptors")},
        )


def test_global_major_headlines_are_recent_first_and_hard_capped():
    payload = build_sports_payload(
        [snapshot(LEAFS), snapshot(RAPTORS), snapshot(BLUE_JAYS)],
        major_headlines=[event_article(i) for i in range(MAX_MAJOR_HEADLINES + 3)],
    )
    assert len(payload["major_headlines"]) == MAX_MAJOR_HEADLINES
    assert payload["major_headlines"][0]["headline"] == "Major event headline 6"
    assert payload["major_headlines"][-1]["headline"] == "Major event headline 3"


def test_payload_contains_no_logo_or_team_palette_contract():
    payload = build_sports_payload([snapshot(LEAFS), snapshot(RAPTORS), snapshot(BLUE_JAYS)])
    text = repr(payload).lower()
    assert "logo" not in text
    assert "team_color" not in text
    assert "team_colour" not in text

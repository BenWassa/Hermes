import datetime as dt
from dataclasses import replace

from src.sports.events import (
    EVENT_REGISTRY,
    EventHighlight,
    EventMatch,
    EventMatchStatus,
    EventSnapshot,
    active_event_specs,
    build_major_events_desk,
    event_article_queries,
    select_event_matches,
    select_olympic_highlights,
)
from src.sports.major_events import build_major_events

UTC = dt.timezone.utc


def spec(key):
    return next(item for item in EVENT_REGISTRY if item.key == key)


def match(identifier, when, *, status=EventMatchStatus.SCHEDULED, canada=False):
    return EventMatch(
        provider_id=identifier,
        start_time_utc=when,
        home_team="Canada" if canada else f"Home {identifier}",
        away_team=f"Away {identifier}",
        status=status,
        canada_involved=canada,
    )


def test_champions_league_is_seasonal_and_not_year_round():
    assert "champions-league" in {s.key for s in active_event_specs(dt.date(2026, 9, 11))}
    assert "champions-league" not in {s.key for s in active_event_specs(dt.date(2026, 7, 11))}


def test_world_cup_and_olympics_activate_only_in_pinned_windows():
    world = spec("fifa-world-cup-2030")
    olympics = spec("summer-olympics-2028")
    assert world.active_on(dt.date(2030, 6, 8))
    assert world.active_on(dt.date(2030, 7, 21))
    assert not world.active_on(dt.date(2030, 6, 7))
    assert not world.active_on(dt.date(2030, 7, 22))
    assert olympics.active_on(dt.date(2028, 7, 14))
    assert olympics.active_on(dt.date(2028, 7, 30))
    assert not olympics.active_on(dt.date(2028, 7, 13))


def test_rugby_and_nfl_are_exception_windows_not_persistent_scoreboards():
    rugby = spec("rugby-world-cup-2027")
    nfl = spec("nfl-postseason")
    assert rugby.active_on(dt.date(2027, 10, 1))
    assert rugby.active_on(dt.date(2027, 11, 13))
    assert not rugby.active_on(dt.date(2027, 9, 30))
    assert nfl.active_on(dt.date(2027, 1, 15))
    assert nfl.active_on(dt.date(2027, 2, 10))
    assert not nfl.active_on(dt.date(2027, 9, 10))


def test_cricket_is_not_in_registry_or_article_queries():
    assert all(item.sport != "cricket" for item in EVENT_REGISTRY)
    all_queries = " ".join(event_article_queries(dt.date(2027, 1, 15))).lower()
    assert "cricket" not in all_queries


def test_event_article_queries_only_exist_when_registry_event_is_active():
    assert event_article_queries(dt.date(2026, 9, 11)) == ()
    olympic_queries = event_article_queries(dt.date(2028, 7, 20))
    assert any("Canada" in query for query in olympic_queries)
    nfl_queries = event_article_queries(dt.date(2027, 1, 20))
    assert "Super Bowl" in nfl_queries


def test_world_cup_canada_match_is_promoted_within_cap():
    world = replace(spec("fifa-world-cup-2030"), max_items=2)
    now = dt.datetime(2030, 6, 20, 12, tzinfo=UTC)
    games = [
        match("early", now + dt.timedelta(hours=1)),
        match("canada", now + dt.timedelta(hours=8), canada=True),
        match("later", now + dt.timedelta(hours=3)),
    ]
    selected = select_event_matches(games, spec=world, now=now)
    assert len(selected) == 2
    assert selected[0].provider_id == "canada"


def test_match_selection_preserves_recent_result_and_next_fixture_utility():
    cl = replace(spec("champions-league"), max_items=4)
    now = dt.datetime(2026, 9, 11, 12, tzinfo=UTC)
    games = [
        match("old", now - dt.timedelta(days=3), status=EventMatchStatus.FINAL),
        match("y1", now - dt.timedelta(hours=18), status=EventMatchStatus.FINAL),
        match("y2", now - dt.timedelta(hours=16), status=EventMatchStatus.FINAL),
        match("next1", now + dt.timedelta(hours=4)),
        match("next2", now + dt.timedelta(days=1)),
    ]
    selected = select_event_matches(games, spec=cl, now=now)
    ids = {item.provider_id for item in selected}
    assert "old" not in ids
    assert {"y1", "y2", "next1", "next2"} == ids


def test_olympics_prioritizes_canada_then_records_and_finals():
    olympics = replace(spec("summer-olympics-2028"), max_items=3)
    base = dt.datetime(2028, 7, 20, 12, tzinfo=UTC)
    items = [
        EventHighlight("routine", "qualifier", base + dt.timedelta(hours=4)),
        EventHighlight("record", "world record", base, world_record=True),
        EventHighlight("canada", "Canada bronze", base - dt.timedelta(hours=1), canada=True),
        EventHighlight("final", "major final", base + dt.timedelta(hours=2), final=True),
    ]
    selected = select_olympic_highlights(items, spec=olympics)
    assert [item.label for item in selected] == ["canada", "record", "final"]


def test_event_mode_expands_global_cap_but_remains_bounded():
    world = spec("fifa-world-cup-2030")
    cl = spec("champions-league")
    fetched = dt.datetime(2030, 6, 20, 12, tzinfo=UTC)
    world_snapshot = EventSnapshot(
        spec=world,
        fetched_at=fetched,
        source="fixture",
        highlights=tuple(EventHighlight(f"w{i}", "x") for i in range(8)),
    )
    cl_snapshot = EventSnapshot(
        spec=cl,
        fetched_at=fetched,
        source="fixture",
        highlights=tuple(EventHighlight(f"c{i}", "x") for i in range(6)),
    )
    desk = build_major_events_desk([cl_snapshot, world_snapshot], on_date=dt.date(2030, 6, 20))
    assert desk.event_mode is True
    assert desk.max_items == 12
    assert desk.snapshots[0].spec.key == "fifa-world-cup-2030"
    assert sum(len(s.matches) + len(s.highlights) for s in desk.snapshots) == 12


class _NoNetwork:
    def get(self, *args, **kwargs):
        raise AssertionError("off-window date must not fetch structured events")


def test_off_window_major_events_are_silent_and_cost_zero_requests():
    now = dt.datetime(2026, 7, 15, 12, tzinfo=UTC)
    desk = build_major_events(now=now, session=_NoNetwork())
    assert desk.snapshots == ()
    assert desk.event_mode is False
    assert desk.max_items == 6

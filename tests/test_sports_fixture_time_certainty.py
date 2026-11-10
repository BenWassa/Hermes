"""Issue #112: provider time certainty, including the Feb 19 2027 Jays fixture."""
from __future__ import annotations

import datetime as dt
from src.sports.models import UTC, GameSummary, GameStatus, SeasonPhase
from src.sports.providers import _parse_mlb_games, _parse_nhl_games, _parse_espn_games


def mlb_game(when, *, tbd=None, detail="Scheduled", official="2027-02-19", status="Preview"):
    status_payload = {"abstractGameState": status, "detailedState": detail}
    if tbd is not None:
        status_payload["startTimeTBD"] = tbd
    return {
        "gamePk": 123,
        "gameDate": when,
        "officialDate": official,
        "status": status_payload,
        "gameType": "S",
        "teams": {
            "home": {"team": {"id": 134, "name": "Pittsburgh Pirates", "abbreviation": "PIT"}},
            "away": {"team": {"id": 141, "name": "Toronto Blue Jays", "abbreviation": "TOR"}},
        },
    }


def test_jays_pirates_official_date_tbd_does_not_imply_0333_start():
    raw = mlb_game("2027-02-19T08:33:00Z", tbd=True)
    game = _parse_mlb_games({"dates": [{"date": "2027-02-19", "games": [raw]}]})[0]
    data = game.to_dict()

    assert data["opponent"] == "Pittsburgh Pirates"
    assert data["scheduled_date"] == "2027-02-19"
    assert data["time_confirmed"] is False
    # The provider's placeholder is still retained for sorting, but display
    # must not format it as a first pitch time when time_confirmed is false.
    assert data["start_time_toronto"] == "2027-02-19T03:33:00-05:00"
    assert data["status"] == "scheduled"


def test_mlb_explicit_tbd_also_accepts_string_flags_and_status_text():
    for raw in (
        mlb_game("2027-02-19T00:00:00Z", tbd="true"),
        mlb_game("2027-02-19T08:33:00Z", detail="Time TBD"),
    ):
        game = _parse_mlb_games({"dates": [{"games": [raw]}]})[0]
        assert game.time_confirmed is False


def test_confirmed_real_start_stays_exact_in_est_and_edt():
    fixtures = [
        ("2027-02-19T18:05:00Z", "2027-02-19T13:05:00-05:00"),
        ("2027-07-19T23:05:00Z", "2027-07-19T19:05:00-04:00"),
    ]
    for when, expected in fixtures:
        raw = mlb_game(when, tbd=False, official=when[:10])
        game = _parse_mlb_games({"dates": [{"games": [raw]}]})[0]
        assert game.time_confirmed is True
        assert game.to_dict()["start_time_toronto"] == expected


def test_arbitrary_or_midnight_time_not_marked_tbd_without_provider_evidence():
    raw = mlb_game("2027-02-19T00:00:00Z", tbd=False)
    game = _parse_mlb_games({"dates": [{"games": [raw]}]})[0]
    assert game.time_confirmed is True  # do not invent unknown status from hour


def test_statuses_remain_separate_from_time_certainty():
    for detail, expected in [("Postponed", GameStatus.POSTPONED), ("Cancelled", GameStatus.CANCELLED)]:
        raw = mlb_game("2027-02-19T08:33:00Z", tbd=True, detail=detail)
        game = _parse_mlb_games({"dates": [{"games": [raw]}]})[0]
        assert game.status == expected
        assert game.time_confirmed is False


def test_team_game_serialization_defaults_to_explicit_time_confirmation():
    game = GameSummary("id", dt.datetime(2027, 2, 19, 18, 5, tzinfo=UTC),
                       "Pittsburgh Pirates", "PIT", "away",
                       GameStatus.SCHEDULED, SeasonPhase.PRESEASON)
    assert game.to_dict()["time_confirmed"] is True


def test_nhl_explicit_schedule_tbd_flag_does_not_leak_clock():
    payload = {"games": [{
        "id": 77, "startTimeUTC": "2027-02-19T08:33:00Z",
        "startTimeTBD": True, "gameState": "FUT", "gameScheduleState": "TBD",
        "homeTeam": {"abbrev": "TOR"}, "awayTeam": {"abbrev": "MTL"},
        "gameType": 2,
    }]}
    assert _parse_nhl_games(payload)[0].time_confirmed is False


def test_espn_explicit_time_tbd_flag_does_not_leak_clock():
    payload = {"events": [{
        "id": "event", "date": "2027-02-19T08:33:00Z",
        "timeTBD": True, "seasonType": {"type": 2},
        "competitions": [{
            "date": "2027-02-19T08:33:00Z",
            "status": {"type": {"state": "pre", "completed": False, "description": "Scheduled"}},
            "competitors": [
                {"homeAway": "home", "team": {"abbreviation": "TOR", "displayName": "Toronto Raptors"}},
                {"homeAway": "away", "team": {"abbreviation": "NYK", "displayName": "New York Knicks"}},
            ],
        }],
    }]}
    assert _parse_espn_games(payload)[0].time_confirmed is False

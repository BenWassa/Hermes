from __future__ import annotations

import datetime as dt

from src.sports import (
    BLUE_JAYS,
    LEAFS,
    RAPTORS,
    GameStatus,
    GameSummary,
    SeasonPhase,
    TeamSnapshot,
    build_toronto_snapshots,
)
from src.sports.models import TORONTO, UTC
from src.sports.providers import (
    _infer_phase,
    _select_games,
    fetch_blue_jays_snapshot,
    parse_blue_jays_snapshot,
    parse_leafs_snapshot,
    parse_raptors_snapshot,
)


def _now(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _nhl_side(abbrev: str, place: str, common: str, score: int | None = None) -> dict:
    out = {
        "abbrev": abbrev,
        "placeName": {"default": place},
        "commonName": {"default": common},
    }
    if score is not None:
        out["score"] = score
    return out


def _nhl_game(
    game_id: int,
    when: str,
    *,
    state: str,
    game_type: int = 2,
    toronto_score: int | None = None,
    opponent_score: int | None = None,
    schedule_state: str = "OK",
) -> dict:
    return {
        "id": game_id,
        "gameType": game_type,
        "startTimeUTC": when,
        "gameState": state,
        "gameScheduleState": schedule_state,
        "homeTeam": _nhl_side("TOR", "Toronto", "Maple Leafs", toronto_score),
        "awayTeam": _nhl_side("MTL", "Montréal", "Canadiens", opponent_score),
    }


def _espn_event(
    event_id: str,
    when: str,
    *,
    state: str,
    completed: bool,
    season_type: int = 2,
    toronto_score: int | None = None,
    opponent_score: int | None = None,
    status_description: str | None = None,
) -> dict:
    score_tor = {} if toronto_score is None else {"value": toronto_score}
    score_opp = {} if opponent_score is None else {"value": opponent_score}
    return {
        "id": event_id,
        "date": when,
        "season": {"type": season_type},
        "competitions": [
            {
                "id": f"c-{event_id}",
                "date": when,
                "status": {
                    "type": {
                        "state": state,
                        "completed": completed,
                        "description": status_description or ("Final" if completed else "Scheduled"),
                    }
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"abbreviation": "TOR", "displayName": "Toronto Raptors"},
                        "score": score_tor,
                    },
                    {
                        "homeAway": "away",
                        "team": {"abbreviation": "BOS", "displayName": "Boston Celtics"},
                        "score": score_opp,
                    },
                ],
            }
        ],
    }


def _mlb_game(
    game_pk: int,
    when: str,
    *,
    abstract: str,
    detailed: str,
    game_type: str = "R",
    toronto_score: int | None = None,
    opponent_score: int | None = None,
) -> dict:
    home = {"team": {"id": 141, "name": "Toronto Blue Jays", "abbreviation": "TOR"}}
    away = {"team": {"id": 147, "name": "New York Yankees", "abbreviation": "NYY"}}
    if toronto_score is not None:
        home["score"] = toronto_score
    if opponent_score is not None:
        away["score"] = opponent_score
    return {
        "gamePk": game_pk,
        "gameDate": when,
        "gameType": game_type,
        "status": {"abstractGameState": abstract, "detailedState": detailed},
        "teams": {"home": home, "away": away},
    }


def test_leafs_regular_snapshot_has_result_record_standing_and_next_game():
    now = _now("2026-01-05T12:00:00Z")
    schedule = {
        "games": [
            _nhl_game(1, "2026-01-04T00:00:00Z", state="OFF", toronto_score=4, opponent_score=2),
            _nhl_game(2, "2026-01-07T00:00:00Z", state="FUT"),
        ]
    }
    standings = {
        "standings": [
            {
                "teamAbbrev": {"default": "TOR"},
                "wins": 24,
                "losses": 13,
                "otLosses": 4,
                "divisionSequence": 2,
                "divisionName": {"default": "Atlantic"},
            }
        ]
    }

    snapshot = parse_leafs_snapshot(schedule, standings, now=now, fetched_at=now)

    assert snapshot.team == LEAFS
    assert snapshot.phase == SeasonPhase.REGULAR
    assert snapshot.last_game.result == "W"
    assert snapshot.last_game.team_score == 4
    assert snapshot.record.display == "24-13-4"
    assert snapshot.standing.label == "2nd Atlantic"
    assert snapshot.next_game.provider_game_id == "2"


def test_raptors_regular_snapshot_uses_provider_record_and_standing():
    now = _now("2026-01-05T12:00:00Z")
    schedule = {
        "events": [
            _espn_event("1", "2026-01-04T00:30:00Z", state="post", completed=True, toronto_score=110, opponent_score=105),
            _espn_event("2", "2026-01-07T00:30:00Z", state="pre", completed=False),
        ]
    }
    team = {
        "team": {
            "record": {"items": [{"name": "overall", "summary": "21-15"}]},
            "standingSummary": "3rd in Atlantic Division",
        }
    }

    snapshot = parse_raptors_snapshot(schedule, team, now=now, fetched_at=now)

    assert snapshot.team == RAPTORS
    assert snapshot.phase == SeasonPhase.REGULAR
    assert snapshot.last_game.result == "W"
    assert snapshot.record.display == "21-15"
    assert snapshot.standing.label == "3rd in Atlantic Division"
    assert snapshot.standing.rank == 3
    assert snapshot.next_game.opponent == "Boston Celtics"


def test_blue_jays_regular_snapshot_has_division_context_and_games_back():
    now = _now("2026-09-11T12:00:00Z")
    schedule = {
        "dates": [
            {"games": [_mlb_game(1, "2026-09-10T23:00:00Z", abstract="Final", detailed="Final", toronto_score=5, opponent_score=3)]},
            {"games": [_mlb_game(2, "2026-09-11T23:00:00Z", abstract="Preview", detailed="Scheduled")]},
        ]
    }
    standings = {
        "records": [
            {
                "division": {"name": "American League East"},
                "teamRecords": [
                    {
                        "team": {"id": 141},
                        "leagueRecord": {"wins": 78, "losses": 65},
                        "divisionRank": "2",
                        "gamesBack": "4.5",
                    }
                ],
            }
        ]
    }

    snapshot = parse_blue_jays_snapshot(schedule, standings, now=now, fetched_at=now)

    assert snapshot.team == BLUE_JAYS
    assert snapshot.phase == SeasonPhase.REGULAR
    assert snapshot.last_game.result == "W"
    assert snapshot.record.display == "78-65"
    assert snapshot.standing.label == "2nd AL East"
    assert snapshot.standing.games_back == "4.5"
    assert snapshot.next_game.provider_game_id == "2"


def test_offseason_suppresses_stale_record_and_last_result_but_keeps_future_date():
    now = _now("2026-07-01T12:00:00Z")
    schedule = {
        "events": [
            _espn_event("old", "2026-04-15T23:00:00Z", state="post", completed=True, toronto_score=100, opponent_score=110),
            _espn_event("future", "2026-10-25T23:00:00Z", state="pre", completed=False),
        ]
    }
    stale_team = {
        "team": {
            "record": {"items": [{"name": "overall", "summary": "35-47"}]},
            "standingSummary": "5th in Atlantic Division",
        }
    }

    snapshot = parse_raptors_snapshot(schedule, stale_team, now=now, fetched_at=now)

    assert snapshot.phase == SeasonPhase.OFFSEASON
    assert snapshot.record is None
    assert snapshot.standing is None
    assert snapshot.last_game is None
    assert snapshot.next_game.provider_game_id == "future"


def test_imminent_postseason_promotes_phase_and_does_not_show_regular_season_last_game():
    now = _now("2026-04-17T12:00:00Z")
    games = [
        GameSummary("regular", _now("2026-04-16T23:00:00Z"), "Opponent", "OPP", "home", GameStatus.FINAL, SeasonPhase.REGULAR, 3, 2, "W"),
        GameSummary("playoff", _now("2026-04-20T23:00:00Z"), "Opponent", "OPP", "home", GameStatus.SCHEDULED, SeasonPhase.POSTSEASON),
    ]

    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)

    assert phase == SeasonPhase.POSTSEASON
    assert last is None
    assert nxt.provider_game_id == "playoff"


def test_postponed_and_cancelled_games_are_not_selected_as_next():
    now = _now("2026-09-11T12:00:00Z")
    games = [
        GameSummary("ppd", _now("2026-09-11T18:00:00Z"), "A", "A", "home", GameStatus.POSTPONED, SeasonPhase.REGULAR),
        GameSummary("cancel", _now("2026-09-12T18:00:00Z"), "B", "B", "home", GameStatus.CANCELLED, SeasonPhase.REGULAR),
        GameSummary("next", _now("2026-09-13T18:00:00Z"), "C", "C", "home", GameStatus.SCHEDULED, SeasonPhase.REGULAR),
    ]

    _, nxt = _select_games(games, SeasonPhase.REGULAR, now)
    assert nxt.provider_game_id == "next"


def test_empty_schedule_is_offseason_without_inventing_state():
    now = _now("2026-07-01T12:00:00Z")
    snapshot = parse_leafs_snapshot({"games": []}, {"standings": []}, now=now, fetched_at=now)

    assert snapshot.phase == SeasonPhase.OFFSEASON
    assert snapshot.last_game is None
    assert snapshot.record is None
    assert snapshot.standing is None
    assert snapshot.next_game is None


def test_serialization_includes_toronto_local_calendar_time():
    game = GameSummary(
        "g1",
        _now("2026-09-12T00:30:00Z"),
        "Opponent",
        "OPP",
        "home",
        GameStatus.SCHEDULED,
        SeasonPhase.REGULAR,
    )

    assert game.start_time_toronto.date() == dt.date(2026, 9, 11)
    assert game.to_dict()["start_time_toronto"].startswith("2026-09-11T20:30:00")


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _RecordingSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, *, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if url.endswith("/schedule"):
            return _FakeResponse({"dates": []})
        return _FakeResponse({"records": []})


def test_mlb_fetch_window_uses_toronto_calendar_date_near_utc_midnight():
    session = _RecordingSession()
    now = _now("2026-09-12T00:30:00Z")  # still Sep 11 in Toronto

    fetch_blue_jays_snapshot(now=now, fetched_at=now, session=session)

    schedule_params = session.calls[0][1]
    toronto_date = now.astimezone(TORONTO).date()
    assert schedule_params["startDate"] == (toronto_date - dt.timedelta(days=120)).isoformat()
    assert schedule_params["endDate"] == (toronto_date + dt.timedelta(days=240)).isoformat()


def _snapshot(team, source: str, *, now: dt.datetime) -> TeamSnapshot:
    return TeamSnapshot(team=team, phase=SeasonPhase.OFFSEASON, source=source, fetched_at=now)


def test_builder_preserves_priority_order_and_isolates_one_provider_failure():
    now = _now("2026-09-11T12:00:00Z")

    def leafs(**kwargs):
        return _snapshot(LEAFS, "NHL", now=kwargs["fetched_at"])

    def raptors(**kwargs):
        raise RuntimeError("provider exploded with internal details")

    def jays(**kwargs):
        return _snapshot(BLUE_JAYS, "MLB Stats API", now=kwargs["fetched_at"])

    snapshots = build_toronto_snapshots(
        now=now,
        fetched_at=now,
        session=object(),
        fetchers={"leafs": leafs, "raptors": raptors, "blue-jays": jays},
    )

    assert [snapshot.team.key for snapshot in snapshots] == ["leafs", "raptors", "blue-jays"]
    assert snapshots[0].available is True
    assert snapshots[1].available is False
    assert snapshots[1].error == "source_unavailable"
    assert "exploded" not in snapshots[1].to_dict()["error"]
    assert snapshots[2].available is True


def test_builder_has_no_curation_or_gemini_dependency():
    import inspect
    import src.sports.toronto as toronto

    source = inspect.getsource(toronto)
    assert "curate" not in source
    assert "gemini" not in source.lower()

from __future__ import annotations

import datetime as dt

from src.sports import SeasonPhase
from src.sports.models import UTC
from src.sports.providers import parse_leafs_snapshot, parse_raptors_snapshot


def _now(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def test_nhl_accepts_plain_string_division_name_seen_live():
    now = _now("2026-01-10T12:00:00Z")
    schedule = {
        "games": [
            {
                "id": 1,
                "gameType": 2,
                "startTimeUTC": "2026-01-09T00:00:00Z",
                "gameState": "OFF",
                "gameScheduleState": "OK",
                "homeTeam": {"abbrev": "TOR", "placeName": {"default": "Toronto"}, "commonName": {"default": "Maple Leafs"}, "score": 3},
                "awayTeam": {"abbrev": "MTL", "placeName": {"default": "Montréal"}, "commonName": {"default": "Canadiens"}, "score": 2},
            }
        ]
    }
    standings = {
        "standings": [
            {
                "teamAbbrev": {"default": "TOR"},
                "divisionName": "Atlantic",
                "divisionSequence": 4,
                "wins": 20,
                "losses": 17,
                "otLosses": 3,
            }
        ]
    }

    snapshot = parse_leafs_snapshot(schedule, standings, now=now, fetched_at=now)

    assert snapshot.available
    assert snapshot.standing.label == "4th Atlantic"


def test_espn_live_season_type_marks_preseason_and_suppresses_stale_standing():
    now = _now("2026-09-11T18:00:00Z")
    schedule = {
        "events": [
            {
                "id": "401902644",
                "date": "2026-10-03T23:00:00Z",
                "season": {"year": 2027, "displayName": "2026-27"},
                "seasonType": {"id": "1", "type": 1, "name": "Preseason", "abbreviation": "pre"},
                "competitions": [
                    {
                        "date": "2026-10-03T23:00:00Z",
                        "status": {"type": {"state": "pre", "completed": False, "description": "Scheduled"}},
                        "competitors": [
                            {"homeAway": "home", "team": {"abbreviation": "TOR", "displayName": "Toronto Raptors"}, "score": {}},
                            {"homeAway": "away", "team": {"abbreviation": "MIA", "displayName": "Miami Heat"}, "score": {}},
                        ],
                    }
                ],
            }
        ]
    }
    stale_team = {
        "team": {
            "record": {"items": [{"name": "overall", "summary": "35-47"}]},
            "standingSummary": "3rd in Atlantic Division",
        }
    }

    snapshot = parse_raptors_snapshot(schedule, stale_team, now=now, fetched_at=now)

    assert snapshot.phase == SeasonPhase.PRESEASON
    assert snapshot.next_game.phase == SeasonPhase.PRESEASON
    assert snapshot.record is None
    assert snapshot.standing is None

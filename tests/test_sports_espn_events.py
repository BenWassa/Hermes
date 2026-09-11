import datetime as dt

from src.sports.espn_events import fetch_espn_event_snapshot, parse_scoreboard, parse_standings
from src.sports.events import EVENT_REGISTRY, EventMatchStatus
from src.sports.major_events import build_major_event_snapshots

UTC = dt.timezone.utc


def spec(key):
    return next(item for item in EVENT_REGISTRY if item.key == key)


def event(identifier, when, home, away, *, status_name="STATUS_SCHEDULED", state="pre", completed=False, home_score=None, away_score=None, stage="league-phase"):
    return {
        "id": identifier,
        "date": when,
        "season": {"year": 2026, "type": 14534, "slug": stage},
        "status": {
            "type": {
                "name": status_name,
                "state": state,
                "completed": completed,
                "description": "Full Time" if completed else "Scheduled",
                "detail": "FT" if completed else "7:00 PM EDT",
            }
        },
        "competitions": [
            {
                "competitors": [
                    {"homeAway": "home", "score": home_score, "team": {"displayName": home, "abbreviation": "CAN" if home == "Canada" else "HOM"}},
                    {"homeAway": "away", "score": away_score, "team": {"displayName": away, "abbreviation": "CAN" if away == "Canada" else "AWY"}},
                ]
            }
        ],
    }


def standings_group(name, teams):
    entries = []
    for index, (team, abbreviation) in enumerate(teams, start=1):
        entries.append(
            {
                "team": {"displayName": team, "abbreviation": abbreviation},
                "stats": [
                    {"name": "gamesPlayed", "value": 1},
                    {"name": "points", "value": max(0, 10 - index)},
                    {"name": "pointDifferential", "value": 5 - index},
                ],
            }
        )
    return {"name": name, "standings": {"entries": entries}}


def test_scoreboard_parses_live_final_scheduled_and_postponed_shapes():
    payload = {
        "events": [
            event("final", "2026-09-10T16:45Z", "Fenerbahce", "AS Roma", status_name="STATUS_FULL_TIME", state="post", completed=True, home_score="1", away_score="1"),
            event("scheduled", "2026-09-16T19:00Z", "PSG", "Bayern", home_score=None, away_score=None),
            event("postponed", "2026-09-17T19:00Z", "Inter", "Benfica", status_name="STATUS_POSTPONED", state="pre"),
        ]
    }
    parsed = parse_scoreboard(payload)
    assert [item.status for item in parsed] == [EventMatchStatus.FINAL, EventMatchStatus.SCHEDULED, EventMatchStatus.POSTPONED]
    assert parsed[0].home_score == 1
    assert parsed[0].away_score == 1
    assert parsed[0].stage == "league-phase"


def test_scoreboard_detects_canada_by_name_or_abbreviation():
    parsed = parse_scoreboard({"events": [event("can", "2030-06-20T18:00Z", "Canada", "Spain")]})
    assert parsed[0].canada_involved is True


def test_malformed_scoreboard_event_is_skipped_not_fabricated():
    parsed = parse_scoreboard({"events": [{"id": "bad", "date": None, "competitions": []}]})
    assert parsed == ()


def test_champions_league_table_keeps_top_three_and_eight_nine_cut():
    teams = [(f"Team {index}", f"T{index}") for index in range(1, 11)]
    table = parse_standings({"children": [standings_group("League Phase 2026-27", teams)]}, spec=spec("champions-league"))
    assert table is not None
    assert [row.position for row in table.rows] == [1, 2, 3, 8, 9]
    assert table.label == "League Phase 2026-27"


def test_world_cup_table_selects_canada_group_only():
    payload = {
        "children": [
            standings_group("Group A", [("Mexico", "MEX"), ("Japan", "JPN")]),
            standings_group("Group B", [("Canada", "CAN"), ("Spain", "ESP"), ("Ghana", "GHA"), ("Chile", "CHI")]),
        ]
    }
    table = parse_standings(payload, spec=spec("fifa-world-cup-2030"))
    assert table is not None
    assert table.label == "Group B"
    assert table.rows[0].team == "Canada"
    assert table.rows[0].canada is True


class _Response:
    def __init__(self, payload=None, *, fail=False):
        self.payload = payload or {}
        self.fail = fail

    def raise_for_status(self):
        if self.fail:
            raise RuntimeError("source failure")

    def json(self):
        return self.payload


class _Session:
    def __init__(self, *, scoreboard_fail_for=(), standings_fail_for=()):
        self.scoreboard_fail_for = set(scoreboard_fail_for)
        self.standings_fail_for = set(standings_fail_for)
        self.calls = []

    def get(self, url, *, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        league = "fifa.world" if "fifa.world" in url else "uefa.champions"
        if "scoreboard" in url:
            if league in self.scoreboard_fail_for:
                return _Response(fail=True)
            return _Response(
                {
                    "events": [
                        event(
                            f"{league}-match",
                            "2030-06-20T18:00Z" if league == "fifa.world" else "2030-06-20T20:00Z",
                            "Canada" if league == "fifa.world" else "PSG",
                            "Spain" if league == "fifa.world" else "Bayern",
                        )
                    ]
                }
            )
        if league in self.standings_fail_for:
            return _Response(fail=True)
        teams = [("Canada", "CAN"), ("Spain", "ESP"), ("Ghana", "GHA"), ("Chile", "CHI")] if league == "fifa.world" else [(f"Team {i}", f"T{i}") for i in range(1, 10)]
        return _Response({"children": [standings_group("Group B" if league == "fifa.world" else "League Phase", teams)]})


def test_standings_failure_keeps_valid_match_snapshot_available():
    now = dt.datetime(2026, 9, 11, 12, tzinfo=UTC)
    session = _Session(standings_fail_for={"uefa.champions"})
    snapshot = fetch_espn_event_snapshot(spec("champions-league"), now=now, session=session)
    assert snapshot.available is True
    assert snapshot.standings is None
    assert len(session.calls) == 2


def test_scoreboard_failure_is_local_unavailable_state():
    now = dt.datetime(2026, 9, 11, 12, tzinfo=UTC)
    session = _Session(scoreboard_fail_for={"uefa.champions"})
    snapshot = fetch_espn_event_snapshot(spec("champions-league"), now=now, session=session)
    assert snapshot.available is False
    assert snapshot.error == "scoreboard_unavailable"
    assert len(session.calls) == 1


def test_request_window_uses_toronto_calendar_date_near_utc_midnight():
    now = dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)  # still Sep 11 in Toronto
    session = _Session()
    fetch_espn_event_snapshot(spec("champions-league"), now=now, session=session)
    scoreboard_call = session.calls[0]
    assert scoreboard_call[1]["dates"] == "20260910-20260918"


def test_world_cup_failure_does_not_suppress_champions_league():
    now = dt.datetime(2030, 6, 20, 12, tzinfo=UTC)
    session = _Session(scoreboard_fail_for={"fifa.world"})
    snapshots = build_major_event_snapshots(now=now, session=session)
    by_key = {snapshot.spec.key: snapshot for snapshot in snapshots}
    assert by_key["fifa-world-cup-2030"].available is False
    assert by_key["champions-league"].available is True

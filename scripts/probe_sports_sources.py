"""One-shot live probe for Sports V2 source audit (#34).

This script is intentionally separate from deterministic CI. It proves that the
candidate public endpoints are reachable from GitHub Actions and that the
minimum response contracts needed by Sports V2 still exist. It must not become
a production dependency or a routine poller.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass
from typing import Callable

import feedparser
import requests

TIMEOUT = 20
UA = "Hermes-Sports-Audit/1.0 (+https://github.com/BenWassa/Hermes)"
NBA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
}


@dataclass(frozen=True)
class Probe:
    name: str
    url: str
    check: Callable[[requests.Response], str]
    headers: dict[str, str] | None = None


def _json(response: requests.Response) -> dict:
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise AssertionError("expected JSON object")
    return data


def nhl_schedule(response: requests.Response) -> str:
    data = _json(response)
    games = data.get("games")
    if not isinstance(games, list):
        raise AssertionError("NHL schedule missing games[]")
    return f"games={len(games)}"


def nhl_standings(response: requests.Response) -> str:
    data = _json(response)
    standings = data.get("standings")
    if not isinstance(standings, list) or not standings:
        raise AssertionError("NHL standings missing standings[]")
    tor = [row for row in standings if (row.get("teamAbbrev") or {}).get("default") == "TOR"]
    if not tor:
        raise AssertionError("NHL standings missing TOR")
    return f"rows={len(standings)} tor=yes"


def mlb_schedule(response: requests.Response) -> str:
    data = _json(response)
    if "dates" not in data or "totalGames" not in data:
        raise AssertionError("MLB schedule missing dates/totalGames")
    return f"games={data.get('totalGames')}"


def mlb_standings(response: requests.Response) -> str:
    data = _json(response)
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise AssertionError("MLB standings missing records[]")
    teams = [tr for record in records for tr in record.get("teamRecords", [])]
    tor = [tr for tr in teams if tr.get("team", {}).get("id") == 141]
    if not tor:
        raise AssertionError("MLB standings missing team 141")
    return f"teams={len(teams)} tor=yes"


def nba_schedule(response: requests.Response) -> str:
    data = _json(response)
    league = data.get("leagueSchedule")
    if not isinstance(league, dict):
        raise AssertionError("NBA schedule missing leagueSchedule")
    dates = league.get("gameDates")
    if not isinstance(dates, list) or not dates:
        raise AssertionError("NBA schedule missing gameDates[]")
    games = [g for day in dates for g in day.get("games", [])]
    tor = [
        g
        for g in games
        if g.get("homeTeam", {}).get("teamId") == 1610612761
        or g.get("awayTeam", {}).get("teamId") == 1610612761
    ]
    if not tor:
        raise AssertionError("NBA schedule missing Raptors")
    return f"games={len(games)} raptors={len(tor)}"


def nba_scoreboard(response: requests.Response) -> str:
    data = _json(response)
    board = data.get("scoreboard")
    if not isinstance(board, dict) or not isinstance(board.get("games"), list):
        raise AssertionError("NBA scoreboard missing scoreboard.games[]")
    return f"games={len(board['games'])}"


def rss(response: requests.Response) -> str:
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise AssertionError(f"RSS parse failed: {parsed.bozo_exception}")
    return f"entries={len(parsed.entries)}"


def asset(response: requests.Response) -> str:
    response.raise_for_status()
    ctype = response.headers.get("content-type", "")
    if "svg" not in ctype and not response.text.lstrip().startswith("<svg"):
        raise AssertionError(f"expected SVG, got {ctype!r}")
    return f"bytes={len(response.content)}"


def main() -> int:
    today = dt.date.today()
    season = today.year if today.month >= 3 else today.year - 1
    nhl_start = today.year if today.month >= 7 else today.year - 1
    nhl_season = f"{nhl_start}{nhl_start + 1}"
    start = today - dt.timedelta(days=21)
    end = today + dt.timedelta(days=21)

    probes = [
        Probe(
            "nhl_schedule",
            f"https://api-web.nhle.com/v1/club-schedule-season/TOR/{nhl_season}",
            nhl_schedule,
        ),
        Probe("nhl_standings", "https://api-web.nhle.com/v1/standings/now", nhl_standings),
        Probe(
            "mlb_schedule",
            "https://statsapi.mlb.com/api/v1/schedule"
            f"?sportId=1&teamId=141&startDate={start.isoformat()}&endDate={end.isoformat()}"
            "&hydrate=team",
            mlb_schedule,
        ),
        Probe(
            "mlb_standings",
            "https://statsapi.mlb.com/api/v1/standings"
            f"?leagueId=103&season={season}&standingsTypes=regularSeason&hydrate=division",
            mlb_standings,
        ),
        Probe(
            "nba_schedule",
            "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
            nba_schedule,
            NBA_HEADERS,
        ),
        Probe(
            "nba_scoreboard",
            "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
            nba_scoreboard,
            NBA_HEADERS,
        ),
        Probe("cbc_nhl", "https://www.cbc.ca/webfeed/rss/rss-sports-nhl", rss),
        Probe("cbc_nba", "https://www.cbc.ca/webfeed/rss/rss-sports-nba", rss),
        Probe("cbc_mlb", "https://www.cbc.ca/webfeed/rss/rss-sports-mlb", rss),
        Probe("cbc_soccer", "https://www.cbc.ca/webfeed/rss/rss-sports-soccer", rss),
        Probe("cbc_olympics", "https://www.cbc.ca/webfeed/rss/rss-sports-olympics", rss),
        Probe("cbc_nfl", "https://www.cbc.ca/webfeed/rss/rss-sports-nfl", rss),
        Probe("nhl_leafs_logo", "https://assets.nhle.com/logos/nhl/svg/TOR_light.svg", asset),
        Probe("mlb_jays_logo", "https://www.mlbstatic.com/team-logos/141.svg", asset),
    ]

    failed: list[str] = []
    evidence: list[dict[str, object]] = []
    for probe in probes:
        headers = probe.headers or {"User-Agent": UA}
        try:
            response = requests.get(probe.url, headers=headers, timeout=TIMEOUT)
            detail = probe.check(response)
            evidence.append(
                {
                    "name": probe.name,
                    "ok": True,
                    "status": response.status_code,
                    "detail": detail,
                }
            )
            print(f"PASS {probe.name}: HTTP {response.status_code}; {detail}")
        except Exception as exc:
            failed.append(probe.name)
            evidence.append({"name": probe.name, "ok": False, "error": str(exc)})
            print(f"FAIL {probe.name}: {exc}", file=sys.stderr)

    print("EVIDENCE_JSON=" + json.dumps(evidence, separators=(",", ":")))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

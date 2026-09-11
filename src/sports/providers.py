"""Provider adapters for deterministic Toronto favourite-team state.

Raw provider JSON is contained here.  The rest of Hermes receives only the
provider-independent objects in :mod:`src.sports.models`.
"""

from __future__ import annotations

import datetime as dt
import re

import requests

from .models import (
    GameStatus,
    GameSummary,
    RecordSummary,
    SeasonPhase,
    StandingSummary,
    TeamRef,
    TeamSnapshot,
    TORONTO,
    UTC,
)

TIMEOUT = 12
USER_AGENT = "Hermes-Sports/1.0 (+https://github.com/BenWassa/Hermes)"

LEAFS = TeamRef("leafs", "Toronto Maple Leafs", "NHL", "TOR", "TOR")
RAPTORS = TeamRef("raptors", "Toronto Raptors", "NBA", "TOR", "tor")
BLUE_JAYS = TeamRef("blue-jays", "Toronto Blue Jays", "MLB", "TOR", "141")

_NHL_BASE = "https://api-web.nhle.com/v1"
_ESPN_NBA_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
_MLB_BASE = "https://statsapi.mlb.com/api/v1"
_PHASE_ORDER = {
    SeasonPhase.OFFSEASON: 0,
    SeasonPhase.PRESEASON: 1,
    SeasonPhase.REGULAR: 2,
    SeasonPhase.POSTSEASON: 3,
}


def _localized(value) -> str:
    """NHL alternates between localized objects and plain strings."""
    if isinstance(value, dict):
        return str(value.get("default") or next(iter(value.values()), ""))
    return str(value or "")


def _iso_datetime(value: str) -> dt.datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("missing event timestamp")
    parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _integer(value) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        value = value.get("value", value.get("displayValue"))
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _ordinal(value: int | None) -> str:
    if value is None:
        return ""
    suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _result(team: int | None, opponent: int | None, status: GameStatus) -> str | None:
    if status != GameStatus.FINAL or team is None or opponent is None:
        return None
    return "W" if team > opponent else "L" if team < opponent else "T"


def _phase_from_type(value, *, provider: str) -> SeasonPhase:
    if provider in {"nhl", "espn"}:
        try:
            code = int(value)
        except (TypeError, ValueError):
            code = 0
        return {1: SeasonPhase.PRESEASON, 2: SeasonPhase.REGULAR, 3: SeasonPhase.POSTSEASON}.get(
            code, SeasonPhase.REGULAR
        )
    code = str(value or "").upper()
    if code in {"S", "E"}:
        return SeasonPhase.PRESEASON
    if code == "R":
        return SeasonPhase.REGULAR
    if code in {"F", "D", "L", "W", "C", "P"}:
        return SeasonPhase.POSTSEASON
    return SeasonPhase.REGULAR


def _infer_phase(games: list[GameSummary], now: dt.datetime) -> SeasonPhase:
    now = now.astimezone(UTC)
    live = [g for g in games if g.status == GameStatus.LIVE]
    if live:
        return max(live, key=lambda g: _PHASE_ORDER[g.phase]).phase

    finals = sorted(
        (g for g in games if g.status == GameStatus.FINAL and g.start_time_utc <= now),
        key=lambda g: g.start_time_utc,
    )
    upcoming = sorted(
        (g for g in games if g.status == GameStatus.SCHEDULED and g.start_time_utc >= now),
        key=lambda g: g.start_time_utc,
    )
    last = finals[-1] if finals else None
    nxt = upcoming[0] if upcoming else None
    if nxt and nxt.start_time_utc - now <= dt.timedelta(days=7):
        if last is None or _PHASE_ORDER[nxt.phase] > _PHASE_ORDER[last.phase]:
            return nxt.phase
    if last and now - last.start_time_utc <= dt.timedelta(days=3):
        return last.phase
    if nxt and nxt.start_time_utc - now <= dt.timedelta(days=45):
        return nxt.phase
    return SeasonPhase.OFFSEASON


def _select_games(
    games: list[GameSummary], phase: SeasonPhase, now: dt.datetime
) -> tuple[GameSummary | None, GameSummary | None]:
    now = now.astimezone(UTC)
    finals = [
        g
        for g in games
        if g.status == GameStatus.FINAL and g.start_time_utc <= now and g.phase == phase
    ]
    upcoming = [
        g for g in games if g.status == GameStatus.SCHEDULED and g.start_time_utc >= now
    ]
    last = max(finals, key=lambda g: g.start_time_utc) if finals else None
    nxt = min(upcoming, key=lambda g: g.start_time_utc) if upcoming else None
    return (None if phase == SeasonPhase.OFFSEASON else last), nxt


def _get_json(session: requests.Session, url: str, *, params: dict | None = None) -> dict:
    response = session.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected JSON shape from {url}")
    return payload


# NHL ---------------------------------------------------------------------


def _nhl_status(game: dict) -> GameStatus:
    state = str(game.get("gameState") or "").upper()
    schedule = str(game.get("gameScheduleState") or "").upper()
    if state in {"CNCL", "CANCELLED", "CANCELED"} or schedule in {"CNCL", "CANCELLED", "CANCELED"}:
        return GameStatus.CANCELLED
    if state in {"PPD", "POSTPONED"} or schedule in {"PPD", "POSTPONED"}:
        return GameStatus.POSTPONED
    if state in {"OFF", "FINAL"}:
        return GameStatus.FINAL
    if state in {"LIVE", "CRIT"}:
        return GameStatus.LIVE
    return GameStatus.SCHEDULED


def _nhl_team_name(team: dict) -> str:
    label = " ".join(
        part
        for part in (_localized(team.get("placeName")), _localized(team.get("commonName")))
        if part
    ).strip()
    return label or str(team.get("abbrev") or "Opponent")


def _parse_nhl_games(payload: dict) -> list[GameSummary]:
    games: list[GameSummary] = []
    for raw in payload.get("games") or []:
        if not isinstance(raw, dict):
            continue
        try:
            start = _iso_datetime(raw.get("startTimeUTC"))
        except ValueError:
            continue
        home, away = raw.get("homeTeam") or {}, raw.get("awayTeam") or {}
        at_home = str(home.get("abbrev") or "").upper() == "TOR"
        team, opponent = (home, away) if at_home else (away, home)
        status = _nhl_status(raw)
        team_score, opponent_score = _integer(team.get("score")), _integer(opponent.get("score"))
        games.append(
            GameSummary(
                provider_game_id=str(raw.get("id") or ""),
                start_time_utc=start,
                opponent=_nhl_team_name(opponent),
                opponent_abbreviation=str(opponent.get("abbrev") or ""),
                home_away="home" if at_home else "away",
                status=status,
                phase=_phase_from_type(raw.get("gameType"), provider="nhl"),
                team_score=team_score,
                opponent_score=opponent_score,
                result=_result(team_score, opponent_score, status),
            )
        )
    return games


def _parse_nhl_record_and_standing(payload: dict) -> tuple[RecordSummary | None, StandingSummary | None]:
    row = next(
        (r for r in payload.get("standings") or [] if _localized(r.get("teamAbbrev")).upper() == "TOR"),
        None,
    )
    if not isinstance(row, dict):
        return None, None
    wins, losses, otl = _integer(row.get("wins")), _integer(row.get("losses")), _integer(row.get("otLosses"))
    record = None
    if wins is not None and losses is not None:
        record = RecordSummary(wins, losses, f"{wins}-{losses}" + (f"-{otl}" if otl is not None else ""), otl)
    rank = _integer(row.get("divisionSequence"))
    division = _localized(row.get("divisionName")) or "Division"
    standing = StandingSummary(f"{_ordinal(rank)} {division}", rank, division) if rank is not None else None
    return record, standing


def parse_leafs_snapshot(
    schedule: dict, standings: dict, *, now: dt.datetime, fetched_at: dt.datetime
) -> TeamSnapshot:
    games = _parse_nhl_games(schedule)
    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)
    record, standing = _parse_nhl_record_and_standing(standings)
    if phase not in {SeasonPhase.REGULAR, SeasonPhase.POSTSEASON}:
        record = standing = None
    return TeamSnapshot(LEAFS, phase, "NHL", fetched_at, last, record, standing, nxt)


def fetch_leafs_snapshot(
    *, now: dt.datetime, fetched_at: dt.datetime, session: requests.Session
) -> TeamSnapshot:
    local = now.astimezone(TORONTO)
    start = local.year if local.month >= 7 else local.year - 1
    schedule = _get_json(session, f"{_NHL_BASE}/club-schedule-season/TOR/{start}{start + 1}")
    standings = _get_json(session, f"{_NHL_BASE}/standings/now")
    return parse_leafs_snapshot(schedule, standings, now=now, fetched_at=fetched_at)


# ESPN / Raptors -----------------------------------------------------------


def _espn_status(event: dict, competition: dict) -> GameStatus:
    kind = (competition.get("status") or event.get("status") or {}).get("type") or {}
    text = " ".join(str(kind.get(k) or "") for k in ("name", "description", "detail", "shortDetail")).lower()
    if "cancel" in text:
        return GameStatus.CANCELLED
    if "postpon" in text:
        return GameStatus.POSTPONED
    if kind.get("completed") is True or str(kind.get("state") or "").lower() == "post":
        return GameStatus.FINAL
    if str(kind.get("state") or "").lower() == "in":
        return GameStatus.LIVE
    return GameStatus.SCHEDULED


def _espn_name(competitor: dict) -> str:
    team = competitor.get("team") or {}
    return str(
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or team.get("abbreviation")
        or "Opponent"
    )


def _espn_season_type(event: dict, competition: dict):
    # Live schedule payloads put the phase in event.seasonType.  Older/fixture
    # shapes sometimes carried it under season.type, so accept both.
    season_type = event.get("seasonType") or competition.get("seasonType") or {}
    if isinstance(season_type, dict) and season_type.get("type") is not None:
        return season_type.get("type")
    season = event.get("season") or competition.get("season") or {}
    return season.get("type") if isinstance(season, dict) else None


def _parse_espn_games(payload: dict) -> list[GameSummary]:
    games: list[GameSummary] = []
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        competition = next(iter(event.get("competitions") or []), None)
        if not isinstance(competition, dict):
            continue
        competitors = [c for c in competition.get("competitors") or [] if isinstance(c, dict)]
        team = next(
            (c for c in competitors if str((c.get("team") or {}).get("abbreviation") or "").upper() == "TOR"),
            None,
        )
        if not team:
            continue
        opponent = next((c for c in competitors if c is not team), None)
        if not opponent:
            continue
        try:
            start = _iso_datetime(competition.get("date") or event.get("date"))
        except ValueError:
            continue
        status = _espn_status(event, competition)
        team_score, opponent_score = _integer(team.get("score")), _integer(opponent.get("score"))
        games.append(
            GameSummary(
                provider_game_id=str(event.get("id") or competition.get("id") or ""),
                start_time_utc=start,
                opponent=_espn_name(opponent),
                opponent_abbreviation=str((opponent.get("team") or {}).get("abbreviation") or ""),
                home_away=str(team.get("homeAway") or "unknown").lower(),
                status=status,
                phase=_phase_from_type(_espn_season_type(event, competition), provider="espn"),
                team_score=team_score,
                opponent_score=opponent_score,
                result=_result(team_score, opponent_score, status),
            )
        )
    return games


def _espn_record(payload: dict) -> RecordSummary | None:
    record = (payload.get("team") or {}).get("record") or {}
    summaries = [str(v) for v in (record.get("summary"), record.get("displayValue")) if v]
    for item in record.get("items") or []:
        if isinstance(item, dict) and str(item.get("name") or "").lower() in {"overall", "total", ""} and item.get("summary"):
            summaries.insert(0, str(item["summary"]))
    for summary in summaries:
        match = re.search(r"(\d+)\s*-\s*(\d+)", summary)
        if match:
            wins, losses = map(int, match.groups())
            return RecordSummary(wins, losses, f"{wins}-{losses}")
    return None


def _espn_standing(payload: dict) -> StandingSummary | None:
    label = str((payload.get("team") or {}).get("standingSummary") or "").strip()
    if not label:
        return None
    rank_match = re.match(r"(\d+)(?:st|nd|rd|th)?\b", label, re.I)
    scope_match = re.search(r"\bin\s+(.+)$", label, re.I)
    return StandingSummary(
        label=label,
        rank=int(rank_match.group(1)) if rank_match else None,
        scope=scope_match.group(1) if scope_match else None,
    )


def parse_raptors_snapshot(
    schedule: dict, team_payload: dict, *, now: dt.datetime, fetched_at: dt.datetime
) -> TeamSnapshot:
    games = _parse_espn_games(schedule)
    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)
    record, standing = _espn_record(team_payload), _espn_standing(team_payload)
    if phase not in {SeasonPhase.REGULAR, SeasonPhase.POSTSEASON}:
        record = standing = None
    return TeamSnapshot(RAPTORS, phase, "ESPN", fetched_at, last, record, standing, nxt)


def fetch_raptors_snapshot(
    *, now: dt.datetime, fetched_at: dt.datetime, session: requests.Session
) -> TeamSnapshot:
    schedule = _get_json(session, f"{_ESPN_NBA_BASE}/teams/tor/schedule")
    team = _get_json(session, f"{_ESPN_NBA_BASE}/teams/tor")
    return parse_raptors_snapshot(schedule, team, now=now, fetched_at=fetched_at)


# MLB / Blue Jays ----------------------------------------------------------


def _mlb_status(game: dict) -> GameStatus:
    status = game.get("status") or {}
    abstract = str(status.get("abstractGameState") or "").lower()
    detail = str(status.get("detailedState") or "").lower()
    text = f"{abstract} {detail}"
    if "cancel" in text:
        return GameStatus.CANCELLED
    if "postpon" in text or "suspend" in text:
        return GameStatus.POSTPONED
    if abstract == "final" or "final" in detail:
        return GameStatus.FINAL
    if abstract == "live" or "in progress" in detail:
        return GameStatus.LIVE
    return GameStatus.SCHEDULED


def _parse_mlb_games(payload: dict) -> list[GameSummary]:
    games: list[GameSummary] = []
    for day in payload.get("dates") or []:
        for game in day.get("games") or []:
            if not isinstance(game, dict):
                continue
            try:
                start = _iso_datetime(game.get("gameDate"))
            except ValueError:
                continue
            home, away = (game.get("teams") or {}).get("home") or {}, (game.get("teams") or {}).get("away") or {}
            at_home = str((home.get("team") or {}).get("id") or "") == "141"
            team, opponent = (home, away) if at_home else (away, home)
            status = _mlb_status(game)
            team_score, opponent_score = _integer(team.get("score")), _integer(opponent.get("score"))
            opp_team = opponent.get("team") or {}
            games.append(
                GameSummary(
                    provider_game_id=str(game.get("gamePk") or ""),
                    start_time_utc=start,
                    opponent=str(opp_team.get("name") or opp_team.get("teamName") or "Opponent"),
                    opponent_abbreviation=str(opp_team.get("abbreviation") or ""),
                    home_away="home" if at_home else "away",
                    status=status,
                    phase=_phase_from_type(game.get("gameType"), provider="mlb"),
                    team_score=team_score,
                    opponent_score=opponent_score,
                    result=_result(team_score, opponent_score, status),
                )
            )
    return games


def _parse_mlb_record_and_standing(payload: dict) -> tuple[RecordSummary | None, StandingSummary | None]:
    division_name, team_row = "AL East", None
    for block in payload.get("records") or []:
        raw_division = str((block.get("division") or {}).get("name") or "")
        if raw_division:
            division_name = raw_division.replace("American League ", "AL ")
        team_row = next(
            (r for r in block.get("teamRecords") or [] if str((r.get("team") or {}).get("id") or "") == "141"),
            None,
        )
        if team_row:
            break
    if not isinstance(team_row, dict):
        return None, None
    league_record = team_row.get("leagueRecord") or {}
    wins, losses = _integer(league_record.get("wins")), _integer(league_record.get("losses"))
    record = RecordSummary(wins, losses, f"{wins}-{losses}") if wins is not None and losses is not None else None
    rank = _integer(team_row.get("divisionRank"))
    games_back = str(team_row.get("gamesBack")) if team_row.get("gamesBack") not in (None, "") else None
    standing = (
        StandingSummary(f"{_ordinal(rank)} {division_name}", rank, division_name, games_back)
        if rank is not None
        else None
    )
    return record, standing


def parse_blue_jays_snapshot(
    schedule: dict, standings: dict, *, now: dt.datetime, fetched_at: dt.datetime
) -> TeamSnapshot:
    games = _parse_mlb_games(schedule)
    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)
    record, standing = _parse_mlb_record_and_standing(standings)
    if phase not in {SeasonPhase.REGULAR, SeasonPhase.POSTSEASON}:
        record = standing = None
    return TeamSnapshot(BLUE_JAYS, phase, "MLB Stats API", fetched_at, last, record, standing, nxt)


def fetch_blue_jays_snapshot(
    *, now: dt.datetime, fetched_at: dt.datetime, session: requests.Session
) -> TeamSnapshot:
    local_date = now.astimezone(TORONTO).date()
    schedule = _get_json(
        session,
        f"{_MLB_BASE}/schedule",
        params={
            "sportId": 1,
            "teamId": 141,
            "startDate": (local_date - dt.timedelta(days=120)).isoformat(),
            "endDate": (local_date + dt.timedelta(days=240)).isoformat(),
            "hydrate": "team",
        },
    )
    standings = _get_json(
        session,
        f"{_MLB_BASE}/standings",
        params={
            "leagueId": 103,
            "season": local_date.year,
            "standingsTypes": "regularSeason",
            "hydrate": "division",
        },
    )
    return parse_blue_jays_snapshot(schedule, standings, now=now, fetched_at=fetched_at)

"""Small provider adapters for Toronto favourite-team state.

Provider JSON is parsed here and nowhere else. The rest of Hermes sees only
``TeamSnapshot`` domain objects. These functions never call Gemini and never
reuse the ordinary news-story schema.
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
    SeasonPhase.PRESEASON: 1,
    SeasonPhase.REGULAR: 2,
    SeasonPhase.POSTSEASON: 3,
    SeasonPhase.OFFSEASON: 0,
}


def _iso_datetime(value: str) -> dt.datetime:
    value = str(value or "").strip()
    if not value:
        raise ValueError("missing event timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _integer(value) -> int | None:
    if value is None or value == "":
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
    suffix = (
        "th"
        if 10 <= value % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    )
    return f"{value}{suffix}"


def _result(
    team_score: int | None, opponent_score: int | None, status: GameStatus
) -> str | None:
    if status != GameStatus.FINAL or team_score is None or opponent_score is None:
        return None
    if team_score > opponent_score:
        return "W"
    if team_score < opponent_score:
        return "L"
    return "T"


def _phase_from_type(value, *, provider: str) -> SeasonPhase:
    if provider in {"nhl", "espn"}:
        try:
            code = int(value)
        except (TypeError, ValueError):
            code = 0
        return {
            1: SeasonPhase.PRESEASON,
            2: SeasonPhase.REGULAR,
            3: SeasonPhase.POSTSEASON,
        }.get(code, SeasonPhase.REGULAR)

    code = str(value or "").upper()
    if code in {"S", "E"}:
        return SeasonPhase.PRESEASON
    if code == "R":
        return SeasonPhase.REGULAR
    if code in {"F", "D", "L", "W", "C", "P"}:
        return SeasonPhase.POSTSEASON
    return SeasonPhase.REGULAR


def _infer_phase(games: list[GameSummary], now: dt.datetime) -> SeasonPhase:
    """Infer reader-facing phase without carrying stale prior-season state.

    A currently live game wins. An imminent later phase (regular after
    preseason or playoffs after regular season) activates up to a week early.
    Otherwise a just-completed game represents the current phase, then an
    upcoming game within 45 days. Farther-away fixtures remain useful as the
    next meaningful date while the team stays labelled offseason.
    """
    now = now.astimezone(UTC)
    live = [game for game in games if game.status == GameStatus.LIVE]
    if live:
        return max(live, key=lambda game: _PHASE_ORDER[game.phase]).phase

    finals = sorted(
        (
            game
            for game in games
            if game.status == GameStatus.FINAL and game.start_time_utc <= now
        ),
        key=lambda game: game.start_time_utc,
    )
    upcoming = sorted(
        (
            game
            for game in games
            if game.status == GameStatus.SCHEDULED and game.start_time_utc >= now
        ),
        key=lambda game: game.start_time_utc,
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
        game
        for game in games
        if game.status == GameStatus.FINAL
        and game.start_time_utc <= now
        and game.phase == phase
    ]
    upcoming = [
        game
        for game in games
        if game.status == GameStatus.SCHEDULED and game.start_time_utc >= now
    ]
    last = max(finals, key=lambda game: game.start_time_utc) if finals else None
    nxt = min(upcoming, key=lambda game: game.start_time_utc) if upcoming else None
    if phase == SeasonPhase.OFFSEASON:
        last = None
    return last, nxt


def _get_json(
    session: requests.Session, url: str, *, params: dict | None = None
) -> dict:
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


# -- NHL / Maple Leafs -----------------------------------------------------


def _nhl_name(team: dict) -> str:
    place = (team.get("placeName") or {}).get("default") or ""
    common = (team.get("commonName") or {}).get("default") or ""
    label = " ".join(part for part in (place, common) if part).strip()
    return label or team.get("abbrev") or "Opponent"


def _nhl_status(game: dict) -> GameStatus:
    state = str(game.get("gameState") or "").upper()
    schedule = str(game.get("gameScheduleState") or "").upper()
    if schedule in {"CNCL", "CANCELLED", "CANCELED"} or state in {
        "CNCL",
        "CANCELLED",
        "CANCELED",
    }:
        return GameStatus.CANCELLED
    if schedule in {"PPD", "POSTPONED"} or state in {"PPD", "POSTPONED"}:
        return GameStatus.POSTPONED
    if state in {"OFF", "FINAL"}:
        return GameStatus.FINAL
    if state in {"LIVE", "CRIT"}:
        return GameStatus.LIVE
    return GameStatus.SCHEDULED


def _parse_nhl_games(schedule: dict) -> list[GameSummary]:
    out: list[GameSummary] = []
    for raw in schedule.get("games") or []:
        if not isinstance(raw, dict):
            continue
        try:
            start = _iso_datetime(raw.get("startTimeUTC"))
        except ValueError:
            continue
        home = raw.get("homeTeam") or {}
        away = raw.get("awayTeam") or {}
        at_home = str(home.get("abbrev") or "").upper() == "TOR"
        team_side, opponent = (home, away) if at_home else (away, home)
        status = _nhl_status(raw)
        team_score = _integer(team_side.get("score"))
        opponent_score = _integer(opponent.get("score"))
        out.append(
            GameSummary(
                provider_game_id=str(raw.get("id") or ""),
                start_time_utc=start,
                opponent=_nhl_name(opponent),
                opponent_abbreviation=str(opponent.get("abbrev") or ""),
                home_away="home" if at_home else "away",
                status=status,
                phase=_phase_from_type(raw.get("gameType"), provider="nhl"),
                team_score=team_score,
                opponent_score=opponent_score,
                result=_result(team_score, opponent_score, status),
            )
        )
    return out


def _parse_nhl_record_and_standing(
    standings: dict,
) -> tuple[RecordSummary | None, StandingSummary | None]:
    row = next(
        (
            item
            for item in standings.get("standings") or []
            if ((item.get("teamAbbrev") or {}).get("default") or "").upper()
            == "TOR"
        ),
        None,
    )
    if not isinstance(row, dict):
        return None, None
    wins = _integer(row.get("wins"))
    losses = _integer(row.get("losses"))
    otl = _integer(row.get("otLosses"))
    record = None
    if wins is not None and losses is not None:
        display = f"{wins}-{losses}" + (f"-{otl}" if otl is not None else "")
        record = RecordSummary(wins, losses, display, otl)
    rank = _integer(row.get("divisionSequence"))
    division = (row.get("divisionName") or {}).get("default") or "Division"
    standing = (
        StandingSummary(
            label=f"{_ordinal(rank)} {division}".strip(),
            rank=rank,
            scope=division,
        )
        if rank is not None
        else None
    )
    return record, standing


def parse_leafs_snapshot(
    schedule: dict,
    standings: dict,
    *,
    now: dt.datetime,
    fetched_at: dt.datetime,
) -> TeamSnapshot:
    games = _parse_nhl_games(schedule)
    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)
    record, standing = _parse_nhl_record_and_standing(standings)
    if phase not in {SeasonPhase.REGULAR, SeasonPhase.POSTSEASON}:
        record = standing = None
    return TeamSnapshot(
        team=LEAFS,
        phase=phase,
        source="NHL",
        fetched_at=fetched_at,
        last_game=last,
        record=record,
        standing=standing,
        next_game=nxt,
    )


def fetch_leafs_snapshot(
    *, now: dt.datetime, fetched_at: dt.datetime, session: requests.Session
) -> TeamSnapshot:
    local_now = now.astimezone(TORONTO)
    season_start = local_now.year if local_now.month >= 7 else local_now.year - 1
    season = f"{season_start}{season_start + 1}"
    schedule = _get_json(
        session, f"{_NHL_BASE}/club-schedule-season/TOR/{season}"
    )
    standings = _get_json(session, f"{_NHL_BASE}/standings/now")
    return parse_leafs_snapshot(schedule, standings, now=now, fetched_at=fetched_at)


# -- ESPN / Raptors --------------------------------------------------------


def _espn_status(event: dict, competition: dict) -> GameStatus:
    status = competition.get("status") or event.get("status") or {}
    kind = status.get("type") or {}
    description = " ".join(
        str(value or "")
        for value in (
            kind.get("name"),
            kind.get("description"),
            kind.get("detail"),
            kind.get("shortDetail"),
        )
    ).lower()
    if "cancel" in description:
        return GameStatus.CANCELLED
    if "postpon" in description:
        return GameStatus.POSTPONED
    if kind.get("completed") is True or str(kind.get("state") or "").lower() == "post":
        return GameStatus.FINAL
    if str(kind.get("state") or "").lower() == "in":
        return GameStatus.LIVE
    return GameStatus.SCHEDULED


def _espn_team_name(competitor: dict) -> str:
    team = competitor.get("team") or {}
    return (
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or team.get("abbreviation")
        or "Opponent"
    )


def _parse_espn_games(schedule: dict) -> list[GameSummary]:
    out: list[GameSummary] = []
    for event in schedule.get("events") or []:
        if not isinstance(event, dict):
            continue
        competition = next(iter(event.get("competitions") or []), None)
        if not isinstance(competition, dict):
            continue
        competitors = [
            item
            for item in competition.get("competitors") or []
            if isinstance(item, dict)
        ]
        team_side = next(
            (
                item
                for item in competitors
                if str((item.get("team") or {}).get("abbreviation") or "").upper()
                == "TOR"
            ),
            None,
        )
        if not team_side:
            continue
        opponent = next((item for item in competitors if item is not team_side), None)
        if not opponent:
            continue
        try:
            start = _iso_datetime(competition.get("date") or event.get("date"))
        except ValueError:
            continue
        status = _espn_status(event, competition)
        team_score = _integer(team_side.get("score"))
        opponent_score = _integer(opponent.get("score"))
        season = event.get("season") or competition.get("season") or {}
        out.append(
            GameSummary(
                provider_game_id=str(event.get("id") or competition.get("id") or ""),
                start_time_utc=start,
                opponent=_espn_team_name(opponent),
                opponent_abbreviation=str(
                    (opponent.get("team") or {}).get("abbreviation") or ""
                ),
                home_away=str(team_side.get("homeAway") or "").lower() or "unknown",
                status=status,
                phase=_phase_from_type(season.get("type"), provider="espn"),
                team_score=team_score,
                opponent_score=opponent_score,
                result=_result(team_score, opponent_score, status),
            )
        )
    return out


def _espn_record(team_payload: dict) -> RecordSummary | None:
    team = team_payload.get("team") or {}
    record = team.get("record") or {}
    summaries: list[str] = []
    for value in (record.get("summary"), record.get("displayValue")):
        if value:
            summaries.append(str(value))
    for item in record.get("items") or []:
        if not isinstance(item, dict):
            continue
        if (
            str(item.get("name") or "").lower() in {"overall", "total", ""}
            and item.get("summary")
        ):
            summaries.insert(0, str(item["summary"]))
    for summary in summaries:
        match = re.search(r"(\d+)\s*-\s*(\d+)", summary)
        if match:
            wins, losses = map(int, match.groups())
            return RecordSummary(wins, losses, f"{wins}-{losses}")
    return None


def _espn_standing(team_payload: dict) -> StandingSummary | None:
    team = team_payload.get("team") or {}
    label = str(team.get("standingSummary") or "").strip()
    if not label:
        return None
    match = re.match(r"(\d+)(?:st|nd|rd|th)?\b", label, flags=re.I)
    rank = int(match.group(1)) if match else None
    scope_match = re.search(r"\bin\s+(.+)$", label, flags=re.I)
    scope = scope_match.group(1) if scope_match else None
    return StandingSummary(label=label, rank=rank, scope=scope)


def parse_raptors_snapshot(
    schedule: dict,
    team_payload: dict,
    *,
    now: dt.datetime,
    fetched_at: dt.datetime,
) -> TeamSnapshot:
    games = _parse_espn_games(schedule)
    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)
    record = _espn_record(team_payload)
    standing = _espn_standing(team_payload)
    if phase not in {SeasonPhase.REGULAR, SeasonPhase.POSTSEASON}:
        record = standing = None
    return TeamSnapshot(
        team=RAPTORS,
        phase=phase,
        source="ESPN",
        fetched_at=fetched_at,
        last_game=last,
        record=record,
        standing=standing,
        next_game=nxt,
    )


def fetch_raptors_snapshot(
    *, now: dt.datetime, fetched_at: dt.datetime, session: requests.Session
) -> TeamSnapshot:
    schedule = _get_json(session, f"{_ESPN_NBA_BASE}/teams/tor/schedule")
    team_payload = _get_json(session, f"{_ESPN_NBA_BASE}/teams/tor")
    return parse_raptors_snapshot(schedule, team_payload, now=now, fetched_at=fetched_at)


# -- MLB / Blue Jays -------------------------------------------------------


def _mlb_status(game: dict) -> GameStatus:
    status = game.get("status") or {}
    abstract = str(status.get("abstractGameState") or "").lower()
    detailed = str(status.get("detailedState") or "").lower()
    combined = f"{abstract} {detailed}"
    if "cancel" in combined:
        return GameStatus.CANCELLED
    if "postpon" in combined or "suspend" in combined:
        return GameStatus.POSTPONED
    if abstract == "final" or "final" in detailed:
        return GameStatus.FINAL
    if abstract == "live" or "in progress" in detailed:
        return GameStatus.LIVE
    return GameStatus.SCHEDULED


def _mlb_name(side: dict) -> str:
    team = side.get("team") or {}
    return team.get("name") or team.get("teamName") or "Opponent"


def _parse_mlb_games(schedule: dict) -> list[GameSummary]:
    out: list[GameSummary] = []
    for day in schedule.get("dates") or []:
        for game in day.get("games") or []:
            if not isinstance(game, dict):
                continue
            try:
                start = _iso_datetime(game.get("gameDate"))
            except ValueError:
                continue
            teams = game.get("teams") or {}
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            at_home = str((home.get("team") or {}).get("id") or "") == "141"
            team_side, opponent = (home, away) if at_home else (away, home)
            status = _mlb_status(game)
            team_score = _integer(team_side.get("score"))
            opponent_score = _integer(opponent.get("score"))
            opponent_team = opponent.get("team") or {}
            out.append(
                GameSummary(
                    provider_game_id=str(game.get("gamePk") or ""),
                    start_time_utc=start,
                    opponent=_mlb_name(opponent),
                    opponent_abbreviation=str(opponent_team.get("abbreviation") or ""),
                    home_away="home" if at_home else "away",
                    status=status,
                    phase=_phase_from_type(game.get("gameType"), provider="mlb"),
                    team_score=team_score,
                    opponent_score=opponent_score,
                    result=_result(team_score, opponent_score, status),
                )
            )
    return out


def _parse_mlb_record_and_standing(
    standings: dict,
) -> tuple[RecordSummary | None, StandingSummary | None]:
    division_name = "AL East"
    team_row = None
    for block in standings.get("records") or []:
        division = block.get("division") or {}
        raw_name = str(division.get("name") or "")
        if raw_name:
            division_name = raw_name.replace("American League ", "AL ")
        for row in block.get("teamRecords") or []:
            if str((row.get("team") or {}).get("id") or "") == "141":
                team_row = row
                break
        if team_row:
            break
    if not isinstance(team_row, dict):
        return None, None

    league_record = team_row.get("leagueRecord") or {}
    wins = _integer(league_record.get("wins"))
    losses = _integer(league_record.get("losses"))
    record = None
    if wins is not None and losses is not None:
        record = RecordSummary(wins, losses, f"{wins}-{losses}")

    rank = _integer(team_row.get("divisionRank"))
    games_back = (
        str(team_row.get("gamesBack"))
        if team_row.get("gamesBack") not in (None, "")
        else None
    )
    standing = None
    if rank is not None:
        standing = StandingSummary(
            label=f"{_ordinal(rank)} {division_name}",
            rank=rank,
            scope=division_name,
            games_back=games_back,
        )
    return record, standing


def parse_blue_jays_snapshot(
    schedule: dict,
    standings: dict,
    *,
    now: dt.datetime,
    fetched_at: dt.datetime,
) -> TeamSnapshot:
    games = _parse_mlb_games(schedule)
    phase = _infer_phase(games, now)
    last, nxt = _select_games(games, phase, now)
    record, standing = _parse_mlb_record_and_standing(standings)
    if phase not in {SeasonPhase.REGULAR, SeasonPhase.POSTSEASON}:
        record = standing = None
    return TeamSnapshot(
        team=BLUE_JAYS,
        phase=phase,
        source="MLB Stats API",
        fetched_at=fetched_at,
        last_game=last,
        record=record,
        standing=standing,
        next_game=nxt,
    )


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
    return parse_blue_jays_snapshot(
        schedule, standings, now=now, fetched_at=fetched_at
    )

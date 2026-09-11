"""ESPN public-site adapters for deterministic Sports V2 major events.

The public JSON surfaces are treated as a bounded, failure-isolated source.
Scoreboard failure makes only that competition unavailable; standings failure
never suppresses otherwise valid results and fixtures.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

import requests

from .events import (
    EventMatch,
    EventMatchStatus,
    EventProvider,
    EventSnapshot,
    EventSpec,
    EventStandingRow,
    EventTable,
    select_event_matches,
)
from .models import TORONTO, UTC

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/{league}/standings"
_TIMEOUT = 15


def _parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _score(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _status(payload: dict) -> EventMatchStatus:
    kind = (payload.get("type") or {}) if isinstance(payload, dict) else {}
    name = str(kind.get("name") or "").upper()
    state = str(kind.get("state") or "").lower()
    completed = bool(kind.get("completed"))
    description = str(kind.get("description") or "").lower()

    if "POSTPON" in name or "postpon" in description:
        return EventMatchStatus.POSTPONED
    if "CANCEL" in name or "cancel" in description:
        return EventMatchStatus.CANCELLED
    if completed or state == "post" or any(token in name for token in ("FULL_TIME", "FINAL")):
        return EventMatchStatus.FINAL
    if state == "in" or "IN_PROGRESS" in name:
        return EventMatchStatus.LIVE
    return EventMatchStatus.SCHEDULED


def _team_name(competitor: dict) -> str:
    team = competitor.get("team") or {}
    return str(team.get("displayName") or team.get("name") or team.get("shortDisplayName") or "Unknown")


def _is_canada(competitor: dict) -> bool:
    team = competitor.get("team") or {}
    name = str(team.get("displayName") or team.get("name") or "").strip().casefold()
    abbrev = str(team.get("abbreviation") or "").strip().upper()
    return name == "canada" or abbrev == "CAN"


def parse_scoreboard(payload: dict) -> tuple[EventMatch, ...]:
    matches: list[EventMatch] = []
    for event in payload.get("events") or []:
        start = _parse_time(event.get("date"))
        competitions = event.get("competitions") or []
        if start is None or not competitions:
            continue
        competition = competitions[0] or {}
        competitors = competition.get("competitors") or []
        home = next((item for item in competitors if item.get("homeAway") == "home"), None)
        away = next((item for item in competitors if item.get("homeAway") == "away"), None)
        if not home or not away:
            continue

        season = event.get("season") or {}
        stage = season.get("slug") or season.get("name")
        status_payload = event.get("status") or competition.get("status") or {}
        status = _status(status_payload)
        detail = str(((status_payload.get("type") or {}).get("detail") or (status_payload.get("type") or {}).get("description") or "")).strip() or None

        matches.append(
            EventMatch(
                provider_id=str(event.get("id") or ""),
                start_time_utc=start.astimezone(UTC),
                home_team=_team_name(home),
                away_team=_team_name(away),
                status=status,
                stage=str(stage) if stage else None,
                home_score=_score(home.get("score")),
                away_score=_score(away.get("score")),
                detail=detail,
                canada_involved=_is_canada(home) or _is_canada(away),
            )
        )
    return tuple(matches)


def _stats(entry: dict) -> dict[str, dict]:
    return {
        str(stat.get("name")): stat
        for stat in (entry.get("stats") or [])
        if stat.get("name")
    }


def _stat_int(stats: dict[str, dict], name: str) -> int | None:
    value = (stats.get(name) or {}).get("value")
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _table_rows(entries: Iterable[dict]) -> tuple[EventStandingRow, ...]:
    rows: list[EventStandingRow] = []
    for position, entry in enumerate(entries, start=1):
        team = entry.get("team") or {}
        name = str(team.get("displayName") or team.get("name") or "Unknown")
        abbreviation = str(team.get("abbreviation") or "").upper()
        stats = _stats(entry)
        rows.append(
            EventStandingRow(
                position=position,
                team=name,
                played=_stat_int(stats, "gamesPlayed"),
                points=_stat_int(stats, "points"),
                goal_difference=_stat_int(stats, "pointDifferential"),
                canada=name.casefold() == "canada" or abbreviation == "CAN",
            )
        )
    return tuple(rows)


def parse_standings(payload: dict, *, spec: EventSpec) -> EventTable | None:
    groups = payload.get("children") or []
    if not groups:
        return None

    if spec.canada_promote:
        canada_group = None
        for group in groups:
            entries = ((group.get("standings") or {}).get("entries") or [])
            if any(row.canada for row in _table_rows(entries)):
                canada_group = group
                break
        group = canada_group
        if group is None:
            return None
        rows = _table_rows(((group.get("standings") or {}).get("entries") or []))[:4]
        return EventTable(label=str(group.get("name") or "Group"), rows=rows)

    group = groups[0]
    all_rows = _table_rows(((group.get("standings") or {}).get("entries") or []))
    # Champions League league phase: top three plus the 8/9 qualification cut.
    wanted = [row for row in all_rows if row.position in {1, 2, 3, 8, 9}]
    rows = tuple(wanted or all_rows[:5])
    return EventTable(label=str(group.get("name") or spec.label), rows=rows[:5])


def _date_window(now: dt.datetime) -> tuple[dt.date, dt.date]:
    today = now.astimezone(TORONTO).date()
    return today - dt.timedelta(days=1), today + dt.timedelta(days=7)


def fetch_espn_event_snapshot(
    spec: EventSpec,
    *,
    now: dt.datetime | None = None,
    session: requests.Session | None = None,
) -> EventSnapshot:
    if spec.provider != EventProvider.ESPN_SOCCER or not spec.provider_code:
        raise ValueError("fetch_espn_event_snapshot requires an ESPN soccer spec")

    now = now or dt.datetime.now(UTC)
    fetched_at = now.astimezone(UTC)
    http = session or requests.Session()
    start_date, end_date = _date_window(now)
    dates = f"{start_date:%Y%m%d}-{end_date:%Y%m%d}"

    try:
        response = http.get(
            ESPN_SCOREBOARD.format(league=spec.provider_code),
            params={"dates": dates},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        all_matches = parse_scoreboard(response.json())
        matches = select_event_matches(all_matches, spec=spec, now=now)
    except Exception:
        return EventSnapshot(
            spec=spec,
            fetched_at=fetched_at,
            source="ESPN",
            available=False,
            error="scoreboard_unavailable",
        )

    table = None
    if spec.include_standings:
        try:
            standings_response = http.get(
                ESPN_STANDINGS.format(league=spec.provider_code),
                timeout=_TIMEOUT,
            )
            standings_response.raise_for_status()
            table = parse_standings(standings_response.json(), spec=spec)
        except Exception:
            table = None

    return EventSnapshot(
        spec=spec,
        fetched_at=fetched_at,
        source="ESPN",
        matches=matches,
        standings=table,
    )

"""Deterministic Sports V2 major-headline discovery and selection.

The module intentionally keeps Sports outside Gemini. Discovery is narrow,
qualification is inspectable, and zero winners means zero model input.
"""

from __future__ import annotations

import datetime as dt
import html
import os
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

import requests

from src.voices.urls import canonical_url

UTC = dt.timezone.utc
GUARDIAN_SEARCH_URL = "https://content.guardianapis.com/search"
_TIMEOUT = 15

TEAM_ALIASES: dict[str, tuple[str, ...]] = {
    "leafs": ("toronto maple leafs", "maple leafs", "leafs"),
    "raptors": ("toronto raptors", "raptors"),
    "blue-jays": ("toronto blue jays", "blue jays", "jays"),
}

# Query one favourite team at a time. Do not fetch Guardian's broad sport pool.
GUARDIAN_TEAM_QUERIES = {
    "leafs": '"Toronto Maple Leafs"',
    "raptors": '"Toronto Raptors"',
    "blue-jays": '"Toronto Blue Jays"',
}

SOURCE_PRIORITY = {
    "reuters": 5,
    "associated press": 5,
    "ap": 5,
    "the guardian": 4,
    "guardian": 4,
    "espn": 3,
}


class Significance(StrEnum):
    CHAMPIONSHIP = "championship"
    LEADERSHIP = "leadership"
    MAJOR_TRANSACTION = "major_transaction"
    MATERIAL_INJURY = "material_injury"
    DISCIPLINE = "discipline"
    RETIREMENT = "retirement"
    AWARD_MILESTONE = "award_milestone"
    DRAFT_ROSTER = "draft_roster"
    INSTITUTIONAL = "institutional"
    CONTROVERSY = "controversy"


SIGNIFICANCE_SCORE = {
    Significance.CHAMPIONSHIP: 100,
    Significance.LEADERSHIP: 90,
    Significance.MAJOR_TRANSACTION: 85,
    Significance.MATERIAL_INJURY: 80,
    Significance.DISCIPLINE: 75,
    Significance.RETIREMENT: 72,
    Significance.AWARD_MILESTONE: 68,
    Significance.DRAFT_ROSTER: 65,
    Significance.INSTITUTIONAL: 62,
    Significance.CONTROVERSY: 55,
}


@dataclass(frozen=True)
class SportsHeadlineCandidate:
    title: str
    description: str
    url: str
    source: str
    published_at: dt.datetime
    team_key: str | None = None
    provider_id: str = ""

    def __post_init__(self) -> None:
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")

    @property
    def text(self) -> str:
        return f"{self.title} {self.description}".strip()


@dataclass(frozen=True)
class QualifiedHeadline:
    candidate: SportsHeadlineCandidate
    team_key: str
    significance: Significance
    corroboration: int = 1

    def to_dict(self) -> dict:
        c = self.candidate
        return {
            "team_key": self.team_key,
            "significance": self.significance.value,
            "headline": c.title,
            "description": c.description,
            "url": c.url,
            "source": c.source,
            "published_at": c.published_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "corroboration": self.corroboration,
        }


_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _clean_text(value: str | None) -> str:
    return " ".join(html.unescape(_TAG_RE.sub(" ", value or "")).split())


def _fold(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.lower()))


def detect_team(text: str) -> str | None:
    folded = f" {_fold(text)} "
    for key, aliases in TEAM_ALIASES.items():
        if any(f" {_fold(alias)} " in folded for alias in aliases):
            return key
    return None


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def classify_significance(candidate: SportsHeadlineCandidate) -> Significance | None:
    """Conservative significance gate. False negatives are intentional."""
    text = _fold(candidate.text)

    # Explicit routine/noise families win before positive terms.
    routine = (
        r"\bpreview\b", r"\bpractice\b", r"line combinations?", r"\bpostgame\b",
        r"game recap", r"\btakeaways?\b", r"\bgrades?\b", r"trade talk",
        r"trade rumours?", r"trade rumors?", r"\bcould sign\b", r"\bmight sign\b",
        r"\blinked to\b", r"\binterview\b", r"\bquotes?\b",
    )
    if _contains_any(text, routine):
        return None

    # Generic 'injury update' is not enough. Require severity/action evidence.
    if "injury update" in text and not _contains_any(
        text,
        (r"\bsurgery\b", r"out for (?:the )?season", r"\bmonths?\b", r"long term", r"long-term", r"indefinitely"),
    ):
        return None

    if _contains_any(text, (r"wins? (?:the )?(?:stanley cup|nba finals|world series)", r"champions?\b", r"clinches? (?:a )?playoff", r"eliminated from (?:the )?playoffs")):
        return Significance.CHAMPIONSHIP
    if _contains_any(text, (r"fires? (?:head )?coach", r"hires? (?:new )?(?:head )?coach", r"fires? (?:general manager|gm|president)", r"hires? (?:general manager|gm|president)")):
        return Significance.LEADERSHIP
    if _contains_any(text, (r"\btrades?\b", r"\btraded\b", r"\bacquires?\b", r"\bsigns?\b.*\b(?:year|contract|deal)\b", r"contract extension", r"extends? .* contract")):
        return Significance.MAJOR_TRANSACTION
    if _contains_any(text, (r"\bsurgery\b", r"out for (?:the )?season", r"\bseason ending\b", r"\bseason-ending\b", r"out .*\bmonths?\b", r"\bindefinitely\b", r"long term injury", r"long-term injury")):
        return Significance.MATERIAL_INJURY
    if _contains_any(text, (r"\bsuspended\b.*\b(?:games?|season)\b", r"\bdisciplin(?:e|ed|ary)\b", r"\bbanned\b")):
        return Significance.DISCIPLINE
    if _contains_any(text, (r"\bretires?\b", r"\bretirement\b")):
        return Significance.RETIREMENT
    if _contains_any(text, (r"wins? (?:the )?(?:mvp|hart|vezina|cy young|rookie of the year)", r"sets? (?:a )?(?:franchise|league|nhl|nba|mlb) record", r"breaks? (?:a )?(?:franchise|league|nhl|nba|mlb) record")):
        return Significance.AWARD_MILESTONE
    if _contains_any(text, (r"\bfirst overall pick\b", r"\bnumber one pick\b", r"\btop pick\b.*\bdraft\b", r"waives? .* captain", r"names? .* captain")):
        return Significance.DRAFT_ROSTER
    if _contains_any(text, (r"\bownership\b.*\b(?:sale|sells?|buys?|change)\b", r"league approves", r"franchise relocation", r"team sale")):
        return Significance.INSTITUTIONAL
    if _contains_any(text, (r"\binvestigation\b", r"\blawsuit\b", r"\bcriminal charges?\b")):
        return Significance.CONTROVERSY
    return None


def _title_tokens(title: str) -> set[str]:
    stop = {"the", "a", "an", "to", "of", "and", "for", "in", "on", "with", "toronto", "says", "report"}
    return {w for w in _WORD_RE.findall(title.lower()) if w not in stop}


def _same_event(a: QualifiedHeadline, b: QualifiedHeadline) -> bool:
    if a.team_key != b.team_key or a.significance != b.significance:
        return False
    au = canonical_url(a.candidate.url)
    bu = canonical_url(b.candidate.url)
    if au and au == bu:
        return True
    at, bt = _title_tokens(a.candidate.title), _title_tokens(b.candidate.title)
    if not at or not bt:
        return False
    return len(at & bt) / len(at | bt) >= 0.72


def qualify(candidates: Iterable[SportsHeadlineCandidate]) -> list[QualifiedHeadline]:
    out: list[QualifiedHeadline] = []
    for candidate in candidates:
        # Cricket is excluded even if a headline also happens to mention Toronto.
        if _contains_any(_fold(candidate.text), (r"\bcricket\b", r"\bipl\b", r"test match")):
            continue
        team = candidate.team_key or detect_team(candidate.text)
        if team not in TEAM_ALIASES:
            continue
        significance = classify_significance(candidate)
        if significance is None:
            continue
        out.append(QualifiedHeadline(candidate=candidate, team_key=team, significance=significance))
    return out


def dedupe_and_rank(candidates: Iterable[QualifiedHeadline], *, now: dt.datetime | None = None) -> list[QualifiedHeadline]:
    now = now or dt.datetime.now(UTC)
    groups: list[list[QualifiedHeadline]] = []
    for item in candidates:
        group = next((g for g in groups if _same_event(item, g[0])), None)
        if group is None:
            groups.append([item])
        else:
            group.append(item)

    ranked: list[QualifiedHeadline] = []
    for group in groups:
        corroboration = len({g.candidate.source.lower().strip() for g in group})
        best = max(group, key=lambda g: _rank_key(g, now=now, corroboration=corroboration))
        ranked.append(QualifiedHeadline(best.candidate, best.team_key, best.significance, corroboration))
    return sorted(ranked, key=lambda g: _rank_key(g, now=now, corroboration=g.corroboration), reverse=True)


def _rank_key(item: QualifiedHeadline, *, now: dt.datetime, corroboration: int) -> tuple:
    source = SOURCE_PRIORITY.get(item.candidate.source.lower().strip(), 1)
    age_hours = max(0.0, (now - item.candidate.published_at.astimezone(UTC)).total_seconds() / 3600)
    recency = max(0, 72 - int(age_hours))
    return (SIGNIFICANCE_SCORE[item.significance], min(corroboration, 3), source, recency, item.candidate.published_at.timestamp())


def select_team_winners(candidates: Iterable[SportsHeadlineCandidate], *, now: dt.datetime | None = None) -> dict[str, QualifiedHeadline]:
    """Return at most one deterministic major headline per favourite team."""
    winners: dict[str, QualifiedHeadline] = {}
    for item in dedupe_and_rank(qualify(candidates), now=now):
        winners.setdefault(item.team_key, item)
    return winners


def sports_model_payload(winners: dict[str, QualifiedHeadline]) -> list[dict]:
    """Initial V2 model boundary: always empty.

    Selected Sports headlines render from source headline/description. Keeping
    this function explicit makes a future budget regression testable.
    """
    return []


def fetch_guardian_team_candidates(
    *,
    since: dt.datetime,
    until: dt.datetime,
    page_size: int = 8,
    session: requests.Session | None = None,
) -> list[SportsHeadlineCandidate]:
    """Fetch narrow Guardian searches for the three favourite teams.

    Missing credentials or one failed team query degrades locally. This never
    falls back to Guardian's broad sport section.
    """
    key = os.environ.get("GUARDIAN_API_KEY")
    if not key:
        return []
    http = session or requests.Session()
    out: list[SportsHeadlineCandidate] = []
    for team_key, query in GUARDIAN_TEAM_QUERIES.items():
        try:
            response = http.get(
                GUARDIAN_SEARCH_URL,
                params={
                    "q": query,
                    "section": "sport",
                    "from-date": since.astimezone(UTC).date().isoformat(),
                    "to-date": until.astimezone(UTC).date().isoformat(),
                    "order-by": "newest",
                    "page-size": page_size,
                    "show-fields": "trailText",
                    "api-key": key,
                },
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            for row in response.json().get("response", {}).get("results", []):
                published = _parse_guardian_time(row.get("webPublicationDate"))
                if published is None or published < since or published > until:
                    continue
                out.append(
                    SportsHeadlineCandidate(
                        title=_clean_text(row.get("webTitle")),
                        description=_clean_text((row.get("fields") or {}).get("trailText")),
                        url=row.get("webUrl") or "",
                        source="The Guardian",
                        published_at=published,
                        team_key=team_key,
                        provider_id=str(row.get("id") or ""),
                    )
                )
        except Exception:
            continue
    return out


def _parse_guardian_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

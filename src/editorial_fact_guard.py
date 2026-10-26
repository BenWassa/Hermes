"""Conservative, source-bound checks for high-impact political claims.

A deterministic guard cannot fully fact-check model prose. It intervenes only
where the exact selected input's public metadata contains a *clear, positive*
contradiction to a tightly patterned claim. Ambiguous/missing evidence abstains.
No new fetch, model call, source bodies, or extra persisted personal data.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from calendar import month_name

from .editorial_integrity import _unique_exact, _unique_minor_slug_drift

log = logging.getLogger("the-daily.fact-guard")

_MONTHS = {name.lower(): number for number, name in enumerate(month_name) if name}
_MONTH = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
_SCHEDULED_VOTE = re.compile(
    r"\b(?:election|vote|polls)\b.{0,75}?"
    r"\b(?:set|scheduled|slated|due|will be held|to be held)\s+(?:for|on)\s+"
    + _MONTH + r"\s+(\d{1,2})(?:,?\s+(\d{4}))?\b",
    re.I,
)
_TODAY_VOTE = re.compile(
    r"(?:\b(?:election|voting|polls)\b.{0,80}\b"
    r"(?:is|are|takes place|begin|begins|start|starts|opened|opens)\s+(?:underway\s+|under way\s+)?today\b)"
    r"|(?:\b(?:election|voting|polls)\b.{0,80}\b(?:underway|under way)\b)"
    r"|(?:\b(?:election|voting|polls)\s+today\b)",
    re.I,
)
_INCUMBENT_PERSON = re.compile(
    r"\bincumbent\s+(?:president|prime minister|premier|governor)\s+"
    r"([A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+){0,2})\b"
)
_REELECTED = re.compile(r"\b(?:re-?elect(?:ed|ion)|wins?\s+(?:a\s+)?(?:second|third|fourth)\s+term)\b", re.I)
_RETURN_TO_POWER = re.compile(r"\b(?:returns?|returning|returned|back)\s+to\s+power\b", re.I)
_FIELDS = ("headline", "sub", "summary", "analysis")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _source_election_day(source_text: str, today: dt.date) -> dt.date | None:
    match = _SCHEDULED_VOTE.search(source_text)
    if not match:
        return None
    try:
        year = int(match.group(3)) if match.group(3) else today.year
        return dt.date(year, _MONTHS[match.group(1).lower()], int(match.group(2)))
    except (ValueError, KeyError):
        return None


def _incumbent_subject(source_text: str) -> str | None:
    if not _REELECTED.search(source_text):
        return None
    person = _INCUMBENT_PERSON.search(source_text)
    return person.group(1).casefold() if person else None


def _contradictions(text: str, *, vote_day: dt.date | None,
                    subject: str | None, today: dt.date) -> set[str]:
    issues = set()
    if vote_day and vote_day > today and _TODAY_VOTE.search(text):
        issues.add("future-vote-described-as-underway")
    if subject and subject in text.casefold() and _RETURN_TO_POWER.search(text):
        issues.add("incumbent-reelection-described-as-return")
    return issues


def _source_fallback(source: dict) -> str:
    # Never fabricate a replacement political event. The source headline is
    # already part of the bounded, model-visible public candidate metadata.
    return str(source.get("title") or "").strip()


def enforce_source_claims(sections: list[dict], model_input: list[dict],
                          today: dt.date) -> dict[str, int]:
    """Remove *contradicted sentences* in matched news cards, not entire stories.

    High-confidence facts are those explicitly supplied by the same selected
    story. If no safe sentence remains in a summary, use the source-stated
    headline rather than invent a winner, officeholder, result or event date.
    """
    stats = {"checked": 0, "flagged": 0, "sentences_withheld": 0,
             "abstained": 0}
    for section in sections:
        for card in section.get("stories", []):
            if card.get("backfill"):
                continue
            link = str(card.get("link") or "")
            source = _unique_exact(link, model_input) or _unique_minor_slug_drift(link, model_input)
            if source is None:
                stats["abstained"] += 1
                continue
            source_text = " ".join(str(source.get(key) or "") for key in ("title", "description"))
            vote_day = _source_election_day(source_text[:600], today)
            subject = _incumbent_subject(source_text[:600])
            if vote_day is None and subject is None:
                stats["abstained"] += 1
                continue
            stats["checked"] += 1
            had_contradiction = False
            for field in _FIELDS:
                value = card.get(field)
                if not isinstance(value, str) or not value.strip():
                    continue
                sentences = _SENTENCE.split(value.strip())
                remaining = []
                for sentence in sentences:
                    issues = _contradictions(sentence, vote_day=vote_day,
                                             subject=subject, today=today)
                    if issues:
                        had_contradiction = True
                        stats["sentences_withheld"] += 1
                        log.warning("Source-bound factual contradiction suppressed: %s", ",".join(sorted(issues)))
                    else:
                        remaining.append(sentence)
                if len(remaining) == len(sentences):
                    continue
                replacement = " ".join(remaining).strip()
                if field == "headline":
                    card[field] = replacement or _source_fallback(source)
                elif field == "summary":
                    card[field] = replacement or _source_fallback(source)
                else:
                    card[field] = replacement or None
            if had_contradiction:
                stats["flagged"] += 1
    if stats["flagged"]:
        log.warning("Source-bound political fact guard checked=%d flagged=%d sentences_withheld=%d abstained=%d",
                    stats["checked"], stats["flagged"], stats["sentences_withheld"], stats["abstained"])
    return stats

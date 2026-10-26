"""Toronto section integrity: keep off-city stories out, never publish without it.

Toronto coverage is not Canada coverage (see canada.py). The Canada-national
intake lane deliberately pulls national and regional Canadian journalism into
the pool, and nothing downstream stopped the single editor call from placing
that material in the Toronto-labelled section (verified by the 30-edition
baseline, HA-04), or from returning no Toronto section at all (HA-03).

This module is the small deterministic safeguard around the existing curation
call. It adds no model call and sends nothing new to the model:

* Every finished Toronto story needs a Toronto/GTA *signal*: it came from a
  configured Toronto local feed, or Toronto/GTA place terms appear in its
  headline or newswire dateline, or appear only in body text with no other
  region or national marker beside them. A story with no signal is moved to
  the desk its source hint names (World/Business/Opinion, only when that desk
  has room) or dropped. It is never silently kept under the Toronto label.
* The signal rules are generic place and feed evidence, not per-story rules.
* After removal the section is topped back up from Toronto-intake candidates
  (Toronto local feeds or a ``toronto`` section hint, never keywords alone)
  in the full eligible pool, so edition size survives.
* The finished edition always carries a Toronto section. If no Toronto
  candidate exists at all the section publishes empty with an error log; the
  build never fails over it.

Backfilled cards are built from source metadata only (and carry ``backfill: True``). They are a fallback and
deliberately plain: no analysis, no invented prose.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from collections import defaultdict
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from . import canada, config, crime
from .voices.urls import canonical_url

log = logging.getLogger("the-daily.toronto")

TORONTO_SECTION_ID = "toronto"

# Desks an off-city story may move to. The story's own intake hint decides;
# anything else (including an unmatched story) goes to World.
_REASSIGN_DESKS = ("world", "business", "opinion")
_DEFAULT_REASSIGN_DESK = "world"

# Toronto proper plus the GTA and its immediate ring, and the civic institutions
# that make a story Toronto-relevant without naming the city. Ambiguous words
# (Peel, Durham, Ajax) are only listed in their regional form.
_TORONTO_TERMS = (
    "toronto", "gta", "greater toronto", "mississauga", "brampton", "vaughan",
    "markham", "richmond hill", "scarborough", "etobicoke", "north york",
    "east york", "york region", "york regional police", "peel region",
    "peel regional police", "durham region", "halton region", "halton hills",
    "oakville", "burlington", "pickering", "oshawa", "newmarket", "caledon",
    "ttc", "metrolinx", "go transit", "queen's park",
    "ontario legislature", "ontario government", "ontario premier",
    "pearson airport", "ontario place",
    # Bare "Hamilton" is a surname and a Grand Prix driver; only the city forms.
    "hamilton, ont", "hamilton, on", "city of hamilton", "hamilton spectator",
    "hamilton police", "hamilton city council", "hamilton tiger-cats",
)

# Region and national markers. They only veto a *body-only* Toronto mention
# (e.g. a national release that lists Toronto among several cities); they never
# create a signal, so an unlisted place still fails the missing-signal test.
_OFF_CITY_TERMS = (
    "alberta", "british columbia", "manitoba", "saskatchewan", "quebec",
    "nova scotia", "new brunswick", "newfoundland", "labrador",
    "prince edward island", "yukon", "northwest territories", "nunavut",
    "vancouver", "calgary", "edmonton", "winnipeg", "regina", "saskatoon",
    "montreal", "ottawa", "halifax", "thunder bay", "sudbury", "windsor",
    "kingston", "nationwide", "across canada", "canada-wide", "coast to coast",
)


def _phrase_re(terms: tuple[str, ...], *, gta_guard: bool = False) -> re.Pattern:
    ordered = sorted(terms, key=len, reverse=True)
    alternatives = []
    for term in ordered:
        pattern = re.escape(term)
        if gta_guard and term == "gta":
            # "GTA VI" / "GTA 6" / "GTA V" are the video game, not the region.
            pattern += r"(?!\s*(?:\d|[ivx]+(?!\w)))"
        alternatives.append(pattern)
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)")


_TORONTO_RE = _phrase_re(_TORONTO_TERMS, gta_guard=True)
_OFF_CITY_RE = _phrase_re(_OFF_CITY_TERMS)
# Newswire datelines open the description: "TORONTO, Oct. 14, 2026 /CNW/ - ...".
_DATELINE_RE = re.compile(r"^\s*([A-Z][A-Z .'’\-–—]{2,40}?)\s*,(?:\s*(ONT?)(?![A-Za-z]))?")
_SENSITIVE_RE = re.compile(
    r"\b(?:shoot|shot|stab|murder|homicid|kill|dead|death|died|dies|fatal|"
    r"assault|attack|war|bomb|terror|disaster|victim|armed robbery|carjack|"
    r"home invasion|kidnap|abduct|gunm[ae]n|gunfire|slain|manslaughter)",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[a-z0-9']{4,}")
_TORONTO_TZ = ZoneInfo(config.TIMEZONE)
_SUMMARY_LIMIT = 320
_DUPLICATE_OVERLAP = 0.6


def _norm(text: object) -> str:
    return str(text or "").replace("’", "'").casefold()


def _feed_names() -> set[str]:
    return {str(feed.get("name")) for feed in config.TORONTO_RSS}


def _identity(story: dict) -> str:
    return canonical_url(story.get("canonical_url") or story.get("link") or "") or str(
        story.get("link") or ""
    )


def toronto_signal(story: dict, candidate: dict | None = None) -> str:
    """Why a story may carry the Toronto label; empty string means no evidence.

    ``story`` is a finished card (headline/sub/summary) or a raw candidate
    (title/description); ``candidate`` is the intake record it came from, when
    known. Order: feed > headline > dateline > body.
    """
    candidate = candidate or {}
    if candidate.get("source") in _feed_names() and not canada.is_canada_national(candidate):
        return "feed"

    strong = _norm(
        " ".join(str(x or "") for x in (candidate.get("title"), story.get("title"), story.get("headline")))
    )
    if _TORONTO_RE.search(strong):
        return "headline"

    description = str(candidate.get("description") or story.get("description") or "")
    dateline = _DATELINE_RE.match(description)
    if dateline and _TORONTO_RE.search(
        _norm(dateline.group(1) + (f", {dateline.group(2)}" if dateline.group(2) else ""))
    ):
        return "dateline"

    weak = _norm(" ".join([strong, description, str(story.get("sub") or ""), str(story.get("summary") or "")]))
    if _TORONTO_RE.search(weak) and not _OFF_CITY_RE.search(weak):
        return "body"
    return ""


def _index(pool: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for candidate in pool:
        for key in (_identity(candidate), str(candidate.get("link") or "")):
            if key:
                index.setdefault(key, candidate)
    return index


def _lookup(story: dict, index: dict[str, dict]) -> dict | None:
    link = str(story.get("link") or "")
    return index.get(_identity(story)) or index.get(link)


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(_norm(text)))


def _is_duplicate(title: str, taken: list[set[str]]) -> bool:
    words = _tokens(title)
    if not words:
        return False
    return any(len(words & other) / len(words | other) >= _DUPLICATE_OVERLAP for other in taken if other)


def _filed_label(pub_date: str, today: dt.date) -> str | None:
    try:
        try:
            when = dt.datetime.fromisoformat(str(pub_date).replace("Z", "+00:00"))
        except ValueError:
            when = parsedate_to_datetime(str(pub_date))
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    local = when.astimezone(_TORONTO_TZ)
    if local.date() == today:
        return local.strftime("%-I:%M %p")
    if local.date() == today - dt.timedelta(days=1):
        return "Yesterday"
    return None


def _clip(text: str) -> str:
    if len(text) <= _SUMMARY_LIMIT:
        return text
    cut = text[:_SUMMARY_LIMIT].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return cut + "…"


def _fallback_card(candidate: dict, card_id: str, today: dt.date) -> dict:
    title = str(candidate.get("title") or "")
    description = str(candidate.get("description") or "").strip()
    summary = _clip(description) if description else f"Reported by {candidate.get('source') or 'a local source'}."
    return {
        "id": card_id,
        "lead": False,
        "kicker": "TORONTO",
        "headline": title,
        "sub": None,
        "summary": summary,
        "analysis": None,
        "time": _filed_label(str(candidate.get("pub_date") or ""), today),
        "tag": None,
        "sensitivity": bool(_SENSITIVE_RE.search(f"{title} {description}")),
        "image": candidate.get("image") or None,
        "link": candidate.get("link"),
        # Marks a card built from source metadata, not chosen by the model
        # (editorial_provenance counts these apart from invented links).
        "backfill": True,
    }


def _round_robin_sources(candidates: list[dict]) -> list[dict]:
    """Interleave sources so one feed cannot supply the whole backfill."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        buckets[str(candidate.get("source") or "")].append(candidate)
    pools = list(buckets.values())
    out: list[dict] = []
    while any(pools):
        for pool in pools:
            if pool:
                out.append(pool.pop(0))
    return out


_OPINION_PATHS = ("/opinion/", "/opinions/", "/commentisfree/", "/voices/", "/leaders/")


def _is_opinion_path(link: str) -> bool:
    lowered = link.casefold()
    return any(path in lowered for path in _OPINION_PATHS)


def _is_opinion(candidate: dict) -> bool:
    return (
        _is_opinion_path(str(candidate.get("link") or ""))
        or candidate.get("section_hint") == "opinion"
        or candidate.get("content_genre") == "opinion"
    )


def _is_toronto_intake(candidate: dict) -> bool:
    """Backfill only trusted Toronto intake, with stricter fallback handling."""
    if canada.is_canada_national(candidate):
        return False
    if candidate.get("source") == config.TORONTO_FALLBACK_RSS["name"]:
        # The syndicated CityNews local feed also contains Hamilton and other
        # non-GTA news. Origin alone is not proof of Toronto relevance.
        return toronto_signal(candidate, candidate) in {"headline", "dateline"}
    return candidate.get("source") in _feed_names() or candidate.get("section_hint") == TORONTO_SECTION_ID


def _backfill(
    need: int, pool: list[dict], sections: list[dict], today: dt.date
) -> list[dict]:
    """Plain cards from Toronto-intake candidates not already in the paper.

    Candidates are limited to Toronto local feeds or items the intake hinted
    ``toronto``; a keyword match (Hamilton the driver, GTA the game) never
    qualifies a World or Business item. Candidates must not include incidents
    withheld by the crime gate, so that gate's decision is not undone here.
    """
    if need <= 0:
        return []
    taken_links: set[str] = set()
    taken_titles: list[set[str]] = []
    taken_ids: set[str] = set()
    for section in sections:
        for story in section.get("stories", []):
            taken_links.update(k for k in (_identity(story), str(story.get("link") or "")) if k)
            taken_titles.append(_tokens(story.get("headline", "")))
            taken_ids.add(str(story.get("id") or ""))

    eligible: list[dict] = []
    for candidate in pool:
        if not candidate.get("title") or not candidate.get("link"):
            continue
        if not _is_toronto_intake(candidate) or _is_opinion(candidate):
            continue
        # Do not backfill with stale or dateless syndicated fallback stories.
        if (candidate.get("source") == config.TORONTO_FALLBACK_RSS["name"]
                and _filed_label(str(candidate.get("pub_date") or ""), today) is None):
            continue
        if crime.is_unsupported_incident(candidate):
            continue
        eligible.append(candidate)
    ordered = _round_robin_sources(eligible)
    # Plain news first; violent-incident items only if nothing else is left.
    ordered.sort(key=lambda c: bool(_SENSITIVE_RE.search(f"{c['title']} {c.get('description') or ''}")))

    cards: list[dict] = []
    for candidate in ordered:
        if len(cards) >= need:
            break
        keys = {_identity(candidate), str(candidate["link"])}
        if keys & taken_links or _is_duplicate(candidate["title"], taken_titles):
            continue
        number = len(cards) + 1
        card_id = f"t{number}"
        while card_id in taken_ids:
            number += 1
            card_id = f"t{number}"
        taken_ids.add(card_id)
        taken_links.update(k for k in keys if k)
        taken_titles.append(_tokens(candidate["title"]))
        cards.append(_fallback_card(candidate, card_id, today))
    return cards


def _section_cap(section_id: str) -> int:
    return next(spec["cap"] for spec in config.SECTIONS if spec["id"] == section_id)


def place_section(sections: list[dict], section: dict) -> None:
    """Insert ``section`` in canonical order (replacing any same-id section)."""
    sections[:] = [s for s in sections if s.get("id") != section["id"]]
    order = {spec["id"]: i for i, spec in enumerate(config.SECTIONS)}
    rank = order.get(section["id"], len(order))
    at = next(
        (i for i, s in enumerate(sections) if order.get(s.get("id"), len(order)) > rank),
        len(sections),
    )
    sections.insert(at, section)


def enforce_toronto_section(
    sections: list[dict],
    pool: list[dict],
    today: dt.date,
) -> tuple[list[dict], dict]:
    """Return sections whose Toronto section is on-city and present.

    ``sections`` is the normalized finished edition, ``pool`` the full eligible
    intake (not just the bounded model input) so backfill can reach Toronto
    candidates the balanced trim did not send. Returns ``(sections, stats)``.
    """
    sections = [dict(s, stories=list(s.get("stories", []))) for s in sections]
    index = _index(pool)
    spec_cap = _section_cap(TORONTO_SECTION_ID)

    toronto = next((s for s in sections if s.get("id") == TORONTO_SECTION_ID), None)
    original = list(toronto["stories"]) if toronto else []

    kept: list[dict] = []
    reassigned = dropped = 0
    for story in original:
        candidate = _lookup(story, index)
        if toronto_signal(story, candidate):
            kept.append(story)
            continue
        hint = str((candidate or {}).get("section_hint") or "")
        desk_id = hint if hint in _REASSIGN_DESKS else _DEFAULT_REASSIGN_DESK
        desk = next((s for s in sections if s.get("id") == desk_id), None)
        if desk is None:
            desk = {"id": desk_id, "label": next(
                s["label"] for s in config.SECTIONS if s["id"] == desk_id), "stories": []}
            place_section(sections, desk)
        links = {str(s.get("link") or "") for s in desk["stories"]}
        if len(desk["stories"]) < _section_cap(desk_id) and story.get("link") not in links:
            story["lead"] = False
            story["analysis"] = None
            desk["stories"].append(story)
            reassigned += 1
        else:
            dropped += 1
        log.info("toronto guard: off-city story left Toronto section -> %s", desk_id)

    target = min(spec_cap, len(original) or spec_cap)
    filled_cards = _backfill(target - len(kept), pool, sections, today)
    kept.extend(filled_cards)

    if not kept:
        message = "Toronto section would publish empty: no on-city story and no Toronto candidate in the pool"
        log.error("toronto guard: %s; publishing an empty Toronto section", message)

    label = next(s["label"] for s in config.SECTIONS if s["id"] == TORONTO_SECTION_ID)
    place_section(sections, {"id": TORONTO_SECTION_ID, "label": label, "stories": kept})
    stats = {
        "original": len(original),
        "kept": len(kept) - len(filled_cards),
        "reassigned": reassigned,
        "dropped": dropped,
        "backfilled": len(filled_cards),
        "final": len(kept),
    }
    log.info(
        "toronto guard original=%(original)d kept=%(kept)d reassigned=%(reassigned)d "
        "dropped=%(dropped)d backfilled=%(backfilled)d final=%(final)d",
        stats,
    )
    return sections, stats

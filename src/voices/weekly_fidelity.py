"""Deterministic editorial-fidelity checks for the weekly Voices brief.

The weekly screen makes exactly one model call whose free text (the lead
summary and per-piece reasons) is never trusted on its own.  This module holds
the pure, model-free rules that decide whether that text may be published next
to the selected cards:

* titles quoted in prose must be exact substrings of a canonical title;
* the summary must not discuss pieces or writers outside the final selected set,
  nor state a piece/writer count that disagrees with the rendered cards;
* summaries and reasons must not use stock filler or ``headline suggests``
  meta-narration;
* pieces whose public excerpt describes association only may not be described
  with causal verbs unless the same sentence keeps the limitation explicit.

When the text fails, callers replace it with :func:`canonical_summary`, which is
built only from canonical source metadata.  Nothing here fetches or calls a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

POSTURE_ASSOCIATION = "association_only"
POSTURE_CAUSAL = "causal_support"
POSTURE_UNSPECIFIED = "unspecified"

_WS = re.compile(r"\s+")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9]+")
_QUOTED = re.compile(r"[“\"]([^“”\"]{3,200})[”\"]")

_CAUSAL_SUPPORT = re.compile(
    r"\b(randomi[sz]ed|controlled trial|natural experiment|field experiment|"
    r"instrumental variable|regression discontinuity|causal (?:effect|evidence|impact))\b",
    re.I,
)
_ASSOCIATION = re.compile(
    r"\b(correlat\w*|associat(?:ed|ion|ions) (?:with|between)|linked to|link between|"
    r"relationship between|observational|cross-sectional|self-report\w*|"
    r"(?:cannot|can't|does not|doesn't|not) (?:establish|prove|show|demonstrate) causa\w*|"
    r"causal limitations?|no causal)\b",
    re.I,
)

# Causal verbs/nouns that upgrade an association into a mechanism.
_CAUSAL_CLAIM = re.compile(
    r"\b(cause[sd]?|causing|causal(?:ly)?|explains?|explained by|explanatory|"
    r"drives?|driven by|drove|leads? to|led to|results? in|resulted in|"
    r"due to|because of|responsible for|accounts? for|thanks to)\b",
    re.I,
)
# A causal word in a sentence that also keeps the limitation explicit is honest.
_CAUSAL_HEDGE = re.compile(
    r"\b(correlat\w*|associat\w*|linked to|link between|observational|"
    r"(?:cannot|can't|does not|doesn't|not) (?:establish|prove|show|demonstrate)|"
    r"not (?:necessarily )?causal|causal limitations?|no causal|"
    r"stops? short of|falls? short of)\b",
    re.I,
)

# Stock phrasing the issue (#70) calls out, plus the ``the headline suggests``
# meta-narration that leaks the model's evidence boundary onto the page.
_FILLER = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"\bevolving landscape\b",
        r"\bprovides? (?:a )?(?:substantive|valuable|significant|rich) insights?\b",
        r"\bsignificant (?:social|societal|cultural) trends?\b",
        r"\b(?:far-reaching|profound|broader) (?:societal )?implications\b",
        r"\bsocietal implications\b",
        r"\b(?:offers?|provides?) a (?:focused|substantive|unique|compelling) (?:look|perspective)\b",
        r"\bprioriti[sz]\w* explanatory depth\b",
        r"\bsheds? (?:new )?light on\b",
        r"\brich tapestry\b",
        r"\bcomplex interplay\b",
        r"\b(?:these|the) selections (?:provide|offer)\b",
        r"\bthe (?:headline|excerpt|description)(?: and (?:the )?(?:headline|excerpt|description))? "
        r"(?:suggests?|indicates?|describes?|implies|signals?)\b",
        r"\bwould have material consequences\b",
        r"\bfits? the reader'?s interests?\b",
        r"\baligns? with the reader'?s\b",
    )
)

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
}
_COUNT_RE = re.compile(
    r"\b(one|two|three|four|five|six|[1-6])\s+(?:(?:distinct|separate|selected|core|new|"
    r"other|different|recent|of the)\s+)*"
    r"(pieces?|articles?|essays?|items?|columns?|selections?|posts?|writers?|voices?)\b",
    re.I,
)
_PIECE_NOUNS = {"piece", "pieces", "article", "articles", "essay", "essays", "item",
                "items", "column", "columns", "selection", "selections", "post", "posts"}


@dataclass(frozen=True)
class Piece:
    """Canonical facts about one candidate, as stored from the source."""

    key: str
    title: str
    writers: tuple[str, ...]
    publication: str = ""
    posture: str = POSTURE_UNSPECIFIED
    excerpt: str = ""


def _norm(text: str) -> str:
    text = (
        (text or "")
        .replace("’", "'").replace("‘", "'")
        .replace("“", '"').replace("”", '"')
    )
    return _WS.sub(" ", text).strip().casefold()


def _words(text: str) -> list[str]:
    return _WORD.findall(_norm(text))


def evidence_posture(*texts: str) -> str:
    """Classify what the public excerpt/headline says about evidence strength."""
    blob = " ".join(t for t in texts if t)
    if not blob:
        return POSTURE_UNSPECIFIED
    if _CAUSAL_SUPPORT.search(blob):
        return POSTURE_CAUSAL
    if _ASSOCIATION.search(blob):
        return POSTURE_ASSOCIATION
    return POSTURE_UNSPECIFIED


def filler_hits(text: str) -> list[str]:
    return [m.group(0).lower() for pat in _FILLER if (m := pat.search(text or ""))]


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE.split(text or "") if s.strip()]


def _mentions(sentence: str, piece: Piece) -> bool:
    folded = _norm(sentence)
    if _norm(piece.title) and _norm(piece.title) in folded:
        return True
    for writer in piece.writers:
        name = _norm(writer)
        if name and name in folded:
            return True
        last = name.split()[-1] if name.split() else ""
        if len(last) >= 4 and re.search(rf"\b{re.escape(last)}\b", folded):
            return True
    title_words = {w for w in _words(piece.title) if len(w) > 3}
    if len(title_words) >= 2:
        overlap = title_words & set(_words(sentence))
        if len(overlap) >= 2 and len(overlap) * 2 >= len(title_words):
            return True
    return False


def causal_overclaims(text: str, pieces: list[Piece], *, single_piece: bool = False) -> list[str]:
    """Sentences that apply causal wording to a piece whose source is association-only.

    ``single_piece`` means the text is already scoped to one piece (a card reason),
    so every sentence is attributed to it.
    """
    guarded = [p for p in pieces if p.posture == POSTURE_ASSOCIATION]
    if not guarded:
        return []
    hits: list[str] = []
    for sentence in _sentences(text):
        if not _CAUSAL_CLAIM.search(sentence) or _CAUSAL_HEDGE.search(sentence):
            continue
        if single_piece or any(_mentions(sentence, p) for p in guarded):
            hits.append(sentence.strip())
    return hits


def quoted_title_problems(text: str, selected: list[Piece], pool: list[Piece]) -> list[str]:
    """Quoted titles must match a canonical title exactly; titles of unselected pieces are out."""
    problems: list[str] = []
    selected_titles = [_norm(p.title) for p in selected]
    other_titles = [_norm(p.title) for p in pool if p.key not in {s.key for s in selected}]
    excerpts = [_norm(p.excerpt) for p in selected if p.excerpt]
    for match in _QUOTED.finditer(text or ""):
        quoted = _norm(match.group(1)).strip(" .,;:")
        if len(quoted.split()) < 3:
            continue
        if any(quoted in title for title in selected_titles):
            continue
        if any(quoted in title for title in other_titles):
            problems.append(f"quotes the title of a piece outside the selected set: {match.group(1)!r}")
        elif any(quoted in excerpt for excerpt in excerpts):
            continue
        else:
            problems.append(f"quoted text is not a canonical selected title: {match.group(1)!r}")
    return problems


def _count_problems(text: str, selected: list[Piece]) -> list[str]:
    """Flag totals larger than the rendered set (the "discussed three, showed one" failure).

    Smaller counts are allowed: "two of the pieces" or a comparison between two of
    three cards does not discuss anything that is missing from the page.
    """
    problems: list[str] = []
    distinct_writers = {w for p in selected for w in p.writers}
    for match in _COUNT_RE.finditer(text or ""):
        number = _NUMBER_WORDS[match.group(1).lower()]
        noun = match.group(2).lower()
        expected = len(selected) if noun in _PIECE_NOUNS else len(distinct_writers)
        if number > expected:
            problems.append(f"states {number} {noun} but the rendered set has {expected}")
    return problems


def summary_problems(
    summary: str,
    selected: list[Piece],
    pool: list[Piece],
    *,
    covers: tuple[str, ...] = (),
) -> list[str]:
    """Reasons the lead synthesis may not be published beside ``selected``."""
    problems: list[str] = []
    selected_keys = {p.key for p in selected}
    if not summary:
        return ["empty summary"]
    outside_covers = [key for key in covers if key not in selected_keys]
    if outside_covers:
        problems.append(f"model reports covering unselected keys: {outside_covers}")

    folded = _norm(summary)
    selected_writers = {_norm(w) for p in selected for w in p.writers}
    for piece in pool:
        if piece.key in selected_keys:
            continue
        title = _norm(piece.title)
        if len(title) >= 8 and title in folded:
            problems.append(f"discusses unselected piece {piece.title!r}")
        for writer in piece.writers:
            name = _norm(writer)
            if name and name not in selected_writers and name in folded:
                problems.append(f"names writer outside the selected set: {writer}")

    problems.extend(_count_problems(summary, selected))
    problems.extend(quoted_title_problems(summary, selected, pool))
    problems.extend(f"generic filler: {hit!r}" for hit in filler_hits(summary))
    problems.extend(
        f"causal wording for association-only source: {s!r}"
        for s in causal_overclaims(summary, selected, single_piece=len(selected) == 1)
    )
    return list(dict.fromkeys(problems))


def reason_problems(reason: str, piece: Piece, selected: list[Piece], pool: list[Piece]) -> list[str]:
    """Reasons a per-card line must be dropped instead of rendered."""
    problems = [f"generic filler: {hit!r}" for hit in filler_hits(reason)]
    problems.extend(quoted_title_problems(reason, selected, pool))
    problems.extend(
        f"causal wording for association-only source: {s!r}"
        for s in causal_overclaims(reason, [piece], single_piece=True)
    )
    return problems


def _byline(piece: Piece) -> str:
    who = " & ".join(piece.writers)
    where = f" in {piece.publication}" if piece.publication else ""
    return f"{who}{where}" if who else piece.publication


def canonical_summary(selected: list[Piece]) -> str:
    """Deterministic lead built only from canonical metadata (no claims about content)."""
    if not selected:
        return ""
    if len(selected) == 1:
        piece = selected[0]
        return f"One Core piece cleared the filter this week: {_byline(piece)}, “{piece.title}”."
    count = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}.get(len(selected), str(len(selected)))
    parts = "; ".join(f"{_byline(p)}, “{p.title}”" for p in selected)
    return (
        f"{count} Core pieces cleared the filter this week, each standing on its own: {parts}."
    )

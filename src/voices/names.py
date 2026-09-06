"""Person-name normalization and byline parsing for Voice attribution.

Two jobs, both deliberately biased toward *under*-matching:

1. ``name_key`` turns a displayed name into a comparable canonical form.
2. ``parse_byline`` turns a displayed byline string into the list of person
   names it actually asserts as authors.

The bias matters. A missed attribution costs the reader one article they can
still find elsewhere; a false attribution puts someone else's writing under a
followed Voice's name. Every rule here therefore prefers returning nothing to
returning a guess: no substring matching, no first-name matching, no fuzzy
distance, no single-token names.
"""

from __future__ import annotations

import re
import unicodedata
from html import unescape

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# Stripped from the front of a byline string.
_BYLINE_PREFIX_RE = re.compile(r"^\s*(?:by|By|BY|from|From)\b[\s:]*", re.UNICODE)

# Coauthor separators. Order matters: the word forms are matched on token
# boundaries so a surname such as "Anderson" is never split on "and".
_SEPARATOR_RE = re.compile(r"\s*(?:[,;/]|\band\b|\bAND\b|&|\bwith\b|\bWith\b)\s*")

# Titles dropped from the front of a name.
_HONORIFICS = {
    "dr", "prof", "professor", "mr", "mrs", "ms", "miss", "mx", "sir", "dame",
    "lord", "lady", "rev", "reverend", "fr", "sen", "rep", "gov", "judge",
    "the", "rt", "hon",
}

# Post-nominals dropped from the end of a name.
_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "dphil", "obe", "cbe",
    "mbe", "kbe", "qc", "kc", "esq", "cfa", "rn", "do", "jd",
}

# Lowercase particles that legitimately sit inside a surname. These are never
# treated as the start of a trailing role/location clause.
_PARTICLES = {
    "van", "von", "de", "del", "della", "der", "den", "di", "da", "dos", "du",
    "la", "le", "el", "al", "bin", "ibn", "ter", "ten", "op", "y", "mac", "mc",
    "st", "san", "santa",
}

# Lowercase words that introduce a trailing location/affiliation clause in a
# displayed byline, e.g. "Jane Doe in Kyiv" or "Jane Doe for Reuters".
_CLAUSE_STARTERS = {"in", "at", "for", "on", "from", "of", "near", "aboard", "reporting"}

# Job-title words. A trailing run of these (with their capitalised beat words)
# is dropped, e.g. "Patrick Wintour Diplomatic editor".
_ROLE_WORDS = {
    "editor", "editors", "correspondent", "correspondents", "reporter",
    "reporters", "columnist", "critic", "writer", "writers", "analyst",
    "commentator", "contributor", "contributors", "staff", "bureau", "chief",
    "anchor", "producer", "photographer", "cartoonist", "blogger",
    "editorial", "board", "desk", "team", "newsroom", "agency", "agencies",
    "press", "wire", "service",
}

# Capitalised words that only ever appear as part of a beat description, i.e.
# immediately before a role word ("Diplomatic editor", "Political Correspondent").
_BEAT_WORDS = {
    "diplomatic", "political", "economics", "economic", "business", "science",
    "health", "environment", "technology", "tech", "media", "sports", "sport",
    "arts", "culture", "world", "national", "international", "global",
    "financial", "markets", "legal", "crime", "defence", "defense", "energy",
    "climate", "education", "transport", "senior", "deputy", "associate",
    "assistant", "special", "chief", "managing", "executive", "contributing",
    "guest", "opinion", "features", "investigations", "investigative",
    "washington", "brussels", "jerusalem", "beijing", "moscow", "kyiv",
    "london", "toronto", "ottawa", "paris", "berlin", "us", "uk", "eu",
}

# Byline strings that assert an organisation rather than a person.
_NON_PERSON = {
    "staff", "editorial board", "the editorial board", "editorial", "reuters",
    "associated press", "the associated press", "ap", "afp", "bloomberg",
    "the canadian press", "canadian press", "pa media", "press association",
    "guardian staff", "reuters staff", "newsroom", "admin", "editor",
    "the guardian", "guardian", "observer editorial", "cbc news", "cbc",
    "special to the star", "star staff", "unknown", "anonymous", "no author",
}


def clean_text(value: str | None) -> str:
    """HTML-unescape, drop tags, collapse whitespace."""
    if not value:
        return ""
    text = _TAG_RE.sub(" ", str(value))
    text = unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _fold(value: str) -> str:
    """Lowercase, strip diacritics, and reduce punctuation to spaces."""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    # Apostrophes join ("O'Brien" -> "obrien"); other punctuation separates.
    text = re.sub(r"[‘’'`ʼ]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _WS_RE.sub(" ", text).strip()


def name_tokens(value: str | None) -> tuple[str, ...]:
    """Canonical comparable token sequence for a person name.

    Honorifics are dropped from the front and post-nominals from the end.
    Returns an empty tuple when the input does not look like a person name.
    """
    folded = _fold(clean_text(value))
    if not folded:
        return ()
    tokens = folded.split(" ")
    while tokens and tokens[0] in _HONORIFICS:
        tokens.pop(0)
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    return tuple(tokens)


def name_key(value: str | None) -> str:
    """Stable string key for a person name, or "" when unusable.

    Single-token inputs return "": Hermes never attributes on a mononym.
    """
    tokens = name_tokens(value)
    if len(tokens) < 2:
        return ""
    if " ".join(tokens) in {_fold(n) for n in _NON_PERSON}:
        return ""
    return " ".join(tokens)


def _drop_middle_initials(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if len(tokens) <= 2:
        return tokens
    kept = [tokens[0]]
    kept.extend(t for t in tokens[1:-1] if len(t) > 1)
    kept.append(tokens[-1])
    return tuple(kept)


def match_key(value: str | None) -> str:
    """Key on which two displayed names are considered the same person.

    This is ``name_key`` with middle *initials* removed, so "Jonathan D.
    Haidt" and "Jonathan Haidt" share a key. A middle *name* is not
    interchangeable with its absence, so "Conrad Moffat Black" keeps its own
    key and only matches "Conrad Black" if an alias says so. Equality of this
    key is the only name test Hermes performs: no substring, prefix, fuzzy, or
    first-name-only matching exists anywhere in the resolver.
    """
    if not name_key(value):
        return ""
    tokens = _drop_middle_initials(name_tokens(value))
    return " ".join(tokens) if len(tokens) >= 2 else ""


def names_match(left: str | None, right: str | None) -> bool:
    """True when two displayed names denote the same person."""
    a = match_key(left)
    return bool(a) and a == match_key(right)


def _strip_trailing_role(part: str) -> str:
    """Drop a trailing job-title/beat clause from one byline part."""
    tokens = part.split()
    changed = True
    while changed and len(tokens) > 2:
        changed = False
        tail = tokens[-1]
        folded = _fold(tail)
        if folded in _ROLE_WORDS:
            tokens.pop()
            changed = True
            continue
        # A beat word only counts as a role clause when a role word already
        # came off behind it, which the loop guarantees by running tail-first.
        if folded in _BEAT_WORDS and len(tokens) > 2 and _fold(tokens[-2]) not in _PARTICLES:
            # Only strip a beat word if what followed it was already stripped
            # as a role word, i.e. the part no longer ends in a plausible name.
            if _looks_like_role_tail(tokens):
                tokens.pop()
                changed = True
    return " ".join(tokens)


def _looks_like_role_tail(tokens: list[str]) -> bool:
    """True when the remaining tail is a beat descriptor, not a surname."""
    return _fold(tokens[-1]) in _BEAT_WORDS


def _truncate_at_clause(part: str) -> str:
    """Cut a byline part before a trailing location/affiliation clause."""
    tokens = part.split()
    for index, token in enumerate(tokens):
        if index < 2:
            continue
        folded = _fold(token)
        # Lowercase in the original *and* a known clause starter. Capitalised
        # words are left alone so surnames like "In" or "Van" survive.
        if token[:1].islower() and folded in _CLAUSE_STARTERS and folded not in _PARTICLES:
            return " ".join(tokens[:index])
    return part


def parse_byline(byline: str | None) -> list[str]:
    """Person names asserted by a displayed byline string.

    ``"By Jane Doe and John Roe"`` -> ``["Jane Doe", "John Roe"]``.
    Organisation bylines, mononyms, and unparseable fragments yield nothing.
    Order is preserved and duplicates are collapsed on their canonical key.
    """
    text = clean_text(byline)
    if not text:
        return []
    text = _BYLINE_PREFIX_RE.sub("", text)
    names: list[str] = []
    seen: set[str] = set()
    for raw_part in _SEPARATOR_RE.split(text):
        part = raw_part.strip(" .·|-")
        if not part:
            continue
        part = _strip_trailing_role(_truncate_at_clause(part))
        key = name_key(part)
        if not key or key in seen:
            continue
        # A fragment made entirely of job-title words is a role, not a person:
        # "Jane Doe, Political Editor" asserts one author, not two.
        if all(token in _ROLE_WORDS or token in _BEAT_WORDS for token in key.split()):
            continue
        seen.add(key)
        names.append(_WS_RE.sub(" ", part).strip())
    return names

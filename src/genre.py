"""Deterministic opinion/commentary detection from publisher URL paths (#84).

Publishers segregate columns, editorials and op-eds under stable URL paths
(``/opinion/``, ``/commentisfree/``, ...). That path is strong *genre*
evidence: it says the piece is commentary, not that its claims are wrong. The
Daily's house rules keep news sections "factual and neutral" and give the
Opinion section licence to take a position (see ``PRODUCT.md``), so a
commentary piece must never be presented as ordinary reporting.

Detection here is pure string work on data Hermes already holds. It adds no
network call and no Gemini call, and it is deliberately conservative:

* Rules are per outlet. An unknown host is never classified, because a bare
  ``/opinion/`` path can mean a *court* opinion (``courtlistener.com/opinion/..``)
  and a bare ``/opinions/`` path usually does.
* Only whole path segments are compared. A slug such as
  ``opinion-poll-shows-lead`` or a section such as ``/news/opinion-polls/`` is
  straight news and does not match.

To cover another outlet, add one entry to the rule tables below.
"""

from __future__ import annotations

from urllib.parse import urlsplit

#: Value stored in a story's ``content_genre`` when opinion evidence exists.
OPINION = "opinion"

#: Tag shown on the card when an opinion piece lands outside the Opinion desk.
OPINION_TAG = "OPINION"

# Existing house labels that already say "this is commentary". An opinion piece
# that the editor model already tagged this way is left exactly as it is.
_OPINION_TAGS = frozenset({"OPINION", "EDITORIAL", "COMMENTARY", "COLUMN", "OP-ED"})


def _is_all_digits(segment: str, length: int) -> bool:
    return len(segment) == length and segment.isdigit()


# host (without "www.") -> first-path-segment names that mean commentary.
# A host also matches its subdomains (``www.``, ``m.``, ``amp.`` ...).
_FIRST_SEGMENT_RULES: dict[str, frozenset[str]] = {
    "thestar.com": frozenset({"opinion"}),
    "theglobeandmail.com": frozenset({"opinion"}),
    "nationalpost.com": frozenset({"opinion"}),
    "financialpost.com": frozenset({"opinion"}),
    "torontosun.com": frozenset({"opinion"}),
    "macleans.ca": frozenset({"opinion"}),
    "ctvnews.ca": frozenset({"opinion"}),
    "theguardian.com": frozenset({"commentisfree"}),
    "wsj.com": frozenset({"opinion"}),
    "bloomberg.com": frozenset({"opinion"}),
    "reuters.com": frozenset({"opinion", "breakingviews"}),
    "telegraph.co.uk": frozenset({"opinion"}),
    "independent.co.uk": frozenset({"voices"}),
    "washingtonpost.com": frozenset({"opinions"}),
    "nytimes.com": frozenset({"opinion"}),
    "economist.com": frozenset({"leaders", "by-invitation"}),
}

# host -> (segment-path prefix) that mean commentary when the path starts with
# exactly these segments. CBC files its commentary under /news/opinion/.
_PREFIX_RULES: dict[str, tuple[tuple[str, ...], ...]] = {
    "cbc.ca": (("news", "opinion"),),
}

# Hosts whose article URLs lead with a /YYYY/MM/DD/ date before the section.
_DATED_SECTION_HOSTS: dict[str, frozenset[str]] = {
    "nytimes.com": frozenset({"opinion"}),
}

# Raw feed categories that are themselves commentary evidence, per provider.
# Guardian ``sectionId`` and NYT Top Stories ``section``.
_CATEGORY_RULES: dict[str, frozenset[str]] = {
    "guardian": frozenset({"commentisfree"}),
    "nyt": frozenset({"opinion"}),
}


def _host_and_segments(url: str | None) -> tuple[str, list[str]]:
    if not url:
        return "", []
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return "", []
    host = (parts.hostname or "").lower()
    segments = [s.lower() for s in parts.path.split("/") if s]
    return host, segments


def _matching_host(host: str, table) -> str | None:
    """The registered domain that ``host`` is, or is a subdomain of."""
    for domain in table:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def _dated_section(segments: list[str]) -> str | None:
    """Section segment of a ``/[interactive/]YYYY/MM/DD/<section>/...`` path."""
    rest = segments[1:] if segments and segments[0] == "interactive" else segments
    if len(rest) >= 4 and _is_all_digits(rest[0], 4) and _is_all_digits(rest[1], 2) and _is_all_digits(rest[2], 2):
        return rest[3]
    return None


def opinion_signal(url: str | None, *, provider: str = "", category: str | None = None) -> str:
    """Return a short evidence label when the item is opinion, else ``""``.

    ``url`` is the article's publisher link. ``provider``/``category`` carry the
    provider's own section name (Guardian ``sectionId``, NYT ``section``) when
    the raw item has one; it is corroborating feed-category evidence, checked
    alongside the path.
    """
    wanted = _CATEGORY_RULES.get((provider or "").lower())
    if wanted and (category or "").strip().lower() in wanted:
        return f"category:{provider}:{(category or '').strip().lower()}"

    host, segments = _host_and_segments(url)
    if not host or not segments:
        return ""

    domain = _matching_host(host, _FIRST_SEGMENT_RULES)
    if domain and segments[0] in _FIRST_SEGMENT_RULES[domain]:
        return f"path:{domain}/{segments[0]}"

    domain = _matching_host(host, _PREFIX_RULES)
    if domain:
        for prefix in _PREFIX_RULES[domain]:
            if tuple(segments[: len(prefix)]) == prefix:
                return f"path:{domain}/{'/'.join(prefix)}"

    domain = _matching_host(host, _DATED_SECTION_HOSTS)
    if domain:
        section = _dated_section(segments)
        if section and section in _DATED_SECTION_HOSTS[domain]:
            return f"path:{domain}/{section}"

    return ""


def is_opinion_link(url: str | None) -> bool:
    return bool(opinion_signal(url))


def tag_opinion_in_edition(edition: dict) -> int:
    """Make sure opinion-path stories outside the Opinion desk carry a tag.

    The curation model decides sections and may omit or mis-assign the tag, so
    this deterministic pass runs after curation and keys off the story's own
    publisher link. Stories in the Opinion section are already presented as
    commentary and are left alone, as is any story whose tag already marks it
    as commentary. Any other tag (for example ``DEVELOPING``) is replaced,
    because a news-style flag on a column would misstate its genre.

    The card template renders the tag chip in the kicker line even when a story
    has no kicker text.

    Returns the number of stories changed.
    """
    changed = 0
    for section in edition.get("sections", []):
        if section.get("id") == "opinion":
            continue
        for story in section.get("stories", []):
            if not is_opinion_link(story.get("link")):
                continue
            current = str(story.get("tag") or "").strip().upper()
            if current in _OPINION_TAGS:
                continue
            story["tag"] = OPINION_TAG
            changed += 1
    return changed

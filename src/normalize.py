"""Task 2 (part 2) - Normalize.

Convert source-native items from fetch.py into one unified story schema:

    {
      "title": str, "description": str, "source": str,
      "section_hint": str,   # world|business|sports|opinion|toronto
      "pub_date": str,       # ISO-ish
      "image": str | None,
      "link": str,

      # authorship and provenance (added for Voices, see VOICES.md)
      "provider": str,               # guardian|nyt|perigon|rss
      "source_article_id": str,      # provider-native article id, when any
      "canonical_url": str,          # tracking-free comparable URL
      "byline": str,                 # the displayed byline, verbatim
      "authors": [{"name": str, "source_author_id": str, ...}],
      "paywalled": bool | None,
    }

The seven original keys are unchanged, so existing curation and rendering keep
working untouched. The added keys exist because the pipeline used to throw
authorship away: the Guardian byline was requested and then dropped, NYT and
Perigon bylines were never read, and nothing recorded which provider an item
came from. Followed-Voice resolution needs all of it, and it is the kind of
metadata a newspaper should not be discarding anyway.

Only *stated authorship* is carried. Provider fields listing people a story is
merely about (NYT ``per_facet``, Perigon ``people``) are deliberately ignored:
being written about is not a byline.

Descriptions are stripped of HTML. Items missing a title or link are dropped.
"""

from __future__ import annotations

import re
from html import unescape

from .voices.names import parse_byline
from .voices.urls import canonical_url

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _authors_from_byline(byline: str) -> list[dict]:
    """Name-only author records parsed out of a displayed byline."""
    return [{"name": name} for name in parse_byline(byline)]


def _normalize_guardian(item: dict) -> dict:
    fields = item.get("fields", {}) or {}
    byline = _clean(fields.get("byline"))

    # Contributor tags are the Guardian's stable per-writer identity. They are
    # far better than the byline string for attribution, and requesting them
    # costs no extra call.
    authors: list[dict] = []
    for tag in item.get("tags") or []:
        if not isinstance(tag, dict) or tag.get("type") != "contributor":
            continue
        name = _clean(tag.get("webTitle")) or " ".join(
            part for part in (tag.get("firstName"), tag.get("lastName")) if part
        )
        tag_id = str(tag.get("id") or "").strip()
        if not name and not tag_id:
            continue
        authors.append({
            "name": name,
            "source_author_id": tag_id,
            "source_author_provider": "guardian",
        })
    if not authors:
        authors = _authors_from_byline(byline)

    link = item.get("webUrl", "")
    return {
        "title": _clean(item.get("webTitle")),
        "description": _clean(fields.get("trailText")),
        "source": "The Guardian",
        "section_hint": item.get("_section_hint", "world"),
        "pub_date": item.get("webPublicationDate", ""),
        "image": fields.get("thumbnail") or None,
        "link": link,
        "provider": "guardian",
        "source_article_id": str(item.get("id") or ""),
        "canonical_url": canonical_url(link),
        "byline": byline,
        "authors": authors,
        "paywalled": False,
    }


def _normalize_nyt(item: dict) -> dict:
    image = None
    multimedia = item.get("multimedia")
    if isinstance(multimedia, list) and multimedia:
        # Prefer a mid-size asset; fall back to the first with a url.
        for m in multimedia:
            if isinstance(m, dict) and m.get("url"):
                image = m["url"]
                break
    elif isinstance(multimedia, dict):
        image = multimedia.get("url")

    # The Top Stories API states authorship only as a displayed byline
    # ("By Jane Doe and John Roe"); there is no stable author id to keep. The
    # Article Search API wraps the same string in an object, so both shapes are
    # accepted rather than assuming one.
    raw_byline = item.get("byline")
    if isinstance(raw_byline, dict):
        raw_byline = raw_byline.get("original") or raw_byline.get("name") or ""
    byline = _clean(raw_byline if isinstance(raw_byline, str) else "")
    link = item.get("url", "")
    return {
        "title": _clean(item.get("title")),
        "description": _clean(item.get("abstract")),
        "source": "The New York Times",
        "section_hint": item.get("_section_hint", "world"),
        "pub_date": item.get("published_date", ""),
        "image": image,
        "link": link,
        "provider": "nyt",
        "source_article_id": str(item.get("uri") or ""),
        "canonical_url": canonical_url(link),
        "byline": byline,
        "authors": _authors_from_byline(byline),
        "paywalled": None,
    }


def _normalize_perigon(item: dict) -> dict:
    source = item.get("source") or {}
    # Perigon's article source object carries a domain (e.g. "ft.com"); prefer a
    # friendly name when present, otherwise show the domain without "www.".
    name = source.get("name") or source.get("domain") or "Perigon"
    if name.startswith("www."):
        name = name[4:]

    byline = _clean(item.get("authorsByline"))
    authors: list[dict] = []
    seen: set[str] = set()
    for entry in (item.get("matchedAuthors") or []) + (item.get("journalists") or []):
        if not isinstance(entry, dict):
            continue
        journalist_id = str(entry.get("id") or "").strip()
        author_name = _clean(entry.get("name") or entry.get("fullName") or "")
        marker = journalist_id or author_name.casefold()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        authors.append({
            "name": author_name,
            "source_author_id": journalist_id,
            "source_author_provider": "perigon",
        })
    if not authors:
        authors = _authors_from_byline(byline)

    link = item.get("url", "")
    paywall = source.get("paywall")
    return {
        "title": _clean(item.get("title")),
        "description": _clean(item.get("description") or item.get("summary")),
        "source": name,
        "section_hint": item.get("_section_hint", "world"),
        "pub_date": item.get("pubDate", "") or item.get("addDate", ""),
        "image": item.get("imageUrl") or None,
        "link": link,
        "provider": "perigon",
        "source_article_id": str(item.get("articleId") or ""),
        "canonical_url": canonical_url(link),
        "byline": byline,
        "authors": authors,
        "paywalled": bool(paywall) if paywall is not None else None,
    }


def _normalize_rss(item: dict) -> dict:
    image = None
    # feedparser exposes media:thumbnail / media:content variously.
    thumbs = item.get("media_thumbnail") or item.get("media_content")
    if isinstance(thumbs, list) and thumbs:
        image = thumbs[0].get("url")
    # Some feeds put an image in an enclosure link.
    if not image:
        for link in item.get("links", []) or []:
            if isinstance(link, dict) and link.get("type", "").startswith("image"):
                image = link.get("href")
                break
    description = item.get("summary") or item.get("description")

    # feedparser folds dc:creator, RSS <author> and Atom <author><name> here.
    byline = _clean(item.get("author") or item.get("dc_creator") or "")
    authors = _authors_from_byline(byline)
    if not authors:
        for candidate in item.get("authors") or []:
            if isinstance(candidate, dict):
                authors.extend(_authors_from_byline(_clean(candidate.get("name", ""))))

    link = item.get("link", "")
    guid = str(item.get("id") or "")
    return {
        "title": _clean(item.get("title")),
        "description": _clean(description),
        "source": item.get("_source_name", "Toronto RSS"),
        "section_hint": item.get("_section_hint", "toronto"),
        "pub_date": item.get("published", "") or item.get("updated", ""),
        "image": image or None,
        "link": link,
        "provider": "rss",
        # A feed guid identifies an item only inside its own feed. It is kept
        # for provenance but is only treated as an article id when it is a
        # real URL, which is comparable across sources.
        "source_article_id": guid if canonical_url(guid) else "",
        "canonical_url": canonical_url(link),
        "byline": byline,
        "authors": authors,
        "paywalled": None,
    }


_DISPATCH = {
    "guardian": _normalize_guardian,
    "nyt": _normalize_nyt,
    "perigon": _normalize_perigon,
    "rss": _normalize_rss,
}

#: The seven keys the curation model has always received. Kept explicit so the
#: added authorship fields cannot silently change the prompt or its cost.
CURATION_KEYS = (
    "title", "description", "source", "section_hint", "pub_date", "image", "link",
)


def curation_view(stories: list[dict]) -> list[dict]:
    """Project stories down to the fields the editor model is given.

    Authorship and provenance are for Hermes, not for the prompt: sending them
    would enlarge every curate call for no editorial benefit and would change
    a contract that currently works.
    """
    return [{key: story.get(key) for key in CURATION_KEYS} for story in stories]


def normalize(raw_items: list[dict]) -> list[dict]:
    """Unify a mixed list of source-native items; drop items missing title/link."""
    out: list[dict] = []
    for item in raw_items:
        fn = _DISPATCH.get(item.get("_src"))
        if fn is None:
            continue
        story = fn(item)
        if story["title"] and story["link"]:
            out.append(story)
    return out

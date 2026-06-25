"""Task 2 (part 2) - Normalize.

Convert source-native items from fetch.py into one unified story schema:

    {
      "title": str, "description": str, "source": str,
      "section_hint": str,   # world|business|sports|opinion|toronto
      "pub_date": str,       # ISO-ish
      "image": str | None,
      "link": str
    }

Descriptions are stripped of HTML. Items missing a title or link are dropped.
"""

from __future__ import annotations

import re
from html import unescape

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _normalize_guardian(item: dict) -> dict:
    fields = item.get("fields", {}) or {}
    return {
        "title": _clean(item.get("webTitle")),
        "description": _clean(fields.get("trailText")),
        "source": "The Guardian",
        "section_hint": item.get("_section_hint", "world"),
        "pub_date": item.get("webPublicationDate", ""),
        "image": fields.get("thumbnail") or None,
        "link": item.get("webUrl", ""),
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
    return {
        "title": _clean(item.get("title")),
        "description": _clean(item.get("abstract")),
        "source": "The New York Times",
        "section_hint": item.get("_section_hint", "world"),
        "pub_date": item.get("published_date", ""),
        "image": image,
        "link": item.get("url", ""),
    }


def _normalize_perigon(item: dict) -> dict:
    source = item.get("source") or {}
    # Perigon's article source object carries a domain (e.g. "ft.com"); prefer a
    # friendly name when present, otherwise show the domain without "www.".
    name = source.get("name") or source.get("domain") or "Perigon"
    if name.startswith("www."):
        name = name[4:]
    return {
        "title": _clean(item.get("title")),
        "description": _clean(item.get("description") or item.get("summary")),
        "source": name,
        "section_hint": item.get("_section_hint", "world"),
        "pub_date": item.get("pubDate", "") or item.get("addDate", ""),
        "image": item.get("imageUrl") or None,
        "link": item.get("url", ""),
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
    return {
        "title": _clean(item.get("title")),
        "description": _clean(description),
        "source": item.get("_source_name", "Toronto RSS"),
        "section_hint": item.get("_section_hint", "toronto"),
        "pub_date": item.get("published", "") or item.get("updated", ""),
        "image": image or None,
        "link": item.get("link", ""),
    }


_DISPATCH = {
    "guardian": _normalize_guardian,
    "nyt": _normalize_nyt,
    "perigon": _normalize_perigon,
    "rss": _normalize_rss,
}


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

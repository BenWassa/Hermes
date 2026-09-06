"""Deterministic integration between followed Voices and the Opinion desk."""

from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .voices.model import VoiceArticle
from .voices.names import clean_text
from .voices.registry import Registry
from .voices.timeparse import parse_timestamp, to_iso
from .voices.urls import url_key

_TORONTO = ZoneInfo("America/Toronto")
_BY_PREFIX = re.compile(r"^\s*by\s+", re.IGNORECASE)


def _publication(article: VoiceArticle) -> str:
    publication = clean_text(article.publication)
    if publication:
        return publication
    link = article.canonical_url or article.url
    try:
        return (urlsplit(link).hostname or "").removeprefix("www.")
    except ValueError:
        return ""


def _author_line(article: VoiceArticle, registry: Registry) -> str:
    names: list[str] = []
    seen: set[str] = set()
    for author in article.authors:
        name = clean_text(author.name)
        marker = name.casefold()
        if name and marker not in seen:
            seen.add(marker)
            names.append(name)
    if names:
        return ", ".join(names)

    byline = clean_text(article.byline)
    if byline:
        return _BY_PREFIX.sub("", byline).strip()

    for voice_id in article.voice_ids:
        voice = registry.get(voice_id)
        if voice and voice.name.casefold() not in seen:
            seen.add(voice.name.casefold())
            names.append(voice.name)
    return ", ".join(names)


def following_seed(article: VoiceArticle, registry: Registry) -> dict:
    # `VoiceArticle.url` is the display link selected by the #10 canonicalizer;
    # `canonical_url` is the normalized comparison form. Preserve the former
    # for the reader rather than rewriting a publisher destination just because
    # Hermes can compare it more conveniently in the identity layer.
    link = article.url or article.canonical_url
    return {
        "key": article.key,
        "identity_keys": sorted(article.identity_keys),
        "headline": clean_text(article.title),
        "description": clean_text(article.description),
        "author": _author_line(article, registry),
        "publication": _publication(article),
        "published_at": to_iso(article.published_at),
        "image": article.image,
        "link": link,
        "paywalled": article.paywalled,
        "voice_ids": list(article.voice_ids),
    }


def following_seeds(articles: list[VoiceArticle], registry: Registry) -> list[dict]:
    return [following_seed(article, registry) for article in articles]


def curation_following_view(seeds: list[dict]) -> list[dict]:
    return [
        {
            "key": seed["key"],
            "headline": seed["headline"],
            "description": seed.get("description") or "",
            "author": seed.get("author") or "",
            "publication": seed.get("publication") or "",
            "published_at": seed.get("published_at"),
            "link": seed.get("link") or "",
        }
        for seed in seeds
    ]


def _following_keys(seeds: list[dict]) -> set[str]:
    keys: set[str] = set()
    for seed in seeds:
        keys.update(k for k in seed.get("identity_keys", []) if k)
        key = url_key(seed.get("link") or "")
        if key:
            keys.add(key)
    return keys


def editorial_without_following(stories: list[dict], seeds: list[dict]) -> list[dict]:
    followed_keys = _following_keys(seeds)
    if not followed_keys:
        return list(stories)

    out: list[dict] = []
    for story in stories:
        if story.get("section_hint") != "opinion":
            out.append(story)
            continue
        story_key = url_key(story.get("canonical_url") or story.get("link") or "")
        if story_key and story_key in followed_keys:
            continue
        out.append(story)
    return out


def _format_time(value: str | None, today: dt.date) -> str:
    published = parse_timestamp(value)
    if published is None:
        return ""
    local = published.astimezone(_TORONTO)
    if local.date() == today:
        return local.strftime("%-I:%M %p")
    if local.date() == today - dt.timedelta(days=1):
        return "Yesterday"
    return local.strftime("%b %-d")


def _fallback_summary(seed: dict) -> str:
    description = clean_text(seed.get("description"))
    if description:
        return description
    author = seed.get("author") or "a followed writer"
    publication = seed.get("publication")
    where = f" at {publication}" if publication else ""
    return f"New writing from {author}{where}. Open the original piece for the full argument."


def build_following_cards(
    seeds: list[dict], model_items: list[dict] | None, *, today: dt.date
) -> list[dict]:
    by_key: dict[str, dict] = {}
    for item in model_items or []:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            by_key.setdefault(item["key"], item)

    cards: list[dict] = []
    for index, seed in enumerate(seeds, start=1):
        model = by_key.get(seed["key"], {})
        sensitivity = bool(model.get("sensitivity", False))
        cards.append(
            {
                "id": f"follow-{index}",
                "lead": False,
                "kicker": None,
                "headline": seed.get("headline") or "Untitled opinion",
                "sub": clean_text(model.get("sub")) or None,
                "summary": clean_text(model.get("summary")) or _fallback_summary(seed),
                "analysis": None,
                "time": _format_time(seed.get("published_at"), today),
                "tag": None,
                "sensitivity": sensitivity,
                "image": None if sensitivity else seed.get("image"),
                "link": seed.get("link") or "",
                "author": seed.get("author") or "",
                "publication": seed.get("publication") or "",
                "paywalled": seed.get("paywalled"),
                "voice_ids": list(seed.get("voice_ids") or []),
                "canonical_key": seed.get("key") or "",
                "following": True,
            }
        )
    return cards


def suppress_opinion_duplicates(edition: dict, seeds: list[dict]) -> int:
    followed_keys = _following_keys(seeds)
    if not followed_keys:
        return 0

    removed = 0
    for section in edition.get("sections", []):
        if section.get("id") != "opinion":
            continue
        kept: list[dict] = []
        for story in section.get("stories", []):
            key = url_key(story.get("link") or "")
            if key and key in followed_keys:
                removed += 1
                continue
            kept.append(story)
        section["stories"] = kept
        if kept and not any(story.get("lead") for story in kept):
            kept[0]["lead"] = True
        break
    return removed

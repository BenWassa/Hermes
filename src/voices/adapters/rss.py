"""RSS / Atom adapter.

The cheapest and most testable discovery tier, and the right default for a
personal site or a newsletter. One GET per distinct feed URL, no key, no
quota, explicit timestamps, and usually real author metadata.

The trap this adapter exists to avoid: *a feed URL is not an identity*. A
publication feed such as a multi-author Substack carries several writers, so
the registry decides per source whether every entry belongs to the Voice
(``authorship: scope``) or whether the entry's own author metadata has to say
so (``authorship: byline``). This adapter simply reports what each entry
claims; ``resolve`` applies the rule.
"""

from __future__ import annotations

import datetime as dt

import feedparser

from ..model import Author, Observation
from ..names import clean_text, parse_byline
from ..timeparse import parse_timestamp
from ..urls import canonical_url, url_host
from .base import AdapterError, FetchWindow, SourceRequest, VoiceSourceAdapter


def _entry_authors(entry) -> tuple[str, tuple[Author, ...]]:
    """Displayed byline and structured authors for one feed entry.

    feedparser folds ``dc:creator``, RSS ``<author>`` and Atom
    ``<author><name>`` into ``author``/``authors``, so all three are covered.
    Feeds have no stable author identifiers, so every author here is
    name-only: attribution from a feed is always byline or scope evidence,
    never provider-id evidence.
    """
    names: list[str] = []
    for candidate in entry.get("authors") or []:
        if isinstance(candidate, dict):
            name = clean_text(candidate.get("name") or candidate.get("email") or "")
            if name:
                names.append(name)
    raw_byline = clean_text(entry.get("author") or entry.get("dc_creator") or "")
    if raw_byline and not names:
        names = parse_byline(raw_byline)
    elif raw_byline and len(names) == 1 and len(parse_byline(raw_byline)) > 1:
        # A single <author> element that actually lists coauthors.
        names = parse_byline(raw_byline)

    parsed: list[str] = []
    for name in names:
        parsed.extend(parse_byline(name) or [])
    seen: set[str] = set()
    authors: list[Author] = []
    for name in parsed:
        if name.casefold() in seen:
            continue
        seen.add(name.casefold())
        authors.append(Author(name=name))
    byline = raw_byline or ", ".join(a.name for a in authors)
    return byline, tuple(authors)


def _entry_image(entry) -> str | None:
    thumbs = entry.get("media_thumbnail") or entry.get("media_content")
    if isinstance(thumbs, list) and thumbs:
        url = thumbs[0].get("url")
        if url:
            return url
    for link in entry.get("links", []) or []:
        if isinstance(link, dict) and str(link.get("type", "")).startswith("image"):
            return link.get("href")
    return None


class RssAdapter(VoiceSourceAdapter):
    type = "rss"
    provider = "rss"
    required_params = ("url",)

    def source_key(self, source) -> str:
        return f"rss:{canonical_url(source.params.get('url', '')) or source.params.get('url', '')}"

    def plan(self, sources: list, window: FetchWindow) -> list[SourceRequest]:
        """One request per distinct feed URL, however many Voices share it."""
        by_key: dict[str, list] = {}
        for voice, source in sources:
            by_key.setdefault(source.key, []).append((voice, source))
        requests_out: list[SourceRequest] = []
        for key, group in sorted(by_key.items()):
            url = group[0][1].params["url"]
            requests_out.append(
                SourceRequest(
                    adapter=self.type,
                    label=group[0][1].params.get("name") or url,
                    source_keys=(key,),
                    payload={
                        "url": url,
                        "publication": group[0][1].params.get("publication", ""),
                        "max_items": int(group[0][1].params.get("max_items", 25)),
                    },
                )
            )
        return requests_out

    def fetch(self, request: SourceRequest, http, window: FetchWindow) -> list[Observation]:
        url = request.payload["url"]
        try:
            response = http.get(url, provider=self.provider)
            parsed = feedparser.parse(response.content)
        except Exception as exc:  # network, DNS, HTTP status
            raise AdapterError(f"rss feed {url} failed: {exc}") from exc

        if parsed.get("bozo") and not parsed.get("entries"):
            raise AdapterError(f"rss feed {url} did not parse: {parsed.get('bozo_exception')}")

        feed_title = clean_text((parsed.get("feed") or {}).get("title", ""))
        publication = request.payload.get("publication") or feed_title or url_host(url)
        now = dt.datetime.now(dt.timezone.utc)

        observations: list[Observation] = []
        for entry in (parsed.get("entries") or [])[: request.payload["max_items"]]:
            link = clean_text(entry.get("link"))
            title = clean_text(entry.get("title"))
            if not link or not title:
                continue
            byline, authors = _entry_authors(entry)
            published_raw = entry.get("published") or entry.get("updated") or ""
            published = parse_timestamp(entry.get("published_parsed") or entry.get("updated_parsed")) \
                or parse_timestamp(published_raw)
            guid = entry.get("id") or ""
            observations.append(
                Observation(
                    adapter=self.type,
                    source_key=request.source_keys[0],
                    provider=self.provider,
                    title=title,
                    url=link,
                    canonical_url=canonical_url(link),
                    description=clean_text(entry.get("summary") or entry.get("description")),
                    image=_entry_image(entry),
                    publication=publication,
                    published_at=published,
                    raw_published=str(published_raw),
                    byline=byline,
                    authors=authors,
                    # A feed guid is only an identity when it is a real URL;
                    # opaque per-publication guids are not comparable across
                    # adapters, so they are not used as provider ids.
                    provider_article_id=guid if canonical_url(guid) else "",
                    fetched_at=now,
                )
            )
        return observations

"""Structured author-archive adapter.

Some writers have a durable public author page at a publication or index that
offers neither a per-author feed nor an API. This adapter reads such a page,
and it is a *site-pattern* adapter, not a person adapter: the registry supplies
the archive URL and structural hints, so any writer on a supporting site can
use it and no code path mentions a person.

Two strategies, in order:

1. **JSON-LD.** ``schema.org`` ``ItemList`` / ``Article`` blocks on the page.
   Machine-readable, published by the site for exactly this purpose, and
   stable across visual redesigns.
2. **Declared structure.** Repeated item elements, each contributing its first
   titled link plus optional date/publication metadata. Only used when the
   source opts in with ``"structural": true``. ``item_class`` may further
   constrain the repeated item when a site uses ``<div>`` rather than
   ``<article>``.

Both fail *closed*. If the expected structure is not there, the adapter raises
``AdapterError`` and contributes nothing. It never falls back to scraping
article bodies: an author archive is a discovery surface for metadata and
canonical links, not something to mirror.

By default extracted article links must stay on the archive's own host, which
keeps publication author pages safe for ``scope`` attribution. An index that
intentionally links to external publishers may opt in with
``allow_external_links``. Such a source can additionally require an exact
``author_path`` inside every repeated item. When configured, that stable author
path is emitted as a source-native provider id so the normal resolver can use
``provider_id`` evidence rather than a name match.
"""

from __future__ import annotations

import datetime as dt
import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from ..model import Author, Observation
from ..names import clean_text
from ..timeparse import parse_timestamp
from ..urls import canonical_url, url_host
from .base import AdapterError, FetchWindow, SourceRequest, VoiceSourceAdapter

_ARTICLE_TYPES = {
    "article", "newsarticle", "opinionnewsarticle", "reportagenewsarticle",
    "analysisnewsarticle", "blogposting", "socialmediaposting", "report",
}


class _LdJsonCollector(HTMLParser):
    """Collects the raw text of every ``application/ld+json`` script block."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._capturing = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        attrs_map = {k.lower(): (v or "") for k, v in attrs}
        if attrs_map.get("type", "").strip().lower() == "application/ld+json":
            self._capturing = True
            self._buffer = []

    def handle_endtag(self, tag):
        if tag == "script" and self._capturing:
            self._capturing = False
            self.blocks.append("".join(self._buffer))

    def handle_data(self, data):
        if self._capturing:
            self._buffer.append(data)


class _ArticleBlockCollector(HTMLParser):
    """Collect metadata from repeated structural author-index items."""

    def __init__(self, item_tag: str = "article", item_class: str = "", author_path: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.item_tag = item_tag
        self.item_class = item_class.strip()
        self.author_path = author_path.strip()
        self.items: list[dict] = []
        self._item_depth = 0
        self._current: dict | None = None
        self._link_depth = 0
        self._link_text: list[str] = []
        self._pending_href = ""
        self._field_tag = ""
        self._field_name = ""
        self._field_text: list[str] = []

    def _matches_item(self, tag: str, attrs_map: dict[str, str]) -> bool:
        if tag != self.item_tag:
            return False
        if not self.item_class:
            return True
        return self.item_class in set(attrs_map.get("class", "").split())

    def handle_starttag(self, tag, attrs):
        attrs_map = {k.lower(): (v or "") for k, v in attrs}
        if self._current is None:
            if self._matches_item(tag, attrs_map):
                self._current = {
                    "href": "", "title": "", "datetime": "", "author_href": "",
                    "author_name": "", "publication": "", "description": "",
                }
                self._item_depth = 1
            return

        if tag == self.item_tag:
            self._item_depth += 1

        if tag == "a" and attrs_map.get("href") and self._link_depth == 0:
            self._pending_href = attrs_map["href"]
            self._link_depth = 1
            self._link_text = []
        elif tag == "time" and attrs_map.get("datetime") and not self._current["datetime"]:
            self._current["datetime"] = attrs_map["datetime"]

        classes = set(attrs_map.get("class", "").split())
        if not self._field_name:
            if "date" in classes and not self._current["datetime"]:
                self._field_tag, self._field_name, self._field_text = tag, "datetime", []
            elif "source" in classes and not self._current["publication"]:
                self._field_tag, self._field_name, self._field_text = tag, "publication", []
            elif "lead" in classes and not self._current["description"]:
                self._field_tag, self._field_name, self._field_text = tag, "description", []

    def handle_endtag(self, tag):
        if tag == "a" and self._link_depth and self._current is not None:
            self._link_depth = 0
            text = clean_text("".join(self._link_text))
            href = self._pending_href
            path = urlsplit(href).path
            if self.author_path and path == self.author_path:
                self._current["author_href"] = href
                self._current["author_name"] = text
            elif text and len(text) > 12 and not self._current["href"]:
                self._current["href"] = href
                self._current["title"] = text
            self._link_text = []
            self._pending_href = ""

        if self._field_name and tag == self._field_tag and self._current is not None:
            value = clean_text("".join(self._field_text))
            if self._field_name == "publication":
                value = value.lstrip("—- ")
            self._current[self._field_name] = value
            self._field_tag = self._field_name = ""
            self._field_text = []

        if tag == self.item_tag and self._current is not None:
            self._item_depth -= 1
            if self._item_depth == 0:
                self.items.append(self._current)
                self._current = None

    def handle_data(self, data):
        if self._link_depth:
            self._link_text.append(data)
        if self._field_name:
            self._field_text.append(data)


def _walk_jsonld(node, out: list[dict]) -> None:
    """Depth-first walk collecting article-shaped JSON-LD objects."""
    if isinstance(node, list):
        for child in node:
            _walk_jsonld(child, out)
        return
    if not isinstance(node, dict):
        return
    raw_type = node.get("@type") or node.get("type") or ""
    types = {str(t).strip().lower() for t in (raw_type if isinstance(raw_type, list) else [raw_type])}
    if types & _ARTICLE_TYPES:
        out.append(node)
    for key in ("@graph", "itemListElement", "item", "mainEntity", "hasPart", "blogPost"):
        if key in node:
            _walk_jsonld(node[key], out)


def _jsonld_items(html: str) -> list[dict]:
    collector = _LdJsonCollector()
    try:
        collector.feed(html)
    except Exception:
        return []
    found: list[dict] = []
    for block in collector.blocks:
        try:
            _walk_jsonld(json.loads(block), found)
        except (json.JSONDecodeError, ValueError):
            continue
    return found


def _jsonld_field(node: dict, *names: str) -> str:
    for name in names:
        value = node.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for inner in ("@id", "url", "name", "headline"):
                if isinstance(value.get(inner), str) and value[inner].strip():
                    return value[inner].strip()
    return ""


def _jsonld_byline(node: dict) -> str:
    author = node.get("author")
    names: list[str] = []
    for entry in author if isinstance(author, list) else [author]:
        if isinstance(entry, str) and entry.strip():
            names.append(entry.strip())
        elif isinstance(entry, dict) and isinstance(entry.get("name"), str):
            names.append(entry["name"].strip())
    return ", ".join(n for n in names if n)


class AuthorPageAdapter(VoiceSourceAdapter):
    type = "author_page"
    provider = "author_page"
    required_params = ("url",)

    def source_key(self, source) -> str:
        return f"author_page:{canonical_url(source.params.get('url', '')) or source.params.get('url', '')}"

    def plan(self, sources: list, window: FetchWindow) -> list[SourceRequest]:
        by_key: dict[str, list] = {}
        for voice, source in sources:
            by_key.setdefault(source.key, []).append((voice, source))
        requests_out: list[SourceRequest] = []
        for key, group in sorted(by_key.items()):
            source = group[0][1]
            requests_out.append(
                SourceRequest(
                    adapter=self.type,
                    label=source.params.get("publication") or source.params["url"],
                    source_keys=(key,),
                    payload={
                        "url": source.params["url"],
                        "publication": source.params.get("publication", ""),
                        "link_prefix": source.params.get("link_prefix", ""),
                        "structural": bool(source.params.get("structural", False)),
                        "item_tag": source.params.get("item_tag", "article"),
                        "item_class": source.params.get("item_class", ""),
                        "author_path": source.params.get("author_path", ""),
                        "allow_external_links": bool(source.params.get("allow_external_links", False)),
                        "max_items": int(source.params.get("max_items", 20)),
                        "paywalled": source.params.get("paywalled"),
                    },
                )
            )
        return requests_out

    def fetch(self, request: SourceRequest, http, window: FetchWindow) -> list[Observation]:
        url = request.payload["url"]
        try:
            response = http.get(url, provider=self.provider, headers={"Accept": "text/html"})
            html = response.text
        except Exception as exc:
            raise AdapterError(f"author page {url} failed: {exc}") from exc
        return self.parse(html, request, base_url=url)

    def parse(self, html: str, request: SourceRequest, *, base_url: str) -> list[Observation]:
        """Extract observations from author-archive markup. Fails closed."""
        payload = request.payload
        host = url_host(base_url)
        publication = payload.get("publication") or host
        prefix = payload.get("link_prefix") or ""
        author_path = str(payload.get("author_path") or "").strip()
        allow_external = bool(payload.get("allow_external_links"))
        now = dt.datetime.now(dt.timezone.utc)
        paywalled = payload.get("paywalled")

        raw_items: list[dict] = []
        for node in _jsonld_items(html):
            link = _jsonld_field(node, "url", "mainEntityOfPage", "@id")
            title = _jsonld_field(node, "headline", "name")
            if not link or not title:
                continue
            raw_items.append({
                "href": link,
                "title": title,
                "datetime": _jsonld_field(node, "datePublished", "dateCreated", "dateModified"),
                "byline": _jsonld_byline(node),
                "author_href": "",
                "author_name": "",
                "publication": "",
                "description": "",
                "strategy": "jsonld",
            })

        if not raw_items and payload.get("structural"):
            collector = _ArticleBlockCollector(
                item_tag=payload.get("item_tag", "article"),
                item_class=payload.get("item_class", ""),
                author_path=author_path,
            )
            try:
                collector.feed(html)
            except Exception as exc:
                raise AdapterError(f"author page {base_url} markup did not parse: {exc}") from exc
            for item in collector.items:
                if item["href"] and item["title"]:
                    raw_items.append({**item, "byline": item.get("author_name", ""), "strategy": "structural"})

        if not raw_items:
            raise AdapterError(
                f"author page {base_url} exposed no recognisable article structure "
                "(no JSON-LD articles; structural parsing disabled or empty)"
            )

        observations: list[Observation] = []
        seen: set[str] = set()
        for item in raw_items[: payload["max_items"] * 3]:
            link = urljoin(base_url, item["href"])
            canonical = canonical_url(link)
            if not canonical:
                continue
            if not allow_external and url_host(link) != host:
                continue
            if prefix and not urlsplit(canonical).path.startswith(prefix):
                continue
            if author_path:
                observed_author_path = urlsplit(item.get("author_href") or "").path
                if observed_author_path != author_path:
                    continue
            if canonical in seen:
                continue
            seen.add(canonical)
            published = parse_timestamp(item.get("datetime"))
            authors: tuple[Author, ...] = ()
            if author_path:
                authors = (Author(
                    name=clean_text(item.get("author_name", "")),
                    provider=host,
                    provider_id=author_path,
                ),)
            observations.append(
                Observation(
                    adapter=self.type,
                    source_key=request.source_keys[0],
                    provider=host,
                    title=clean_text(item["title"]),
                    url=link,
                    canonical_url=canonical,
                    publication=clean_text(item.get("publication") or "") or publication or url_host(link),
                    paywalled=paywalled,
                    published_at=published,
                    raw_published=str(item.get("datetime") or ""),
                    byline=clean_text(item.get("byline", "")),
                    authors=authors,
                    author_scoped=True,
                    fetched_at=now,
                )
            )
            if len(observations) >= payload["max_items"]:
                break
        if not observations:
            qualifier = "matching the configured author identity" if author_path else "usable"
            raise AdapterError(f"author page {base_url} yielded no {qualifier} article links")
        return observations

"""Perigon journalist adapter: the cross-publication coverage expander.

Perigon's value here is its journalist identity. A writer who moves between
outlets keeps one ``journalistId``, so one stable id covers publications
Hermes has no feed or first-party API for. Articles come back with
``authorsByline``, ``matchedAuthors`` and ``journalists``, which is exactly the
provider-id evidence the resolver wants.

Budget note: this is the scarcest provider Hermes uses. Perigon's personal
tier is measured in requests per month (150 at the time of writing), so this
adapter is a once-a-day reconciliation pass, never a poller. ``journalistId``
accepts repeated values and ORs them, so every Perigon-registered Voice is
covered by a single request per run. The per-run budget defaults to 1.
"""

from __future__ import annotations

import datetime as dt

from ..model import Author, Observation
from ..names import clean_text, parse_byline
from ..timeparse import parse_timestamp
from ..urls import canonical_url, url_host
from .base import AdapterError, FetchWindow, SourceRequest, VoiceSourceAdapter

PERIGON_URL = "https://api.perigon.io/v1/all"

#: journalistId values per request. Perigon ORs repeated values.
IDS_PER_REQUEST = 25


def perigon_authors(item: dict) -> tuple[str, tuple[Author, ...]]:
    """Byline and journalist-identity authors from one Perigon article."""
    byline = clean_text(item.get("authorsByline"))
    authors: list[Author] = []
    seen: set[str] = set()
    for entry in (item.get("matchedAuthors") or []) + (item.get("journalists") or []):
        if not isinstance(entry, dict):
            continue
        journalist_id = str(entry.get("id") or "").strip()
        name = clean_text(entry.get("name") or entry.get("fullName") or "")
        marker = journalist_id or name.casefold()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        authors.append(Author(name=name, provider="perigon", provider_id=journalist_id))
    if not authors:
        authors = [Author(name=name) for name in parse_byline(byline)]
    return byline, tuple(authors)


def observation_from_article(item: dict, *, source_key: str, adapter: str,
                             fetched_at: dt.datetime) -> Observation | None:
    """Build an Observation from one Perigon ``articles`` entry."""
    title = clean_text(item.get("title"))
    link = clean_text(item.get("url"))
    if not title or not link:
        return None
    source = item.get("source") or {}
    publication = clean_text(source.get("name") or source.get("domain") or "") or url_host(link)
    if publication.startswith("www."):
        publication = publication[4:]
    byline, authors = perigon_authors(item)
    paywall = source.get("paywall")
    raw_published = str(item.get("pubDate") or item.get("addDate") or "")
    return Observation(
        adapter=adapter,
        source_key=source_key,
        provider="perigon",
        title=title,
        url=link,
        canonical_url=canonical_url(link),
        description=clean_text(item.get("description") or item.get("summary")),
        image=item.get("imageUrl") or None,
        publication=publication,
        paywalled=bool(paywall) if paywall is not None else None,
        published_at=parse_timestamp(raw_published),
        raw_published=raw_published,
        byline=byline,
        authors=authors,
        provider_article_id=str(item.get("articleId") or ""),
        reprint=bool(item.get("reprint")),
        reprint_group_id=str(item.get("reprintGroupId") or ""),
        fetched_at=fetched_at,
    )


class PerigonJournalistAdapter(VoiceSourceAdapter):
    type = "perigon_journalist"
    provider = "perigon"
    required_params = ("journalist_id",)

    def source_key(self, source) -> str:
        return f"perigon_journalist:{str(source.params.get('journalist_id', '')).strip()}"

    def plan(self, sources: list, window: FetchWindow) -> list[SourceRequest]:
        by_id: dict[str, list[str]] = {}
        for _voice, source in sources:
            journalist_id = str(source.params["journalist_id"]).strip()
            by_id.setdefault(journalist_id, []).append(source.key)
        ids = sorted(by_id)
        requests_out: list[SourceRequest] = []
        for start in range(0, len(ids), IDS_PER_REQUEST):
            chunk = ids[start:start + IDS_PER_REQUEST]
            keys = tuple(sorted({key for jid in chunk for key in by_id[jid]}))
            requests_out.append(
                SourceRequest(
                    adapter=self.type,
                    label=f"perigon journalists {start // IDS_PER_REQUEST + 1}",
                    source_keys=keys,
                    payload={"journalist_ids": chunk},
                )
            )
        return requests_out

    def fetch(self, request: SourceRequest, http, window: FetchWindow) -> list[Observation]:
        import os

        key = os.environ.get("PERIGON_API_KEY")
        if not key:
            raise AdapterError("PERIGON_API_KEY not set")
        journalist_ids = request.payload["journalist_ids"]
        params = {
            "apiKey": key,
            "journalistId": journalist_ids,
            "from": window.since.strftime("%Y-%m-%dT%H:%M:%S"),
            "sortBy": "date",
            "language": "en",
            # Reprints are handled by Hermes' own syndication grouping, which
            # keeps the provenance; asking Perigon to hide them would lose it.
            "showReprints": "true",
            "size": min(100, max(10, 10 * len(journalist_ids))),
        }
        try:
            response = http.get(PERIGON_URL, provider=self.provider, params=params)
            articles = response.json().get("articles") or []
        except Exception as exc:
            raise AdapterError(f"perigon journalist query failed: {exc}") from exc

        now = dt.datetime.now(dt.timezone.utc)
        wanted = {jid.strip() for jid in journalist_ids}
        observations: list[Observation] = []
        for item in articles:
            observation = observation_from_article(
                item, source_key="", adapter=self.type, fetched_at=now
            )
            if observation is None:
                continue
            matched = [a.provider_id for a in observation.authors if a.provider_id in wanted]
            if not matched:
                continue
            observation.source_key = f"perigon_journalist:{matched[0]}"
            observations.append(observation)
        return observations

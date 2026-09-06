"""Guardian contributor adapter.

The Guardian is the best-behaved first-party source Hermes has for Voices: it
publishes a stable contributor tag per writer (``profile/georgemonbiot``), the
Content API filters on it, and ``show-tags=contributor`` returns those tags on
every result. That gives provider-id attribution rather than name matching.

Budget note: the Guardian tag filter treats ``|`` as OR, so *every* registered
Guardian contributor is covered by one request, not one request per person.
Tags are chunked only to keep the query string sane. Non-commercial developer
access is documented at 500 calls/day and 1 call/second, so a handful of daily
requests is comfortably inside it.
"""

from __future__ import annotations

import datetime as dt

from ..model import Author, Observation
from ..names import clean_text
from ..timeparse import parse_timestamp
from ..urls import canonical_url
from .base import AdapterError, FetchWindow, SourceRequest, VoiceSourceAdapter

GUARDIAN_URL = "https://content.guardianapis.com/search"

#: Contributor tags per request. The API ORs them; this only bounds URL length.
TAGS_PER_REQUEST = 12


def guardian_authors(item: dict) -> tuple[str, tuple[Author, ...]]:
    """Byline and contributor-tag authors from one Guardian result."""
    fields = item.get("fields") or {}
    byline = clean_text(fields.get("byline"))
    authors: list[Author] = []
    for tag in item.get("tags") or []:
        if not isinstance(tag, dict) or tag.get("type") != "contributor":
            continue
        tag_id = str(tag.get("id") or "").strip()
        name = clean_text(tag.get("webTitle")) or " ".join(
            part for part in (tag.get("firstName"), tag.get("lastName")) if part
        )
        if not tag_id and not name:
            continue
        authors.append(Author(name=name, provider="guardian", provider_id=tag_id))
    return byline, tuple(authors)


def observation_from_result(item: dict, *, source_key: str, adapter: str,
                            fetched_at: dt.datetime) -> Observation | None:
    """Build an Observation from one Guardian ``results`` entry."""
    title = clean_text(item.get("webTitle"))
    link = clean_text(item.get("webUrl"))
    if not title or not link:
        return None
    fields = item.get("fields") or {}
    byline, authors = guardian_authors(item)
    raw_published = str(item.get("webPublicationDate") or "")
    return Observation(
        adapter=adapter,
        source_key=source_key,
        provider="guardian",
        title=title,
        url=link,
        canonical_url=canonical_url(link),
        description=clean_text(fields.get("trailText")),
        image=fields.get("thumbnail") or None,
        publication="The Guardian",
        published_at=parse_timestamp(raw_published),
        raw_published=raw_published,
        byline=byline,
        authors=authors,
        provider_article_id=str(item.get("id") or ""),
        fetched_at=fetched_at,
    )


class GuardianContributorAdapter(VoiceSourceAdapter):
    type = "guardian_contributor"
    provider = "guardian"
    required_params = ("tag",)

    def source_key(self, source) -> str:
        return f"guardian_contributor:{str(source.params.get('tag', '')).strip().lower()}"

    def plan(self, sources: list, window: FetchWindow) -> list[SourceRequest]:
        by_tag: dict[str, list[str]] = {}
        for _voice, source in sources:
            tag = str(source.params["tag"]).strip()
            by_tag.setdefault(tag, []).append(source.key)
        tags = sorted(by_tag)
        requests_out: list[SourceRequest] = []
        for start in range(0, len(tags), TAGS_PER_REQUEST):
            chunk = tags[start:start + TAGS_PER_REQUEST]
            keys = tuple(sorted({key for tag in chunk for key in by_tag[tag]}))
            requests_out.append(
                SourceRequest(
                    adapter=self.type,
                    label=f"guardian contributors {start // TAGS_PER_REQUEST + 1}",
                    source_keys=keys,
                    payload={"tags": chunk},
                )
            )
        return requests_out

    def fetch(self, request: SourceRequest, http, window: FetchWindow) -> list[Observation]:
        import os

        key = os.environ.get("GUARDIAN_API_KEY")
        if not key:
            raise AdapterError("GUARDIAN_API_KEY not set")
        tags = request.payload["tags"]
        params = {
            "tag": "|".join(tags),
            "show-fields": "thumbnail,trailText,byline",
            "show-tags": "contributor",
            "order-by": "newest",
            "from-date": window.since.date().isoformat(),
            "page-size": min(50, max(10, 10 * len(tags))),
            "api-key": key,
        }
        try:
            response = http.get(GUARDIAN_URL, provider=self.provider, params=params)
            results = (response.json().get("response") or {}).get("results") or []
        except Exception as exc:
            raise AdapterError(f"guardian contributor query failed: {exc}") from exc

        now = dt.datetime.now(dt.timezone.utc)
        wanted = {tag.lower() for tag in tags}
        observations: list[Observation] = []
        for item in results:
            observation = observation_from_result(
                item, source_key="", adapter=self.type, fetched_at=now
            )
            if observation is None:
                continue
            # Attach the observation to the specific contributor source that
            # asked for it, so scoping and diagnostics stay per-source even
            # though the request was batched.
            matched = [
                a.provider_id for a in observation.authors
                if a.provider_id and a.provider_id.lower() in wanted
            ]
            if not matched:
                # The OR query should not return this; drop it rather than
                # attach it to an arbitrary source.
                continue
            observation.source_key = f"guardian_contributor:{matched[0].lower()}"
            observations.append(observation)
        return observations

"""Core Voice data model.

Three record types flow through the foundation:

``Observation``
    One sighting of one article through one adapter. Adapters produce these
    and nothing else; they know nothing about Voices. An observation keeps the
    source-native evidence verbatim so a later attribution can be explained.

``Attribution``
    The claim "this observation shows work by this Voice", together with the
    evidence class and the exact detail that satisfied it.

``VoiceArticle``
    One canonical article: the merge of every observation that resolved to the
    same piece, plus the union of its attributions.

Everything is plain data with an ``as_dict`` so build diagnostics, fixtures,
and later slices can serialise it without importing behaviour.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, replace

from .timeparse import to_iso

# Evidence classes, strongest first. The order is load-bearing: it decides
# which attribution is reported as primary and is asserted in tests.
EVIDENCE_PROVIDER_ID = "provider_author_id"
EVIDENCE_SOURCE_SCOPE = "source_scope"
EVIDENCE_BYLINE_ALIAS = "byline_alias"

EVIDENCE_ORDER = (EVIDENCE_PROVIDER_ID, EVIDENCE_SOURCE_SCOPE, EVIDENCE_BYLINE_ALIAS)


def evidence_rank(evidence: str) -> int:
    try:
        return EVIDENCE_ORDER.index(evidence)
    except ValueError:
        return len(EVIDENCE_ORDER)


@dataclass(frozen=True)
class Author:
    """One author as the source stated them.

    ``provider_id`` is the source-native contributor/journalist identifier
    when the provider has one (Guardian contributor tag, Perigon journalist
    id). It is the only author field strong enough to attribute on by itself.
    """

    name: str = ""
    provider: str = ""
    provider_id: str = ""

    def as_dict(self) -> dict:
        out: dict = {"name": self.name}
        if self.provider_id:
            out["source_author_id"] = self.provider_id
            out["source_author_provider"] = self.provider
        return out


@dataclass
class Observation:
    """One article as seen through one adapter."""

    # Where it came from.
    adapter: str                      # "rss" | "guardian_contributor" | ...
    source_key: str                   # dedupe/scoping key for the source
    provider: str = ""                # "guardian" | "nyt" | "perigon" | host
    source_id: str = ""               # registry source id, or "" for the pool

    # What was seen.
    title: str = ""
    url: str = ""
    canonical_url: str = ""
    description: str = ""
    image: str | None = None
    publication: str = ""             # display name of the publishing outlet
    published_at: dt.datetime | None = None
    raw_published: str = ""
    # Whether the publisher gates this piece. Recorded so Following can say so
    # and so nothing downstream mistakes "no description" for "no article".
    paywalled: bool | None = None

    # Authorship evidence, verbatim from the source.
    byline: str = ""
    authors: tuple[Author, ...] = ()
    author_scoped: bool = False       # every item from this source is one Voice

    # Provider-native identity and syndication hints.
    provider_article_id: str = ""
    reprint: bool = False
    reprint_group_id: str = ""

    fetched_at: dt.datetime | None = None

    def as_dict(self) -> dict:
        return {
            "adapter": self.adapter,
            "source_key": self.source_key,
            "source_id": self.source_id,
            "provider": self.provider,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "publication": self.publication,
            "paywalled": self.paywalled,
            "published_at": to_iso(self.published_at),
            "raw_published": self.raw_published,
            "byline": self.byline,
            "authors": [a.as_dict() for a in self.authors],
            "author_scoped": self.author_scoped,
            "provider_article_id": self.provider_article_id,
            "reprint": self.reprint,
            "reprint_group_id": self.reprint_group_id,
            "fetched_at": to_iso(self.fetched_at),
        }


@dataclass(frozen=True)
class Attribution:
    """Why Hermes believes an observation is work by a Voice."""

    voice_id: str
    evidence: str
    detail: str
    source_key: str = ""
    adapter: str = ""

    def as_dict(self) -> dict:
        return {
            "voice_id": self.voice_id,
            "evidence": self.evidence,
            "detail": self.detail,
            "source_key": self.source_key,
            "adapter": self.adapter,
        }


@dataclass
class VoiceArticle:
    """One canonical article, merged across every adapter that saw it."""

    key: str                                   # stable canonical identity key
    title: str = ""
    canonical_url: str = ""
    url: str = ""
    publication: str = ""
    description: str = ""
    image: str | None = None
    published_at: dt.datetime | None = None
    paywalled: bool | None = None

    identity_keys: frozenset[str] = frozenset()
    observations: list[Observation] = field(default_factory=list)
    attributions: list[Attribution] = field(default_factory=list)

    # Syndication: copies of the same piece run by another publisher. They stay
    # separate articles; exactly one of a group is the primary.
    syndication_group: str = ""
    syndication_primary: bool = True
    syndicated_from: str = ""                  # key of the primary, if not one

    @property
    def voice_ids(self) -> list[str]:
        seen: list[str] = []
        for attribution in sorted(
            self.attributions, key=lambda a: (evidence_rank(a.evidence), a.voice_id)
        ):
            if attribution.voice_id not in seen:
                seen.append(attribution.voice_id)
        return seen

    @property
    def byline(self) -> str:
        for observation in self.observations:
            if observation.byline:
                return observation.byline
        return ""

    @property
    def authors(self) -> list[Author]:
        out: list[Author] = []
        seen: set[tuple[str, str]] = set()
        for observation in self.observations:
            for author in observation.authors:
                marker = (author.provider_id or "", author.name.casefold())
                if marker in seen:
                    continue
                seen.add(marker)
                out.append(author)
        return out

    @property
    def discovered_via(self) -> list[str]:
        seen: list[str] = []
        for observation in self.observations:
            label = observation.source_key or observation.adapter
            if label not in seen:
                seen.append(label)
        return seen

    def evidence_for(self, voice_id: str) -> Attribution | None:
        """The strongest attribution recorded for one Voice."""
        candidates = [a for a in self.attributions if a.voice_id == voice_id]
        if not candidates:
            return None
        return min(candidates, key=lambda a: (evidence_rank(a.evidence), a.detail))

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "canonical_url": self.canonical_url,
            "link": self.url or self.canonical_url,
            "source": self.publication,
            "description": self.description,
            "image": self.image,
            "pub_date": to_iso(self.published_at),
            "paywalled": self.paywalled,
            "byline": self.byline,
            "authors": [a.as_dict() for a in self.authors],
            "voice_ids": self.voice_ids,
            "discovered_via": self.discovered_via,
            "syndication": {
                "group": self.syndication_group,
                "primary": self.syndication_primary,
                "syndicated_from": self.syndicated_from,
            },
            "attributions": [a.as_dict() for a in self.attributions],
            "observations": [o.as_dict() for o in self.observations],
        }


def with_fetched_at(observation: Observation, when: dt.datetime) -> Observation:
    """Stamp an observation's fetch time without mutating the original."""
    return replace(observation, fetched_at=when)

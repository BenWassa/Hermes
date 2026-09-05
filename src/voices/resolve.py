"""Voice attribution: deciding which Voice, if any, wrote an observation.

This is the part that must not be clever. Three evidence classes are accepted,
in strength order, and nothing else:

``provider_author_id``
    A structured author on the item carries a provider identifier the Voice
    registered (a Guardian contributor tag, a Perigon journalist id). Valid
    anywhere the item turns up, including the ordinary morning pool.

``source_scope``
    The item came from a source the Voice registered with
    ``authorship: "scope"`` - a personal feed, a publication author archive.
    The source itself is the assertion of authorship.

``byline_alias``
    A name on the item's *byline* matches one of the Voice's aliases exactly
    (see ``names.match_key``), **and** the item is in that Voice's declared
    byline scope: it came from one of the Voice's own registered sources, or
    from a host listed in ``byline_publications``.

Everything else is rejected, and rejections are recorded rather than dropped
so a missed piece can be diagnosed. In particular:

* a name appearing in a title, description, body, or a provider's "people
  mentioned" facet (NYT ``per_facet``, Perigon ``people``) is never
  authorship;
* an unscoped byline match is never authorship, which is what keeps a common
  name from collecting strangers' work;
* a Voice set to ``require_evidence: "provider_id"`` refuses byline evidence
  entirely.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .model import (
    EVIDENCE_BYLINE_ALIAS,
    EVIDENCE_PROVIDER_ID,
    EVIDENCE_SOURCE_SCOPE,
    Attribution,
    Observation,
    evidence_rank,
)
from .names import match_key, parse_byline
from .registry import AUTHORSHIP_BYLINE, AUTHORSHIP_SCOPE, Registry, Voice
from .urls import url_host

log = logging.getLogger("the-daily.voices.resolve")


@dataclass(frozen=True)
class Rejection:
    """A near-miss worth being able to explain later."""

    voice_id: str
    reason: str
    detail: str
    url: str = ""

    def as_dict(self) -> dict:
        return {"voice_id": self.voice_id, "reason": self.reason, "detail": self.detail, "url": self.url}


def observation_author_names(observation: Observation) -> list[str]:
    """Person names the observation *asserts as authors*.

    Structured authors first, falling back to parsing the displayed byline.
    Nothing else on the record is consulted: title, description, and
    people-mentioned facets are not authorship evidence.
    """
    names = [author.name for author in observation.authors if author.name]
    if not names and observation.byline:
        names = parse_byline(observation.byline)
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = match_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


class VoiceResolver:
    """Attributes observations to Voices using registry evidence."""

    def __init__(self, registry: Registry):
        self.registry = registry
        self._by_provider_id: dict[str, Voice] = {}
        self._by_alias: dict[str, list[Voice]] = {}
        self._source_owners: dict[str, list[tuple[Voice, object]]] = {}

        for voice in registry.active:
            for key in voice.provider_id_keys:
                self._by_provider_id[key] = voice
            if voice.accepts_byline_evidence:
                for key in voice.alias_keys:
                    self._by_alias.setdefault(key, []).append(voice)
            for source in voice.enabled_sources:
                self._source_owners.setdefault(source.key, []).append((voice, source))

    # -- evidence probes ---------------------------------------------------

    def _provider_id_attributions(self, observation: Observation) -> list[Attribution]:
        found: list[Attribution] = []
        for author in observation.authors:
            if not author.provider_id:
                continue
            provider = (author.provider or observation.provider or "").lower()
            voice = self._by_provider_id.get(f"{provider}:{author.provider_id.strip().lower()}")
            if voice is None:
                continue
            found.append(
                Attribution(
                    voice_id=voice.id,
                    evidence=EVIDENCE_PROVIDER_ID,
                    detail=f"{provider}:{author.provider_id}",
                    source_key=observation.source_key,
                    adapter=observation.adapter,
                )
            )
        return found

    def _scope_attributions(self, observation: Observation) -> list[Attribution]:
        found: list[Attribution] = []
        for voice, source in self._source_owners.get(observation.source_key, []):
            if source.authorship != AUTHORSHIP_SCOPE:
                continue
            found.append(
                Attribution(
                    voice_id=voice.id,
                    evidence=EVIDENCE_SOURCE_SCOPE,
                    detail=f"source '{source.id}' is scoped to this voice",
                    source_key=observation.source_key,
                    adapter=observation.adapter,
                )
            )
        return found

    def _byline_scope_for(self, voice: Voice, observation: Observation) -> str:
        """Why this Voice is allowed to match a byline here, or ""."""
        for owner, source in self._source_owners.get(observation.source_key, []):
            if owner.id == voice.id and source.authorship == AUTHORSHIP_BYLINE:
                return f"own source '{source.id}'"
        host = url_host(observation.canonical_url or observation.url)
        if host and host in voice.byline_publications:
            return f"declared publication '{host}'"
        return ""

    def _byline_attributions(
        self, observation: Observation, rejections: list[Rejection]
    ) -> list[Attribution]:
        found: list[Attribution] = []
        for name in observation_author_names(observation):
            key = match_key(name)
            for voice in self._by_alias.get(key, []):
                scope = self._byline_scope_for(voice, observation)
                if not scope:
                    rejections.append(
                        Rejection(
                            voice_id=voice.id,
                            reason="byline_out_of_scope",
                            detail=(
                                f"byline '{name}' matches voice '{voice.id}' but "
                                f"{observation.source_key or observation.adapter} is not one of its "
                                "registered sources or declared publications"
                            ),
                            url=observation.url,
                        )
                    )
                    continue
                found.append(
                    Attribution(
                        voice_id=voice.id,
                        evidence=EVIDENCE_BYLINE_ALIAS,
                        detail=f"byline '{name}' via {scope}",
                        source_key=observation.source_key,
                        adapter=observation.adapter,
                    )
                )
        return found

    def _record_provider_only_rejections(
        self, observation: Observation, rejections: list[Rejection]
    ) -> None:
        """Note when a strict Voice's name appeared but was not accepted."""
        for name in observation_author_names(observation):
            key = match_key(name)
            for voice in self.registry.active:
                if voice.accepts_byline_evidence or key not in voice.alias_keys:
                    continue
                rejections.append(
                    Rejection(
                        voice_id=voice.id,
                        reason="requires_provider_id",
                        detail=(
                            f"byline '{name}' matches voice '{voice.id}', which only accepts "
                            "provider-id evidence; no matching provider id on this item"
                        ),
                        url=observation.url,
                    )
                )

    # -- public API --------------------------------------------------------

    def attribute(self, observation: Observation) -> tuple[list[Attribution], list[Rejection]]:
        """Attributions for one observation, plus rejected near-misses."""
        rejections: list[Rejection] = []
        attributions = self._provider_id_attributions(observation)
        attributions += self._scope_attributions(observation)
        attributions += self._byline_attributions(observation, rejections)

        attributed = {a.voice_id for a in attributions}
        self._record_provider_only_rejections(observation, rejections)
        rejections = [r for r in rejections if r.voice_id not in attributed]

        # Collapse to the strongest evidence per voice, deterministically.
        best: dict[str, Attribution] = {}
        for attribution in attributions:
            current = best.get(attribution.voice_id)
            if current is None or evidence_rank(attribution.evidence) < evidence_rank(current.evidence):
                best[attribution.voice_id] = attribution
        return [best[k] for k in sorted(best)], rejections

    def attribute_all(
        self, observations: list[Observation]
    ) -> tuple[dict[int, list[Attribution]], list[Rejection]]:
        """Attribute a batch, keyed by the observation's index in the input."""
        by_index: dict[int, list[Attribution]] = {}
        all_rejections: list[Rejection] = []
        for index, observation in enumerate(observations):
            attributions, rejections = self.attribute(observation)
            if attributions:
                by_index[index] = attributions
            all_rejections.extend(rejections)
        for rejection in all_rejections:
            log.debug("voice attribution rejected: %s", rejection.detail)
        return by_index, all_rejections

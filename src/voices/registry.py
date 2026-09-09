"""The Voice registry: product membership, schema, validation, and identity indexing.

A Voice is a person. V2 keeps product membership separate from technical
availability: ``tier`` says why Hermes tracks the person, while ``enabled``,
``dormant``, ``notify`` and ``sources`` remain operational facts.

Identity owns three separable things:

``provider_ids``
    Stable source-native contributor/journalist identifiers. These attribute
    globally: wherever an article turns up carrying that id, it is this
    person's work.

``aliases``
    Displayed byline spellings. These attribute only inside a declared scope,
    never globally. The scope is the Voice's own registered sources plus any
    hosts listed in ``byline_publications``. That single restriction is what
    stops a common name from collecting strangers' articles: Hermes never
    scans the world for a name, it only reads bylines where the operator said
    this person publishes.

``sources``
    Where to actively go looking. A source declares how authorship is
    established for the items it returns:

    ``scope``       every item from this source is this Voice (a personal
                    feed, a publication author archive);
    ``byline``      match this Voice's aliases against the item's own byline
                    (a multi-author publication feed);
    ``provider_id`` match this Voice's provider ids against the item's
                    structured authors (Guardian contributor tags, Perigon
                    journalist ids).

Discovery and attribution are separate on purpose. A source that fetches does
not automatically grant attribution, and an attribution rule does not require
a fetch: the ordinary morning pool (Guardian/NYT/Perigon/RSS) is attributed
for free, with no extra provider requests at all.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .names import match_key
from .urls import canonical_url, normalize_host

log = logging.getLogger("the-daily.voices.registry")

REGISTRY_PATH = Path("data/voices.json")
SCHEMA_VERSION = 1

TIER_CORE = "core"
TIER_SELECTIVE = "selective"
TIER_DISCOVERY = "discovery"
VOICE_TIERS = {TIER_CORE, TIER_SELECTIVE, TIER_DISCOVERY}

AUTHORSHIP_SCOPE = "scope"
AUTHORSHIP_BYLINE = "byline"
AUTHORSHIP_PROVIDER_ID = "provider_id"
AUTHORSHIP_MODES = {AUTHORSHIP_SCOPE, AUTHORSHIP_BYLINE, AUTHORSHIP_PROVIDER_ID}

EVIDENCE_ANY = "byline"
EVIDENCE_PROVIDER_ONLY = "provider_id"
REQUIRE_EVIDENCE = {EVIDENCE_ANY, EVIDENCE_PROVIDER_ONLY}


class RegistryError(ValueError):
    """The registry file is invalid. Raised with every problem found."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("invalid voice registry:\n  - " + "\n  - ".join(problems))


@dataclass(frozen=True)
class ProviderIdentity:
    """A stable source-native identifier for a person."""

    provider: str
    id: str

    @property
    def key(self) -> str:
        return f"{self.provider.lower()}:{self.id.strip().lower()}"


@dataclass(frozen=True)
class VoiceSource:
    """One place to look for a Voice's new work."""

    id: str
    type: str
    authorship: str
    enabled: bool = True
    params: dict = field(default_factory=dict)
    note: str = ""

    @property
    def key(self) -> str:
        """Request-dedupe key. Two Voices sharing a feed fetch it once."""
        from .adapters import source_key_for  # local import: adapters import us

        return source_key_for(self)


@dataclass(frozen=True)
class Voice:
    """A tracked person with independent product and operational state."""

    id: str
    name: str
    tier: str = TIER_CORE
    enabled: bool = True
    notify: bool = True
    dormant: bool = False
    require_evidence: str = EVIDENCE_ANY
    aliases: tuple[str, ...] = ()
    provider_ids: tuple[ProviderIdentity, ...] = ()
    byline_publications: tuple[str, ...] = ()
    sources: tuple[VoiceSource, ...] = ()
    note: str = ""

    @property
    def alias_keys(self) -> frozenset[str]:
        """Canonical match keys for the display name and every alias."""
        keys = {match_key(self.name)}
        keys.update(match_key(alias) for alias in self.aliases)
        return frozenset(k for k in keys if k)

    @property
    def provider_id_keys(self) -> frozenset[str]:
        return frozenset(p.key for p in self.provider_ids)

    @property
    def enabled_sources(self) -> tuple[VoiceSource, ...]:
        return tuple(s for s in self.sources if s.enabled)

    @property
    def accepts_byline_evidence(self) -> bool:
        return self.require_evidence != EVIDENCE_PROVIDER_ONLY


@dataclass(frozen=True)
class Registry:
    """A validated set of Voices plus the indexes the resolver needs."""

    voices: tuple[Voice, ...] = ()
    version: int = SCHEMA_VERSION

    @property
    def active(self) -> tuple[Voice, ...]:
        return tuple(v for v in self.voices if v.enabled)

    @property
    def notifiable(self) -> tuple[Voice, ...]:
        """Voices retaining the legacy V1 per-article watcher switch."""
        return tuple(v for v in self.active if v.notify)

    def for_tiers(self, tiers: set[str] | frozenset[str]) -> "Registry":
        """Return the same registry narrowed by product tier, not operation flags."""
        return Registry(
            voices=tuple(v for v in self.voices if v.tier in tiers),
            version=self.version,
        )

    def for_legacy_watcher(self) -> "Registry":
        """Keep V1 watcher polling bounded to the Voices whose V1 notify switch is on."""
        return Registry(voices=self.notifiable, version=self.version)

    def get(self, voice_id: str) -> Voice | None:
        for voice in self.voices:
            if voice.id == voice_id:
                return voice
        return None

    def sources_by_key(self) -> dict[str, list[tuple[Voice, VoiceSource]]]:
        """Every enabled source of every enabled Voice, grouped for batching.

        Grouping by key is what turns "N voices sharing a publication feed"
        into one request, and what lets an observation from a shared feed be
        offered to each Voice that registered it.
        """
        grouped: dict[str, list[tuple[Voice, VoiceSource]]] = {}
        for voice in self.active:
            for source in voice.enabled_sources:
                grouped.setdefault(source.key, []).append((voice, source))
        return grouped


# --- validation -----------------------------------------------------------

_ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def _require_str(value, label: str, problems: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{label} must be a non-empty string")
        return ""
    return value.strip()


def _parse_source(raw, voice_id: str, index: int, problems: list[str]) -> VoiceSource | None:
    from .adapters import ADAPTER_TYPES, required_params

    label = f"voice '{voice_id}' source #{index}"
    if not isinstance(raw, dict):
        problems.append(f"{label} must be an object")
        return None

    source_type = _require_str(raw.get("type"), f"{label}.type", problems)
    if source_type and source_type not in ADAPTER_TYPES:
        problems.append(
            f"{label}.type '{source_type}' is not a known adapter "
            f"(known: {', '.join(sorted(ADAPTER_TYPES))})"
        )
        return None

    authorship = raw.get("authorship")
    if authorship is None:
        problems.append(f"{label}.authorship is required (one of {sorted(AUTHORSHIP_MODES)})")
        return None
    if authorship not in AUTHORSHIP_MODES:
        problems.append(f"{label}.authorship '{authorship}' must be one of {sorted(AUTHORSHIP_MODES)}")
        return None

    source_id = raw.get("id") or f"{voice_id}-{source_type}-{index}"
    params = {k: v for k, v in raw.items() if k not in {"id", "type", "authorship", "enabled", "note"}}

    missing = [p for p in required_params(source_type) if not params.get(p)]
    if missing:
        problems.append(f"{label} ({source_type}) is missing required field(s): {', '.join(missing)}")
        return None

    if source_type in {"rss", "author_page"}:
        url = params.get("url", "")
        if not canonical_url(url):
            problems.append(f"{label}.url '{url}' is not an absolute http(s) URL")
            return None

    return VoiceSource(
        id=str(source_id),
        type=source_type,
        authorship=authorship,
        enabled=bool(raw.get("enabled", True)),
        params=params,
        note=str(raw.get("note", "")),
    )


def _parse_voice(raw, index: int, problems: list[str]) -> Voice | None:
    label = f"voice #{index}"
    if not isinstance(raw, dict):
        problems.append(f"{label} must be an object")
        return None

    voice_id = _require_str(raw.get("id"), f"{label}.id", problems)
    if voice_id and (set(voice_id) - _ID_CHARS):
        problems.append(f"voice id '{voice_id}' must be lowercase letters, digits and hyphens")
    name = _require_str(raw.get("name"), f"voice '{voice_id or index}'.name", problems)
    if not voice_id or not name:
        return None

    if not match_key(name):
        problems.append(
            f"voice '{voice_id}'.name '{name}' does not parse as a person name "
            "(a Voice is a person, and needs at least a given name and a surname)"
        )
        return None

    tier = raw.get("tier", TIER_CORE)
    if tier not in VOICE_TIERS:
        problems.append(f"voice '{voice_id}'.tier '{tier}' must be one of {sorted(VOICE_TIERS)}")
        tier = TIER_CORE

    require_evidence = raw.get("require_evidence", EVIDENCE_ANY)
    if require_evidence not in REQUIRE_EVIDENCE:
        problems.append(
            f"voice '{voice_id}'.require_evidence '{require_evidence}' must be one of "
            f"{sorted(REQUIRE_EVIDENCE)}"
        )
        require_evidence = EVIDENCE_ANY

    aliases: list[str] = []
    for alias in raw.get("aliases", []) or []:
        if not isinstance(alias, str) or not match_key(alias):
            problems.append(f"voice '{voice_id}' alias {alias!r} does not parse as a person name")
            continue
        aliases.append(alias.strip())

    provider_ids: list[ProviderIdentity] = []
    seen_provider_keys: set[str] = set()
    for entry in raw.get("provider_ids", []) or []:
        if not isinstance(entry, dict):
            problems.append(f"voice '{voice_id}' provider_ids entries must be objects")
            continue
        provider = _require_str(entry.get("provider"), f"voice '{voice_id}' provider_ids.provider", problems)
        pid = _require_str(entry.get("id"), f"voice '{voice_id}' provider_ids.id", problems)
        if not provider or not pid:
            continue
        identity = ProviderIdentity(provider=provider.lower(), id=pid)
        if identity.key in seen_provider_keys:
            problems.append(f"voice '{voice_id}' repeats provider id '{identity.key}'")
            continue
        seen_provider_keys.add(identity.key)
        provider_ids.append(identity)

    publications: list[str] = []
    for host in raw.get("byline_publications", []) or []:
        normalized = normalize_host(str(host))
        if not normalized or "." not in normalized:
            problems.append(f"voice '{voice_id}' byline_publications entry {host!r} is not a host")
            continue
        publications.append(normalized)

    sources: list[VoiceSource] = []
    seen_source_ids: set[str] = set()
    seen_source_keys: set[str] = set()
    for source_index, raw_source in enumerate(raw.get("sources", []) or []):
        source = _parse_source(raw_source, voice_id, source_index, problems)
        if source is None:
            continue
        if source.id in seen_source_ids:
            problems.append(f"voice '{voice_id}' repeats source id '{source.id}'")
            continue
        if source.key in seen_source_keys:
            problems.append(
                f"voice '{voice_id}' declares the same source twice ('{source.key}'), "
                "which would poll it redundantly"
            )
            continue
        seen_source_ids.add(source.id)
        seen_source_keys.add(source.key)
        sources.append(source)

    voice = Voice(
        id=voice_id,
        name=name,
        tier=tier,
        enabled=bool(raw.get("enabled", True)),
        notify=bool(raw.get("notify", True)),
        dormant=bool(raw.get("dormant", False)),
        require_evidence=require_evidence,
        aliases=tuple(aliases),
        provider_ids=tuple(provider_ids),
        byline_publications=tuple(publications),
        sources=tuple(sources),
        note=str(raw.get("note", "")),
    )

    if voice.enabled and not voice.dormant:
        usable = voice.enabled_sources or voice.provider_ids or voice.byline_publications
        if not usable:
            problems.append(
                f"voice '{voice_id}' is enabled but has no usable source or identity; "
                'set "dormant": true to keep it registered without discovery'
            )
    if voice.require_evidence == EVIDENCE_PROVIDER_ONLY and not voice.provider_ids:
        byline_scoped = [s for s in voice.enabled_sources if s.authorship == AUTHORSHIP_BYLINE]
        if byline_scoped and not voice.dormant:
            problems.append(
                f"voice '{voice_id}' requires provider-id evidence but declares no provider_ids, "
                "so its byline sources can never attribute anything"
            )
    return voice


def validate(data) -> tuple[Registry, list[str]]:
    """Parse and validate registry data. Returns the registry and problems."""
    problems: list[str] = []
    if not isinstance(data, dict):
        raise RegistryError(["registry must be a JSON object"])

    version = data.get("version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        problems.append(f"unsupported registry version {version!r} (expected {SCHEMA_VERSION})")

    raw_voices = data.get("voices")
    if not isinstance(raw_voices, list):
        raise RegistryError(problems + ["registry.voices must be a list"])

    voices: list[Voice] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_voices):
        voice = _parse_voice(raw, index, problems)
        if voice is None:
            continue
        if voice.id in seen_ids:
            problems.append(f"duplicate voice id '{voice.id}'")
            continue
        seen_ids.add(voice.id)
        voices.append(voice)

    # Two enabled Voices answering to the same byline is a genuine ambiguity:
    # a byline match could not tell them apart, so refuse the registry rather
    # than attribute arbitrarily.
    alias_owners: dict[str, list[str]] = {}
    for voice in voices:
        if not voice.enabled or not voice.accepts_byline_evidence:
            continue
        for key in voice.alias_keys:
            alias_owners.setdefault(key, []).append(voice.id)
    for key, owners in sorted(alias_owners.items()):
        if len(owners) > 1:
            problems.append(
                f"byline '{key}' is claimed by more than one enabled voice ({', '.join(sorted(owners))}); "
                'disambiguate with provider_ids and "require_evidence": "provider_id"'
            )

    # A provider identity belongs to exactly one person.
    provider_owners: dict[str, list[str]] = {}
    for voice in voices:
        for key in voice.provider_id_keys:
            provider_owners.setdefault(key, []).append(voice.id)
    for key, owners in sorted(provider_owners.items()):
        if len(owners) > 1:
            problems.append(f"provider id '{key}' is claimed by more than one voice ({', '.join(sorted(owners))})")

    return Registry(voices=tuple(voices), version=SCHEMA_VERSION), problems


def load_registry(path: Path | str = REGISTRY_PATH, *, strict: bool = True) -> Registry:
    """Load and validate the registry file.

    ``strict`` (the default, and what CI and the build use) raises on any
    problem. Non-strict logs them and returns whatever parsed, which the audit
    CLI uses to report on a half-broken file instead of refusing to run.
    """
    path = Path(path)
    if not path.exists():
        if strict:
            raise RegistryError([f"registry file not found: {path}"])
        log.warning("voice registry %s not found; continuing with no voices", path)
        return Registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryError([f"{path} is not valid JSON: {exc}"]) from exc

    registry, problems = validate(data)
    if problems:
        if strict:
            raise RegistryError(problems)
        for problem in problems:
            log.warning("voice registry: %s", problem)
    return registry

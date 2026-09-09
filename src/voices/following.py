"""Deterministic morning Following selection.

V2 keeps the reader-priority surface finite while giving Core Voices breadth
before depth. Selective writing passes one generic metadata-based substantive
writing gate before it can compete for an ordinary slot; Discovery never gains
Following eligibility from tier membership. Nothing here calls a model.
"""

from __future__ import annotations

import datetime as dt
import re

from .model import VoiceArticle
from .registry import Registry, TIER_CORE, TIER_DISCOVERY, TIER_SELECTIVE
from .urls import url_key

_MIN_TIME = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
_SELECTIVE_MIN_DESCRIPTION_CHARS = 140
_NON_SUBSTANTIVE_FORMAT = re.compile(
    r"\b(podcast|video|livestream|live stream|webinar|event|announcement|transcript|clip|shorts?)\b",
    re.IGNORECASE,
)


def _recency_key(article: VoiceArticle) -> tuple:
    """Newest first, with a stable tie-break so ordering never wobbles."""
    published = article.published_at or _MIN_TIME
    return (-published.timestamp(), article.title.casefold(), article.key)


def qualifies_selective(article: VoiceArticle) -> bool:
    """Generic deterministic gate for Selective tier writing.

    Selective is intentionally stricter than Core, but the rule must not smuggle
    ideology, popularity, engagement or a fabricated quality score into the
    product. A candidate therefore needs enough publisher-supplied description
    to establish that it is a substantive written argument, and obvious
    audio/video/event/transcript formats are excluded. Missing metadata fails
    closed. This rule is source- and person-agnostic and adds zero Gemini calls.
    """
    title = " ".join((article.title or "").split())
    description = " ".join((article.description or "").split())
    if not title or len(description) < _SELECTIVE_MIN_DESCRIPTION_CHARS:
        return False
    if _NON_SUBSTANTIVE_FORMAT.search(f"{title} {description[:240]}"):
        return False
    return True


def _legacy_select_following(
    articles: list[VoiceArticle],
    *,
    cap: int,
    per_voice: int,
    voice_order: list[str] | None,
) -> list[VoiceArticle]:
    """V1-compatible selector for callers/tests that have no V2 registry."""
    if cap <= 0:
        return []

    eligible = [a for a in articles if a.voice_ids and a.syndication_primary]
    eligible.sort(key=_recency_key)

    by_voice: dict[str, list[VoiceArticle]] = {}
    for article in eligible:
        by_voice.setdefault(article.voice_ids[0], []).append(article)

    explicit = voice_order or []

    def voice_rank(voice_id: str) -> tuple:
        position = explicit.index(voice_id) if voice_id in explicit else len(explicit)
        return (position, _recency_key(by_voice[voice_id][0]))

    order = sorted(by_voice, key=voice_rank)
    chosen: list[VoiceArticle] = []
    taken: set[str] = set()
    for round_index in range(max(1, per_voice)):
        for voice_id in order:
            items = by_voice[voice_id]
            if round_index >= len(items):
                continue
            chosen.append(items[round_index])
            taken.add(items[round_index].key)
            if len(chosen) >= cap:
                break
        if len(chosen) >= cap:
            break

    for article in eligible:
        if len(chosen) >= cap:
            break
        if article.key in taken:
            continue
        chosen.append(article)
        taken.add(article.key)

    chosen.sort(key=_recency_key)
    return chosen[:cap]


def _eligible_voice(article: VoiceArticle, registry: Registry) -> tuple[str, str] | None:
    """Pick the product-relevant coauthor deterministically, Core before Selective."""
    candidates: list[tuple[int, str, str]] = []
    rank = {TIER_CORE: 0, TIER_SELECTIVE: 1, TIER_DISCOVERY: 2}
    for voice_id in article.voice_ids:
        voice = registry.get(voice_id)
        if voice is None or not voice.enabled or voice.tier == TIER_DISCOVERY:
            continue
        if voice.tier == TIER_SELECTIVE and not qualifies_selective(article):
            continue
        candidates.append((rank[voice.tier], voice.id, voice.tier))
    if not candidates:
        return None
    _, voice_id, tier = min(candidates)
    return voice_id, tier


def select_following(
    articles: list[VoiceArticle],
    *,
    cap: int,
    per_voice: int,
    voice_order: list[str] | None = None,
    registry: Registry | None = None,
    overflow_cap: int | None = None,
) -> list[VoiceArticle]:
    """Choose the articles the morning Following block shows.

    With a V2 registry, one newest article from each distinct Core Voice is
    selected before anyone gets depth. The ordinary ceiling remains ``cap``.
    Only extra distinct Core Voices may extend that set, and only as far as
    ``overflow_cap``. When Core breadth fits inside the normal ceiling, the
    remaining ordinary slots are filled deterministically from Core depth and
    qualified Selective writing; Discovery is excluded.

    ``registry=None`` retains the exact V1 selection contract for legacy unit
    fixtures and non-production callers during migration.
    """
    if registry is None:
        return _legacy_select_following(
            articles, cap=cap, per_voice=per_voice, voice_order=voice_order
        )
    if cap <= 0:
        return []

    hard_cap = max(cap, overflow_cap if overflow_cap is not None else cap)
    eligible: list[tuple[VoiceArticle, str, str]] = []
    for article in articles:
        if not article.syndication_primary:
            continue
        voice = _eligible_voice(article, registry)
        if voice is None:
            continue
        eligible.append((article, voice[0], voice[1]))
    eligible.sort(key=lambda item: _recency_key(item[0]))

    core_by_voice: dict[str, list[VoiceArticle]] = {}
    selective: list[tuple[VoiceArticle, str]] = []
    for article, voice_id, tier in eligible:
        if tier == TIER_CORE:
            core_by_voice.setdefault(voice_id, []).append(article)
        else:
            selective.append((article, voice_id))

    explicit = voice_order or []

    def core_rank(voice_id: str) -> tuple:
        position = explicit.index(voice_id) if voice_id in explicit else len(explicit)
        return (position, _recency_key(core_by_voice[voice_id][0]), voice_id)

    core_order = sorted(core_by_voice, key=core_rank)
    breadth_limit = min(hard_cap, len(core_order)) if len(core_order) > cap else len(core_order)

    chosen: list[VoiceArticle] = []
    taken: set[str] = set()
    counts: dict[str, int] = {}
    for voice_id in core_order[:breadth_limit]:
        article = core_by_voice[voice_id][0]
        chosen.append(article)
        taken.add(article.key)
        counts[voice_id] = 1

    # Core-only overflow is complete once every admitted overflow slot has
    # introduced a distinct Core Voice. Selective and depth never extend it.
    if len(core_order) > cap:
        chosen.sort(key=_recency_key)
        return chosen[:hard_cap]

    remaining: list[tuple[VoiceArticle, str]] = []
    for voice_id, items in core_by_voice.items():
        remaining.extend((article, voice_id) for article in items if article.key not in taken)
    remaining.extend((article, voice_id) for article, voice_id in selective if article.key not in taken)
    remaining.sort(key=lambda item: _recency_key(item[0]))

    # Preserve the V1 anti-domination shape inside the ordinary six: offer up
    # to per_voice items per person before allowing pure-recency leftovers.
    for article, voice_id in remaining:
        if len(chosen) >= cap:
            break
        if counts.get(voice_id, 0) >= max(1, per_voice):
            continue
        chosen.append(article)
        taken.add(article.key)
        counts[voice_id] = counts.get(voice_id, 0) + 1

    for article, voice_id in remaining:
        if len(chosen) >= cap:
            break
        if article.key in taken:
            continue
        chosen.append(article)
        taken.add(article.key)
        counts[voice_id] = counts.get(voice_id, 0) + 1

    chosen.sort(key=_recency_key)
    return chosen[:cap]


def suppress_duplicates(following: list[VoiceArticle], edition_links: list[str]) -> list[VoiceArticle]:
    """Drop Following entries the ordinary edition already shows.

    The editor may independently pick a followed piece for Today's Opinion.
    When that happens the reader should see one card, not two. Matching is on
    canonical identity keys, not on the raw link, so a tracking parameter or
    an AMP mirror in the edition does not defeat it.
    """
    edition_keys = {url_key(link) for link in edition_links if url_key(link)}
    if not edition_keys:
        return list(following)
    return [a for a in following if not (a.identity_keys & edition_keys)]

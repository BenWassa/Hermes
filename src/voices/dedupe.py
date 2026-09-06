"""Article identity: collapsing observations into canonical articles.

The same piece reaches Hermes several ways. A followed essay can arrive via
its publication's feed, the Guardian API, Perigon, and the ordinary morning
fetch, each with a different URL shape and a different provider id. Following
must show it once, and the later watcher must alert once.

The mechanism is a union over *identity keys*. Each observation contributes
the keys on which it may legitimately be recognised again:

* ``url:``  the canonical URL, after tracking parameters and AMP mirrors are
  removed. This is the cross-provider join: every provider ultimately points
  at the publisher's own URL.
* ``pid:``  provider-native article ids. These join two sightings from the
  same provider; they are not comparable across providers, so they never
  merge a Guardian record with a Perigon one on their own.
* ``fp:``   a bounded same-host fallback (host + title slug + publication
  day) for sources with no stable id and a URL that moved.

Observations sharing any key are the same article. Nothing merges on title
alone, on author alone, or across hosts.

**Syndication is deliberately not identity.** A column run by two publishers
is two articles with two canonical URLs, and collapsing them would throw away
a real fact. Instead they are *grouped*: one member is elected primary and the
others record which primary they belong to, so Following presents one entry
while the provenance survives. Grouping requires the same normalized title,
the same author, and publication within a short window, so two unrelated
pieces cannot group.
"""

from __future__ import annotations

import datetime as dt
import logging

from .model import Attribution, Observation, VoiceArticle
from .names import match_key
from .timeparse import day_key
from .urls import canonical_url, fingerprint_key, provider_key, syndication_key, url_key, url_host

log = logging.getLogger("the-daily.voices.dedupe")

#: Publication times this far apart are not the same syndicated run.
SYNDICATION_WINDOW = dt.timedelta(days=3)


def identity_keys(observation: Observation) -> set[str]:
    """Every key this observation may be recognised by."""
    keys: set[str] = set()
    canonical = observation.canonical_url or canonical_url(observation.url)
    if canonical:
        keys.add(f"url:{canonical}")
    item_key = url_key(observation.url)
    if item_key:
        keys.add(item_key)
    if observation.provider and observation.provider_article_id:
        keys.add(provider_key(observation.provider, observation.provider_article_id))
    fingerprint = fingerprint_key(
        observation.url or canonical, observation.title, day_key(observation.published_at)
    )
    if fingerprint:
        keys.add(fingerprint)
    return {k for k in keys if k}


class _Union:
    """Tiny union-find over identity keys."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, key: str) -> str:
        self._parent.setdefault(key, key)
        root = key
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[key] != root:  # path compression
            self._parent[key], key = root, self._parent[key]
        return root

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            # Bind to the lexicographically smaller root so grouping is stable
            # across runs regardless of observation order.
            low, high = sorted((root_a, root_b))
            self._parent[high] = low


def _pick_canonical_url(observations: list[Observation]) -> tuple[str, str]:
    """Choose the article's canonical URL and its display link.

    Provider-declared publisher URLs (Guardian ``webUrl``, a feed's own link)
    are already canonical; the choice below is a deterministic tie-break, not
    a guess: prefer the shortest canonical URL seen, then the alphabetically
    first, so two runs over the same observations always agree.
    """
    candidates = sorted(
        {(o.canonical_url or canonical_url(o.url)) for o in observations if (o.canonical_url or canonical_url(o.url))}
    )
    if not candidates:
        return "", observations[0].url if observations else ""
    canonical = min(candidates, key=lambda u: (len(u), u))
    display = next(
        (o.url for o in observations if (o.canonical_url or canonical_url(o.url)) == canonical),
        canonical,
    )
    return canonical, display


def _observation_rank(observation: Observation) -> tuple:
    """Preference order when merging conflicting field values.

    A first-party or first-party-API sighting outranks an aggregator, which
    outranks a bare pool sighting, because the publisher's own record of a
    headline and timestamp is the one to trust.
    """
    adapter_rank = {
        "rss": 0,
        "author_page": 1,
        "guardian_contributor": 1,
        "pool": 3,
        "perigon_journalist": 2,
    }.get(observation.adapter, 2)
    return (adapter_rank, observation.published_at or dt.datetime.max.replace(tzinfo=dt.timezone.utc))


def merge_observations(
    observations: list[Observation],
    attributions_by_index: dict[int, list[Attribution]] | None = None,
) -> list[VoiceArticle]:
    """Collapse observations into canonical articles.

    Order-independent: the same observations in any order produce the same
    articles with the same keys.
    """
    attributions_by_index = attributions_by_index or {}
    union = _Union()
    keys_by_index: dict[int, set[str]] = {}

    for index, observation in enumerate(observations):
        keys = identity_keys(observation)
        if not keys:
            # Nothing to key on at all: give it a private key so it survives
            # as its own article rather than merging with something else.
            keys = {f"anon:{index}:{observation.title}"}
        keys_by_index[index] = keys
        anchor = min(keys)
        for key in keys:
            union.union(anchor, key)

    grouped: dict[str, list[int]] = {}
    for index, keys in keys_by_index.items():
        grouped.setdefault(union.find(min(keys)), []).append(index)

    articles: list[VoiceArticle] = []
    for root, indexes in grouped.items():
        members = sorted(indexes)
        group = [observations[i] for i in members]
        ordered = sorted(group, key=_observation_rank)
        canonical, display = _pick_canonical_url(ordered)

        published = [o.published_at for o in ordered if o.published_at]
        merged_attributions: list[Attribution] = []
        seen_attributions: set[tuple[str, str, str]] = set()
        for index in members:
            for attribution in attributions_by_index.get(index, []):
                marker = (attribution.voice_id, attribution.evidence, attribution.detail)
                if marker in seen_attributions:
                    continue
                seen_attributions.add(marker)
                merged_attributions.append(attribution)

        all_keys = set()
        for index in members:
            all_keys |= keys_by_index[index]

        article = VoiceArticle(
            key=f"url:{canonical}" if canonical else root,
            title=next((o.title for o in ordered if o.title), ""),
            canonical_url=canonical,
            url=display or canonical,
            publication=next((o.publication for o in ordered if o.publication), ""),
            description=next((o.description for o in ordered if o.description), ""),
            image=next((o.image for o in ordered if o.image), None),
            published_at=min(published) if published else None,
            paywalled=next((o.paywalled for o in ordered if o.paywalled is not None), None),
            identity_keys=frozenset(all_keys),
            observations=ordered,
            attributions=merged_attributions,
        )
        articles.append(article)

    # Newest first, undated last, key as the stable tie-break.
    def order(article: VoiceArticle) -> tuple:
        published = article.published_at
        return (published is None, -published.timestamp() if published else 0.0, article.key)

    articles.sort(key=order)
    return articles


def _syndication_author_key(article: VoiceArticle) -> str:
    """The author identity a syndication group is keyed on."""
    voice_ids = article.voice_ids
    if voice_ids:
        return f"voice:{voice_ids[0]}"
    for author in article.authors:
        key = match_key(author.name)
        if key:
            return f"name:{key}"
    return ""


def syndication_keys_for(article: VoiceArticle) -> set[str]:
    """The grouping keys one article carries, computed outside a run.

    ``group_syndication`` only links copies that are present in the *same*
    run. The release-time watcher needs the same link across runs: a column
    alerted on Monday must not alert again when a second publisher's reprint
    is discovered on Tuesday. Recording these keys in durable state alongside
    the article's identity keys gives that, using exactly the semantics
    ``group_syndication`` already applies rather than a second, looser rule.
    """
    keys = {f"reprint:{o.reprint_group_id}" for o in article.observations if o.reprint_group_id}
    soft = syndication_key(
        article.title, _syndication_author_key(article), day_key(article.published_at)
    )
    if soft:
        keys.add(soft)
    return keys


def group_syndication(articles: list[VoiceArticle]) -> list[VoiceArticle]:
    """Group cross-publisher copies of one piece without merging them.

    Two signals are used, and an article may carry both. A provider that
    already tracks reprints (Perigon's ``reprintGroupId``) is trusted
    directly. Independently, a group can form from the same normalized title,
    the same author, and publication dates inside ``SYNDICATION_WINDOW``. The
    signals are unioned, so a run where only the reprinted copy is flagged
    still groups with its original.

    Election of the primary is deterministic: a copy a provider flagged as a
    reprint never wins, then earliest publication (the original run), then the
    shortest canonical URL.
    """
    union = _Union()
    keys_by_article: dict[int, set[str]] = {}

    for index, article in enumerate(articles):
        keys: set[str] = set()
        for observation in article.observations:
            if observation.reprint_group_id:
                keys.add(f"reprint:{observation.reprint_group_id}")
        soft = syndication_key(
            article.title, _syndication_author_key(article), day_key(article.published_at)
        )
        if soft:
            keys.add(soft)
        if not keys:
            continue
        keys_by_article[index] = keys
        anchor = min(keys)
        for key in keys:
            union.union(anchor, key)

    components: dict[str, list[int]] = {}
    for index, keys in keys_by_article.items():
        components.setdefault(union.find(min(keys)), []).append(index)

    for group_key, indexes in components.items():
        members = [articles[i] for i in indexes]
        if len(members) < 2:
            continue
        dated = [m for m in members if m.published_at]
        if dated and (max(m.published_at for m in dated) - min(m.published_at for m in dated)) > SYNDICATION_WINDOW:
            continue
        if len({url_host(m.canonical_url) for m in members}) < 2:
            # One publisher: identity keys already handle real duplicates, and
            # grouping here would only hide a genuine second piece.
            continue

        def rank(article: VoiceArticle) -> tuple:
            is_reprint = any(o.reprint for o in article.observations)
            return (
                is_reprint,
                article.published_at or dt.datetime.max.replace(tzinfo=dt.timezone.utc),
                len(article.canonical_url),
                article.canonical_url,
            )

        ordered = sorted(members, key=rank)
        primary = ordered[0]
        for article in ordered:
            article.syndication_group = group_key
            article.syndication_primary = article is primary
            article.syndicated_from = "" if article is primary else primary.key
        log.info(
            "voices: grouped %d syndicated copies under %s (primary %s)",
            len(ordered), group_key, primary.canonical_url,
        )
    return articles

"""The deterministic Following set.

Selection policy for the morning Following block, kept here (with tests)
rather than in a template or a model prompt. Two properties matter:

* **Deterministic.** The same articles always produce the same block in the
  same order. Nothing here consults a model; a reader's explicit follow is not
  a ranking signal to be outvoted.
* **Finite.** The Daily is a finished paper. A hard cap applies, and one
  prolific writer cannot fill the block: each Voice gets a small guaranteed
  share first, and only then are leftover slots filled by recency.

Rendering is issue #11's job. This module produces the ordered set it renders.
"""

from __future__ import annotations

import datetime as dt

from .model import VoiceArticle
from .urls import url_key

_MIN_TIME = dt.datetime.min.replace(tzinfo=dt.timezone.utc)


def _recency_key(article: VoiceArticle) -> tuple:
    """Newest first, with a stable tie-break so ordering never wobbles."""
    published = article.published_at or _MIN_TIME
    return (-published.timestamp(), article.title.casefold(), article.key)


def select_following(
    articles: list[VoiceArticle],
    *,
    cap: int,
    per_voice: int,
    voice_order: list[str] | None = None,
) -> list[VoiceArticle]:
    """Choose the articles the Following block shows.

    Two passes. The first is round-robin across Voices, newest Voice first, so
    breadth comes before depth: everyone the reader follows who published gets
    a slot before anyone gets a second. It runs at most ``per_voice`` rounds.
    The second pass fills any slots still empty with the newest of what is
    left, which is what keeps the block full on a day when only one writer
    published.

    Syndicated copies are represented by their primary only, so one piece run
    by two publishers cannot occupy two slots.
    """
    if cap <= 0:
        return []

    eligible = [a for a in articles if a.voice_ids and a.syndication_primary]
    eligible.sort(key=_recency_key)

    by_voice: dict[str, list[VoiceArticle]] = {}
    for article in eligible:
        by_voice.setdefault(article.voice_ids[0], []).append(article)

    explicit = voice_order or []

    def voice_rank(voice_id: str) -> tuple:
        # An explicit order wins; otherwise the Voice that published most
        # recently leads, which keeps the block's top honest.
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

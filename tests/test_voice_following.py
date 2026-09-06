"""The deterministic, finite Following selection."""

from __future__ import annotations

import datetime as dt

from src.voices.following import select_following, suppress_duplicates
from src.voices.model import Attribution, VoiceArticle
from tests.conftest import NOW


def article(key: str, voice: str, hours_ago: float, *, title="A Piece",
            primary=True, url=None) -> VoiceArticle:
    canonical = url or f"https://example.com/{key}"
    return VoiceArticle(
        key=f"url:{canonical}",
        title=f"{title} {key}",
        canonical_url=canonical,
        url=canonical,
        published_at=NOW - dt.timedelta(hours=hours_ago),
        identity_keys=frozenset({f"url:{canonical}"}),
        attributions=[Attribution(voice, "byline_alias", "x")],
        syndication_primary=primary,
    )


def test_no_followed_material_yields_an_empty_block():
    assert select_following([], cap=6, per_voice=2) == []


def test_one_followed_piece():
    chosen = select_following([article("a", "haidt", 2)], cap=6, per_voice=2)
    assert [a.key for a in chosen] == ["url:https://example.com/a"]


def test_several_writers_are_ordered_newest_first():
    chosen = select_following(
        [article("a", "haidt", 5), article("b", "black", 1), article("c", "peterson", 3)],
        cap=6, per_voice=2,
    )
    assert [a.voice_ids[0] for a in chosen] == ["black", "peterson", "haidt"]


def test_the_cap_holds():
    items = [article(str(i), f"voice-{i}", i) for i in range(12)]
    assert len(select_following(items, cap=6, per_voice=2)) == 6


def test_one_prolific_writer_cannot_crowd_out_the_others():
    prolific = [article(f"p{i}", "haidt", i) for i in range(8)]
    others = [article("q", "black", 20), article("r", "peterson", 21)]
    chosen = select_following(prolific + others, cap=6, per_voice=2)

    assert {a.voice_ids[0] for a in chosen} == {"haidt", "black", "peterson"}
    assert sum(1 for a in chosen if a.voice_ids[0] == "black") == 1
    assert len(chosen) == 6


def test_every_voice_gets_a_slot_before_anyone_gets_a_second():
    items = [
        article("a1", "haidt", 1), article("a2", "haidt", 2),
        article("b1", "black", 3), article("b2", "black", 4),
        article("c1", "peterson", 5),
    ]
    chosen = select_following(items, cap=3, per_voice=2)
    assert {a.voice_ids[0] for a in chosen} == {"haidt", "black", "peterson"}


def test_a_single_active_voice_still_fills_the_block():
    """per_voice is a fairness floor for others, not a ceiling on a quiet day."""
    items = [article(f"p{i}", "haidt", i) for i in range(6)]
    assert len(select_following(items, cap=4, per_voice=2)) == 4


def test_leftover_slots_fill_by_recency_after_every_voice_is_served():
    prolific = [article(f"p{i}", "haidt", i) for i in range(5)]
    chosen = select_following(prolific + [article("q", "black", 40)], cap=4, per_voice=2)
    assert sum(1 for a in chosen if a.voice_ids[0] == "haidt") == 3
    assert sum(1 for a in chosen if a.voice_ids[0] == "black") == 1


def test_selection_is_deterministic_regardless_of_input_order():
    items = [article(str(i), f"v{i % 3}", i) for i in range(9)]
    forward = [a.key for a in select_following(items, cap=5, per_voice=2)]
    backward = [a.key for a in select_following(list(reversed(items)), cap=5, per_voice=2)]
    assert forward == backward


def test_undated_items_sort_last_without_crashing():
    dated = article("a", "haidt", 1)
    undated = article("b", "black", 1)
    undated.published_at = None
    chosen = select_following([undated, dated], cap=6, per_voice=2)
    assert [a.key for a in chosen] == [dated.key, undated.key]


def test_a_syndicated_copy_never_takes_its_own_slot():
    original = article("orig", "haidt", 5, url="https://theatlantic.com/x")
    copy = article("copy", "haidt", 3, url="https://nationalpost.com/x", primary=False)
    chosen = select_following([original, copy], cap=6, per_voice=2)
    assert [a.canonical_url for a in chosen] == ["https://theatlantic.com/x"]


def test_an_unattributed_article_is_not_followed_material():
    orphan = article("a", "haidt", 1)
    orphan.attributions = []
    assert select_following([orphan], cap=6, per_voice=2) == []


def test_a_cap_of_zero_yields_nothing():
    assert select_following([article("a", "haidt", 1)], cap=0, per_voice=2) == []


# --- duplicate suppression against the ordinary desk ----------------------

def test_a_piece_the_editor_also_picked_is_shown_once():
    followed = [article("a", "haidt", 1, url="https://afterbabel.com/p/attention")]
    remaining = suppress_duplicates(followed, ["https://www.afterbabel.com/p/attention?utm_source=x"])
    assert remaining == []


def test_suppression_matches_on_identity_not_raw_link():
    followed = [article("a", "haidt", 1, url="https://theguardian.com/commentisfree/2026/sep/05/rivers")]
    edition = ["https://amp.theguardian.com/commentisfree/2026/sep/05/rivers/amp/?CMP=share"]
    assert suppress_duplicates(followed, edition) == []


def test_suppression_leaves_unrelated_pieces_alone():
    followed = [article("a", "haidt", 1, url="https://afterbabel.com/p/attention")]
    assert len(suppress_duplicates(followed, ["https://afterbabel.com/p/something-else"])) == 1


def test_suppression_with_an_empty_edition_is_a_no_op():
    followed = [article("a", "haidt", 1)]
    assert suppress_duplicates(followed, []) == followed

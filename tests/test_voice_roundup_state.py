from __future__ import annotations

import datetime as dt
import json

from src.voices.roundup_state import (
    MAX_PUBLICATION,
    MAX_TITLE,
    MAX_URL,
    STATUS_PENDING,
    RoundupState,
    load_state,
    state_from_text,
)

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 13, 21, 30, tzinfo=UTC)


def observe(
    state: RoundupState,
    key: str = "url:https://example.com/a",
    *,
    keys=(),
    voices=("core-a",),
    first_seen=NOW,
    published_at=None,
    title="A useful essay",
    url="https://example.com/a",
    publication="Example",
    surfaced=None,
):
    return state.observe(
        key=key,
        keys={key, *keys},
        voice_ids=voices,
        first_seen=first_seen,
        published_at=published_at or (NOW - dt.timedelta(hours=2)),
        title=title,
        url=url,
        publication=publication,
        first_morning_surfaced_at=surfaced,
    )


def trusted_state() -> RoundupState:
    return RoundupState(collecting_since=NOW - dt.timedelta(days=8))


def test_roundtrip_is_deterministic_and_stores_only_bounded_public_metadata(tmp_path):
    state = trusted_state()
    observe(
        state,
        keys=("pid:provider:1", "syn:essay|voice:core-a|2026-09-13"),
        title="A" * 500,
        publication="P" * 300,
        url="https://example.com/" + "x" * 900,
    )
    state.claim_period(
        "2026-09-13",
        cutoff=NOW,
        claimed_at=NOW,
        selection_keys=["url:https://example.com/a"],
        status=STATUS_PENDING,
    )

    first = state.dumps()
    second = state.dumps()
    assert first == second
    data = json.loads(first)
    item = next(iter(data["items"].values()))
    assert len(item["title"]) == MAX_TITLE
    assert len(item["publication"]) == MAX_PUBLICATION
    assert len(item["url"]) <= MAX_URL
    forbidden = {"body", "description", "summary", "image", "read", "unread"}
    assert forbidden.isdisjoint(item)

    path = tmp_path / "state.json"
    path.write_text(first, encoding="utf-8")
    loaded = load_state(path)
    assert not loaded.untrusted
    assert loaded.dumps() == first


def test_observe_matches_secondary_key_and_unions_identity_and_voice_ids():
    state = trusted_state()
    first, changed = observe(
        state,
        keys=("pid:provider:123",),
        voices=("core-a",),
    )
    assert changed

    second, changed = observe(
        state,
        key="url:https://mirror.example/b",
        keys=("pid:provider:123", "reprint:group-1"),
        voices=("core-b",),
        url="https://mirror.example/b",
    )
    assert changed
    assert second is first
    assert len(state.items) == 1
    assert set(second.voice_ids) == {"core-a", "core-b"}
    assert "reprint:group-1" in second.keys


def test_metadata_enrichment_is_order_independent():
    a = trusted_state()
    b = trusted_state()
    kwargs1 = dict(
        title="Short",
        publication="Example",
        url="https://example.com/a?utm_source=x",
    )
    kwargs2 = dict(
        title="A much more descriptive headline",
        publication="Example Publication",
        url="https://example.com/a",
    )

    observe(a, **kwargs1)
    observe(a, **kwargs2)
    observe(b, **kwargs2)
    observe(b, **kwargs1)

    assert next(iter(a.items.values())).as_dict() == next(iter(b.items.values())).as_dict()


def test_first_seen_and_morning_surface_are_sticky_earliest_values():
    state = trusted_state()
    later = NOW
    earlier = NOW - dt.timedelta(hours=5)
    surfaced_later = NOW - dt.timedelta(hours=1)
    surfaced_earlier = NOW - dt.timedelta(hours=3)

    observe(state, first_seen=later, surfaced=surfaced_later)
    item, _ = observe(state, first_seen=earlier, surfaced=surfaced_earlier)

    assert item.first_seen == earlier
    assert item.first_morning_surfaced_at == surfaced_earlier


def test_mark_morning_urls_uses_canonical_url_equivalence():
    state = trusted_state()
    observe(state, url="https://www.example.com/a?utm_source=mail")

    changed = state.mark_morning_urls({"https://example.com/a"}, NOW)

    assert changed == 1
    assert next(iter(state.items.values())).first_morning_surfaced_at == NOW
    assert state.mark_morning_urls({"https://example.com/a"}, NOW + dt.timedelta(hours=1)) == 0


def test_prune_enforces_retention_and_hard_cap():
    state = trusted_state()
    observe(
        state,
        key="url:https://example.com/old",
        url="https://example.com/old",
        first_seen=NOW - dt.timedelta(days=20),
    )
    for index in range(6):
        observe(
            state,
            key=f"url:https://example.com/{index}",
            url=f"https://example.com/{index}",
            first_seen=NOW - dt.timedelta(hours=index),
        )

    dropped = state.prune(NOW, retention=dt.timedelta(days=14), max_entries=3)

    assert dropped == 4
    assert len(state.items) == 3
    assert "url:https://example.com/old" not in state.items


def test_one_last_roundup_record_is_overwritten_by_next_period_only():
    state = trusted_state()
    first = state.claim_period(
        "2026-09-13", cutoff=NOW, claimed_at=NOW, selection_keys=["a"], status=STATUS_PENDING
    )
    same = state.claim_period(
        "2026-09-13",
        cutoff=NOW,
        claimed_at=NOW + dt.timedelta(hours=1),
        selection_keys=["b"],
        status=STATUS_PENDING,
    )
    assert same is first
    assert same.selection_keys == ("a",)

    next_claim = state.claim_period(
        "2026-09-20",
        cutoff=NOW + dt.timedelta(days=7),
        claimed_at=NOW + dt.timedelta(days=7),
        selection_keys=["c"],
        status=STATUS_PENDING,
    )
    assert state.last_roundup is next_claim
    assert next_claim.period_id == "2026-09-20"


def test_missing_state_is_cold_and_corrupt_state_recovers_silently(tmp_path):
    missing = load_state(tmp_path / "missing.json")
    assert missing.cold and missing.untrusted

    corrupt = state_from_text("{not json")
    assert corrupt.recovered and corrupt.untrusted


def test_partially_bad_state_retains_valid_entries_but_is_untrusted():
    state = trusted_state()
    observe(state)
    data = json.loads(state.dumps())
    data["items"]["broken"] = {"first_seen": "nope"}

    recovered = state_from_text(json.dumps(data))

    assert recovered.recovered
    assert recovered.untrusted
    assert "url:https://example.com/a" in recovered.items

from __future__ import annotations

import datetime as dt
import inspect
import json
from pathlib import Path

from src.voices.discover import DiscoveryResult, SourceStatus
from src.voices.model import Attribution, VoiceArticle
from src.voices.notify import NotifyError, RecordingNotifier
from src.voices.registry import (
    Registry,
    TIER_CORE,
    TIER_DISCOVERY,
    TIER_SELECTIVE,
    Voice,
)
from src.voices.roundup import (
    MODE_FREQUENT,
    SKIP_ALREADY_CLAIMED,
    SKIP_OUTSIDE_GRACE,
    _valid_observations,
    automatic_period,
    build_roundup_alert,
    collect_daily,
    core_registry,
    eligible_items,
    morning_edition_urls,
    period_for_id,
    publish_weekly,
    render_roundup,
    select_weekly,
)
from src.voices.roundup_state import (
    STATUS_FAILED,
    STATUS_PENDING,
    FileRoundupStore,
    RoundupState,
    RoundupStore,
    state_from_text,
)

UTC = dt.timezone.utc
PUBLISH_NOW = dt.datetime(2026, 9, 13, 22, 0, tzinfo=UTC)
PERIOD = period_for_id("2026-09-13")


def registry() -> Registry:
    return Registry(
        voices=(
            Voice(id="core-a", name="Core Alpha", tier=TIER_CORE, enabled=True, notify=False),
            Voice(id="core-b", name="Core Beta", tier=TIER_CORE, enabled=True, notify=False),
            Voice(id="core-c", name="Core Gamma", tier=TIER_CORE, enabled=False, notify=False),
            Voice(
                id="selective",
                name="Selective Writer",
                tier=TIER_SELECTIVE,
                enabled=True,
                notify=True,
            ),
            Voice(
                id="discovery",
                name="Discovery Writer",
                tier=TIER_DISCOVERY,
                enabled=True,
                notify=True,
            ),
        )
    )


def article(
    key: str,
    voice_ids=("core-a",),
    *,
    when=PUBLISH_NOW - dt.timedelta(hours=2),
    title=None,
    url=None,
    publication="Example",
) -> VoiceArticle:
    link = url or f"https://example.com/{key}"
    return VoiceArticle(
        key=f"url:{link}",
        title=title or f"Essay {key}",
        canonical_url=link,
        url=link,
        publication=publication,
        published_at=when,
        identity_keys=frozenset({f"url:{link}"}),
        attributions=[
            Attribution(voice_id, "byline_alias", voice_id)
            for voice_id in voice_ids
        ],
    )


def trusted_state() -> RoundupState:
    return RoundupState(collecting_since=PERIOD.start - dt.timedelta(hours=1))


def add_item(
    state: RoundupState,
    key: str,
    voice_ids=("core-a",),
    *,
    published=PUBLISH_NOW - dt.timedelta(hours=2),
    surfaced=None,
    title=None,
    publication="Example",
):
    link = f"https://example.com/{key}"
    item, _ = state.observe(
        key=f"url:{link}",
        keys={f"url:{link}"},
        voice_ids=voice_ids,
        first_seen=published + dt.timedelta(minutes=5),
        published_at=published,
        title=title or f"Essay {key}",
        url=link,
        publication=publication,
        first_morning_surfaced_at=surfaced,
    )
    return item


def write_state(path: Path, state: RoundupState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.dumps(), encoding="utf-8")


def test_core_tier_is_the_only_roundup_membership_authority():
    reg = registry()
    assert {voice.id for voice in core_registry(reg).voices} == {"core-a", "core-b", "core-c"}

    state = trusted_state()
    add_item(state, "core", ("core-a",))
    add_item(state, "disabled-core", ("core-c",))
    add_item(state, "selective", ("selective",))
    add_item(state, "discovery", ("discovery",))

    keys = {item.key for item in eligible_items(state, reg, PERIOD)}

    assert "url:https://example.com/core" in keys
    assert "url:https://example.com/disabled-core" in keys
    assert "url:https://example.com/selective" not in keys
    assert "url:https://example.com/discovery" not in keys


def test_shared_results_retain_only_core_attributions():
    reg = registry()
    mixed = article("mixed", ("core-a", "selective"))
    selective_only = article("selective-only", ("selective",))
    result = DiscoveryResult(
        articles=[mixed, selective_only],
        fresh=[mixed, selective_only],
    )

    observations = _valid_observations(result, reg)

    assert len(observations) == 1
    assert observations[0][1] == ("core-a",)


def test_selection_is_breadth_first_and_never_exceeds_two_per_voice():
    state = trusted_state()
    reg = registry()
    add_item(state, "a1", ("core-a",), published=PUBLISH_NOW - dt.timedelta(minutes=10))
    add_item(state, "a2", ("core-a",), published=PUBLISH_NOW - dt.timedelta(minutes=20))
    add_item(state, "a3", ("core-a",), published=PUBLISH_NOW - dt.timedelta(minutes=30))
    add_item(state, "b1", ("core-b",), published=PUBLISH_NOW - dt.timedelta(hours=4))
    add_item(state, "c1", ("core-c",), published=PUBLISH_NOW - dt.timedelta(hours=5))

    selected = select_weekly(state, reg, PERIOD)

    keys = {item.key.rsplit("/", 1)[-1] for item in selected}
    assert keys == {"a1", "a2", "b1", "c1"}
    assert "a3" not in keys


def test_selection_caps_at_six_distinct_voices_before_depth():
    voices = tuple(
        Voice(id=f"core-{i}", name=f"Core Writer {i}", tier=TIER_CORE)
        for i in range(8)
    )
    reg = Registry(voices=voices)
    state = trusted_state()
    for i in range(8):
        add_item(
            state,
            f"v{i}",
            (f"core-{i}",),
            published=PUBLISH_NOW - dt.timedelta(minutes=i),
        )

    selected = select_weekly(state, reg, PERIOD)

    assert len(selected) == 6
    assert len({item.voice_ids[0] for item in selected}) == 6


def test_unsurfaced_work_is_preferred_within_a_voice_before_freshness():
    state = trusted_state()
    reg = registry()
    surfaced = add_item(
        state,
        "new-surfaced",
        ("core-a",),
        published=PUBLISH_NOW - dt.timedelta(minutes=5),
        surfaced=PUBLISH_NOW - dt.timedelta(minutes=2),
    )
    missed = add_item(
        state,
        "older-missed",
        ("core-a",),
        published=PUBLISH_NOW - dt.timedelta(hours=3),
    )

    selected = select_weekly(state, reg, PERIOD, cap=1, max_per_voice=1)

    assert selected == [missed]
    assert surfaced not in selected


def test_multi_author_piece_counts_toward_each_core_voice_cap():
    state = trusted_state()
    reg = registry()
    shared = add_item(state, "shared", ("core-a", "core-b"))
    add_item(state, "a2", ("core-a",), published=PUBLISH_NOW - dt.timedelta(hours=1))
    add_item(state, "b2", ("core-b",), published=PUBLISH_NOW - dt.timedelta(hours=2))
    add_item(state, "a3", ("core-a",), published=PUBLISH_NOW - dt.timedelta(hours=3))
    add_item(state, "b3", ("core-b",), published=PUBLISH_NOW - dt.timedelta(hours=4))

    selected = select_weekly(state, reg, PERIOD)

    assert shared in selected
    counts = {"core-a": 0, "core-b": 0}
    for item in selected:
        for voice_id in item.voice_ids:
            if voice_id in counts:
                counts[voice_id] += 1
    assert counts["core-a"] <= 2
    assert counts["core-b"] <= 2


def test_period_uses_toronto_calendar_boundaries_across_dst():
    fall = period_for_id("2026-11-01")
    spring = period_for_id("2026-03-08")

    assert fall.cutoff == dt.datetime(2026, 11, 1, 22, 0, tzinfo=UTC)
    assert fall.start == dt.datetime(2026, 10, 25, 21, 0, tzinfo=UTC)
    assert fall.cutoff - fall.start == dt.timedelta(hours=169)

    assert spring.cutoff == dt.datetime(2026, 3, 8, 21, 0, tzinfo=UTC)
    assert spring.start == dt.datetime(2026, 3, 1, 22, 0, tzinfo=UTC)
    assert spring.cutoff - spring.start == dt.timedelta(hours=167)


def test_automatic_period_recovers_same_sunday_on_monday_but_not_midweek():
    sunday = automatic_period(dt.datetime(2026, 9, 13, 22, 43, tzinfo=UTC))
    monday = automatic_period(dt.datetime(2026, 9, 14, 22, 43, tzinfo=UTC))
    late_monday = automatic_period(dt.datetime(2026, 9, 15, 2, 30, tzinfo=UTC))
    wednesday = automatic_period(dt.datetime(2026, 9, 16, 22, 0, tzinfo=UTC))

    assert sunday and sunday.period_id == "2026-09-13"
    assert monday and monday.period_id == "2026-09-13"
    assert late_monday is None
    assert wednesday is None


def test_out_of_period_and_pre_baseline_items_are_ineligible():
    state = trusted_state()
    reg = registry()
    add_item(state, "old", published=PERIOD.start - dt.timedelta(minutes=1))
    add_item(state, "new", published=PERIOD.cutoff + dt.timedelta(minutes=1))
    add_item(state, "inside", published=PERIOD.start + dt.timedelta(hours=2))
    state.collecting_since = PERIOD.start + dt.timedelta(hours=3)

    assert eligible_items(state, reg, PERIOD) == []


def test_morning_edition_signal_reads_only_current_committed_artifact(tmp_path):
    now = dt.datetime(2026, 9, 9, 16, 0, tzinfo=UTC)
    edition = {
        "date": "Wednesday, September 9, 2026",
        "following": [{"link": "https://example.com/follow"}],
        "sections": [{"id": "front", "stories": [{"link": "https://example.com/front"}]}],
    }
    path = tmp_path / "index.html"
    path.write_text(
        '<script id="edition" type="application/json">'
        + json.dumps(edition)
        + "</script>",
        encoding="utf-8",
    )

    assert morning_edition_urls(path, now=now) == {
        "https://example.com/follow",
        "https://example.com/front",
    }

    edition["date"] = "Tuesday, September 8, 2026"
    path.write_text(
        '<script id="edition" type="application/json">'
        + json.dumps(edition)
        + "</script>",
        encoding="utf-8",
    )
    assert morning_edition_urls(path, now=now) is None


def test_daily_collection_api_cannot_accept_a_notifier():
    assert "notifier" not in inspect.signature(collect_daily).parameters


def test_daily_overlap_upserts_without_duplicate_state(monkeypatch, tmp_path):
    reg = registry()
    art = article("daily")
    result = DiscoveryResult(
        articles=[art],
        fresh=[art],
        statuses=[SourceStatus("rss", "core feed", ("rss:key",), True, items=1)],
    )

    def fake_discover(*args, **kwargs):
        return result, 1, MODE_FREQUENT

    monkeypatch.setattr("src.voices.roundup.discover_core", fake_discover)
    state_path = tmp_path / "state.json"
    store = FileRoundupStore(state_path)

    first = collect_daily(reg, store=store, now=PUBLISH_NOW, edition_path=tmp_path / "none")
    second = collect_daily(
        reg,
        store=store,
        now=PUBLISH_NOW + dt.timedelta(hours=1),
        edition_path=tmp_path / "none",
    )

    assert first.baseline
    assert first.observed == 1
    assert second.observed == 1
    assert second.changed == 0
    assert len(state_from_text(state_path.read_text(encoding="utf-8")).items) == 1


def test_all_source_failure_does_not_establish_false_baseline(monkeypatch, tmp_path):
    result = DiscoveryResult(
        statuses=[SourceStatus("rss", "dead feed", ("rss:key",), False, error="down")]
    )

    def fake_discover(*args, **kwargs):
        return result, 1, MODE_FREQUENT

    monkeypatch.setattr("src.voices.roundup.discover_core", fake_discover)
    state_path = tmp_path / "state.json"

    outcome = collect_daily(
        registry(),
        store=FileRoundupStore(state_path),
        now=PUBLISH_NOW,
        edition_path=tmp_path / "none",
    )

    assert outcome.exit_code == 1
    assert not state_path.exists()


def test_rendered_page_is_restrained_and_contains_direct_links():
    state = trusted_state()
    reg = registry()
    first = add_item(state, "one", ("core-a",), publication="Example Review")
    second = add_item(state, "two", ("core-b",), publication="Another Review")

    page = render_roundup(PERIOD, [first, second], reg)

    assert "Voices this week" in page
    assert "A few pieces worth catching up on." in page
    assert "https://example.com/one" in page
    assert "Open original" in page
    assert "min-height:44px" in page
    for forbidden in ("Load more", "Unread", "Archive", "Recommendations", "Dashboard"):
        assert forbidden not in page


def test_notification_is_one_compact_roundup_link(monkeypatch):
    state = trusted_state()
    reg = registry()
    items = [
        add_item(state, "one", ("core-a",)),
        add_item(state, "two", ("core-b",)),
        add_item(state, "three", ("core-c",)),
    ]
    monkeypatch.setattr("src.config.SITE_URL", "https://example.test/Hermes/")

    alert = build_roundup_alert(items, reg)
    payload = alert.as_payload("topic")

    assert alert.title == "Voices this week"
    assert alert.click == "https://example.test/Hermes/voices/"
    assert "3 pieces from" in alert.message
    assert payload["priority"] == 3
    assert payload["tags"] == ["memo"]


def test_first_weekly_run_publishes_then_notifies_once(tmp_path):
    reg = registry()
    state = trusted_state()
    add_item(state, "one", ("core-a",))
    state_path = tmp_path / "state.json"
    page_path = tmp_path / "voices" / "index.html"
    write_state(state_path, state)
    store = FileRoundupStore(state_path)
    notifier = RecordingNotifier()

    first = publish_weekly(
        reg,
        store=store,
        notifier=notifier,
        now=PUBLISH_NOW,
        page_path=page_path,
        edition_path=tmp_path / "missing",
        fetch=False,
    )
    second = publish_weekly(
        reg,
        store=store,
        notifier=notifier,
        now=PUBLISH_NOW + dt.timedelta(minutes=30),
        page_path=page_path,
        edition_path=tmp_path / "missing",
        fetch=False,
    )

    assert first.published and first.notified
    assert page_path.exists()
    assert len(notifier.sent) == 1
    assert second.skipped == SKIP_ALREADY_CLAIMED
    assert len(notifier.sent) == 1


def test_zero_item_week_publishes_dated_empty_page_and_sends_nothing(tmp_path):
    state = trusted_state()
    state_path = tmp_path / "state.json"
    page_path = tmp_path / "voices" / "index.html"
    write_state(state_path, state)
    notifier = RecordingNotifier()

    outcome = publish_weekly(
        registry(),
        store=FileRoundupStore(state_path),
        notifier=notifier,
        now=PUBLISH_NOW,
        page_path=page_path,
        edition_path=tmp_path / "missing",
        fetch=False,
    )

    assert outcome.published and outcome.empty
    assert not notifier.sent
    assert "No Core Voice pieces" in page_path.read_text(encoding="utf-8")


def test_incomplete_baseline_claims_period_suppressed_without_notification(tmp_path):
    state = RoundupState(collecting_since=PERIOD.start + dt.timedelta(days=2))
    add_item(state, "one")
    state_path = tmp_path / "state.json"
    page_path = tmp_path / "voices" / "index.html"
    write_state(state_path, state)
    notifier = RecordingNotifier()

    outcome = publish_weekly(
        registry(),
        store=FileRoundupStore(state_path),
        notifier=notifier,
        now=PUBLISH_NOW,
        page_path=page_path,
        edition_path=tmp_path / "missing",
        fetch=False,
    )

    assert outcome.published and outcome.suppressed
    assert not notifier.sent
    assert "baseline was re-established" in page_path.read_text(encoding="utf-8")


class LosingStore(RoundupStore):
    def __init__(self, state: RoundupState):
        self.remote = state.dumps()
        self.publish_calls = 0

    def load(self):
        return state_from_text(self.remote)

    def save_state(self, state, message: str) -> bool:
        return False

    def publish(self, state, page_html: str, page_path, message: str) -> bool:
        self.publish_calls += 1
        return False


def test_lost_publish_race_sends_nothing():
    state = trusted_state()
    add_item(state, "one")
    store = LosingStore(state)
    notifier = RecordingNotifier()

    outcome = publish_weekly(
        registry(),
        store=store,
        notifier=notifier,
        now=PUBLISH_NOW,
        fetch=False,
        push_attempts=2,
    )

    assert not outcome.published
    assert store.publish_calls == 2
    assert not notifier.sent


class WinnerAfterRaceStore(LosingStore):
    def publish(self, state, page_html: str, page_path, message: str) -> bool:
        self.publish_calls += 1
        if self.publish_calls == 1:
            winner = state_from_text(self.remote)
            winner.claim_period(
                PERIOD.period_id,
                cutoff=PERIOD.cutoff,
                claimed_at=PUBLISH_NOW,
                selection_keys=["url:https://example.com/one"],
                status=STATUS_PENDING,
            )
            self.remote = winner.dumps()
        return False


def test_overlapping_winner_claim_stops_loser_before_notification():
    state = trusted_state()
    add_item(state, "one")
    store = WinnerAfterRaceStore(state)
    notifier = RecordingNotifier()

    outcome = publish_weekly(
        registry(),
        store=store,
        notifier=notifier,
        now=PUBLISH_NOW,
        fetch=False,
        push_attempts=3,
    )

    assert outcome.skipped == SKIP_ALREADY_CLAIMED
    assert not notifier.sent


class PublishThenOutcomeWriteFails(RoundupStore):
    def __init__(self, state: RoundupState):
        self.remote = state.dumps()

    def load(self):
        return state_from_text(self.remote)

    def save_state(self, state, message: str) -> bool:
        return False

    def publish(self, state, page_html: str, page_path, message: str) -> bool:
        self.remote = state.dumps()
        return True


def test_delivery_outcome_write_failure_cannot_reopen_period():
    state = trusted_state()
    add_item(state, "one")
    store = PublishThenOutcomeWriteFails(state)
    notifier = RecordingNotifier()

    first = publish_weekly(
        registry(), store=store, notifier=notifier, now=PUBLISH_NOW, fetch=False
    )
    second = publish_weekly(
        registry(),
        store=store,
        notifier=notifier,
        now=PUBLISH_NOW + dt.timedelta(minutes=20),
        fetch=False,
    )

    assert first.notified
    assert len(notifier.sent) == 1
    assert second.skipped == SKIP_ALREADY_CLAIMED
    assert len(notifier.sent) == 1


class FailingNotifier:
    def send(self, alert):
        raise NotifyError("ambiguous network failure")


def test_ntfy_failure_is_terminal_for_period(tmp_path):
    state = trusted_state()
    add_item(state, "one")
    state_path = tmp_path / "state.json"
    page_path = tmp_path / "voices" / "index.html"
    write_state(state_path, state)
    store = FileRoundupStore(state_path)

    first = publish_weekly(
        registry(),
        store=store,
        notifier=FailingNotifier(),
        now=PUBLISH_NOW,
        page_path=page_path,
        edition_path=tmp_path / "missing",
        fetch=False,
    )
    second_recorder = RecordingNotifier()
    second = publish_weekly(
        registry(),
        store=store,
        notifier=second_recorder,
        now=PUBLISH_NOW + dt.timedelta(minutes=5),
        page_path=page_path,
        edition_path=tmp_path / "missing",
        fetch=False,
    )

    assert first.notify_failed
    assert state_from_text(state_path.read_text(encoding="utf-8")).last_roundup.status == STATUS_FAILED
    assert second.skipped == SKIP_ALREADY_CLAIMED
    assert not second_recorder.sent


def test_automatic_weekly_run_outside_grace_stops_before_store_or_network():
    class ExplodingStore(RoundupStore):
        def load(self):
            raise AssertionError("store should not be touched")

    outcome = publish_weekly(
        registry(),
        store=ExplodingStore(),
        notifier=RecordingNotifier(),
        now=dt.datetime(2026, 9, 16, 20, 0, tzinfo=UTC),
    )

    assert outcome.skipped == SKIP_OUTSIDE_GRACE

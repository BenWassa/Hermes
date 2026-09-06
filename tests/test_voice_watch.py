"""The release-time watcher, tested at its operational failure boundaries.

Happy-path parsing is already covered by the adapter and dedupe suites. What
matters here is what happens when a run is repeated, interrupted, raced,
partially broken, or handed state it cannot trust, because those are the
conditions under which a notification system sends the same thing twice.

Every test drives the real ``run_watch`` through the real adapters against
recorded feed content. Only three things are doubles: the HTTP client, the
state store (so a lost push race can be staged deterministically) and the
notifier.
"""

from __future__ import annotations

import datetime as dt

import pytest

from tests.conftest import FakeHttp, FakeNotifier, FakeResponse, FakeStore, registry_from, rss_feed
from src import config
from src.voices.http import RequestBudget
from src.voices.state import (
    STATUS_ADOPTED,
    STATUS_FAILED,
    STATUS_NOTIFIED,
    STATUS_PENDING,
    STATUS_SUPPRESSED,
)
from src.voices.watch import (
    MODE_FREQUENT,
    MODE_RECONCILE,
    SKIP_NO_VOICES,
    SKIP_QUIET_HOURS,
    in_quiet_hours,
    provider_cadence,
    reconcile_due,
    run_watch,
)

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 5, 18, 0, tzinfo=UTC)
YESTERDAY = "Fri, 05 Sep 2026 12:00:00 +0000"

BABEL_FEED = "https://www.afterbabel.com/feed"
PETERSON_FEED = "https://drjordanbpeterson.substack.com/feed"


# --- registries and sources ----------------------------------------------

def babel_voice(**overrides) -> dict:
    """A multi-author publication feed: authorship must come from the byline."""
    voice = {
        "id": "jonathan-haidt",
        "name": "Jonathan Haidt",
        "aliases": ["Jon Haidt"],
        "sources": [{
            "id": "after-babel", "type": "rss", "url": BABEL_FEED,
            "publication": "After Babel", "authorship": "byline",
        }],
    }
    voice.update(overrides)
    return voice


def peterson_voice(**overrides) -> dict:
    """A personal newsletter: the source itself is the proof of authorship."""
    voice = {
        "id": "jordan-peterson",
        "name": "Jordan Peterson",
        "sources": [{
            "id": "jbp", "type": "rss", "url": PETERSON_FEED,
            "publication": "Jordan B Peterson", "authorship": "scope",
        }],
    }
    voice.update(overrides)
    return voice


def babel_entry(title: str, slug: str, *, author: str = "Jonathan Haidt", published: str = YESTERDAY) -> dict:
    return {
        "title": title,
        "link": f"https://www.afterbabel.com/p/{slug}",
        "author": author,
        "published": published,
    }


def routes(**feeds) -> dict:
    """Map a feed URL to its content, or to an exception to break that source."""
    table = {}
    for key, value in feeds.items():
        url = {"babel": BABEL_FEED, "peterson": PETERSON_FEED}[key]
        table[url] = value if isinstance(value, Exception) else FakeResponse(text=value)
    return table


def watch(registry, store, notifier, http, **kwargs):
    """``run_watch`` with the deterministic knobs pinned."""
    params = dict(
        now=NOW,
        quiet_hours=None,
        lookback=dt.timedelta(hours=24),
        retention=dt.timedelta(days=14),
        max_entries=500,
        max_alerts=5,
        reconcile_every=dt.timedelta(hours=24),
        push_attempts=3,
    )
    params.update(kwargs)
    return run_watch(registry, store=store, notifier=notifier, http=http, **params)


@pytest.fixture
def haidt():
    return registry_from([babel_voice()])


def seeded_store() -> FakeStore:
    """A store holding valid but empty state, so a run is not a cold start."""
    from src.voices.state import WatchState

    state = WatchState(last_reconcile_at=NOW - dt.timedelta(hours=1), updated_at=NOW)
    return FakeStore(state.dumps())


# =========================================================================
# First discovery, reruns, and retries
# =========================================================================

def test_first_discovery_of_an_article_sends_exactly_one_alert(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(babel=rss_feed([babel_entry("Treasure Your Attention", "attention")])))

    outcome = watch(haidt, store, notifier, http)

    assert outcome.delivered == 1
    assert notifier.messages == ["Treasure Your Attention"]
    alert = notifier.sent[0]
    assert alert.title == "Jonathan Haidt — After Babel"
    assert alert.click == "https://www.afterbabel.com/p/attention"  # the publisher's own URL
    assert list(store.statuses().values()) == [STATUS_NOTIFIED]


def test_alert_copy_carries_no_urgency_or_engagement_furniture(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(babel=rss_feed([babel_entry("Treasure Your Attention", "attention")])))

    watch(haidt, store, notifier, http)

    payload = notifier.sent[0].as_payload("topic")
    assert payload["priority"] == 3
    text = f"{payload['title']} {payload['message']}"
    for banned in ("BREAKING", "URGENT", "!!", "NEW ", "unread", "🚨"):
        assert banned not in text
    assert set(payload) <= {"topic", "title", "message", "priority", "tags", "click"}


def test_an_immediate_rerun_of_the_same_input_sends_nothing_more(haidt):
    """The idempotency contract, in its simplest form."""
    store, notifier = seeded_store(), FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])

    watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))
    first = len(notifier.sent)
    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert first == 1
    assert len(notifier.sent) == 1
    assert outcome.delivered == 0
    assert outcome.candidates == 1  # it was found again, and recognised


def test_ten_reruns_still_send_one_alert(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])

    for _ in range(10):
        watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert len(notifier.sent) == 1


def test_a_url_that_gains_tracking_parameters_is_not_a_new_article(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    watch(haidt, store, notifier,
          FakeHttp(routes(babel=rss_feed([babel_entry("Treasure Your Attention", "attention")]))))

    tracked = babel_entry("Treasure Your Attention", "attention")
    tracked["link"] += "?utm_source=twitter&ref=share"
    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([tracked]))))

    assert len(notifier.sent) == 1


def test_a_retry_after_a_partial_execution_does_not_re_alert(haidt):
    """The crash case: the claim was pushed, the send never happened.

    The next run must treat the claim as binding. Re-alerting a pending entry
    would be exactly the duplicate the claim-first ordering exists to prevent.
    """
    store, notifier = seeded_store(), FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])

    class DiesAfterClaiming(FakeNotifier):
        def send(self, alert):
            raise KeyboardInterrupt("runner cancelled mid-send")

    with pytest.raises(KeyboardInterrupt):
        watch(haidt, store, DiesAfterClaiming(), FakeHttp(routes(babel=feed)))

    assert list(store.statuses().values()) == [STATUS_PENDING]

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert outcome.delivered == 0
    assert notifier.sent == []
    assert list(store.statuses().values()) == [STATUS_PENDING]


# =========================================================================
# Duplicate discovery
# =========================================================================

def test_one_article_reachable_through_two_adapters_alerts_once(now):
    """Two Voices, two feeds, one syndicating link: still one reader-visible piece."""
    registry = registry_from([
        babel_voice(),
        {
            "id": "zach-rausch", "name": "Zach Rausch",
            "sources": [{
                "id": "mirror", "type": "rss", "url": PETERSON_FEED,
                "publication": "After Babel", "authorship": "byline",
            }],
        },
    ])
    entry = babel_entry("Treasure Your Attention", "attention")
    mirrored = dict(entry, author="Zach Rausch")
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(babel=rss_feed([entry]), peterson=rss_feed([mirrored])))

    outcome = watch(registry, store, notifier, http)

    assert outcome.candidates == 1
    assert len(notifier.sent) == 1
    assert len(store.state().entries) == 1


def test_the_second_adapter_discovering_a_piece_on_a_later_run_is_silent(haidt):
    """Perigon's daily reconciliation must not re-announce yesterday's feed item."""
    from src.voices.state import state_from_text

    store, notifier = seeded_store(), FakeNotifier()
    watch(haidt, store, notifier,
          FakeHttp(routes(babel=rss_feed([babel_entry("Treasure Your Attention", "attention")]))))

    # The same canonical URL arrives again, this time with a provider id
    # attached, as an aggregator would deliver it.
    same_url = babel_entry("Treasure Your Attention", "attention")
    same_url["guid"] = "https://www.afterbabel.com/p/attention"
    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([same_url]))))

    assert len(notifier.sent) == 1
    assert len(state_from_text(store.content).entries) == 1


def test_a_co_authored_piece_is_one_alert_naming_both_writers():
    registry = registry_from([
        babel_voice(),
        {
            "id": "zach-rausch", "name": "Zach Rausch",
            "byline_publications": ["afterbabel.com"],
            "sources": [{
                "id": "babel-shared", "type": "rss", "url": BABEL_FEED,
                "publication": "After Babel", "authorship": "byline",
            }],
        },
    ])
    entry = babel_entry("The Anxious Generation", "anxious", author="Jonathan Haidt and Zach Rausch")
    store, notifier = seeded_store(), FakeNotifier()

    outcome = watch(registry, store, notifier, FakeHttp(routes(babel=rss_feed([entry]))))

    assert outcome.delivered == 1
    assert notifier.sent[0].title == "Jonathan Haidt & Zach Rausch — After Babel"
    assert store.state().entries[notifier.sent[0].article_key].voice_ids == (
        "jonathan-haidt", "zach-rausch",
    )


# =========================================================================
# Syndication and reprints
# =========================================================================

def _syndicating_registry() -> object:
    """One Voice publishing the same column on two hosts."""
    return registry_from([{
        "id": "conrad-black",
        "name": "Conrad Black",
        "sources": [
            {"id": "sun", "type": "rss", "url": BABEL_FEED,
             "publication": "The New York Sun", "authorship": "scope"},
            {"id": "post", "type": "rss", "url": PETERSON_FEED,
             "publication": "National Post", "authorship": "scope"},
        ],
    }])


def _copy(host: str) -> dict:
    return {
        "title": "The Case For Parliament",
        "link": f"https://{host}/article/the-case-for-parliament",
        "published": YESTERDAY,
    }


def test_two_publishers_running_one_column_in_the_same_pass_alert_once():
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(
        babel=rss_feed([_copy("www.nysun.com")], title="The New York Sun"),
        peterson=rss_feed([_copy("nationalpost.com")], title="National Post"),
    ))

    outcome = watch(_syndicating_registry(), store, notifier, http)

    assert outcome.delivered == 1
    assert len(notifier.sent) == 1


def test_a_reprint_discovered_on_a_later_run_does_not_alert_again():
    """Cross-run syndication: in-run grouping cannot see yesterday's alert,
    so the grouping keys are recorded in durable state alongside identity."""
    store, notifier = seeded_store(), FakeNotifier()

    watch(_syndicating_registry(), store, notifier,
          FakeHttp(routes(babel=rss_feed([_copy("www.nysun.com")], title="The New York Sun"),
                          peterson=rss_feed([]))))
    assert len(notifier.sent) == 1

    watch(_syndicating_registry(), store, notifier,
          FakeHttp(routes(babel=rss_feed([_copy("www.nysun.com")], title="The New York Sun"),
                          peterson=rss_feed([_copy("nationalpost.com")], title="National Post"))))

    assert len(notifier.sent) == 1
    assert notifier.sent[0].click == "https://www.nysun.com/article/the-case-for-parliament"


def test_a_genuinely_different_column_by_the_same_writer_still_alerts():
    """The syndication guard must not swallow the next piece."""
    store, notifier = seeded_store(), FakeNotifier()
    watch(_syndicating_registry(), store, notifier,
          FakeHttp(routes(babel=rss_feed([_copy("www.nysun.com")]), peterson=rss_feed([]))))

    second = {
        "title": "A Different Argument Entirely",
        "link": "https://www.nysun.com/article/a-different-argument",
        "published": YESTERDAY,
    }
    watch(_syndicating_registry(), store, notifier,
          FakeHttp(routes(babel=rss_feed([_copy("www.nysun.com"), second]), peterson=rss_feed([]))))

    assert len(notifier.sent) == 2


# =========================================================================
# Several new pieces, and the per-run cap
# =========================================================================

def test_several_new_pieces_each_get_their_own_alert(haidt):
    entries = [babel_entry(f"Essay {i}", f"essay-{i}") for i in range(3)]
    store, notifier = seeded_store(), FakeNotifier()

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))))

    assert outcome.delivered == 3
    assert sorted(notifier.messages) == ["Essay 0", "Essay 1", "Essay 2"]


def test_a_backlog_dump_is_capped_and_the_remainder_recorded_as_seen(haidt):
    """A finished paper does not buzz nine times; the rest go to the edition."""
    entries = [babel_entry(f"Essay {i}", f"essay-{i}") for i in range(9)]
    store, notifier = seeded_store(), FakeNotifier()

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))), max_alerts=3)

    assert outcome.delivered == 3
    assert outcome.suppressed == 6
    statuses = list(store.statuses().values())
    assert statuses.count(STATUS_NOTIFIED) == 3
    assert statuses.count(STATUS_SUPPRESSED) == 6


def test_suppressed_pieces_are_never_alerted_on_a_later_run(haidt):
    entries = [babel_entry(f"Essay {i}", f"essay-{i}") for i in range(5)]
    store, notifier = seeded_store(), FakeNotifier()
    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))), max_alerts=2)

    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))), max_alerts=2)

    assert len(notifier.sent) == 2


# =========================================================================
# Source failure
# =========================================================================

def test_one_broken_source_does_not_stop_the_others(now):
    registry = registry_from([babel_voice(), peterson_voice()])
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(
        babel=RuntimeError("feed 503"),
        peterson=rss_feed([{"title": "On Order", "link": "https://drjordanbpeterson.substack.com/p/order",
                            "published": YESTERDAY}]),
    ))

    outcome = watch(registry, store, notifier, http)

    assert outcome.delivered == 1
    assert notifier.messages == ["On Order"]
    assert [s.ok for s in outcome.statuses].count(False) == 1
    assert "feed 503" in outcome.failures[0].error
    assert outcome.exit_code == 0  # partial degradation is normal, not an alarm


def test_every_source_failing_sends_nothing_and_reports_a_blind_run(now):
    registry = registry_from([babel_voice(), peterson_voice()])
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(babel=RuntimeError("dns"), peterson=RuntimeError("timeout")))

    outcome = watch(registry, store, notifier, http)

    assert notifier.sent == []
    assert outcome.all_sources_failed
    assert outcome.exit_code == 1
    assert store.saves == []  # nothing changed, so nothing was committed


def test_a_source_outage_does_not_forget_what_was_already_alerted(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])
    watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    watch(haidt, store, notifier, FakeHttp(routes(babel=RuntimeError("down"))))
    watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert len(notifier.sent) == 1


# =========================================================================
# Notification and persistence failure
# =========================================================================

def test_a_failed_notification_is_recorded_and_never_retried(haidt):
    """The request may have reached ntfy before the error surfaced, so a retry
    is the one path that could produce a duplicate."""
    store = seeded_store()
    failing = FakeNotifier(fail_on=lambda alert: True)
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])

    outcome = watch(haidt, store, failing, FakeHttp(routes(babel=feed)))

    assert outcome.delivered == 0 and outcome.failed == 1
    assert list(store.statuses().values()) == [STATUS_FAILED]

    healthy = FakeNotifier()
    watch(haidt, store, healthy, FakeHttp(routes(babel=feed)))

    assert healthy.sent == []


def test_one_failed_alert_does_not_stop_the_rest(haidt):
    entries = [babel_entry(f"Essay {i}", f"essay-{i}") for i in range(3)]
    store = seeded_store()
    notifier = FakeNotifier(fail_on=lambda alert: alert.message == "Essay 1")

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))))

    assert outcome.delivered == 2 and outcome.failed == 1
    assert sorted(notifier.messages) == ["Essay 0", "Essay 2"]


def test_nothing_is_sent_when_the_claim_cannot_be_persisted(haidt):
    """Notifying against state that did not save is how retries duplicate."""
    store = FakeStore(seeded_store().content, reject=99)
    notifier = FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert notifier.sent == []
    assert outcome.persisted is False
    assert outcome.exit_code == 1
    assert outcome.claim_attempts == 3


def test_the_run_after_a_failed_persist_alerts_normally(haidt):
    """A lost claim delays an alert; it does not lose it."""
    content = seeded_store().content
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])
    notifier = FakeNotifier()

    watch(haidt, FakeStore(content, reject=99), notifier, FakeHttp(routes(babel=feed)))
    assert notifier.sent == []

    outcome = watch(haidt, FakeStore(content), notifier, FakeHttp(routes(babel=feed)))

    assert outcome.delivered == 1


def test_delivery_outcomes_failing_to_persist_does_not_re_alert(haidt):
    """The second write is bookkeeping. Losing it leaves entries pending,
    which is still a claim, which is still never re-alerted."""
    store = FakeStore(seeded_store().content, reject=0)
    notifier = FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])

    original_save = store.save
    calls = {"n": 0}

    def save(state, message):
        calls["n"] += 1
        if calls["n"] >= 2:   # the claim lands; the outcome write does not
            return False
        return original_save(state, message)

    store.save = save
    watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))
    assert len(notifier.sent) == 1
    assert list(store.statuses().values()) == [STATUS_PENDING]

    store.save = original_save
    watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert len(notifier.sent) == 1


def test_a_run_that_finds_nothing_new_writes_no_commit(haidt):
    """Repo-backed state is only worth it if it stays quiet: an hourly job
    that commits every hour is an hourly job that spams the history."""
    store, notifier = seeded_store(), FakeNotifier()
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])
    watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))
    store.saves.clear()

    for _ in range(5):
        watch(haidt, store, notifier, FakeHttp(routes(babel=feed)))

    assert store.saves == []


def test_a_run_with_no_qualifying_work_at_all_writes_no_commit(haidt):
    store, notifier = seeded_store(), FakeNotifier()

    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([]))))

    assert store.saves == []
    assert notifier.sent == []


def test_a_cold_start_always_establishes_a_baseline_even_with_nothing_to_adopt(haidt):
    """Otherwise the file never exists, every run is another cold start, and
    the watcher never alerts about anything."""
    store, notifier = FakeStore(None), FakeNotifier()

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([]))))

    assert outcome.adopted == 0
    assert len(store.saves) == 1
    assert not store.state().untrusted

    store.saves.clear()
    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([]))))
    assert store.saves == []


# =========================================================================
# Overlapping runs
# =========================================================================

def test_a_run_that_loses_the_push_race_drops_what_the_winner_claimed(haidt):
    """Two watchers find the same piece. Between them, one alert."""
    feed = rss_feed([babel_entry("Treasure Your Attention", "attention")])
    winner_notifier, loser_notifier = FakeNotifier(), FakeNotifier()
    content = seeded_store().content

    shared = {"content": content}

    def a_concurrent_run_lands_first(store, state, message):
        """Stage the winner's push arriving while this run is deciding."""
        if store.reject > 0:
            winner = FakeStore(shared["content"])
            watch(haidt, winner, winner_notifier, FakeHttp(routes(babel=feed)))
            shared["content"] = winner.content
            store.content = winner.content

    loser = FakeStore(content, reject=1, on_save=a_concurrent_run_lands_first)

    outcome = watch(haidt, loser, loser_notifier, FakeHttp(routes(babel=feed)))

    assert len(winner_notifier.sent) == 1
    assert loser_notifier.sent == []
    assert outcome.delivered == 0
    assert outcome.claim_attempts == 2


def test_a_run_that_loses_a_race_still_alerts_for_what_the_winner_missed(haidt):
    """The loser re-decides rather than standing down wholesale."""
    both = rss_feed([babel_entry("Essay A", "a"), babel_entry("Essay B", "b")])
    only_a = rss_feed([babel_entry("Essay A", "a")])
    content = seeded_store().content
    winner_notifier, loser_notifier = FakeNotifier(), FakeNotifier()

    def a_concurrent_run_lands_first(store, state, message):
        if store.reject > 0:
            winner = FakeStore(content)
            watch(haidt, winner, winner_notifier, FakeHttp(routes(babel=only_a)))
            store.content = winner.content

    loser = FakeStore(content, reject=1, on_save=a_concurrent_run_lands_first)

    outcome = watch(haidt, loser, loser_notifier, FakeHttp(routes(babel=both)))

    assert winner_notifier.messages == ["Essay A"]
    assert loser_notifier.messages == ["Essay B"]
    assert outcome.delivered == 1


# =========================================================================
# Untrusted state
# =========================================================================

def test_a_cold_start_adopts_without_announcing_a_back_catalogue(haidt):
    entries = [babel_entry(f"Essay {i}", f"essay-{i}") for i in range(4)]
    store, notifier = FakeStore(None), FakeNotifier()

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))))

    assert notifier.sent == []
    assert outcome.adopted == 4
    assert set(store.statuses().values()) == {STATUS_ADOPTED}


def test_the_run_after_a_cold_start_alerts_normally(haidt):
    store, notifier = FakeStore(None), FakeNotifier()
    watch(haidt, store, notifier,
          FakeHttp(routes(babel=rss_feed([babel_entry("Old Essay", "old")]))))

    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([
        babel_entry("Old Essay", "old"), babel_entry("New Essay", "new"),
    ]))))

    assert notifier.messages == ["New Essay"]


def test_malformed_state_adopts_silently_and_is_rewritten_clean(haidt):
    store = FakeStore('{"version": 1, "seen": {"url:x": "corrupted"}}')
    notifier = FakeNotifier()

    outcome = watch(haidt, store, notifier,
                    FakeHttp(routes(babel=rss_feed([babel_entry("Essay", "essay")]))))

    assert notifier.sent == []
    assert outcome.adopted == 1
    recovered = store.state()
    assert not recovered.recovered
    assert set(recovered.entries.values().__iter__().__next__().voice_ids) == {"jonathan-haidt"}


def test_state_that_breaks_between_attempts_stands_down_without_alerting(haidt):
    """Never notify against state that stopped being readable mid-run."""
    def corrupt_on_first_save(store, state, message):
        if store.reject > 0:
            store.content = "{ not json"

    store = FakeStore(seeded_store().content, reject=1, on_save=corrupt_on_first_save)
    notifier = FakeNotifier()

    outcome = watch(haidt, store, notifier,
                    FakeHttp(routes(babel=rss_feed([babel_entry("Essay", "essay")]))))

    assert notifier.sent == []
    assert outcome.persisted is False


# =========================================================================
# What qualifies
# =========================================================================

@pytest.mark.parametrize(
    "published, reason",
    [
        ("Mon, 01 Sep 2026 12:00:00 +0000", "older than the alerting window"),
        ("Sat, 30 Sep 2028 12:00:00 +0000", "implausibly far in the future"),
        ("", "undated"),
        ("not a date at all", "unparseable"),
    ],
)
def test_work_outside_the_window_is_not_alerted(haidt, published, reason):
    store, notifier = seeded_store(), FakeNotifier()
    entry = babel_entry("Essay", "essay", published=published)

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([entry]))))

    assert notifier.sent == [], reason
    assert outcome.candidates == 0


def test_a_voice_with_notifications_switched_off_is_discovered_but_silent():
    registry = registry_from([babel_voice(notify=False)])
    store, notifier = seeded_store(), FakeNotifier()

    outcome = watch(registry, store, notifier,
                    FakeHttp(routes(babel=rss_feed([babel_entry("Essay", "essay")]))))

    assert notifier.sent == []
    assert outcome.candidates == 0


def test_a_byline_that_is_not_the_followed_writer_is_not_alerted(haidt):
    """The multi-author feed case: the feed URL alone proves nothing."""
    store, notifier = seeded_store(), FakeNotifier()
    entry = babel_entry("Someone Else's Essay", "theirs", author="Freya India")

    outcome = watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([entry]))))

    assert notifier.sent == []
    assert outcome.candidates == 0


def test_no_enabled_voices_does_no_work_at_all():
    registry = registry_from([babel_voice(enabled=False)])
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp({})

    outcome = watch(registry, store, notifier, http)

    assert outcome.skipped == SKIP_NO_VOICES
    assert http.calls == [] and store.loads == 0


# =========================================================================
# Request budget and cadence
# =========================================================================

def _mixed_registry():
    return registry_from([
        babel_voice(),
        {
            "id": "george-monbiot", "name": "George Monbiot",
            "provider_ids": [{"provider": "guardian", "id": "profile/georgemonbiot"}],
            "sources": [{"id": "g", "type": "guardian_contributor",
                         "tag": "profile/georgemonbiot", "authorship": "provider_id"}],
        },
        {
            "id": "conrad-black", "name": "Conrad Black",
            "provider_ids": [{"provider": "perigon", "id": "12345"}],
            "sources": [{"id": "p", "type": "perigon_journalist",
                         "journalist_id": "12345", "authorship": "provider_id"}],
        },
    ])


def test_a_frequent_run_never_spends_the_scarce_provider(monkeypatch):
    """Perigon's personal tier is measured in requests per month. Hourly
    polling would spend a month's allowance in a week."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "k")
    monkeypatch.setenv("PERIGON_API_KEY", "k")
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp({
        BABEL_FEED: FakeResponse(text=rss_feed([])),
        "content.guardianapis.com": FakeResponse(payload={"response": {"results": []}}),
        "api.perigon.io": FakeResponse(payload={"articles": []}),
    })

    outcome = watch(_mixed_registry(), store, notifier, http)

    assert outcome.mode == MODE_FREQUENT
    assert "perigon" not in outcome.budget
    assert outcome.budget == {"guardian": 1, "rss": 1}


def test_a_reconciliation_run_includes_the_scarce_provider(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "k")
    monkeypatch.setenv("PERIGON_API_KEY", "k")
    store, notifier = FakeStore(seeded_store().content), FakeNotifier()
    http = FakeHttp({
        BABEL_FEED: FakeResponse(text=rss_feed([])),
        "content.guardianapis.com": FakeResponse(payload={"response": {"results": []}}),
        "api.perigon.io": FakeResponse(payload={"articles": []}),
    })

    outcome = watch(_mixed_registry(), store, notifier, http,
                    reconcile_every=dt.timedelta(minutes=30))

    assert outcome.mode == MODE_RECONCILE
    assert outcome.budget == {"guardian": 1, "perigon": 1, "rss": 1}


def test_a_reconciliation_run_records_its_marker_so_the_next_hour_is_cheap(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "k")
    monkeypatch.setenv("PERIGON_API_KEY", "k")
    store, notifier = FakeStore(seeded_store().content), FakeNotifier()

    def http():
        return FakeHttp({
            BABEL_FEED: FakeResponse(text=rss_feed([])),
            "content.guardianapis.com": FakeResponse(payload={"response": {"results": []}}),
            "api.perigon.io": FakeResponse(payload={"articles": []}),
        })

    watch(_mixed_registry(), store, notifier, http(), reconcile_every=dt.timedelta(minutes=30))
    assert store.state().last_reconcile_at == NOW

    second = watch(_mixed_registry(), store, notifier, http(),
                   reconcile_every=dt.timedelta(minutes=30), now=NOW + dt.timedelta(minutes=10))

    assert second.mode == MODE_FREQUENT


def test_request_cost_scales_with_sources_not_with_voices(monkeypatch):
    """Ten Voices sharing one feed and one contributor query is two requests."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "k")
    voices = [babel_voice()]
    for index in range(9):
        voices.append({
            "id": f"writer-{index}", "name": f"Writer{index} Surname{index}",
            "provider_ids": [{"provider": "guardian", "id": f"profile/w{index}"}],
            "sources": [{"id": f"g{index}", "type": "guardian_contributor",
                         "tag": f"profile/w{index}", "authorship": "provider_id"}],
        })
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp({
        BABEL_FEED: FakeResponse(text=rss_feed([])),
        "content.guardianapis.com": FakeResponse(payload={"response": {"results": []}}),
    })

    outcome = watch(registry_from(voices), store, notifier, http)

    assert outcome.budget == {"guardian": 1, "rss": 1}


def test_an_exhausted_budget_degrades_that_provider_and_no_other(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "k")
    registry = registry_from([babel_voice(), peterson_voice()])
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(
        babel=rss_feed([babel_entry("Essay", "essay")]),
        peterson=rss_feed([]),
    ), budget=RequestBudget(limits={"rss": 1}))

    outcome = watch(registry, store, notifier, http)

    assert outcome.delivered == 1
    assert any("budget" in s.error for s in outcome.failures)


def test_the_watcher_never_fetches_the_morning_pool(haidt):
    """Rebuilding the edition to send a notification is the failure mode this
    whole design exists to avoid."""
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(babel=rss_feed([babel_entry("Essay", "essay")])))

    watch(haidt, store, notifier, http)

    assert [url for url, _ in http.calls] == [BABEL_FEED]


def test_offline_runs_make_no_requests_and_alert_nothing(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp({})

    outcome = watch(haidt, store, notifier, http, fetch=False)

    assert http.calls == []
    assert outcome.planned == 0
    assert notifier.sent == []


# =========================================================================
# Pruning inside a run
# =========================================================================

def test_a_run_prunes_state_past_the_retention_window(haidt):
    from src.voices.state import SeenEntry, WatchState

    old = SeenEntry(
        key="url:https://example.com/ancient",
        keys=("url:https://example.com/ancient",),
        voice_ids=("jonathan-haidt",),
        first_seen=NOW - dt.timedelta(days=40),
        published_at=NOW - dt.timedelta(days=40),
        status=STATUS_NOTIFIED,
    )
    state = WatchState(entries={old.key: old}, last_reconcile_at=NOW - dt.timedelta(hours=1))
    store, notifier = FakeStore(state.dumps()), FakeNotifier()

    outcome = watch(haidt, store, notifier,
                    FakeHttp(routes(babel=rss_feed([babel_entry("Essay", "essay")]))))

    assert outcome.pruned == 1
    assert "url:https://example.com/ancient" not in store.state().entries


def test_state_stays_bounded_across_many_runs(haidt):
    store, notifier = seeded_store(), FakeNotifier()

    for day in range(20):
        moment = NOW + dt.timedelta(days=day)
        published = moment.strftime("%a, %d %b %Y %H:%M:%S +0000")
        entries = [babel_entry(f"Essay {day}-{i}", f"essay-{day}-{i}", published=published)
                   for i in range(3)]
        watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed(entries))),
              now=moment, max_entries=12)

    assert len(store.state().entries) <= 12


# =========================================================================
# Quiet hours and cadence helpers
# =========================================================================

def test_quiet_hours_stop_a_run_before_it_spends_anything(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    http = FakeHttp(routes(babel=rss_feed([babel_entry("Essay", "essay")])))
    three_am_toronto = dt.datetime(2026, 9, 6, 7, 0, tzinfo=UTC)

    outcome = watch(haidt, store, notifier, http, now=three_am_toronto, quiet_hours=(23, 6))

    assert outcome.skipped == SKIP_QUIET_HOURS
    assert http.calls == [] and store.loads == 0 and notifier.sent == []


def test_work_published_during_quiet_hours_is_alerted_afterwards(haidt):
    store, notifier = seeded_store(), FakeNotifier()
    overnight = babel_entry("Essay", "essay", published="Sun, 06 Sep 2026 05:00:00 +0000")

    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([overnight]))),
          now=dt.datetime(2026, 9, 6, 7, 0, tzinfo=UTC), quiet_hours=(23, 6))
    assert notifier.sent == []

    watch(haidt, store, notifier, FakeHttp(routes(babel=rss_feed([overnight]))),
          now=dt.datetime(2026, 9, 6, 12, 0, tzinfo=UTC), quiet_hours=(23, 6))

    assert notifier.messages == ["Essay"]


@pytest.mark.parametrize(
    "hour_utc, quiet",
    [(7, True), (5, True), (9, True), (10, False), (11, False), (16, False), (3, True), (2, False)],
)
def test_quiet_window_wraps_midnight_in_local_time(hour_utc, quiet):
    moment = dt.datetime(2026, 9, 6, hour_utc, 30, tzinfo=UTC)  # EDT = UTC-4
    assert in_quiet_hours(moment, (23, 6)) is quiet


def test_quiet_hours_can_be_switched_off():
    assert in_quiet_hours(dt.datetime(2026, 9, 6, 7, 0, tzinfo=UTC), None) is False
    assert in_quiet_hours(dt.datetime(2026, 9, 6, 7, 0, tzinfo=UTC), ()) is False


def test_an_unknown_provider_is_held_back_to_reconciliation():
    """A new adapter must be conservative with someone else's quota."""
    assert provider_cadence("something-new") == MODE_RECONCILE
    assert provider_cadence("rss") == MODE_FREQUENT


def test_reconciliation_is_due_when_state_has_never_recorded_one():
    from src.voices.state import WatchState

    assert reconcile_due(WatchState(), NOW, every=dt.timedelta(hours=24))
    recent = WatchState(last_reconcile_at=NOW - dt.timedelta(hours=1))
    assert not reconcile_due(recent, NOW, every=dt.timedelta(hours=24))
    stale = WatchState(last_reconcile_at=NOW - dt.timedelta(hours=30))
    assert reconcile_due(stale, NOW, every=dt.timedelta(hours=24))


# =========================================================================
# The shipped configuration
# =========================================================================

def test_the_shipped_registry_plans_a_sane_frequent_run(production_registry, monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "k")
    from src.voices.adapters import FetchWindow
    from src.voices.watch import plan_for_mode

    window = FetchWindow(since=NOW - dt.timedelta(hours=24), until=NOW)
    frequent = plan_for_mode(production_registry, window, MODE_FREQUENT)
    reconcile = plan_for_mode(production_registry, window, MODE_RECONCILE)

    assert len(frequent) <= 6, "an hourly run must stay small"
    assert len(reconcile) >= len(frequent)
    for request in frequent:
        assert request.adapter != "perigon_journalist"


def test_the_watch_budget_is_at_least_the_shipped_plan(production_registry):
    from src.voices.adapters import FetchWindow, get_adapter
    from src.voices.watch import plan_for_mode

    window = FetchWindow(since=NOW - dt.timedelta(hours=24), until=NOW)
    per_provider: dict[str, int] = {}
    for request in plan_for_mode(production_registry, window, MODE_RECONCILE):
        provider = get_adapter(request.adapter).provider
        per_provider[provider] = per_provider.get(provider, 0) + 1

    for provider, count in per_provider.items():
        assert config.VOICE_WATCH_REQUEST_BUDGET[provider] >= count, provider

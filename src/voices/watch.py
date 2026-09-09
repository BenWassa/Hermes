"""The release-time watcher: discover, claim, alert.

One job, run often and cheaply: notice that a followed writer has published,
and send one quiet notification about it. It never builds an edition, never
calls the curation model, and never touches ``docs/``. The morning paper is
still where a followed piece is *read*; this only shortens the wait.

    load durable state
    -> plan the cheap sources (and the scarce ones once a day)
    -> fetch, degrading one source at a time
    -> attribute and canonicalise through the #10 identity model
    -> claim what state has never seen, and push that claim
    -> notify what was claimed
    -> record the outcome

Two orderings carry the whole correctness argument.

**The claim is pushed before any notification is sent.** A crash, a cancelled
runner, or a failed delivery after that point loses an alert; none of them can
produce a second one. The reverse order would trade a rare lost alert for a
routine duplicate, which is the failure a reader actually notices.

**The claim is written with a compare-and-swap.** ``git push`` is rejected when
the branch moved, and a rejection sends this run back to re-read state and
re-decide what is still unclaimed. Two overlapping runs that both find the same
article therefore alert once between them, and a run that loses every attempt
sends nothing at all rather than notifying against state it could not save.

The guarantee is **at-most-once**, and it is a real at-most-once rather than a
hopeful one. It is not exactly-once, which GitHub Actions plus a third-party
push service cannot provide: a runner killed between the claim and the send
loses that alert permanently, and the piece surfaces in the next morning
edition instead. See ``VOICES.md`` section 20.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from .. import config
from .adapters import FetchWindow, get_adapter
from .dedupe import syndication_keys_for
from .discover import SourceStatus, plan_requests, resolve_observations, run_requests
from .http import RequestBudget, VoiceHttp
from .model import VoiceArticle
from .notify import Alert, NotifyError, Notifier, build_alert
from .registry import Registry
from .state import (
    STATUS_ADOPTED,
    STATUS_FAILED,
    STATUS_NOTIFIED,
    STATUS_PENDING,
    STATUS_SUPPRESSED,
    StateStore,
    WatchState,
)
from .window import EditionWindow

log = logging.getLogger("the-daily.voices.watch")

UTC = dt.timezone.utc

MODE_FREQUENT = "frequent"
MODE_RECONCILE = "reconcile"

#: Why a run did nothing. Not failures: each is a deliberate decision.
SKIP_QUIET_HOURS = "quiet_hours"
SKIP_NO_VOICES = "no_voices"


# --- cadence and scheduling ----------------------------------------------

def provider_cadence(provider: str, cadence: dict | None = None) -> str:
    """How often a provider may be polled.

    Unknown providers are held back to the reconciliation pass. A new adapter
    is therefore conservative with someone else's quota until an operator
    decides it is cheap enough to poll hourly.
    """
    cadence = config.VOICE_WATCH_CADENCE if cadence is None else cadence
    return cadence.get(provider, MODE_RECONCILE)


def reconcile_due(state: WatchState, now: dt.datetime, *, every: dt.timedelta) -> bool:
    """Whether this run should also poll the scarce providers.

    Driven by durable state rather than by a second cron entry, so a missed or
    throttled run delays reconciliation instead of skipping it for a day.
    """
    if state.last_reconcile_at is None:
        return True
    return now - state.last_reconcile_at >= every


def in_quiet_hours(now: dt.datetime, quiet_hours, timezone: str | None = None) -> bool:
    """Whether ``now`` falls inside the configured quiet window.

    A newspaper that buzzes at 4am is not a quiet newspaper. Runs inside the
    window stop before spending a single provider request; overnight work is
    picked up by the first run after it closes.
    """
    if not quiet_hours:
        return False
    start, end = quiet_hours
    local = now
    try:
        from zoneinfo import ZoneInfo

        local = now.astimezone(ZoneInfo(timezone or config.TIMEZONE))
    except Exception:  # noqa: BLE001 - a missing tz database must not stop a run
        log.warning("voice watch: timezone %s unavailable; quiet hours evaluated in UTC", timezone)
    hour = local.hour
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end  # window wraps midnight


# --- results --------------------------------------------------------------

@dataclass
class WatchOutcome:
    """Everything one watcher run did, and why."""

    mode: str = MODE_FREQUENT
    skipped: str = ""
    planned: int = 0
    statuses: list[SourceStatus] = field(default_factory=list)
    budget: dict[str, int] = field(default_factory=dict)
    candidates: int = 0
    new_keys: list[str] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    delivered: int = 0
    failed: int = 0
    suppressed: int = 0
    adopted: int = 0
    pruned: int = 0
    persisted: bool = True
    claim_attempts: int = 0

    @property
    def failures(self) -> list[SourceStatus]:
        return [s for s in self.statuses if not s.ok]

    @property
    def all_sources_failed(self) -> bool:
        return bool(self.statuses) and not any(s.ok for s in self.statuses)

    @property
    def exit_code(self) -> int:
        """0 normal (partial degradation included), 1 worth an operator's attention."""
        if self.new_keys and not self.persisted:
            return 1
        if self.all_sources_failed:
            return 1
        return 0

    def diagnostics(self) -> dict:
        return {
            "mode": self.mode,
            "skipped": self.skipped,
            "requests": self.budget,
            "sources": [s.as_dict() for s in self.statuses],
            "candidates": self.candidates,
            "new": len(self.new_keys),
            "delivered": self.delivered,
            "failed": self.failed,
            "suppressed": self.suppressed,
            "adopted": self.adopted,
            "pruned": self.pruned,
            "persisted": self.persisted,
            "claim_attempts": self.claim_attempts,
        }


# --- identity -------------------------------------------------------------

def article_state_keys(article: VoiceArticle, related: list[VoiceArticle] | None = None) -> set[str]:
    """Every key durable state should remember this article by.

    The article's own identity keys make a second sighting through a different
    adapter match. The syndication keys make a *reprint* discovered on a later
    run match. Any grouped copies contribute their identity keys too, so the
    copy alone is recognised even when the primary is the one that was
    alerted.
    """
    keys = set(article.identity_keys) | {article.key}
    keys |= syndication_keys_for(article)
    for copy in related or []:
        keys |= set(copy.identity_keys) | {copy.key}
        keys |= syndication_keys_for(copy)
    return {key for key in keys if key}


def notifiable_voice_ids(article: VoiceArticle, registry: Registry) -> list[str]:
    """Followed writers on this article who have alerting switched on."""
    out: list[str] = []
    for voice_id in article.voice_ids:
        voice = registry.get(voice_id)
        if voice and voice.enabled and voice.notify:
            out.append(voice_id)
    return out


def _syndication_copies(article: VoiceArticle, articles: list[VoiceArticle]) -> list[VoiceArticle]:
    if not article.syndication_group:
        return []
    return [
        other
        for other in articles
        if other is not article and other.syndication_group == article.syndication_group
    ]


# --- discovery ------------------------------------------------------------

def watch_budget() -> RequestBudget:
    return RequestBudget(limits=dict(config.VOICE_WATCH_REQUEST_BUDGET))


def plan_for_mode(registry: Registry, window: FetchWindow, mode: str, cadence=None) -> list:
    """The provider requests this run is allowed to make.

    A frequent run polls only the providers cheap enough to poll hourly; a
    reconciliation run polls everything. The filter is applied to the *plan*,
    after #10 has already collapsed every source into as few requests as the
    providers allow, so nothing here can turn one Voice into one request.
    """
    # V2 product membership must not enlarge the still-live V1 release watcher.
    # During migration, `notify` keeps only its legacy operational meaning, so
    # plan requests from that bounded set even when callers pass the full V2 registry.
    watcher_registry = registry.for_legacy_watcher()
    planned = plan_requests(watcher_registry, window)
    if mode == MODE_RECONCILE:
        return planned
    return [
        request
        for request in planned
        if provider_cadence(get_adapter(request.adapter).provider, cadence) == MODE_FREQUENT
    ]


def discover_for_watch(
    registry: Registry,
    *,
    window: EditionWindow,
    mode: str,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
    cadence=None,
    fetch: bool = True,
):
    """Fetch and resolve, without the morning pool and without a build.

    Deliberately not ``discover()``: the build's pool comes from a full
    ``src.fetch`` run costing Guardian, NYT and Perigon requests, and paying
    for that hourly would be rebuilding the newspaper to send a notification.
    The watcher pays only for the Voice sources themselves.
    """
    fetch_window = FetchWindow(since=window.since, until=window.until)
    planned = plan_for_mode(registry, fetch_window, mode, cadence) if fetch else []
    statuses: list[SourceStatus] = []
    observations: list = []
    spent: dict[str, int] = {}

    if planned:
        http = http or VoiceHttp(budget=budget or watch_budget())
        log.info(
            "voice watch: %s pass, %d source(s) -> %d provider request(s)",
            mode, len(registry.sources_by_key()), len(planned),
        )
        observations, statuses = run_requests(planned, http, fetch_window)
        spent = http.budget.report()

    result = resolve_observations(registry, observations, window)
    result.statuses = statuses
    result.budget = spent
    return result, len(planned)


# --- the run --------------------------------------------------------------

def run_watch(
    registry: Registry,
    *,
    store: StateStore,
    notifier: Notifier,
    now: dt.datetime | None = None,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
    fetch: bool = True,
    lookback: dt.timedelta | None = None,
    quiet_hours=(),
    cadence=None,
    max_alerts: int | None = None,
    retention: dt.timedelta | None = None,
    max_entries: int | None = None,
    reconcile_every: dt.timedelta | None = None,
    push_attempts: int | None = None,
) -> WatchOutcome:
    """One complete watcher run."""
    now = now or dt.datetime.now(UTC)
    lookback = lookback or dt.timedelta(hours=config.VOICE_WATCH_LOOKBACK_HOURS)
    retention = retention or dt.timedelta(days=config.VOICE_WATCH_RETENTION_DAYS)
    max_entries = config.VOICE_WATCH_MAX_ENTRIES if max_entries is None else max_entries
    max_alerts = config.VOICE_WATCH_MAX_ALERTS_PER_RUN if max_alerts is None else max_alerts
    reconcile_every = reconcile_every or dt.timedelta(hours=config.VOICE_WATCH_RECONCILE_HOURS)
    attempts_allowed = push_attempts or config.VOICE_WATCH_PUSH_ATTEMPTS
    quiet = config.VOICE_WATCH_QUIET_HOURS if quiet_hours == () else quiet_hours

    outcome = WatchOutcome()

    if in_quiet_hours(now, quiet):
        log.info("voice watch: inside quiet hours; no requests, no alerts")
        outcome.skipped = SKIP_QUIET_HOURS
        return outcome
    if not registry.active:
        log.info("voice watch: no enabled voices; nothing to do")
        outcome.skipped = SKIP_NO_VOICES
        return outcome

    state = store.load()
    outcome.mode = MODE_RECONCILE if reconcile_due(state, now, every=reconcile_every) else MODE_FREQUENT

    window = EditionWindow(
        since=now - lookback,
        until=now,
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )
    result, planned = discover_for_watch(
        registry, window=window, mode=outcome.mode, http=http, budget=budget,
        cadence=cadence, fetch=fetch,
    )
    outcome.planned = planned
    outcome.statuses = result.statuses
    outcome.budget = result.budget
    for failure in outcome.failures:
        log.warning("voice watch: degraded source %s: %s", failure.label, failure.error)
    if outcome.all_sources_failed:
        log.error("voice watch: every planned source failed; the run is blind this cycle")

    # Only work inside the window, attributed to a Voice that wants alerts,
    # with somewhere to send the reader. Syndicated copies are represented by
    # their primary, which ``resolve_observations`` has already elected.
    candidates: list[tuple[VoiceArticle, list[str]]] = []
    for article in result.fresh:
        voice_ids = notifiable_voice_ids(article, registry)
        if not voice_ids or not article.title or not (article.canonical_url or article.url):
            continue
        candidates.append((article, voice_ids))
    outcome.candidates = len(candidates)

    if state.untrusted:
        return _adopt(state, candidates, result, store, outcome, now, retention, max_entries)

    return _claim_and_notify(
        registry, state, candidates, result, store, notifier, outcome, now,
        retention=retention, max_entries=max_entries, max_alerts=max_alerts,
        attempts_allowed=attempts_allowed,
    )


def _adopt(state, candidates, result, store, outcome, now, retention, max_entries) -> WatchOutcome:
    """Cold start or recovered state: learn what exists, announce nothing.

    Neither a fresh install nor a corrupted file is evidence that the reader
    has not seen this work, so treating either as "everything is new" would
    announce a back catalogue. One silent cycle costs at most one delayed
    alert and rewrites the file clean.
    """
    reason = "cold start" if state.cold else "recovered state"
    for article, voice_ids in candidates:
        state.claim(
            article.key,
            article_state_keys(article, _syndication_copies(article, result.articles)),
            voice_ids=voice_ids,
            first_seen=now,
            published_at=article.published_at,
            status=STATUS_ADOPTED,
        )
    outcome.adopted = len(candidates)
    state.last_reconcile_at = now if outcome.mode == MODE_RECONCILE else state.last_reconcile_at
    outcome.pruned = state.prune(now, retention=retention, max_entries=max_entries)
    state.updated_at = now
    # Always written, even with nothing to adopt: this write is what makes the
    # file exist and parse, and without it every subsequent run would be
    # another untrusted run that never alerts.
    outcome.persisted = store.save(state, f"chore(voices): adopt watcher state ({reason})")
    log.warning(
        "voice watch: %s; adopted %d article(s) without alerting", reason, outcome.adopted
    )
    return outcome


def _claim_and_notify(
    registry, state, candidates, result, store, notifier, outcome, now, *,
    retention, max_entries, max_alerts, attempts_allowed,
) -> WatchOutcome:
    """The normal path: claim durably, then alert what was claimed."""
    by_key = {article.key: (article, voice_ids) for article, voice_ids in candidates}
    to_alert: list[str] = []
    persisted = False

    for attempt in range(1, attempts_allowed + 1):
        outcome.claim_attempts = attempt
        if attempt > 1:
            # Someone moved the branch under us. Re-read and re-decide: the
            # winner's claims are now visible, so anything they took drops out
            # of our list before a single notification goes out.
            state = store.load()
            if state.untrusted:
                log.error("voice watch: state became unreadable mid-run; standing down")
                outcome.persisted = False
                return outcome

        before = state.fingerprint()
        fresh_claims: list[str] = []
        for article, voice_ids in candidates:
            if state.has(article_state_keys(article)):
                continue
            fresh_claims.append(article.key)

        to_alert = fresh_claims[:max_alerts]
        over_cap = fresh_claims[max_alerts:]
        for key in fresh_claims:
            article, voice_ids = by_key[key]
            state.claim(
                key,
                article_state_keys(article, _syndication_copies(article, result.articles)),
                voice_ids=voice_ids,
                first_seen=now,
                published_at=article.published_at,
                status=STATUS_PENDING if key in to_alert else STATUS_SUPPRESSED,
            )
        outcome.new_keys = list(fresh_claims)
        outcome.suppressed = len(over_cap)
        if over_cap:
            log.info(
                "voice watch: %d new piece(s) beyond the per-run cap of %d recorded as seen; "
                "they appear in the morning edition rather than as alerts",
                len(over_cap), max_alerts,
            )

        if outcome.mode == MODE_RECONCILE:
            state.last_reconcile_at = now
        outcome.pruned = state.prune(now, retention=retention, max_entries=max_entries)

        if state.fingerprint() == before:
            # Nothing new, nothing pruned, no reconciliation marker to move.
            # A quiet hour leaves no commit behind at all.
            persisted = True
            break

        state.updated_at = now
        message = (
            f"chore(voices): watcher state, {len(fresh_claims)} new"
            if fresh_claims
            else "chore(voices): watcher state"
        )
        if store.save(state, message):
            persisted = True
            break
        log.warning("voice watch: claim attempt %d/%d lost the push race", attempt, attempts_allowed)

    outcome.persisted = persisted
    if not persisted:
        # Never notify against a claim that is not durable. The next run will
        # find the same articles and try again; nothing is lost but time.
        if outcome.new_keys:
            log.error(
                "voice watch: could not persist %d claim(s) after %d attempt(s); "
                "sending nothing this run",
                len(outcome.new_keys), outcome.claim_attempts,
            )
        return outcome

    if not to_alert:
        log.info("voice watch: nothing new (%d candidate(s) already seen)", outcome.candidates)
        return outcome

    _deliver(registry, state, by_key, to_alert, notifier, outcome)
    _persist_outcomes(state, store, outcome, now)
    return outcome


def _deliver(registry, state, by_key, to_alert, notifier, outcome) -> None:
    """Send the claimed alerts.

    A failed delivery is terminal, not retried on the next run. The request
    may have reached ntfy before the error surfaced, so retrying it would be
    the one path that can produce a duplicate; the piece appears in the
    morning edition instead, and the failure is recorded in state.
    """
    for key in to_alert:
        article, voice_ids = by_key[key]
        alert = build_alert(article, registry, voice_ids=voice_ids)
        try:
            notifier.send(alert)
        except NotifyError as exc:
            log.error("voice watch: alert for %s failed: %s", article.canonical_url, exc)
            state.mark(key, STATUS_FAILED, error=str(exc), attempted=True)
            outcome.failed += 1
            continue
        state.mark(key, STATUS_NOTIFIED, attempted=True)
        outcome.delivered += 1
        outcome.alerts.append(alert)


def _persist_outcomes(state, store, outcome, now) -> None:
    """Record delivery results. Best effort: correctness does not depend on it.

    The claims are already durable, so a failure here leaves entries reading
    ``pending`` forever. That is still never re-alerted; it only costs the
    operator a clear record of what went out.
    """
    state.updated_at = now
    if store.save(state, f"chore(voices): watcher state, {outcome.delivered} alerted"):
        return
    log.warning("voice watch: delivery outcomes could not be recorded; claims remain durable")

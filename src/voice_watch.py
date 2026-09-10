"""Core Voice release-alert operator entrypoint.

    python -m src.voice_watch                 # scheduled Core release alerts
    python -m src.voice_watch --dry-run       # fetch/report; no writes/model/ntfy
    python -m src.voice_watch --no-push       # real run with local state/pages
    python -m src.voice_watch --offline       # no provider requests
    python -m src.voice_watch --smoke         # bounded live Core-source + ntfy check
    python -m src.voice_watch --state-report  # inspect durable claim state

Production eligibility is authoritative ``tier == core``.  The existing
watcher claim/CAS machinery is retained, but the notification stage now prepares
one stable Hermes article-summary page after the claim is durable and before
ntfy is attempted.  Summary/page failure degrades to the original publisher
link without reopening the claim.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys

from . import config
from .voices.notify import Alert, NotifyError, NtfyNotifier, RecordingNotifier
from .voices.registry import RegistryError, load_registry
from .voices.release import (
    DryRunArticlePagePublisher,
    FileArticlePagePublisher,
    GeminiSummaryProvider,
    GitArticlePagePublisher,
    MetadataSummaryProvider,
    ReleasePreparer,
)
from .voices.release_runtime import ReleaseNotifier, core_alert_registry
from .voices.state import FileStateStore, GitError, GitStateStore, StateStore, load_state
from .voices.watch import (
    MODE_RECONCILE,
    WatchOutcome,
    discover_for_watch,
    run_watch,
    watch_budget,
)
from .voices.window import EditionWindow

log = logging.getLogger("the-daily.voices.watch")
UTC = dt.timezone.utc

EXIT_OK = 0
EXIT_DEGRADED = 1
EXIT_CONFIG = 2


class ReadOnlyStore(StateStore):
    """Reads real state and records would-be writes without changing it."""

    def __init__(self, inner: StateStore):
        self.inner = inner
        self.writes: list[str] = []

    def load(self):
        return self.inner.load()

    def save(self, state, message: str) -> bool:
        self.writes.append(message)
        return True


def build_store(args) -> StateStore:
    if args.dry_run:
        return ReadOnlyStore(FileStateStore(args.state))
    if args.no_push:
        return FileStateStore(args.state)
    return GitStateStore(args.state, branch=args.branch, remote=args.remote)


def build_release_notifier(args, registry):
    """Build the post-claim summary/page/notifier chain.

    Dry runs intentionally use metadata-only summary preparation and a no-op
    page publisher, so inspection spends no Gemini quota and writes nothing.
    """
    if args.dry_run:
        delegate = RecordingNotifier()
        summarizer = MetadataSummaryProvider()
        publisher = DryRunArticlePagePublisher()
    else:
        topic = os.environ.get("NTFY_TOPIC", "").strip()
        if not topic:
            return None
        delegate = NtfyNotifier(topic, base_url=config.NTFY_BASE_URL)
        summarizer = GeminiSummaryProvider()
        publisher = (
            FileArticlePagePublisher()
            if args.no_push
            else GitArticlePagePublisher(branch=args.branch, remote=args.remote)
        )

    return ReleaseNotifier(
        delegate=delegate,
        preparer=ReleasePreparer(summarizer=summarizer, publisher=publisher),
        registry=registry,
    )


# --- reporting ------------------------------------------------------------

def report(outcome: WatchOutcome, *, as_json: bool, alerts: list[Alert] | None = None) -> None:
    if as_json:
        payload = outcome.diagnostics()
        if alerts is not None:
            payload["release_pages"] = sum("/voices/articles/" in alert.click for alert in alerts)
            payload["release_fallbacks"] = sum("/voices/articles/" not in alert.click for alert in alerts)
        print(json.dumps(payload, indent=2))
        return
    if outcome.skipped:
        print(f"skipped: {outcome.skipped}")
        return
    print(f"mode:      {outcome.mode}")
    print(f"requests:  {outcome.budget or '{}'} across {outcome.planned} planned request(s)")
    for status in outcome.statuses:
        mark = "ok  " if status.ok else "FAIL"
        detail = f"{status.items} item(s)" if status.ok else status.error
        print(f"  [{mark}] {status.adapter:<22} {status.label[:52]:<52} {detail}")
    print(f"candidates: {outcome.candidates} in window")
    print(f"new:        {len(outcome.new_keys)} (delivered {outcome.delivered}, "
          f"failed {outcome.failed}, suppressed {outcome.suppressed})")
    if outcome.adopted:
        print(f"adopted:    {outcome.adopted} without alerting")
    if outcome.pruned:
        print(f"pruned:     {outcome.pruned} old entr(ies)")
    if not outcome.persisted:
        print("state:      NOT PERSISTED; no alerts were sent")
    for alert in alerts if alerts is not None else outcome.alerts:
        print(f"\n  {alert.title}\n  {alert.message}\n  {alert.click}")


def state_report(path: str) -> int:
    state = load_state(path)
    counts: dict[str, int] = {}
    for entry in state.entries.values():
        counts[entry.status] = counts.get(entry.status, 0) + 1
    print(f"state:            {path}")
    print(f"readable:         {'no (recovering)' if state.recovered else 'yes'}"
          f"{' (cold start)' if state.cold else ''}")
    print(f"entries:          {len(state.entries)} {counts or ''}")
    print(f"updated_at:       {state.updated_at}")
    print(f"last_reconcile:   {state.last_reconcile_at}")
    for problem in state.problems:
        print(f"  problem: {problem}")
    return EXIT_DEGRADED if state.recovered else EXIT_OK


# --- live smoke -----------------------------------------------------------

def smoke(args, registry) -> int:
    """Bounded Core-source validation plus one labelled test notification."""
    now = dt.datetime.now(UTC)
    core = core_alert_registry(registry)
    window = EditionWindow(
        since=now - dt.timedelta(hours=config.VOICE_WATCH_LOOKBACK_HOURS),
        until=now,
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )
    print("== Core sources (live, reconcile pass: every adapter) ==")
    result, planned = discover_for_watch(
        core, window=window, mode=MODE_RECONCILE, budget=watch_budget()
    )
    print(f"planned:  {planned} provider request(s)")
    print(f"spent:    {result.budget or '{}'}")
    for status in result.statuses:
        mark = "ok  " if status.ok else "FAIL"
        detail = f"{status.items} item(s)" if status.ok else status.error
        print(f"  [{mark}] {status.adapter:<22} {status.label[:52]:<52} {detail}")
    print(f"\nresolved: {len(result.articles)} article(s), {len(result.fresh)} inside the window")
    for article in result.fresh[:10]:
        print(f"  {', '.join(article.voice_ids)}: {article.title[:70]}")
        print(f"    {article.canonical_url}")

    failures = [status for status in result.statuses if not status.ok]
    print("\n== ntfy ==")
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("  NTFY_TOPIC not set; delivery NOT verified")
        return EXIT_DEGRADED
    if args.no_notify:
        print("  --no-notify: delivery NOT verified")
        return EXIT_DEGRADED if failures else EXIT_OK
    alert = Alert(
        title="The Daily — Voice watcher check",
        message=f"Smoke test {now.strftime('%Y-%m-%d %H:%M')}Z. Not a real alert.",
        click=config.SITE_URL,
    )
    try:
        NtfyNotifier(topic, base_url=config.NTFY_BASE_URL).send(alert)
    except NotifyError as exc:
        print(f"  FAIL {exc}")
        return EXIT_DEGRADED
    print(f"  ok   one test notification sent to {config.NTFY_BASE_URL}/<topic>")
    return EXIT_DEGRADED if failures else EXIT_OK


# --- main -----------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.voice_watch",
        description="Release-time Hermes summaries and alerts for Core Voices.",
    )
    parser.add_argument("--registry", default=config.VOICES_REGISTRY_PATH)
    parser.add_argument("--state", default=config.VOICE_WATCH_STATE_PATH)
    parser.add_argument("--branch", default=os.environ.get("VOICE_WATCH_BRANCH", "main"))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--dry-run", action="store_true",
                        help="report a metadata-only preview; write nothing, send nothing")
    parser.add_argument("--no-push", action="store_true",
                        help="write state/pages locally only, never commit or push")
    parser.add_argument("--offline", action="store_true",
                        help="make no provider requests")
    parser.add_argument("--smoke", action="store_true",
                        help="bounded live check of Core sources plus one test notification")
    parser.add_argument("--no-notify", action="store_true",
                        help="with --smoke, check sources but do not send the test notification")
    parser.add_argument("--ignore-quiet-hours", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit machine-readable diagnostics")
    parser.add_argument("--state-report", action="store_true",
                        help="describe durable state and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.state_report:
        return state_report(args.state)

    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    if args.smoke:
        return smoke(args, registry)

    watcher_registry = core_alert_registry(registry)
    notifier = build_release_notifier(args, watcher_registry)
    if notifier is None:
        print("NTFY_TOPIC is not set; refusing to run without a delivery channel "
              "(use --dry-run to inspect what would be sent)", file=sys.stderr)
        return EXIT_CONFIG

    try:
        outcome = run_watch(
            watcher_registry,
            store=build_store(args),
            notifier=notifier,
            fetch=not args.offline,
            quiet_hours=None if args.ignore_quiet_hours else (),
        )
    except GitError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    prepared_alerts = [prepared.alert for prepared in notifier.prepared]
    report(outcome, as_json=args.json, alerts=prepared_alerts)
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())

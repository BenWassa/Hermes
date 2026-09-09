"""Release-time Voice watcher: the operator entrypoint.

    python -m src.voice_watch                 # the scheduled run (git state + ntfy)
    python -m src.voice_watch --dry-run       # fetch and report; write nothing, send nothing
    python -m src.voice_watch --no-push       # real run against a local state file
    python -m src.voice_watch --offline       # no provider requests at all
    python -m src.voice_watch --smoke         # bounded live check of sources and ntfy
    python -m src.voice_watch --state-report  # what durable state currently holds

The scheduled form is the only one that writes state or sends a real alert.
``--smoke`` is the live validation path: it exercises every adapter against the
real sources, sends exactly one clearly-labelled test notification, and writes
nothing, so it can be run before or after a deploy without creating a duplicate
alert for a real article.
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
    """Reads real state, refuses to write. Backs ``--dry-run``.

    ``save`` reports success so the run continues exactly as it would in
    production, which is the point: a dry run should show the alerts a real
    run would send, not a run that aborted on a failed write.
    """

    def __init__(self, inner: StateStore):
        self.inner = inner
        self.writes: list[str] = []

    def load(self):
        return self.inner.load()

    def save(self, state, message: str) -> bool:
        self.writes.append(message)
        return True


def build_store(args) -> StateStore:
    path = args.state
    if args.dry_run:
        return ReadOnlyStore(FileStateStore(path))
    if args.no_push:
        return FileStateStore(path)
    return GitStateStore(path, branch=args.branch, remote=args.remote)


def build_notifier(args):
    if args.dry_run:
        return RecordingNotifier()
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        return None
    return NtfyNotifier(topic, base_url=config.NTFY_BASE_URL)


# --- reporting ------------------------------------------------------------

def report(outcome: WatchOutcome, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(outcome.diagnostics(), indent=2))
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
    for alert in outcome.alerts:
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
    """Bounded live validation. Writes nothing; sends one labelled test alert.

    This is the check the deterministic suite deliberately cannot do. It
    proves the two things only the network can prove: that the configured
    source URLs and keys actually answer, and that the ntfy topic actually
    delivers. It never claims or alerts a real article, so running it twice
    costs two obvious test messages and no duplicate release alert.
    """
    now = dt.datetime.now(UTC)
    window = EditionWindow(
        since=now - dt.timedelta(hours=config.VOICE_WATCH_LOOKBACK_HOURS),
        until=now,
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )
    print("== sources (live, reconcile pass: every adapter) ==")
    result, planned = discover_for_watch(
        registry, window=window, mode=MODE_RECONCILE, budget=watch_budget()
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

    failures = [s for s in result.statuses if not s.ok]

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
        description="Release-time alerts for followed Voices.",
    )
    parser.add_argument("--registry", default=config.VOICES_REGISTRY_PATH)
    parser.add_argument("--state", default=config.VOICE_WATCH_STATE_PATH)
    parser.add_argument("--branch", default=os.environ.get("VOICE_WATCH_BRANCH", "main"))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what a real run would do; write nothing, send nothing")
    parser.add_argument("--no-push", action="store_true",
                        help="write state to the local file only, never commit or push")
    parser.add_argument("--offline", action="store_true",
                        help="make no provider requests (exercises state and delivery paths)")
    parser.add_argument("--smoke", action="store_true",
                        help="bounded live check of every source plus one test notification")
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
        # Smoke/audit deliberately sees the full registry so operators can
        # validate new V2 morning sources without changing watcher state.
        return smoke(args, registry)

    notifier = build_notifier(args)
    if notifier is None:
        print("NTFY_TOPIC is not set; refusing to run without a delivery channel "
              "(use --dry-run to inspect what would be sent)", file=sys.stderr)
        return EXIT_CONFIG

    try:
        store = build_store(args)
        # `notify` retains only its V1 operational meaning during the V2
        # migration. New Core/Selective sources must not silently increase the
        # release-alert watcher's polling surface before the weekly replacement
        # is ready.
        watcher_registry = registry.for_legacy_watcher()
        outcome = run_watch(
            watcher_registry,
            store=store,
            notifier=notifier,
            fetch=not args.offline,
            quiet_hours=None if args.ignore_quiet_hours else (),
        )
    except GitError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    report(outcome, as_json=args.json)
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())

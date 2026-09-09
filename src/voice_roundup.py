"""Operator entrypoint for the Voices V2 weekly roundup.

Scheduled production:
    python -m src.voice_roundup collect
    python -m src.voice_roundup weekly

Safe inspection:
    python -m src.voice_roundup collect --dry-run
    python -m src.voice_roundup weekly --dry-run --period 2026-09-13
    python -m src.voice_roundup state-report

Daily collection never constructs a notifier. Weekly dry runs use an in-memory
recording notifier and a read-only store, so they cannot send or publish.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from . import config
from .voices.notify import NtfyNotifier, RecordingNotifier
from .voices.registry import RegistryError, load_registry
from .voices.roundup import collect_daily, period_for_id, publish_weekly
from .voices import roundup_settings as settings
from .voices.roundup_state import (
    FileRoundupStore,
    GitRoundupError,
    GitRoundupStore,
    RoundupStore,
    load_state,
)

log = logging.getLogger("the-daily.voices.roundup")

EXIT_OK = 0
EXIT_DEGRADED = 1
EXIT_CONFIG = 2


class ReadOnlyRoundupStore(RoundupStore):
    def __init__(self, inner: RoundupStore):
        self.inner = inner
        self.writes: list[str] = []
        self.pages: list[str] = []

    def load(self):
        return self.inner.load()

    def save_state(self, state, message: str) -> bool:
        self.writes.append(message)
        return True

    def publish(self, state, page_html: str, page_path, message: str) -> bool:
        self.writes.append(message)
        self.pages.append(page_html)
        return True


def build_store(args) -> RoundupStore:
    local = FileRoundupStore(args.state)
    if args.dry_run:
        return ReadOnlyRoundupStore(local)
    if args.no_push:
        return local
    return GitRoundupStore(
        args.state,
        page_path=args.page,
        branch=args.branch,
        remote=args.remote,
    )


def print_outcome(outcome, *, as_json: bool) -> None:
    data = outcome.diagnostics()
    if as_json:
        print(json.dumps(data, indent=2))
        return
    for key, value in data.items():
        if key == "sources":
            continue
        print(f"{key:14} {value}")
    for status in data.get("sources", []):
        mark = "ok" if status["ok"] else "FAIL"
        detail = status["items"] if status["ok"] else status["error"]
        print(f"  [{mark:<4}] {status['adapter']:<22} {status['label'][:54]:<54} {detail}")


def state_report(path: str, *, as_json: bool) -> int:
    state = load_state(path)
    data = {
        "state": path,
        "readable": not state.recovered,
        "cold": state.cold,
        "collecting_since": state.collecting_since.isoformat() if state.collecting_since else None,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        "last_reconcile_at": (
            state.last_reconcile_at.isoformat() if state.last_reconcile_at else None
        ),
        "items": len(state.items),
        "last_roundup": state.last_roundup.as_dict() if state.last_roundup else None,
        "problems": list(state.problems),
    }
    if as_json:
        print(json.dumps(data, indent=2))
    else:
        for key, value in data.items():
            print(f"{key:18} {value}")
    return EXIT_DEGRADED if state.recovered else EXIT_OK


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="python -m src.voice_roundup",
        description="Daily silent Core collection and weekly Voices roundup.",
    )
    root.add_argument(
        "operation",
        choices=("collect", "weekly", "state-report"),
        help="silent daily collection, weekly publication, or state inspection",
    )
    root.add_argument("--registry", default=config.VOICES_REGISTRY_PATH)
    root.add_argument("--state", default=settings.STATE_PATH)
    root.add_argument("--page", default=settings.PAGE_PATH)
    root.add_argument("--branch", default=os.environ.get("VOICE_ROUNDUP_BRANCH", "main"))
    root.add_argument("--remote", default="origin")
    root.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch/report normally but write and notify nothing",
    )
    root.add_argument(
        "--no-push",
        action="store_true",
        help="write collection state locally rather than committing it",
    )
    root.add_argument(
        "--offline",
        action="store_true",
        help="make no provider requests; only valid with --dry-run",
    )
    root.add_argument(
        "--period",
        help="explicit Sunday period YYYY-MM-DD; weekly dry-run only",
    )
    root.add_argument("--json", action="store_true")
    root.add_argument("-v", "--verbose", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.offline and not args.dry_run:
        print("--offline is inspection-only; add --dry-run", file=sys.stderr)
        return EXIT_CONFIG
    if args.period and (args.operation != "weekly" or not args.dry_run):
        print("--period is allowed only for a weekly --dry-run", file=sys.stderr)
        return EXIT_CONFIG
    if args.operation == "weekly" and args.no_push and not args.dry_run:
        print("weekly publication requires durable git state; use --dry-run for local inspection",
              file=sys.stderr)
        return EXIT_CONFIG

    if args.operation == "state-report":
        return state_report(args.state, as_json=args.json)

    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    try:
        store = build_store(args)
        if args.operation == "collect":
            outcome = collect_daily(
                registry,
                store=store,
                fetch=not args.offline,
            )
        else:
            if args.dry_run:
                notifier = RecordingNotifier()
            else:
                topic = os.environ.get("NTFY_TOPIC", "").strip()
                if not topic:
                    print(
                        "NTFY_TOPIC is required for weekly publication; "
                        "use --dry-run to inspect safely",
                        file=sys.stderr,
                    )
                    return EXIT_CONFIG
                notifier = NtfyNotifier(topic, base_url=config.NTFY_BASE_URL)

            period = period_for_id(args.period) if args.period else None
            outcome = publish_weekly(
                registry,
                store=store,
                notifier=notifier,
                period=period,
                page_path=args.page,
                fetch=not args.offline,
            )
    except (GitRoundupError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    print_outcome(outcome, as_json=args.json)
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())

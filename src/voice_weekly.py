"""Grounded weekly Voice digest entry point.

The weekly relevance screen may use public feed/archive descriptions gathered
through the existing generic Voice adapters. It never fetches article bodies
and performs at most one Gemini screening/synthesis call per invocation.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from . import config
from .voice_digest import (
    DeterministicWeeklyCurator,
    GeminiWeeklyCurator,
    publish_weekly_screened,
)
from .voices import roundup_settings as settings
from .voices.notify import NtfyNotifier, RecordingNotifier
from .voices.registry import RegistryError, load_registry
from .voices.roundup import period_for_id
from .voices.roundup_state import FileRoundupStore, GitRoundupError, GitRoundupStore, RoundupStore
from .voices.weekly_context import weekly_public_descriptions

log = logging.getLogger("the-daily.voices.weekly")
EXIT_CONFIG = 2


class GroundedGeminiWeeklyCurator(GeminiWeeklyCurator):
    """One weekly model call grounded in public source descriptions when available."""

    def __init__(
        self,
        *,
        client=None,
        model: str | None = None,
        descriptions: dict[str, str] | None = None,
        context_loader=weekly_public_descriptions,
    ):
        super().__init__(client=client, model=model)
        self.descriptions = descriptions
        self.context_loader = context_loader

    def _descriptions(self, registry, period) -> dict[str, str]:
        """Public excerpts for the week; degraded context is an empty (still grounded) mapping."""
        if self.descriptions is not None:
            return self.descriptions
        try:
            return self.context_loader(registry, period)
        except Exception as exc:  # noqa: BLE001 - context failure must remain local
            log.warning("voice weekly: public source context degraded: %s", exc)
            return {}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.voice_weekly")
    p.add_argument("operation", choices=("weekly",))
    p.add_argument("--registry", default=config.VOICES_REGISTRY_PATH)
    p.add_argument("--state", default=settings.STATE_PATH)
    p.add_argument("--branch", default=os.environ.get("VOICE_ROUNDUP_BRANCH", "main"))
    p.add_argument("--remote", default="origin")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--period", help="explicit Sunday YYYY-MM-DD; dry-run only")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    if args.period and not args.dry_run:
        print("--period is inspection-only; add --dry-run", file=sys.stderr)
        return EXIT_CONFIG
    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    try:
        if args.dry_run:
            store: RoundupStore = FileRoundupStore(args.state)
            notifier = RecordingNotifier()
            curator = DeterministicWeeklyCurator()
        else:
            store = GitRoundupStore(
                args.state,
                page_path=settings.PAGE_PATH,
                branch=args.branch,
                remote=args.remote,
            )
            topic = os.environ.get("NTFY_TOPIC", "").strip()
            if not topic:
                print(
                    "NTFY_TOPIC is required for the weekly Voice digest",
                    file=sys.stderr,
                )
                return EXIT_CONFIG
            notifier = NtfyNotifier(topic, base_url=config.NTFY_BASE_URL)
            curator = GroundedGeminiWeeklyCurator()

        explicit_period = period_for_id(args.period) if args.period else None
        return publish_weekly_screened(
            registry,
            store=store,
            notifier=notifier,
            period=explicit_period,
            curator=curator,
            refresh=not args.dry_run,
            dry_run=args.dry_run,
        )
    except (GitRoundupError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())

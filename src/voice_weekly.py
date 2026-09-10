"""Grounded weekly Voice digest entry point.

The weekly relevance screen may use public feed/archive descriptions gathered
through the existing generic Voice adapters. It never fetches article bodies
and performs at most one Gemini screening/synthesis call per invocation.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from google.genai import types

from . import config
from .voice_digest import (
    MAX_REASON_CHARS,
    MAX_SUMMARY_CHARS,
    SUMMARY_MAX_TOKENS,
    WEEKLY_CAP,
    DeterministicWeeklyCurator,
    GeminiWeeklyCurator,
    WeeklyCuration,
    _already_surfaced,
    _clip,
    _voice_names,
    candidate_pool,
    publish_weekly_screened,
)
from .voices import roundup_settings as settings
from .voices.notify import NtfyNotifier, RecordingNotifier
from .voices.registry import RegistryError, load_registry
from .voices.roundup import period_for_id
from .voices.roundup_state import FileRoundupStore, GitRoundupError, GitRoundupStore, RoundupStore
from .voices.weekly_context import description_for_item, weekly_public_descriptions

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
        if self.descriptions is not None:
            return self.descriptions
        try:
            return self.context_loader(registry, period)
        except Exception as exc:  # noqa: BLE001 - context failure must remain local
            log.warning("voice weekly: public source context degraded: %s", exc)
            return {}

    def curate(self, candidates, registry, *, period) -> WeeklyCuration:
        pool = candidate_pool(candidates, period)
        if not pool:
            return WeeklyCuration(
                (), "No Core Voice pieces to catch up on this week.", {}, False
            )

        descriptions = self._descriptions(registry, period)
        payload_items = []
        for item in pool:
            source_description = description_for_item(item, descriptions)
            payload_items.append(
                {
                    "key": item.key,
                    "writer": " & ".join(_voice_names(item, registry)),
                    "publication": item.publication,
                    "published_at": (
                        item.published_at.isoformat() if item.published_at else None
                    ),
                    "headline": item.title,
                    "source_description": source_description or None,
                    "already_in_morning_daily": _already_surfaced(item, period),
                }
            )

        prompt = json.dumps(
            {
                "reader_goal": (
                    "A finite private weekly reading brief. The reader values substantive, "
                    "explanatory writing on world affairs, economics/markets, technology/AI, "
                    "institutions, politics and consequential social/cultural questions. "
                    "Attention is scarce; routine publication churn is not enough."
                ),
                "evidence_boundary": (
                    "Candidates contain publisher/feed metadata. source_description, when present, "
                    "is a public feed/archive excerpt or description and may be incomplete; it is "
                    "not proof that you have the full article. Ground every selection reason and "
                    "the weekly summary only in supplied fields."
                ),
                "selection_rules": [
                    "Select 1 to 3 pieces maximum; fewer is better when the week is weak.",
                    "Prefer work that the supplied headline and excerpt support as substantive, explanatory or materially consequential.",
                    "Prefer material significance and novelty over frequency, fame or recency alone.",
                    "Avoid redundant pieces covering substantially the same topic or apparent argument.",
                    "Prefer useful breadth across writers when quality is comparable.",
                    "De-prioritize pieces already surfaced in the morning Daily unless clearly exceptional.",
                    "When a candidate has no source_description, be more conservative and do not infer its argument from the headline alone.",
                    "Never invent article arguments, evidence, quotations or conclusions beyond the supplied metadata/excerpts.",
                ],
                "candidates": payload_items,
                "output": {
                    "selected_keys": "array of 1-3 exact candidate keys",
                    "summary": (
                        "one concise 120-180 word editorial brief explaining why this small "
                        "shortlist is worth attention, grounded only in supplied metadata and "
                        "public excerpts; do not pretend to have read unavailable full articles"
                    ),
                    "reasons": (
                        "object mapping each selected key to one short attention-based reason "
                        "grounded in supplied metadata/excerpt"
                    ),
                },
            },
            ensure_ascii=False,
        )

        cfg_kwargs: dict = {
            "system_instruction": (
                "You are the attention editor for Hermes, a private finite newspaper. Your job "
                "is to say no to most material. Screen for likely reader value, not author prestige "
                "or publication frequency. Public source descriptions are partial metadata, not "
                "full articles. Never invent article arguments, evidence, quotations or conclusions. "
                "Return strict JSON only."
            ),
            "response_mime_type": "application/json",
            "max_output_tokens": SUMMARY_MAX_TOKENS,
            "temperature": 0.15,
        }
        if "2.5" in self.model:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=256)
        response = self._client().models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
        if not response.text:
            raise RuntimeError("empty weekly screening response")
        raw = json.loads(response.text)
        if not isinstance(raw, dict):
            raise ValueError("weekly screening response must be an object")

        allowed = {item.key for item in pool}
        raw_keys = raw.get("selected_keys") or []
        if not isinstance(raw_keys, list):
            raise ValueError("selected_keys must be a list")
        selected: list[str] = []
        for key in raw_keys:
            if isinstance(key, str) and key in allowed and key not in selected:
                selected.append(key)
            if len(selected) >= WEEKLY_CAP:
                break
        if not selected:
            raise ValueError("weekly screening selected no valid candidates")

        summary = _clip(raw.get("summary"), MAX_SUMMARY_CHARS)
        if not summary:
            raise ValueError("weekly screening omitted summary")

        reasons: dict[str, str] = {}
        raw_reasons = raw.get("reasons") or {}
        if isinstance(raw_reasons, dict):
            for key in selected:
                reason = _clip(raw_reasons.get(key), MAX_REASON_CHARS)
                if reason:
                    reasons[key] = reason

        return WeeklyCuration(
            selected_keys=tuple(selected),
            summary=summary,
            reasons=reasons,
            model_used=True,
        )


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

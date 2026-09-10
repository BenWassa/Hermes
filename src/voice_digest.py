"""Weekly-only Voice notification product.

The routine Core collector remains silent.  This module adds two reader surfaces
on top of its bounded state:

* ``recent`` refreshes a quiet, finite shelf of recent Core writing.  It has no
  notifier and no model capability.
* ``weekly`` performs one bounded relevance-screening/synthesis call for one
  trusted weekly period, publishes one compact roundup, then sends at most one
  ntfy notification after the period claim and page are durable.

No article body is fetched here.  Screening uses only the already-collected
public metadata (writer, publication, date, headline, and whether the piece was
already surfaced in the morning Daily), so it must not invent article arguments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from . import config
from .voices import roundup_settings as settings
from .voices.names import clean_text
from .voices.notify import Alert, NtfyNotifier, NotifyError, RecordingNotifier
from .voices.registry import Registry, RegistryError, TIER_CORE, load_registry
from .voices.roundup import automatic_period, collect_daily, eligible_items, period_for_id, select_weekly
from .voices.roundup_state import (
    STATUS_EMPTY,
    STATUS_FAILED,
    STATUS_NOTIFIED,
    STATUS_PENDING,
    STATUS_SUPPRESSED,
    FileRoundupStore,
    GitRoundupError,
    GitRoundupStore,
    RoundupItem,
    RoundupState,
    RoundupStore,
)

log = logging.getLogger("the-daily.voices.digest")
UTC = dt.timezone.utc
TORONTO = ZoneInfo(config.TIMEZONE)

RECENT_PAGE_PATH = Path("docs/voices/recent/index.html")
WEEKLY_CAP = 3
MODEL_POOL_CAP = 30
RECENT_CAP = 40
MAX_SUMMARY_CHARS = 1800
MAX_REASON_CHARS = 360
SUMMARY_MAX_TOKENS = int(os.environ.get("VOICE_WEEKLY_SUMMARY_MAX_TOKENS", "1400"))

EXIT_OK = 0
EXIT_DEGRADED = 1
EXIT_CONFIG = 2


@dataclass(frozen=True)
class WeeklyCuration:
    selected_keys: tuple[str, ...]
    summary: str
    reasons: dict[str, str]
    model_used: bool = False
    fallback_reason: str = ""


class WeeklyCurator:
    def curate(
        self,
        candidates: list[RoundupItem],
        registry: Registry,
        *,
        period,
    ) -> WeeklyCuration:
        raise NotImplementedError


def _clip(value: object, limit: int) -> str:
    text = clean_text(str(value or ""))
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def _voice_names(item: RoundupItem, registry: Registry) -> list[str]:
    names: list[str] = []
    for voice_id in item.voice_ids:
        voice = registry.get(voice_id)
        if voice and voice.tier == TIER_CORE and voice.name not in names:
            names.append(voice.name)
    return names


def _already_surfaced(item: RoundupItem, period) -> bool:
    surfaced = item.first_morning_surfaced_at
    return bool(surfaced and period.start < surfaced <= period.cutoff)


def _pool_rank(item: RoundupItem, period) -> tuple:
    published = item.published_at or dt.datetime.min.replace(tzinfo=UTC)
    return (
        int(_already_surfaced(item, period)),
        -published.timestamp(),
        item.key,
    )


def candidate_pool(candidates: list[RoundupItem], period) -> list[RoundupItem]:
    """Bound model input while preferring pieces the morning Daily did not already surface."""
    return sorted(candidates, key=lambda item: _pool_rank(item, period))[:MODEL_POOL_CAP]


class DeterministicWeeklyCurator(WeeklyCurator):
    """Conservative fallback: small, broad, and biased toward work missed in the Daily."""

    def curate(self, candidates, registry, *, period) -> WeeklyCuration:
        state = RoundupState(
            collecting_since=period.start - dt.timedelta(seconds=1),
            items={item.key: item for item in candidates},
        )
        selected = select_weekly(
            state,
            registry,
            period,
            cap=WEEKLY_CAP,
            max_per_voice=1,
        )
        names: list[str] = []
        for item in selected:
            for name in _voice_names(item, registry):
                if name not in names:
                    names.append(name)
        if selected:
            people = ", ".join(names[:3])
            summary = (
                "Hermes kept this fallback deliberately small after the relevance screen was "
                "unavailable. It favors recent Core writing that was not already prominent in "
                "the morning Daily, with breadth across writers where possible"
                + (f": {people}." if people else ".")
            )
        else:
            summary = "No Core Voice writing cleared the conservative weekly fallback."
        return WeeklyCuration(
            selected_keys=tuple(item.key for item in selected),
            summary=summary,
            reasons={},
            model_used=False,
            fallback_reason="deterministic fallback",
        )


class GeminiWeeklyCurator(WeeklyCurator):
    """One model call that screens attention-worthiness and writes one weekly editorial brief."""

    def __init__(self, *, client=None, model: str | None = None):
        self.client = client
        self.model = model or config.CURATE_MODEL

    def _client(self):
        if self.client is not None:
            return self.client
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
        self.client = genai.Client(api_key=key)
        return self.client

    def curate(self, candidates, registry, *, period) -> WeeklyCuration:
        pool = candidate_pool(candidates, period)
        if not pool:
            return WeeklyCuration((), "No Core Voice pieces to catch up on this week.", {}, False)

        payload_items = []
        for item in pool:
            payload_items.append(
                {
                    "key": item.key,
                    "writer": " & ".join(_voice_names(item, registry)),
                    "publication": item.publication,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "headline": item.title,
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
                "selection_rules": [
                    "Select 1 to 3 pieces maximum; fewer is better when the week is weak.",
                    "Prefer work likely to add a new model, argument, explanation or important development.",
                    "Prefer material significance and novelty over frequency, fame or recency alone.",
                    "Avoid redundant pieces covering substantially the same apparent topic.",
                    "Prefer useful breadth across writers when quality is comparable.",
                    "De-prioritize pieces already surfaced in the morning Daily unless clearly exceptional.",
                    "Do not infer article arguments or facts that are not supported by the supplied metadata.",
                ],
                "candidates": payload_items,
                "output": {
                    "selected_keys": "array of 1-3 exact candidate keys",
                    "summary": (
                        "one concise 120-180 word editorial brief explaining why this small "
                        "shortlist is worth attention, grounded only in writer/headline/publication metadata; "
                        "do not pretend to have read unavailable article bodies"
                    ),
                    "reasons": "object mapping selected key to one short attention-based reason",
                },
            },
            ensure_ascii=False,
        )

        cfg_kwargs: dict = {
            "system_instruction": (
                "You are the attention editor for Hermes, a private finite newspaper. Your job is "
                "to say no to most material. Screen for likely reader value, not author prestige or "
                "publication frequency. You have metadata, not article bodies: never invent article "
                "arguments, evidence, quotations or conclusions. Return strict JSON only."
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


def screen_weekly(candidates, registry, *, period, curator: WeeklyCurator | None = None):
    fallback = DeterministicWeeklyCurator()
    curator = curator or GeminiWeeklyCurator()
    try:
        return curator.curate(candidates, registry, period=period)
    except Exception as exc:  # noqa: BLE001 - model failure must degrade locally
        log.warning("voice digest: weekly relevance screen degraded: %s", exc)
        result = fallback.curate(candidates, registry, period=period)
        return WeeklyCuration(
            selected_keys=result.selected_keys,
            summary=result.summary,
            reasons=result.reasons,
            model_used=False,
            fallback_reason=str(exc),
        )


def _format_day(value: dt.datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(TORONTO).strftime("%b %-d")


def _card(item: RoundupItem, registry: Registry, *, reason: str = "") -> str:
    names = " &amp; ".join(html.escape(name) for name in _voice_names(item, registry))
    meta = " · ".join(
        part
        for part in (
            names,
            html.escape(item.publication),
            _format_day(item.published_at),
        )
        if part
    )
    reason_html = f'<p class="reason">{html.escape(reason)}</p>' if reason else ""
    return (
        '<article class="piece">'
        f'<div class="meta">{meta}</div>'
        f'<h2>{html.escape(item.title)}</h2>'
        f'{reason_html}'
        f'<a class="open" href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener">'
        'Read original <span aria-hidden="true">→</span></a>'
        '</article>'
    )


def _page_shell(*, title: str, eyebrow: str, heading: str, dek: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta name="theme-color" content="#1a2744" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#101722" media="(prefers-color-scheme: dark)" />
  <title>{html.escape(title)}</title>
  <style>
    :root{{--paper:#faf8f3;--desk:#efece6;--ink:#17130d;--meta:#6c665c;--rule:#dcd6cc;--navy:#1a2744;--link:#1a2744}}
    @media(prefers-color-scheme:dark){{:root{{--paper:#151a22;--desk:#0e1219;--ink:#e9e3d5;--meta:#a39c8f;--rule:#2f3540;--navy:#a3b3d2;--link:#b7c5df}}}}
    *{{box-sizing:border-box}}html,body{{margin:0;background:var(--desk)}}
    body{{color:var(--ink);font-family:Georgia,serif;-webkit-font-smoothing:antialiased}}
    main{{min-height:100vh;min-height:100svh;max-width:680px;margin:0 auto;background:var(--paper);padding:calc(22px + env(safe-area-inset-top)) calc(20px + env(safe-area-inset-right)) calc(42px + env(safe-area-inset-bottom)) calc(20px + env(safe-area-inset-left))}}
    .brand{{font-family:Arial,sans-serif;color:var(--navy);text-decoration:none;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;display:inline-flex;align-items:center;min-height:44px}}
    header{{border-top:4px solid var(--navy);padding:18px 0 20px}}.eyebrow{{font-family:Arial,sans-serif;color:var(--meta);font-size:.68rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;margin-bottom:7px}}
    h1{{font-size:2.05rem;line-height:1.04;margin:0 0 8px;color:var(--navy)}}.dek{{margin:0;font-size:1rem;line-height:1.5}}
    .summary{{border-top:1px solid var(--rule);padding:20px 0;font-size:1.05rem;line-height:1.58}}
    .section-title{{font-family:Arial,sans-serif;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--meta);margin:22px 0 0}}
    .piece{{border-top:1px solid var(--rule);padding:18px 0 16px}}.meta{{font-family:Arial,sans-serif;color:var(--meta);font-size:.72rem;line-height:1.45;margin-bottom:7px}}
    h2{{font-size:1.28rem;line-height:1.2;margin:0}}.reason{{margin:8px 0 0;line-height:1.5;color:var(--meta)}}
    .open,.quiet-link{{color:var(--link);font-family:Arial,sans-serif;font-size:.78rem;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;min-height:44px;margin-top:7px}}
    .recent{{list-style:none;padding:0;margin:0;border-top:1px solid var(--rule)}}.recent li{{border-bottom:1px solid var(--rule);padding:13px 0}}
    .recent a{{color:var(--ink);text-decoration:none;font-weight:700;line-height:1.28}}.recent .meta{{margin:5px 0 0}}
    .empty{{border-top:1px solid var(--rule);color:var(--meta);line-height:1.55;padding:25px 0;margin:0}}
    a:focus-visible{{outline:2px solid var(--navy);outline-offset:3px}}
  </style>
</head>
<body><main>
<a class="brand" href="../../">The Daily</a>
<header><div class="eyebrow">{html.escape(eyebrow)}</div><h1>{html.escape(heading)}</h1><p class="dek">{html.escape(dek)}</p></header>
{body}
</main></body></html>"""


def render_weekly(period, selected, registry, curation: WeeklyCuration, *, suppressed=False) -> str:
    label = period.cutoff.astimezone(TORONTO).strftime("Week ending %B %-d, %Y")
    if suppressed:
        body = '<p class="empty">No roundup this week because Hermes did not have a trusted full-period collection baseline.</p>'
    elif not selected:
        body = '<p class="empty">Nothing this week cleared the deliberately small attention filter.</p>'
    else:
        cards = "".join(
            _card(item, registry, reason=curation.reasons.get(item.key, ""))
            for item in selected
        )
        body = (
            f'<div class="summary">{html.escape(curation.summary)}</div>'
            '<div class="section-title">Worth your time</div>'
            f'{cards}'
            '<a class="quiet-link" href="recent/">Browse all recent Core writing →</a>'
        )
    return _page_shell(
        title="Voices this week · The Daily",
        eyebrow="Voices this week",
        heading="A small weekly reading brief.",
        dek=f"{label}. One screen, one summary, no article-by-article alerts.",
        body=body,
    )


def recent_items(state: RoundupState, registry: Registry, *, cap: int = RECENT_CAP) -> list[RoundupItem]:
    items = []
    for item in state.items.values():
        if not item.title or not item.url:
            continue
        if not any(
            (voice := registry.get(voice_id)) is not None and voice.tier == TIER_CORE
            for voice_id in item.voice_ids
        ):
            continue
        items.append(item)
    items.sort(
        key=lambda item: (
            -(item.published_at.timestamp() if item.published_at else 0),
            item.key,
        )
    )
    return items[:cap]


def render_recent(state: RoundupState, registry: Registry) -> str:
    items = recent_items(state, registry)
    if not items:
        body = '<p class="empty">No recent Core writing has been collected yet.</p>'
    else:
        rows = []
        for item in items:
            names = " &amp; ".join(html.escape(name) for name in _voice_names(item, registry))
            meta = " · ".join(part for part in (names, html.escape(item.publication), _format_day(item.published_at)) if part)
            rows.append(
                '<li>'
                f'<a href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener">{html.escape(item.title)}</a>'
                f'<div class="meta">{meta}</div>'
                '</li>'
            )
        body = '<ul class="recent" aria-label="Recent Core writing">' + "".join(rows) + '</ul>'
    return _page_shell(
        title="Recent Voices · The Daily",
        eyebrow="Quiet shelf",
        heading="Recent Core writing.",
        dek="Collected for optional browsing. Nothing on this page creates a notification or unread obligation.",
        body=body,
    )


def build_weekly_alert(selected: list[RoundupItem], registry: Registry) -> Alert:
    names: list[str] = []
    for item in selected:
        for name in _voice_names(item, registry):
            if name not in names:
                names.append(name)
    people = ", ".join(names[:3])
    message = "Your one weekly Voices brief is ready."
    if people:
        message += f" This week: {people}."
    return Alert(
        title="Voices this week",
        message=message,
        click=urljoin(config.SITE_URL.rstrip("/") + "/", "voices/"),
    )


def publish_recent(registry: Registry, *, state_path: str, branch: str, remote: str, dry_run: bool) -> int:
    if dry_run:
        state = FileRoundupStore(state_path).load()
        print(f"recent: {len(recent_items(state, registry))} item(s); no write")
        return EXIT_OK
    store = GitRoundupStore(
        state_path,
        page_path=RECENT_PAGE_PATH,
        branch=branch,
        remote=remote,
    )
    state = store.load()
    page = render_recent(state, registry)
    if not store.publish(state, page, RECENT_PAGE_PATH, "chore(voices): refresh quiet recent shelf"):
        return EXIT_DEGRADED
    print(f"recent: published {len(recent_items(state, registry))} item(s)")
    return EXIT_OK


def publish_weekly_screened(
    registry: Registry,
    *,
    store: RoundupStore,
    notifier,
    now: dt.datetime | None = None,
    period=None,
    curator: WeeklyCurator | None = None,
    refresh: bool = True,
    dry_run: bool = False,
) -> int:
    now = now or dt.datetime.now(UTC)
    period = period or automatic_period(now)
    if period is None:
        print("weekly: outside publication/recovery window")
        return EXIT_OK

    if refresh and not dry_run:
        refreshed = collect_daily(registry, store=store, now=now)
        if refreshed.exit_code:
            log.warning("voice digest: final weekly collection degraded; using trusted retained state if available")

    state = store.load()
    if state.last_roundup and state.last_roundup.period_id == period.period_id:
        print(f"weekly: {period.period_id} already claimed; no notification")
        return EXIT_OK

    incomplete = state.collecting_since is None or state.collecting_since > period.start
    candidates = eligible_items(state, registry, period) if not incomplete else []

    if incomplete:
        curation = WeeklyCuration((), "", {}, False, "incomplete baseline")
        selected: list[RoundupItem] = []
        status = STATUS_SUPPRESSED
    elif not candidates:
        curation = WeeklyCuration((), "No Core Voice pieces to catch up on this week.", {}, False)
        selected = []
        status = STATUS_EMPTY
    else:
        use_curator = curator or (DeterministicWeeklyCurator() if dry_run else GeminiWeeklyCurator())
        curation = screen_weekly(candidates, registry, period=period, curator=use_curator)
        selected_by_key = {item.key: item for item in candidates}
        selected = [selected_by_key[key] for key in curation.selected_keys if key in selected_by_key][:WEEKLY_CAP]
        status = STATUS_PENDING if selected else STATUS_EMPTY

    if dry_run:
        print(json.dumps({
            "period": period.period_id,
            "candidates": len(candidates),
            "selected": [item.key for item in selected],
            "model_used": curation.model_used,
            "summary": curation.summary,
            "fallback_reason": curation.fallback_reason,
        }, indent=2))
        return EXIT_OK

    # The screening/model call above is deliberately outside this CAS retry loop:
    # one invocation performs at most one model request even if an unrelated writer
    # moves main while the period claim is being published.
    attempts = settings.PUSH_ATTEMPTS
    published_state: RoundupState | None = None
    final_selected = selected
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            state = store.load()
            if state.last_roundup and state.last_roundup.period_id == period.period_id:
                print(f"weekly: {period.period_id} claimed by another writer; no notification")
                return EXIT_OK
            final_selected = [state.items[key] for key in curation.selected_keys if key in state.items][:WEEKLY_CAP]
            if status == STATUS_PENDING and not final_selected:
                status = STATUS_EMPTY

        state.claim_period(
            period.period_id,
            cutoff=period.cutoff,
            claimed_at=now,
            selection_keys=[item.key for item in final_selected],
            status=status,
        )
        state.updated_at = now
        page = render_weekly(
            period,
            final_selected,
            registry,
            curation,
            suppressed=status == STATUS_SUPPRESSED,
        )
        if store.publish(
            state,
            page,
            settings.PAGE_PATH,
            f"chore(voices): publish screened roundup {period.period_id}",
        ):
            published_state = state
            break
        log.warning("voice digest: weekly publish race %d/%d", attempt, attempts)

    if published_state is None:
        return EXIT_DEGRADED
    if status in {STATUS_EMPTY, STATUS_SUPPRESSED} or not final_selected:
        return EXIT_OK

    try:
        notifier.send(build_weekly_alert(final_selected, registry))
    except NotifyError as exc:
        log.error("voice digest: weekly ntfy failed: %s", exc)
        published_state.mark_roundup(period.period_id, STATUS_FAILED)
        exit_code = EXIT_DEGRADED
    else:
        published_state.mark_roundup(period.period_id, STATUS_NOTIFIED)
        exit_code = EXIT_OK

    published_state.updated_at = now
    if not store.save_state(
        published_state,
        f"chore(voices): record screened roundup delivery {period.period_id}",
    ):
        log.warning("voice digest: delivery outcome did not persist; durable period claim remains terminal")
    return exit_code


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.voice_digest")
    p.add_argument("operation", choices=("recent", "weekly"))
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
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    if args.period and not args.dry_run:
        print("--period is inspection-only; add --dry-run", file=sys.stderr)
        return EXIT_CONFIG
    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG

    try:
        if args.operation == "recent":
            return publish_recent(
                registry,
                state_path=args.state,
                branch=args.branch,
                remote=args.remote,
                dry_run=args.dry_run,
            )

        if args.dry_run:
            store: RoundupStore = FileRoundupStore(args.state)
            notifier = RecordingNotifier()
        else:
            store = GitRoundupStore(
                args.state,
                page_path=settings.PAGE_PATH,
                branch=args.branch,
                remote=args.remote,
            )
            topic = os.environ.get("NTFY_TOPIC", "").strip()
            if not topic:
                print("NTFY_TOPIC is required for the weekly Voice digest", file=sys.stderr)
                return EXIT_CONFIG
            notifier = NtfyNotifier(topic, base_url=config.NTFY_BASE_URL)

        explicit_period = period_for_id(args.period) if args.period else None
        return publish_weekly_screened(
            registry,
            store=store,
            notifier=notifier,
            period=explicit_period,
            curator=DeterministicWeeklyCurator() if args.dry_run else None,
            refresh=not args.dry_run,
            dry_run=args.dry_run,
        )
    except (GitRoundupError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())

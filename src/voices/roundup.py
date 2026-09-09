"""Voices V2 daily collection and weekly Core roundup product.

The morning edition and this product are operationally independent. This
module fetches only registry-declared Core Voice sources, accumulates bounded
public metadata, and publishes one overwrite-only weekly page. It never calls
Gemini and never interprets the legacy ``notify`` switch.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from .. import config
from .adapters import FetchWindow, get_adapter
from .dedupe import syndication_keys_for
from .discover import DiscoveryResult, SourceStatus, plan_requests, resolve_observations, run_requests
from .http import RequestBudget, VoiceHttp
from .model import VoiceArticle
from .names import clean_text
from .notify import Alert, Notifier, NotifyError
from .registry import Registry, TIER_CORE
from . import roundup_settings as settings
from .roundup_state import (
    STATUS_EMPTY,
    STATUS_FAILED,
    STATUS_NOTIFIED,
    STATUS_PENDING,
    STATUS_SUPPRESSED,
    RoundupItem,
    RoundupState,
    RoundupStore,
)
from .urls import canonical_url, title_slug
from .window import EditionWindow

log = logging.getLogger("the-daily.voices.roundup")
UTC = dt.timezone.utc
TORONTO = ZoneInfo(config.TIMEZONE)

MODE_FREQUENT = "frequent"
MODE_RECONCILE = "reconcile"

SKIP_ALREADY_CLAIMED = "already_claimed"
SKIP_OUTSIDE_GRACE = "outside_grace"
SKIP_UNTRUSTED_SOURCES = "untrusted_sources"

_EDITION_RE = re.compile(
    r'<script\s+id=["\']edition["\']\s+type=["\']application/json["\']>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class WeeklyPeriod:
    period_id: str
    start: dt.datetime
    cutoff: dt.datetime


@dataclass
class CollectionOutcome:
    mode: str = MODE_FREQUENT
    planned: int = 0
    statuses: list[SourceStatus] = field(default_factory=list)
    budget: dict[str, int] = field(default_factory=dict)
    observed: int = 0
    changed: int = 0
    surfaced: int = 0
    pruned: int = 0
    baseline: bool = False
    persisted: bool = True
    push_attempts: int = 0

    @property
    def all_sources_failed(self) -> bool:
        return bool(self.statuses) and not any(status.ok for status in self.statuses)

    @property
    def exit_code(self) -> int:
        if self.all_sources_failed or not self.persisted:
            return 1
        return 0

    def diagnostics(self) -> dict:
        return {
            "mode": self.mode,
            "planned": self.planned,
            "requests": self.budget,
            "sources": [status.as_dict() for status in self.statuses],
            "observed": self.observed,
            "changed": self.changed,
            "surfaced": self.surfaced,
            "pruned": self.pruned,
            "baseline": self.baseline,
            "persisted": self.persisted,
            "push_attempts": self.push_attempts,
        }


@dataclass
class WeeklyOutcome:
    period_id: str = ""
    skipped: str = ""
    planned: int = 0
    statuses: list[SourceStatus] = field(default_factory=list)
    budget: dict[str, int] = field(default_factory=dict)
    candidates: int = 0
    selected: list[RoundupItem] = field(default_factory=list)
    published: bool = False
    empty: bool = False
    suppressed: bool = False
    notified: bool = False
    notify_failed: bool = False
    push_attempts: int = 0

    @property
    def all_sources_failed(self) -> bool:
        return bool(self.statuses) and not any(status.ok for status in self.statuses)

    @property
    def exit_code(self) -> int:
        if self.notify_failed:
            return 1
        if not self.skipped and not self.published:
            return 1
        return 0

    def diagnostics(self) -> dict:
        return {
            "period_id": self.period_id,
            "skipped": self.skipped,
            "planned": self.planned,
            "requests": self.budget,
            "sources": [status.as_dict() for status in self.statuses],
            "candidates": self.candidates,
            "selected": [item.key for item in self.selected],
            "published": self.published,
            "empty": self.empty,
            "suppressed": self.suppressed,
            "notified": self.notified,
            "notify_failed": self.notify_failed,
            "push_attempts": self.push_attempts,
        }


def core_registry(registry: Registry) -> Registry:
    """Product membership filter. Legacy ``notify`` is deliberately irrelevant."""
    return registry.for_tiers({TIER_CORE})


def core_voice_ids(article: VoiceArticle, registry: Registry) -> tuple[str, ...]:
    ids = []
    for voice_id in article.voice_ids:
        voice = registry.get(voice_id)
        if voice and voice.tier == TIER_CORE and voice_id not in ids:
            ids.append(voice_id)
    return tuple(ids)


def provider_cadence(provider: str) -> str:
    return settings.CADENCE.get(provider, MODE_RECONCILE)


def reconcile_due(state: RoundupState, now: dt.datetime) -> bool:
    if state.last_reconcile_at is None:
        return True
    return now - state.last_reconcile_at >= dt.timedelta(
        hours=settings.RECONCILE_HOURS
    )


def roundup_budget() -> RequestBudget:
    return RequestBudget(limits=dict(settings.REQUEST_BUDGET))


def discover_core(
    registry: Registry,
    state: RoundupState,
    *,
    now: dt.datetime,
    fetch: bool = True,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
) -> tuple[DiscoveryResult, int, str]:
    """Run one bounded Core-only source pass with a 48-hour overlap."""
    core = core_registry(registry)
    mode = MODE_RECONCILE if reconcile_due(state, now) else MODE_FREQUENT
    window = EditionWindow(
        since=now - dt.timedelta(hours=settings.LOOKBACK_HOURS),
        until=now,
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )
    fetch_window = FetchWindow(since=window.since, until=window.until)

    planned = plan_requests(core, fetch_window) if fetch else []
    if mode != MODE_RECONCILE:
        planned = [
            request
            for request in planned
            if provider_cadence(get_adapter(request.adapter).provider) == MODE_FREQUENT
        ]

    observations = []
    statuses: list[SourceStatus] = []
    spent: dict[str, int] = {}
    if planned:
        http = http or VoiceHttp(budget=budget or roundup_budget())
        observations, statuses = run_requests(planned, http, fetch_window)
        spent = http.budget.report()

    result = resolve_observations(core, observations, window)
    result.statuses = statuses
    result.budget = spent
    return result, len(planned), mode


def _syndication_copies(article: VoiceArticle, articles: list[VoiceArticle]) -> list[VoiceArticle]:
    if not article.syndication_group:
        return []
    return [
        other
        for other in articles
        if other is not article and other.syndication_group == article.syndication_group
    ]


def roundup_article_keys(
    article: VoiceArticle,
    related: list[VoiceArticle] | None = None,
) -> set[str]:
    """Reuse the exact identity and syndication semantics from V1."""
    keys = set(article.identity_keys) | {article.key}
    keys |= syndication_keys_for(article)
    for copy in related or []:
        keys |= set(copy.identity_keys) | {copy.key}
        keys |= syndication_keys_for(copy)
    return {key for key in keys if key}


def _valid_observations(
    result: DiscoveryResult,
    registry: Registry,
) -> list[tuple[VoiceArticle, tuple[str, ...], set[str]]]:
    out = []
    for article in result.fresh:
        voice_ids = core_voice_ids(article, registry)
        link = article.url or article.canonical_url
        if (
            not voice_ids
            or not article.title
            or not article.published_at
            or not canonical_url(link)
            or not article.syndication_primary
        ):
            continue
        copies = _syndication_copies(article, result.articles)
        out.append((article, voice_ids, roundup_article_keys(article, copies)))
    return out


def _parse_edition_date(value: object) -> dt.date | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%A, %B %d, %Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def morning_edition_urls(
    path: Path | str,
    *,
    now: dt.datetime,
) -> set[str] | None:
    """Return URLs in today's committed edition, or None when the signal is unknown."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _EDITION_RE.search(text)
    if not match:
        return None
    try:
        edition = json.loads(match.group(1).replace("<\\/", "</"))
    except (json.JSONDecodeError, TypeError):
        return None
    local_date = now.astimezone(TORONTO).date()
    if _parse_edition_date(edition.get("date")) != local_date:
        return None

    urls: set[str] = set()
    for card in edition.get("following", []) or []:
        if isinstance(card, dict) and card.get("link"):
            urls.add(str(card["link"]))
    for section in edition.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        for story in section.get("stories", []) or []:
            if isinstance(story, dict) and story.get("link"):
                urls.add(str(story["link"]))
    return urls


def _merge_result_into_state(
    state: RoundupState,
    observations,
    *,
    now: dt.datetime,
    edition_urls: set[str] | None,
    mode: str,
    source_healthy: bool,
) -> tuple[int, int, int]:
    changed = 0
    for article, voice_ids, keys in observations:
        _, did_change = state.observe(
            key=article.key,
            keys=keys,
            voice_ids=voice_ids,
            first_seen=now,
            published_at=article.published_at,
            title=clean_text(article.title),
            url=article.url or article.canonical_url,
            publication=clean_text(article.publication),
        )
        changed += int(did_change)

    surfaced = 0
    if edition_urls is not None:
        surfaced = state.mark_morning_urls(edition_urls, now)

    if mode == MODE_RECONCILE and source_healthy:
        state.last_reconcile_at = now
    pruned = state.prune(
        now,
        retention=dt.timedelta(days=settings.RETENTION_DAYS),
        max_entries=settings.MAX_ENTRIES,
    )
    return changed, surfaced, pruned


def collect_daily(
    registry: Registry,
    *,
    store: RoundupStore,
    now: dt.datetime | None = None,
    edition_path: Path | str = "docs/index.html",
    fetch: bool = True,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
    push_attempts: int | None = None,
) -> CollectionOutcome:
    """One silent daily collection. No notifier is accepted by this API."""
    now = now or dt.datetime.now(UTC)
    attempts_allowed = push_attempts or settings.PUSH_ATTEMPTS
    initial = store.load()

    result, planned, mode = discover_core(
        registry, initial, now=now, fetch=fetch, http=http, budget=budget
    )
    observations = _valid_observations(result, registry)
    edition_urls = morning_edition_urls(edition_path, now=now)
    source_healthy = not (bool(result.statuses) and not any(s.ok for s in result.statuses))

    outcome = CollectionOutcome(
        mode=mode,
        planned=planned,
        statuses=result.statuses,
        budget=result.budget,
        observed=len(observations),
    )
    if not source_healthy:
        log.error("voice roundup: all planned Core sources failed; baseline/state not advanced")
        return outcome

    for attempt in range(1, attempts_allowed + 1):
        outcome.push_attempts = attempt
        state = initial if attempt == 1 else store.load()
        before = state.fingerprint()

        if state.untrusted:
            state.collecting_since = now
            state.cold = False
            state.recovered = False
            state.problems = ()
            outcome.baseline = True

        changed, surfaced, pruned = _merge_result_into_state(
            state,
            observations,
            now=now,
            edition_urls=edition_urls,
            mode=mode,
            source_healthy=source_healthy,
        )
        outcome.changed = changed
        outcome.surfaced = surfaced
        outcome.pruned = pruned

        if state.fingerprint() == before and not outcome.baseline:
            outcome.persisted = True
            return outcome

        state.updated_at = now
        if store.save_state(state, "chore(voices): collect Core roundup state"):
            outcome.persisted = True
            return outcome
        log.warning(
            "voice roundup: collection push attempt %d/%d lost a race",
            attempt,
            attempts_allowed,
        )

    outcome.persisted = False
    return outcome


def period_for_id(period_id: str) -> WeeklyPeriod:
    cutoff_date = dt.date.fromisoformat(period_id)
    if cutoff_date.weekday() != 6:
        raise ValueError("roundup period id must be a Sunday date")
    cutoff_local = dt.datetime.combine(
        cutoff_date,
        dt.time(settings.CUTOFF_HOUR, 0),
        tzinfo=TORONTO,
    )
    start_local = cutoff_local - dt.timedelta(days=7)
    return WeeklyPeriod(
        period_id=period_id,
        start=start_local.astimezone(UTC),
        cutoff=cutoff_local.astimezone(UTC),
    )


def automatic_period(now: dt.datetime) -> WeeklyPeriod | None:
    """Sunday-after-cutoff or bounded Monday fallback; never stale midweek."""
    local = now.astimezone(TORONTO)
    if local.weekday() == 6 and local.hour >= settings.CUTOFF_HOUR:
        cutoff_date = local.date()
    elif local.weekday() == 0 and local.hour <= settings.MONDAY_GRACE_HOUR:
        cutoff_date = local.date() - dt.timedelta(days=1)
    else:
        return None
    return period_for_id(cutoff_date.isoformat())


def _surface_rank(item: RoundupItem, period: WeeklyPeriod) -> int:
    surfaced = item.first_morning_surfaced_at
    return int(bool(surfaced and period.start < surfaced <= period.cutoff))


def _item_priority(item: RoundupItem, period: WeeklyPeriod) -> tuple:
    published = item.published_at or dt.datetime.min.replace(tzinfo=UTC)
    return (
        _surface_rank(item, period),
        -published.timestamp(),
        title_slug(item.title),
        item.key,
    )


def eligible_items(
    state: RoundupState,
    registry: Registry,
    period: WeeklyPeriod,
) -> list[RoundupItem]:
    out: list[RoundupItem] = []
    if state.collecting_since is None:
        return out
    for item in state.items.values():
        if (
            item.published_at is None
            or not (period.start < item.published_at <= period.cutoff)
            or item.published_at < state.collecting_since
            or not item.title
            or not canonical_url(item.url)
        ):
            continue
        if not any(
            (voice := registry.get(voice_id)) is not None and voice.tier == TIER_CORE
            for voice_id in item.voice_ids
        ):
            continue
        out.append(item)
    return out


def _item_core_ids(item: RoundupItem, registry: Registry) -> tuple[str, ...]:
    return tuple(
        voice_id
        for voice_id in item.voice_ids
        if (voice := registry.get(voice_id)) is not None and voice.tier == TIER_CORE
    )


def select_weekly(
    state: RoundupState,
    registry: Registry,
    period: WeeklyPeriod,
    *,
    cap: int | None = None,
    max_per_voice: int | None = None,
) -> list[RoundupItem]:
    """Two breadth-first rounds, then newest-first display order."""
    cap = settings.CAP if cap is None else cap
    max_per_voice = (
        settings.MAX_PER_VOICE
        if max_per_voice is None
        else max_per_voice
    )
    candidates = eligible_items(state, registry, period)
    queues: dict[str, list[RoundupItem]] = {}
    for item in candidates:
        for voice_id in _item_core_ids(item, registry):
            queues.setdefault(voice_id, []).append(item)
    for queue in queues.values():
        queue.sort(key=lambda item: _item_priority(item, period))

    selected: list[RoundupItem] = []
    selected_keys: set[str] = set()
    counts: dict[str, int] = {voice_id: 0 for voice_id in queues}

    for round_index in range(max_per_voice):
        if len(selected) >= cap:
            break

        def best_remaining(voice_id: str) -> RoundupItem | None:
            if counts.get(voice_id, 0) > round_index:
                return None
            for item in queues[voice_id]:
                if item.key in selected_keys:
                    continue
                ids = _item_core_ids(item, registry)
                if all(counts.get(other, 0) < max_per_voice for other in ids):
                    return item
            return None

        ordered_voices = sorted(
            queues,
            key=lambda voice_id: (
                _item_priority(best_remaining(voice_id), period)
                if best_remaining(voice_id) is not None
                else (99, 0, "", ""),
                voice_id,
            ),
        )
        for voice_id in ordered_voices:
            if len(selected) >= cap:
                break
            if counts.get(voice_id, 0) > round_index:
                continue
            item = best_remaining(voice_id)
            if item is None:
                continue
            selected.append(item)
            selected_keys.add(item.key)
            for item_voice in _item_core_ids(item, registry):
                counts[item_voice] = counts.get(item_voice, 0) + 1

    selected.sort(
        key=lambda item: (
            -(item.published_at.timestamp() if item.published_at else 0),
            item.key,
        )
    )
    return selected[:cap]


def _voice_names(item: RoundupItem, registry: Registry) -> list[str]:
    names: list[str] = []
    for voice_id in _item_core_ids(item, registry):
        voice = registry.get(voice_id)
        if voice and voice.name not in names:
            names.append(voice.name)
    return names


def _format_day(value: dt.datetime) -> str:
    return value.astimezone(TORONTO).strftime("%b %-d")


def render_roundup(
    period: WeeklyPeriod,
    items: list[RoundupItem],
    registry: Registry,
    *,
    suppressed: bool = False,
) -> str:
    """Render the single current roundup page; no archive or dynamic state."""
    period_local = period.cutoff.astimezone(TORONTO)
    label = period_local.strftime("Week ending %B %-d, %Y")
    if suppressed:
        intro = (
            '<p class="empty">No roundup this week. The collection baseline '
            "was re-established during this period.</p>"
        )
    elif not items:
        intro = '<p class="empty">No Core Voice pieces to catch up on this week.</p>'
    else:
        cards = []
        for item in items[: settings.CAP]:
            names = " &amp; ".join(html.escape(name) for name in _voice_names(item, registry))
            meta_parts = [
                part for part in (
                    names,
                    html.escape(item.publication),
                    _format_day(item.published_at) if item.published_at else "",
                )
                if part
            ]
            meta = " · ".join(meta_parts)
            cards.append(
                '<article class="piece">'
                f'<div class="meta">{meta}</div>'
                f'<h2>{html.escape(item.title)}</h2>'
                f'<a class="open" href="{html.escape(item.url, quote=True)}" '
                'target="_blank" rel="noopener">Open original <span aria-hidden="true">→</span></a>'
                "</article>"
            )
        intro = "".join(cards)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta name="theme-color" content="#1a2744" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#101722" media="(prefers-color-scheme: dark)" />
  <title>Voices this week · The Daily</title>
  <style>
    :root {{
      --paper:#faf8f3; --desk:#efece6; --ink:#17130d; --meta:#6c665c;
      --rule:#dcd6cc; --navy:#1a2744; --link:#1a2744;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --paper:#151a22; --desk:#0e1219; --ink:#e9e3d5; --meta:#a39c8f;
        --rule:#2f3540; --navy:#a3b3d2; --link:#b7c5df;
      }}
    }}
    * {{ box-sizing:border-box; }}
    html,body {{ margin:0; background:var(--desk); }}
    body {{
      color:var(--ink); font-family:Georgia,serif; -webkit-font-smoothing:antialiased;
    }}
    main {{
      min-height:100vh; min-height:100svh; max-width:680px; margin:0 auto;
      background:var(--paper);
      padding:calc(22px + env(safe-area-inset-top)) calc(20px + env(safe-area-inset-right))
              calc(40px + env(safe-area-inset-bottom)) calc(20px + env(safe-area-inset-left));
    }}
    .brand {{
      font-family:Arial,sans-serif; color:var(--navy); text-decoration:none;
      font-size:.72rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
      display:inline-flex; align-items:center; min-height:44px;
    }}
    header {{ border-top:4px solid var(--navy); padding:18px 0 20px; }}
    .eyebrow {{
      font-family:Arial,sans-serif; color:var(--meta); font-size:.68rem; font-weight:700;
      letter-spacing:.13em; text-transform:uppercase; margin-bottom:7px;
    }}
    h1 {{ font-size:2.1rem; line-height:1.02; margin:0 0 8px; color:var(--navy); }}
    .dek {{ margin:0; font-size:1rem; line-height:1.45; }}
    .period {{
      margin-top:8px; font-family:Arial,sans-serif; color:var(--meta); font-size:.72rem;
    }}
    .piece {{ border-top:1px solid var(--rule); padding:20px 0 18px; }}
    .meta {{
      font-family:Arial,sans-serif; color:var(--meta); font-size:.72rem; line-height:1.45;
      margin-bottom:7px;
    }}
    h2 {{ font-size:1.35rem; line-height:1.18; margin:0; }}
    .open {{
      color:var(--link); font-family:Arial,sans-serif; font-size:.78rem; font-weight:700;
      text-decoration:none; display:inline-flex; align-items:center; min-height:44px;
      margin-top:8px;
    }}
    .open:focus-visible,.brand:focus-visible {{ outline:2px solid var(--navy); outline-offset:3px; }}
    .empty {{
      border-top:1px solid var(--rule); color:var(--meta); line-height:1.55;
      padding:28px 0; margin:0;
    }}
  </style>
</head>
<body>
  <main>
    <a class="brand" href="../">The Daily</a>
    <header>
      <div class="eyebrow">Voices this week</div>
      <h1>A few pieces worth catching up on.</h1>
      <p class="dek">A finite weekly selection from the Core Voices Hermes follows.</p>
      <div class="period">{html.escape(label)}</div>
    </header>
    <section aria-label="Weekly Core Voices selection">{intro}</section>
  </main>
</body>
</html>
"""


def build_roundup_alert(items: list[RoundupItem], registry: Registry) -> Alert:
    names: list[str] = []
    for item in items:
        for name in _voice_names(item, registry):
            if name not in names:
                names.append(name)
    shown = names[:3]
    if len(names) > 3:
        people = ", ".join(shown) + f" +{len(names) - 3}"
    elif len(shown) == 2:
        people = " & ".join(shown)
    else:
        people = ", ".join(shown)
    piece_word = "piece" if len(items) == 1 else "pieces"
    message = f"{len(items)} {piece_word}"
    if people:
        message += f" from {people}"
    message += "."
    click = urljoin(config.SITE_URL.rstrip("/") + "/", "voices/")
    return Alert(
        title="Voices this week",
        message=message,
        click=click,
        article_key="",
    )


def _merge_final_discovery(
    state: RoundupState,
    observations,
    *,
    now: dt.datetime,
    edition_urls: set[str] | None,
    mode: str,
    source_healthy: bool,
) -> None:
    _merge_result_into_state(
        state,
        observations,
        now=now,
        edition_urls=edition_urls,
        mode=mode,
        source_healthy=source_healthy,
    )


def publish_weekly(
    registry: Registry,
    *,
    store: RoundupStore,
    notifier: Notifier,
    now: dt.datetime | None = None,
    period: WeeklyPeriod | None = None,
    edition_path: Path | str = "docs/index.html",
    page_path: Path | str | None = None,
    fetch: bool = True,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
    push_attempts: int | None = None,
) -> WeeklyOutcome:
    """Publish/claim first, then send at most one weekly notification."""
    now = now or dt.datetime.now(UTC)
    page_path = page_path or settings.PAGE_PATH
    period = period or automatic_period(now)
    outcome = WeeklyOutcome()
    if period is None:
        outcome.skipped = SKIP_OUTSIDE_GRACE
        return outcome
    outcome.period_id = period.period_id

    initial = store.load()
    if initial.last_roundup and initial.last_roundup.period_id == period.period_id:
        outcome.skipped = SKIP_ALREADY_CLAIMED
        outcome.published = True
        outcome.empty = initial.last_roundup.status == STATUS_EMPTY
        outcome.suppressed = initial.last_roundup.status == STATUS_SUPPRESSED
        return outcome

    result, planned, mode = discover_core(
        registry, initial, now=now, fetch=fetch, http=http, budget=budget
    )
    observations = _valid_observations(result, registry)
    edition_urls = morning_edition_urls(edition_path, now=now)
    source_healthy = not (bool(result.statuses) and not any(s.ok for s in result.statuses))
    outcome.planned = planned
    outcome.statuses = result.statuses
    outcome.budget = result.budget

    attempts_allowed = push_attempts or settings.PUSH_ATTEMPTS
    selected: list[RoundupItem] = []
    final_state: RoundupState | None = None

    for attempt in range(1, attempts_allowed + 1):
        outcome.push_attempts = attempt
        state = initial if attempt == 1 else store.load()

        if state.last_roundup and state.last_roundup.period_id == period.period_id:
            outcome.skipped = SKIP_ALREADY_CLAIMED
            outcome.published = True
            outcome.empty = state.last_roundup.status == STATUS_EMPTY
            outcome.suppressed = state.last_roundup.status == STATUS_SUPPRESSED
            return outcome

        if state.untrusted:
            if not source_healthy:
                outcome.skipped = SKIP_UNTRUSTED_SOURCES
                return outcome
            state.collecting_since = now
            state.cold = False
            state.recovered = False
            state.problems = ()

        _merge_final_discovery(
            state,
            observations,
            now=now,
            edition_urls=edition_urls,
            mode=mode,
            source_healthy=source_healthy,
        )
        state.updated_at = now

        incomplete = state.collecting_since is None or state.collecting_since > period.start
        if incomplete:
            selected = []
            status = STATUS_SUPPRESSED
            outcome.suppressed = True
        else:
            selected = select_weekly(state, registry, period)
            outcome.candidates = len(eligible_items(state, registry, period))
            if not selected and not source_healthy:
                outcome.skipped = SKIP_UNTRUSTED_SOURCES
                return outcome
            status = STATUS_PENDING if selected else STATUS_EMPTY
            outcome.empty = not selected

        state.claim_period(
            period.period_id,
            cutoff=period.cutoff,
            claimed_at=now,
            selection_keys=[item.key for item in selected],
            status=status,
        )
        page = render_roundup(
            period, selected, registry, suppressed=status == STATUS_SUPPRESSED
        )
        if store.publish(
            state,
            page,
            page_path,
            f"chore(voices): publish roundup {period.period_id}",
        ):
            outcome.published = True
            outcome.selected = list(selected)
            final_state = state
            break
        log.warning(
            "voice roundup: weekly publish attempt %d/%d lost a race",
            attempt,
            attempts_allowed,
        )

    if not outcome.published or final_state is None:
        return outcome
    if outcome.empty or outcome.suppressed:
        return outcome

    alert = build_roundup_alert(selected, registry)
    try:
        notifier.send(alert)
    except NotifyError as exc:
        log.error("voice roundup: weekly ntfy failed: %s", exc)
        outcome.notify_failed = True
        final_state.mark_roundup(period.period_id, STATUS_FAILED)
    else:
        outcome.notified = True
        final_state.mark_roundup(period.period_id, STATUS_NOTIFIED)

    final_state.updated_at = now
    if not store.save_state(
        final_state,
        f"chore(voices): record roundup delivery {period.period_id}",
    ):
        log.warning(
            "voice roundup: delivery outcome did not persist; durable pending claim remains terminal"
        )
    return outcome

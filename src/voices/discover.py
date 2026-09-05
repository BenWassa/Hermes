"""Voice discovery: plan, fetch, attribute, canonicalize, report.

The orchestration contract for the whole foundation:

    registry + morning pool
        -> plan provider requests (batched, budgeted)
        -> fetch each request, failing locally
        -> attribute observations to Voices (evidence only)
        -> merge into canonical articles
        -> group syndicated copies
        -> classify against the edition window
        -> diagnostics

Three properties this file is responsible for:

**Cost does not scale with the number of Voices.** Sources are deduplicated
and batched per provider before anything is fetched: every Guardian
contributor rides in one query, every Perigon journalist in one, and a feed
two Voices share is fetched once. The morning pool is attributed for free.

**One broken source is one broken source.** Every fetch is wrapped; a failure
records a diagnostic and the run continues with everything else.

**A failure can be explained afterwards.** The result carries per-source
status, the request budget actually spent, rejected near-miss attributions,
and every observation behind every article.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from .. import config
from .adapters import AdapterError, FetchWindow, SourceRequest, get_adapter
from .dedupe import group_syndication, merge_observations
from .http import BudgetExceeded, RequestBudget, VoiceHttp
from .model import Author, Observation, VoiceArticle
from .names import clean_text, parse_byline
from .registry import Registry
from .resolve import Rejection, VoiceResolver
from .timeparse import parse_timestamp
from .urls import canonical_url
from .window import EditionWindow, WindowVerdict, partition

log = logging.getLogger("the-daily.voices")

UTC = dt.timezone.utc


@dataclass
class SourceStatus:
    """What happened to one planned request."""

    adapter: str
    label: str
    source_keys: tuple[str, ...]
    ok: bool
    items: int = 0
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "adapter": self.adapter,
            "label": self.label,
            "sources": list(self.source_keys),
            "ok": self.ok,
            "items": self.items,
            "error": self.error,
        }


@dataclass
class DiscoveryResult:
    """Everything one discovery run produced, including why."""

    articles: list[VoiceArticle] = field(default_factory=list)
    fresh: list[VoiceArticle] = field(default_factory=list)
    statuses: list[SourceStatus] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    budget: dict[str, int] = field(default_factory=dict)
    window: EditionWindow | None = None
    buckets: dict[str, list[VoiceArticle]] = field(default_factory=dict)

    @property
    def failures(self) -> list[SourceStatus]:
        return [s for s in self.statuses if not s.ok]

    def diagnostics(self) -> dict:
        """A compact, JSON-safe summary for build logs and later slices."""
        return {
            "window": {
                "since": self.window.since.isoformat() if self.window else None,
                "until": self.window.until.isoformat() if self.window else None,
            },
            "requests": self.budget,
            "sources": [s.as_dict() for s in self.statuses],
            "articles": len(self.articles),
            "fresh": len(self.fresh),
            "dropped": {
                verdict: len(items)
                for verdict, items in self.buckets.items()
                if verdict != WindowVerdict.FRESH.value and items
            },
            "rejected_attributions": [r.as_dict() for r in self.rejections],
        }


# --- the morning pool as observations -------------------------------------

def observations_from_pool(stories: list[dict]) -> list[Observation]:
    """Turn normalized morning-pool stories into observations.

    This is the cheapest discovery path Hermes has: the ordinary Guardian,
    NYT, Perigon and RSS fetch already ran, and its records now carry
    authorship. Attributing them costs zero provider requests, and it is how a
    followed writer's piece is found in a section Hermes was fetching anyway.
    """
    observations: list[Observation] = []
    for story in stories:
        link = story.get("link") or ""
        title = story.get("title") or ""
        if not link or not title:
            continue
        provider = story.get("provider") or ""
        authors = tuple(
            Author(
                name=clean_text(author.get("name", "")),
                provider=author.get("source_author_provider", "") or provider,
                provider_id=str(author.get("source_author_id") or ""),
            )
            for author in story.get("authors") or []
            if isinstance(author, dict) and (author.get("name") or author.get("source_author_id"))
        )
        if not authors and story.get("byline"):
            authors = tuple(Author(name=name) for name in parse_byline(story["byline"]))
        observations.append(
            Observation(
                adapter="pool",
                source_key=f"pool:{provider}" if provider else "pool",
                provider=provider,
                title=title,
                url=link,
                canonical_url=story.get("canonical_url") or canonical_url(link),
                description=story.get("description", ""),
                image=story.get("image"),
                publication=story.get("source", ""),
                paywalled=story.get("paywalled"),
                published_at=parse_timestamp(story.get("pub_date")),
                raw_published=str(story.get("pub_date") or ""),
                byline=story.get("byline", ""),
                authors=authors,
                provider_article_id=str(story.get("source_article_id") or ""),
                fetched_at=dt.datetime.now(UTC),
            )
        )
    return observations


# --- planning and running -------------------------------------------------

def plan_requests(registry: Registry, window: FetchWindow) -> list[SourceRequest]:
    """Collapse every enabled source into as few provider requests as possible."""
    by_type: dict[str, list] = {}
    for _key, owners in registry.sources_by_key().items():
        # One entry per source key; a feed two Voices share is planned once.
        voice, source = owners[0]
        by_type.setdefault(source.type, []).append((voice, source))

    planned: list[SourceRequest] = []
    for source_type, sources in sorted(by_type.items()):
        adapter = get_adapter(source_type)
        planned.extend(adapter.plan(sources, window))
    return planned


def default_budget() -> RequestBudget:
    """Per-run provider allowances.

    Perigon is the binding constraint: a personal-tier allowance measured in
    requests per month means one request per run, reconciliation only. The
    others are generous but still bounded, so a registry mistake shows up as a
    logged budget error instead of a quota incident.
    """
    return RequestBudget(limits=dict(config.VOICE_REQUEST_BUDGET))


def run_requests(
    planned: list[SourceRequest], http: VoiceHttp, window: FetchWindow
) -> tuple[list[Observation], list[SourceStatus]]:
    """Execute planned requests, degrading one source at a time."""
    observations: list[Observation] = []
    statuses: list[SourceStatus] = []
    for request in planned:
        adapter = get_adapter(request.adapter)
        try:
            items = adapter.fetch(request, http, window)
        except BudgetExceeded as exc:
            log.warning("voices: %s skipped, budget spent: %s", request.label, exc)
            statuses.append(SourceStatus(request.adapter, request.label, request.source_keys, False, error=str(exc)))
            continue
        except AdapterError as exc:
            log.warning("voices: source '%s' failed: %s", request.label, exc)
            statuses.append(SourceStatus(request.adapter, request.label, request.source_keys, False, error=str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - an adapter bug is still local
            log.warning("voices: source '%s' raised %s: %s", request.label, type(exc).__name__, exc)
            statuses.append(SourceStatus(request.adapter, request.label, request.source_keys, False, error=repr(exc)))
            continue
        observations.extend(items)
        statuses.append(SourceStatus(request.adapter, request.label, request.source_keys, True, items=len(items)))
    return observations, statuses


def resolve_observations(
    registry: Registry, observations: list[Observation], window: EditionWindow
) -> DiscoveryResult:
    """Attribute, merge, group and classify a set of observations."""
    resolver = VoiceResolver(registry)
    attributions, rejections = resolver.attribute_all(observations)

    # Only observations that actually resolved to a Voice become articles.
    # Everything else is morning-pool noise the ordinary editor already owns.
    kept_indexes = sorted(attributions)
    kept = [observations[i] for i in kept_indexes]
    remapped = {new: attributions[old] for new, old in enumerate(kept_indexes)}

    articles = merge_observations(kept, remapped)
    articles = group_syndication(articles)
    buckets = partition(articles, window)
    fresh = [a for a in buckets[WindowVerdict.FRESH.value] if a.syndication_primary]

    return DiscoveryResult(
        articles=articles,
        fresh=fresh,
        rejections=rejections,
        window=window,
        buckets=buckets,
    )


def discover(
    registry: Registry,
    *,
    pool: list[dict] | None = None,
    window: EditionWindow | None = None,
    http: VoiceHttp | None = None,
    budget: RequestBudget | None = None,
    fetch: bool = True,
) -> DiscoveryResult:
    """Full discovery run.

    ``fetch=False`` attributes the morning pool alone and makes no network
    requests at all, which is what the deterministic tests and a
    quota-exhausted run both use.
    """
    window = window or EditionWindow.ending_now(
        lookback=dt.timedelta(hours=config.VOICE_LOOKBACK_HOURS),
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )
    fetch_window = FetchWindow(since=window.since, until=window.until)

    observations = observations_from_pool(pool or [])
    statuses: list[SourceStatus] = []
    spent: dict[str, int] = {}

    if fetch and registry.active:
        http = http or VoiceHttp(budget=budget or default_budget())
        planned = plan_requests(registry, fetch_window)
        log.info(
            "voices: %d voice(s), %d source(s) -> %d provider request(s)",
            len(registry.active), len(registry.sources_by_key()), len(planned),
        )
        fetched, statuses = run_requests(planned, http, fetch_window)
        observations.extend(fetched)
        spent = http.budget.report()

    result = resolve_observations(registry, observations, window)
    result.statuses = statuses
    result.budget = spent

    log.info(
        "voices: %d article(s) resolved, %d fresh, %d source failure(s), %d provider request(s)",
        len(result.articles), len(result.fresh), len(result.failures), sum(spent.values()),
    )
    for failure in result.failures:
        log.warning("voices: degraded source %s (%s): %s", failure.label, failure.adapter, failure.error)
    return result

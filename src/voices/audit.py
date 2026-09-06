"""Bounded live audit for Voice sources.

Deterministic tests must never depend on the network, so live checking lives
here instead: a small operator command that exercises the real sources once,
reports what each returned, and never writes anything.

    python -m src.voices.audit                 # validate + report the plan
    python -m src.voices.audit --live          # actually fetch every source
    python -m src.voices.audit --live --voice conrad-black
    python -m src.voices.audit journalist "Jonathan Haidt"

The last form resolves a Perigon journalist id so it can be pasted into the
registry, which is the one manual step a cross-publication Voice needs. It
costs one Perigon request, so it is a deliberate command rather than something
the build does on its own.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys

from .. import config
from .adapters import FetchWindow
from .discover import default_budget, discover, plan_requests
from .http import VoiceHttp
from .registry import RegistryError, load_registry
from .window import EditionWindow

log = logging.getLogger("the-daily.voices.audit")

PERIGON_JOURNALISTS_URL = "https://api.perigon.io/v1/journalists/all"


def _window() -> EditionWindow:
    return EditionWindow.ending_now(
        lookback=dt.timedelta(hours=config.VOICE_LOOKBACK_HOURS),
        future_skew=dt.timedelta(minutes=config.VOICE_FUTURE_SKEW_MINUTES),
    )


def _print_plan(registry, window: EditionWindow) -> int:
    planned = plan_requests(registry, FetchWindow(since=window.since, until=window.until))
    print(f"voices:  {len(registry.active)} enabled of {len(registry.voices)}")
    print(f"sources: {len(registry.sources_by_key())} distinct")
    print(f"plan:    {len(planned)} provider request(s) per run")
    by_provider: dict[str, int] = {}
    for request in planned:
        from .adapters import get_adapter

        provider = get_adapter(request.adapter).provider
        by_provider[provider] = by_provider.get(provider, 0) + 1
    for provider, count in sorted(by_provider.items()):
        limit = config.VOICE_REQUEST_BUDGET.get(provider)
        print(f"  {provider}: {count} request(s) per run (budget {limit})")
    for request in planned:
        print(f"  - [{request.adapter}] {request.label} -> {', '.join(request.source_keys)}")
    return 0


def _run_live(registry, window: EditionWindow, voice_id: str | None) -> int:
    if voice_id:
        registry = type(registry)(
            voices=tuple(v for v in registry.voices if v.id == voice_id), version=registry.version
        )
        if not registry.voices:
            print(f"no such voice: {voice_id}", file=sys.stderr)
            return 2

    result = discover(registry, window=window, budget=default_budget())

    print(f"\nrequests spent: {result.budget or '{}'}")
    print("\nsources:")
    for status in result.statuses:
        mark = "ok " if status.ok else "FAIL"
        detail = f"{status.items} item(s)" if status.ok else status.error
        print(f"  [{mark}] {status.adapter:<22} {status.label[:60]:<60} {detail}")

    print(f"\narticles resolved: {len(result.articles)} ({len(result.fresh)} inside the window)")
    for article in result.articles[:25]:
        voices = ", ".join(article.voice_ids) or "-"
        print(f"\n  {article.title[:88]}")
        print(f"    voice(s):   {voices}")
        print(f"    published:  {article.published_at}")
        print(f"    link:       {article.canonical_url}")
        print(f"    via:        {', '.join(article.discovered_via)}")
        for voice_id_ in article.voice_ids:
            evidence = article.evidence_for(voice_id_)
            if evidence:
                print(f"    evidence:   {voice_id_} <- {evidence.evidence} ({evidence.detail})")
        if not article.syndication_primary:
            print(f"    syndicated copy of {article.syndicated_from}")

    dropped = {k: len(v) for k, v in result.buckets.items() if k != "fresh" and v}
    if dropped:
        print(f"\noutside the window: {dropped}")
    if result.rejections:
        print("\nrejected attributions (near misses, kept for diagnosis):")
        for rejection in result.rejections[:20]:
            print(f"  {rejection.reason}: {rejection.detail}")

    return 1 if result.failures else 0


def _resolve_journalist(name: str) -> int:
    key = os.environ.get("PERIGON_API_KEY")
    if not key:
        print("PERIGON_API_KEY not set", file=sys.stderr)
        return 2
    http = VoiceHttp(budget=default_budget())
    try:
        response = http.get(
            PERIGON_JOURNALISTS_URL, provider="perigon", params={"apiKey": key, "name": name, "size": 10}
        )
        results = response.json().get("results") or response.json().get("journalists") or []
    except Exception as exc:  # noqa: BLE001 - operator command, report and stop
        print(f"perigon journalist lookup failed: {exc}", file=sys.stderr)
        return 1
    if not results:
        print(f"no Perigon journalist matched {name!r}")
        return 1
    print(f"{len(results)} match(es) for {name!r}. Paste the right id into data/voices.json:\n")
    for entry in results:
        print(json.dumps({
            "id": entry.get("id"),
            "name": entry.get("fullName") or entry.get("name"),
            "title": entry.get("title"),
            "top_sources": [s.get("name") for s in (entry.get("topSources") or [])[:5]],
        }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.voices.audit", description=__doc__)
    parser.add_argument("command", nargs="?", default="check", choices=["check", "journalist"])
    parser.add_argument("name", nargs="?", help="journalist name to resolve (with 'journalist')")
    parser.add_argument("--live", action="store_true", help="actually fetch every enabled source")
    parser.add_argument("--voice", help="limit a live run to one voice id")
    parser.add_argument("--registry", default=config.VOICES_REGISTRY_PATH)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "journalist":
        if not args.name:
            parser.error("journalist requires a name")
        return _resolve_journalist(args.name)

    try:
        registry = load_registry(args.registry, strict=False)
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    window = _window()
    print(f"registry: {args.registry}")
    print(f"window:   {window.since.isoformat()} .. {window.until.isoformat()}\n")
    code = _print_plan(registry, window)
    if not args.live:
        print("\n(dry run; pass --live to fetch)")
        return code
    return _run_live(registry, window, args.voice)


if __name__ == "__main__":
    sys.exit(main())

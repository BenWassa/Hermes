# The Daily

An autonomous overnight pipeline that assembles a personalized Toronto morning
newspaper, renders it as a static web page, and pushes a notification after a
successful publication. The primary build targets 05:17 America/Toronto, with
bounded same-morning recovery attempts if GitHub's scheduler is delayed or drops
a run. World and business news come from the Guardian, NYT, and Perigon APIs;
Toronto local news comes from RSS. Google Gemini dedupes, sections, ranks, and
summarizes. The result deploys to GitHub Pages and an ntfy.sh push links straight
to it.

> v2 of this repo. The previous React/Firebase intelligence dashboard ("Hermes
> v1") is preserved under [archive/v1-hermes/](archive/v1-hermes/) and tagged
> `v1-final`. Product authority: [PRODUCT.md](PRODUCT.md). Voices V2 authority:
> [VOICES_V2.md](VOICES_V2.md).

## Pipeline

```text
weather -> fetch -> normalize -> discover Voices -> curate (Gemini) -> select Following -> resolve images -> render -> deploy -> notify
```

| Module | Role |
|---|---|
| [src/weather.py](src/weather.py) | Open-Meteo Toronto forecast (no key) |
| [src/fetch.py](src/fetch.py) | Guardian + NYT + Perigon APIs, Toronto RSS (graceful per-source failure) |
| [src/normalize.py](src/normalize.py) | Unify sources into one story schema while preserving authorship |
| [src/curate.py](src/curate.py) | One Gemini call: dedupe, section, rank, summarize, flag |
| [src/opinion.py](src/opinion.py) | Deterministic finite Following selection + dedupe from Today's Opinion |
| [src/images.py](src/images.py) | Keep source thumbnails; suppress on sensitive stories |
| [src/render.py](src/render.py) | Inject edition JSON into the HTML template |
| [src/build.py](src/build.py) | Morning-edition orchestrator |
| [src/voices/](src/voices/) | Voice registry, adapters, authorship, canonical identity, dedupe/syndication and bounded state |
| [src/voice_roundup.py](src/voice_roundup.py) | Silent Core collection and durable weekly-period state |
| [src/voice_digest.py](src/voice_digest.py) | Quiet recent shelf + screened weekly digest; sole proactive Voice notification path |
| [src/voice_watch.py](src/voice_watch.py) | Legacy release-watch engine retained for manual read-only diagnostics; not scheduled |
| [template/index.template.html](template/index.template.html) | The newspaper UI (vanilla HTML/CSS/JS) |

## Voices

A **Voice** is a person, not a publication. Hermes can follow a writer and find
their new work wherever it can establish authorship reliably: a personal feed,
a publication author archive, the Guardian contributor API, an aggregator
journalist identity, or an outlet already present in the morning fetch.

[data/voices.json](data/voices.json) holds reviewed registry/source configuration.
`tier` is the product authority. The current roster and Core / Selective /
Discovery semantics are locked in [VOICES_V2.md](VOICES_V2.md); [VOICES.md](VOICES.md)
remains the implementation authority for identity, source, evidence, canonical
article and state-safety machinery.

### Current notification contract

There are **no routine per-article Voice notifications**.

Core writing is collected silently into bounded state and appears on a finite
`/voices/recent/` shelf for optional browsing. There are no unread counters,
badges, streaks, backlog prompts, or article-by-article Gemini calls.

Once per weekly period Hermes screens the collected Core writing for likely
attention-worthiness. Publication by a Core Voice is only collection
eligibility; it does not guarantee a roundup slot. Screening favors substantive
or explanatory value, material relevance, novelty versus the rest of the week,
non-redundancy, and useful breadth. The digest is deliberately small: at most
three pieces, and fewer when the week is weak.

The weekly job performs at most one screening/synthesis model call per
invocation, publishes one compact `/voices/` brief, then may send **one** ntfy
notification after the weekly period/page claim is durable. If model screening
fails, Hermes falls back to a conservative deterministic max-three shortlist.
Only the weekly Voice job receives both Gemini and ntfy capability.

The morning Daily notification is independent and remains once per published
edition.

### Adding a Voice

A registry entry separates intellectual membership from technical source
availability. Example:

```jsonc
{
  "id": "jane-doe",
  "name": "Jane Doe",
  "tier": "core",
  "enabled": true,
  "notify": false,                  // legacy compatibility field; not product authority
  "aliases": ["J. A. Doe"],
  "provider_ids": [
    {"provider": "guardian", "id": "profile/janedoe"}
  ],
  "byline_publications": ["nytimes.com"],
  "sources": [
    {
      "id": "jane-newsletter",
      "type": "rss",
      "url": "https://janedoe.example/feed",
      "publication": "Jane Doe",
      "authorship": "scope"
    }
  ]
}
```

Then validate before committing:

```bash
python -m src.voices.audit
python -m src.voices.audit --live
python -m src.voices.audit --live --voice jane-doe
```

Changing `notify` must not promote, demote, include, or exclude a Voice from the
V2 product. `tier` defines product membership; `enabled` and source-level
`enabled` describe operational reachability.

### Identity and sources

**Identity** decides whether an article belongs to a Voice. **Sources** decide
where Hermes looks. They remain separate so a feed cannot accidentally grant
authorship to every item it returns.

| Field | Evidence it grants | Use it when |
|---|---|---|
| `provider_ids` | strongest; valid anywhere for that provider | provider has a stable contributor/journalist id |
| `sources[].authorship: "scope"` | the source itself is the proof | personal feed or publication author archive |
| `sources[].authorship: "byline"` | entry byline must match | multi-author publication feed |
| `byline_publications` | byline match on those hosts only | writer appears in an outlet Hermes already fetches |

A name is matched against an item's **byline**, never its title, description or
a provider's "people mentioned" field. Aliases are identity evidence, not
search terms. Prefer provider IDs and source-scoped structural evidence whenever
available.

### Source types and lifecycle

| `type` | Needs | Request shape |
|---|---|---|
| `rss` | `url` | one per distinct feed, shared across Voices |
| `guardian_contributor` | `tag` | one batched request for contributors |
| `perigon_journalist` | `journalist_id` | one batched request for journalists |
| `author_page` | `url` (+ optional structural fields) | one per distinct first-party archive |

Resolve a Perigon journalist id once and store the stable result:

```bash
python -m src.voices.audit journalist "Jane Doe"
```

To disable a failing source without changing intellectual membership, set
`"enabled": false` on that source. Do not demote a Core Voice because a source
is blocked, stale or temporarily unreachable. Remove a source only after its
replacement is validated.

### Adding a generic adapter

Do not add writer-specific scrapers. A new source family belongs under
`src/voices/adapters/` and must work for any registry entry satisfying its
schema.

1. Implement stable `source_key`, bounded request planning, public-metadata fetch
   and normalized `Observation` records. Route network calls through `VoiceHttp`.
2. Register the adapter and required registry fields. Prefer provider IDs or
   first-party structural metadata; fail closed when authorship is uncertain.
3. Add it to the relevant bounded cadence/request policy.
4. Add recorded fixtures and deterministic tests for success, malformed data,
   attribution, dedupe and partial failure. CI must not depend on live network.
5. Run one bounded live audit from the actual GitHub Actions environment before
   shipping the source family.

### Provider requirements and boundaries

Quotas are external contracts. Re-check providers before materially changing
cadence.

- **Guardian Open Platform:** `GUARDIAN_API_KEY` required for Guardian-backed
  news and contributor discovery.
- **NYT Top Stories:** `NYT_API_KEY` required for the morning pool.
- **Perigon:** `PERIGON_API_KEY` is optional and scarce; Voice reconciliation is
  bounded and batched.
- **RSS / first-party author pages:** no API key, but poll conservatively. A
  403/429 is a source failure, not permission to evade access controls.
- **ntfy:** `NTFY_TOPIC` is used by the morning Daily push and the single weekly
  Voice digest. Routine Core collection and manual Voice inspection do not
  receive the topic.

Hermes stores public metadata needed to identify and render an item, then links
to the publisher's article. It does not fetch or store paywalled article bodies
and never attempts to bypass subscription controls.

The important request invariant is that cost scales with distinct source
families/URLs, not `Voice count × providers × frequent polls`.

### Troubleshooting Voice discovery

- **A Voice went quiet:** `python -m src.voices.audit --live --voice <id>`.
- **A source returns 401/403/429:** verify credentials/provider policy. Do not
  add retry storms or scrape around restrictions.
- **A source broke structurally:** disable only that source while investigating;
  other sources and ordinary Opinion continue.
- **An article was found but not shown:** inspect freshness/attribution output and
  the finite morning/weekly selection rules.
- **A wrong article was attributed:** tighten source scope/provider identity;
  never compensate with title/description keyword matching.

### Voice operator commands

The old release-watch engine remains useful for diagnostics, but its production
workflow always invokes it in read-only dry-run mode and gives it neither
Gemini nor ntfy credentials.

```bash
python -m src.voice_watch --dry-run
python -m src.voices.audit --live --voice <id>
python -m src.voice_roundup collect --dry-run
python -m src.voice_digest recent --dry-run
python -m src.voice_digest weekly --dry-run --period YYYY-MM-DD
```

Do not use the legacy `voice_watch --smoke` command for routine validation: it
can send a labeled ntfy test when a topic is deliberately supplied locally.
The shipped GitHub workflow does not expose that capability.

`data/voice_watch_state.json` and historical `/voices/articles/...` pages are
retained for compatibility with #26-era history. They no longer drive a
scheduled notification product. Current weekly collection/period authority is
`data/voice_roundup_state.json`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite is deterministic and never touches the network: adapters run against
recorded fixtures and Chromium tests render local artifacts. CI runs on pushes
and pull requests via [.github/workflows/ci.yml](.github/workflows/ci.yml).
Live source checking is deliberately separate.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.build
open docs/index.html
```

## Configuration

Secrets come from the environment or GitHub repository secrets; `PAGES_URL` is
a repository variable.

| Var | Needed for |
|---|---|
| `GEMINI_API_KEY` | morning curation + weekly Voice screening/synthesis |
| `GUARDIAN_API_KEY` | Guardian news + Core Voice contributor collection |
| `NYT_API_KEY` | NYT morning pool |
| `PERIGON_API_KEY` | optional Perigon news + bounded Voice reconciliation |
| `NTFY_TOPIC` | morning Daily push + one weekly Voice digest |
| `PAGES_URL` | published-site links/cache busting |
| `CURATE_MODEL` | optional Gemini model override |
| `VOICE_LOOKBACK_HOURS` | morning Voice discovery window |
| `NTFY_BASE_URL` | optional ntfy-compatible host override |

Legacy `VOICE_WATCH_*` tunables remain only for manual release-watch diagnostics
and compatibility tests; they do not configure a scheduled per-article alert
product.

## Deployment (GitHub Pages + Actions)

- [.github/workflows/build.yml](.github/workflows/build.yml) — targets 05:17
  America/Toronto, with 05:37, 06:17 and 07:17 bounded recoveries. It no-ops
  before source/model work once that Toronto-calendar edition exists.
- [.github/workflows/notify.yml](.github/workflows/notify.yml) — sends the one
  morning Daily push only after a run actually publishes today's edition.
- [.github/workflows/voice-roundup.yml](.github/workflows/voice-roundup.yml) —
  daily silent Core collection + quiet recent-shelf refresh; weekly screened
  digest publication and the sole proactive Voice push.
- [.github/workflows/voice-watch.yml](.github/workflows/voice-watch.yml) — manual
  read-only Core-source/identity inspection only. No schedule, Gemini secret or
  ntfy topic.

The Daily and Voice roundup use independent non-cancelling concurrency groups
and disjoint write paths, with bounded git retry/compare-and-swap behavior.
[tests/test_workflows.py](tests/test_workflows.py) locks the credential and
notification boundaries.

Pages serves `docs/` on `main` at `https://BenWassa.github.io/Hermes/`.

## First-run checklist

- Get Gemini, Guardian and NYT API keys; add Perigon only when used.
- Pick a hard-to-guess ntfy topic and subscribe the intended client.
- Add repository secrets and the `PAGES_URL` repository variable.
- Enable GitHub Pages from `main` / `docs`.
- Run `python -m src.voices.audit` and one bounded live Voice audit.
- Trigger `Build The Daily`; confirm one edition and one morning push.
- Use `voice_watch --dry-run`, not a notification smoke, for routine Voice
  inspection.
- Inspect a weekly digest with `voice_digest weekly --dry-run --period ...`
  before deliberately testing live weekly delivery.

## Notes

- House style: factual, headline-first, 2–3 sentence summaries, no em dashes.
- Every opened morning story carries an **Ask AI** control for deeper briefing.
- Sensitive stories render text-only by design.
- Source thumbnails are hotlinked; some may rot. Caching remains a later item.

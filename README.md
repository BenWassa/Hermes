# The Daily

An autonomous overnight pipeline that assembles a personalized Toronto morning
newspaper, renders it as a static web page, and pushes a notification after a
successful publication. The primary build targets 05:17 America/Toronto, with
bounded same-morning recovery attempts if GitHub's scheduler is delayed or drops
a run. World and business news come from the Guardian, NYT, and Perigon APIs
(Perigon aggregates FT, Reuters, Bloomberg and thousands more, so the business
desk reads like a professional's, not just one paper); Toronto local news comes
from RSS. Google Gemini (`gemini-2.5-flash`, free tier) dedupes, sections, ranks,
and summarizes; a sensitivity rule keeps hard news text-only. The result deploys
to GitHub Pages and an ntfy.sh push links straight to it.

> v2 of this repo. The previous React/Firebase intelligence dashboard ("Hermes
> v1") is preserved under [archive/v1-hermes/](archive/v1-hermes/) and tagged
> `v1-final`. Product spec: [PRD_daily_newspaper.md](PRD_daily_newspaper.md);
> task-level build spec: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).

## Pipeline

```
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
| [src/build.py](src/build.py) | Orchestrator (single entrypoint) |
| [src/voices/](src/voices/) | Followed writers: registry, source adapters, authorship resolution, article identity, watcher state |
| [src/voice_watch.py](src/voice_watch.py) | Release-time alerts for followed writers (separate hourly job, never rebuilds the edition) |
| [template/index.template.html](template/index.template.html) | The newspaper UI (vanilla HTML/CSS/JS) |

## Voices (followed writers)

A **Voice** is a person, not a publication. Hermes can follow a writer and find
their new work wherever it can establish authorship reliably: a personal feed,
a publication author archive, the Guardian's contributor API, an aggregator's
journalist identity, or an outlet already present in the ordinary morning
fetch. The design and implementation authority is [VOICES.md](VOICES.md).

The registry in [data/voices.json](data/voices.json) is the source of truth.
For this one-reader product, following someone is a reviewed config change: the
overnight GitHub Actions build is what does the fetching, and a browser toggle
could not tell it anything.

### Adding a Voice

```jsonc
{
  "id": "jane-doe",                 // lowercase, hyphenated, stable forever
  "name": "Jane Doe",
  "enabled": true,
  "notify": true,                   // only if at least one watcher source exists
  "aliases": ["J. A. Doe"],         // other spellings of the same person
  "provider_ids": [                 // stable per-writer ids, strongest evidence
    {"provider": "guardian", "id": "profile/janedoe"}
  ],
  "byline_publications": ["nytimes.com"],   // hosts where her byline alone is trusted
  "sources": [                      // where discovery actively goes looking
    {
      "id": "jane-newsletter",     // stable operator label; do not casually rename
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
python -m src.voices.audit                    # schema + request plan, no network
python -m src.voices.audit --live             # fetch each configured source once
python -m src.voices.audit --live --voice jane-doe
```

A Voice may be deliberately **morning-only**. `byline_publications` and provider
identity found in the ordinary morning pool can attribute a writer without any
extra watcher source. In that case set `"notify": false`; release alerts are not
magic and the watcher does not rerun the full morning NYT/Perigon/Guardian pool.
The shipped registry has a regression test that rejects `notify: true` when an
enabled production Voice has no active watcher source.

### Identity and sources

**Identity** decides whether an article is hers. **Sources** decide where
Hermes looks. They stay separate so an ordinary morning response can attribute
work at no extra request cost, and so registering a feed does not accidentally
blanket-grant authorship to every item on it.

| Field | Evidence it grants | Use it when |
|---|---|---|
| `provider_ids` | strongest; valid anywhere for that provider | the provider has a stable contributor/journalist id |
| `sources[].authorship: "scope"` | the source itself is the proof | a personal feed, or a publication's own author archive |
| `sources[].authorship: "byline"` | the entry's byline must match | a multi-author publication feed |
| `byline_publications` | byline match on those hosts only | she writes for an outlet Hermes already fetches |

A name is only matched against an item's **byline**, never its title,
description, or a provider's "people mentioned" field. A byline match is only
accepted inside a declared scope. Set `"require_evidence": "provider_id"` on a
genuinely ambiguous name to refuse byline evidence altogether.

Aliases are identity evidence, not search terms. Add only spellings that really
refer to the same person. Provider IDs and source URLs are stronger and should
be preferred whenever the source offers them.

### Source types and lifecycle

| `type` | Needs | Request shape |
|---|---|---|
| `rss` | `url` | one per distinct feed, shared across Voices |
| `guardian_contributor` | `tag` (for example `profile/janedoe`) | one batched request for all contributors |
| `perigon_journalist` | `journalist_id` | one batched request for all journalists |
| `author_page` | `url` (+ optional `link_prefix`, `structural`) | one per distinct first-party archive page |

Resolve a Perigon journalist id once and store the stable result:

```bash
python -m src.voices.audit journalist "Jane Doe"
```

To **disable a failing source without unfollowing the writer**, set
`"enabled": false` on that source. To stop following the writer entirely, set
the Voice's `"enabled": false`. To keep the Voice in the morning paper but stop
release-time pushes, set `"notify": false`. Remove a source only after its
replacement is validated; leaving a disabled entry for one review cycle makes
operator intent easier to audit.

### Adding a generic adapter

Do not add a writer-specific scraper. A new source family belongs under
`src/voices/adapters/` and must work for any registry entry that satisfies its
schema.

1. Implement the `VoiceSourceAdapter` contract: stable `source_key`, bounded
   request planning, public-metadata fetch, and normalized `Observation`
   records. Route every network call through `VoiceHttp` so the request budget
   remains enforceable.
2. Register the adapter in `src/voices/adapters/__init__.py` and define any
   required registry fields. Prefer provider IDs or first-party structural
   metadata; fail closed when authorship cannot be established.
3. Add its provider to request-budget/cadence policy in `src/config.py`.
   Unknown watcher providers are deliberately reconciliation-only, never
   silently hourly.
4. Add recorded fixtures and deterministic tests covering success, malformed
   responses, attribution, dedupe and partial failure. Never make CI depend on
   the live network.
5. Run the live audit once from the actual GitHub Actions environment before
   shipping the source family, then update this runbook and `VOICES.md` with
   the observed limitation if the provider treats hosted runners differently.

### Provider requirements, quotas and boundaries

Quotas are external contracts, not constants Hermes controls. Re-check the
provider before materially changing cadence.

- **Guardian Open Platform:** `GUARDIAN_API_KEY` is required. The current
  non-commercial developer allowance is 500 requests/day with a 1 request/sec
  rate limit. Voice contributor tags batch into one call.
- **NYT Top Stories:** `NYT_API_KEY` is required for the morning pool, including
  Opinion. There is no separate Voice-specific NYT poll in the watcher.
- **Perigon:** `PERIGON_API_KEY` is optional. The current Free tier is 150 API
  requests/month for personal/non-commercial use, so Voice reconciliation is
  daily rather than hourly and journalist IDs batch into one request.
- **RSS / first-party author pages:** no API key, but they are still somebody
  else's infrastructure. Poll conservatively; a 403/429 is a source failure,
  not permission to evade bot controls.
- **ntfy:** `NTFY_TOPIC` is used for both the morning edition notification and
  optional Voice alerts. `NTFY_BASE_URL` may point to another ntfy-compatible
  host.

Hermes stores public metadata needed to identify and render an item, then links
to the publisher's canonical article. It does not fetch or store paywalled
article bodies and never attempts to bypass a subscription. API use must stay
within the operator's provider terms and licence.

Request budgets live in `VOICE_REQUEST_BUDGET` and watcher cadence/bounds in
`VOICE_WATCH_*` in [src/config.py](src/config.py). The important invariant is
that request cost scales with **distinct source families/URLs**, not
`Voice count × providers × hourly polls`.

### Troubleshooting discovery

- **A Voice went quiet.** Run `python -m src.voices.audit --live --voice <id>`.
  Each source reports `ok` with an item count, or `FAIL` with the reason.
- **A source returns 401/403/429.** Confirm credentials and current provider
  policy first. Do not add retry storms or pretend a blocked HTML page is a
  feed. Disable or replace the source with a supported first-party/API path.
- **A source broke structurally.** Disable only that source while investigating;
  other sources and ordinary Opinion continue. Adapters fail closed rather
  than guessing authorship.
- **An article was found but not shown.** The audit reports `stale`, `future`,
  and `undated` window exclusions plus rejected near-miss attribution reasons.
  Morning Following also has a finite cap and deterministic ordering.
- **A wrong article was attributed.** The audit prints the evidence class for
  every accepted Voice match. Tighten the source scope or provider identity;
  never compensate with title/description keyword matching.

### Release-time alerts

The morning edition remains where a followed piece is read. The watcher only
shortens the wait: when a `notify: true` Voice publishes through an active
watcher source, it sends one quiet ntfy message on the same topic as the
morning push.

```text
Jonathan Haidt — After Babel
Treasure Your Attention
```

Tapping it opens the publisher's article. There is no BREAKING language, no
urgency priority, no badge and no unread count. The morning push is unchanged.

[.github/workflows/voice-watch.yml](.github/workflows/voice-watch.yml) runs
hourly. GitHub's scheduler is **eventually soon, not realtime**: a cron can be
delayed or dropped, so no delivery latency is promised. Cheap sources may run
hourly; scarce providers are held for state-driven reconciliation. Nothing is
polled during 23:00–06:00 America/Toronto quiet hours.

**One publication produces at most one alert.** The watcher commits its claim
to `data/voice_watch_state.json` *before* sending. A `git push` acts as the
compare-and-swap: overlapping runs cannot both claim the same piece. Reruns,
retries, alternate adapter discovery and syndication aliases are silent. The
deliberate trade is that a runner killed after claiming but before delivery may
lose one alert; duplicating a push is considered worse, and the morning edition
still carries the work.

Operator commands:

```bash
python -m src.voice_watch --dry-run       # discover + report; no state writes or pushes
python -m src.voice_watch --smoke         # every live source + exactly one labeled ntfy test
python -m src.voice_watch --smoke --no-notify  # live source smoke without a test push
python -m src.voice_watch --state-report  # inspect durable claim state
python -m src.voice_watch --no-push       # real logic against local state, no git push
```

`--smoke` never claims real articles or writes watcher state. It may still send
one deliberately labeled test notification unless `--no-notify` is supplied.
Use the no-notify form for repeated source diagnostics after delivery itself
has already been verified.

### Watcher state recovery

`data/voice_watch_state.json` is a **claim log**, not an unread list or delivery
queue. Every stored status (`pending`, `notified`, `failed`, `suppressed`,
`adopted`) means that article has already been accounted for and must not be
re-alerted.

Safe procedure:

1. Run `python -m src.voice_watch --state-report` and preserve the current file
   in git history before editing anything.
2. If only one entry is wrong, prefer a reviewed minimal edit. Never change a
   terminal entry back to `pending` expecting a retry; `pending` is already a
   claim and will not re-alert.
3. If the file is lost or unusable, deleting/resetting it is safe from **alert
   bursts**: the next trusted run treats the state as cold/recovered and adopts
   everything it can currently see without notifying. That costs one silent
   cycle by design.
4. Run `--dry-run`/`--state-report` after recovery. Do not fabricate identity
   keys by hand when a clean cold adoption can rebuild them.

State is bounded by `VOICE_WATCH_RETENTION_DAYS` and
`VOICE_WATCH_MAX_ENTRIES`; retention must remain longer than the alert lookback
window. See [VOICES.md §20](VOICES.md#20-slice-c-the-release-time-watcher) for
the concurrency and failure model.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite is deterministic and never touches the network: adapters run against
recorded provider fixtures in `tests/fixtures/`, and Chromium tests render the
exact production template. It runs automatically on every push and pull
request via [.github/workflows/ci.yml](.github/workflows/ci.yml). Live source
checking is deliberately separate: `python -m src.voices.audit --live` and the
watcher's smoke commands above.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
python -m src.build           # builds docs/index.html
open docs/index.html
```

Individual stages are runnable for debugging: `python -m src.weather`,
`python -m src.fetch`, `python -m src.render` (the last renders the bundled
fixture at `data/fixtures/edition_sample.json`, so it works with no API keys).

## Configuration

Secrets come from the environment (local `.env`, gitignored) or GitHub repo
secrets in CI. See [.env.example](.env.example).

| Var | Needed for |
|---|---|
| `GEMINI_API_KEY` | curation (Google AI Studio) |
| `GUARDIAN_API_KEY` | Guardian world/business/sport/opinion + Guardian Voice contributors |
| `NYT_API_KEY` | NYT world/business/opinion morning pool |
| `PERIGON_API_KEY` | optional Perigon world/business/markets + configured Perigon Voice reconciliation |
| `NTFY_TOPIC` | morning push + optional Voice release alerts |
| `PAGES_URL` | cache-buster + morning notification link (CI: repo **variable**) |
| `CURATE_MODEL` | optional model override (default `gemini-2.5-flash`) |
| `VOICE_LOOKBACK_HOURS` | optional morning Voice discovery window (default 36) |
| `VOICE_WATCH_LOOKBACK_HOURS` | optional release-alert window (default 24) |
| `VOICE_WATCH_RECONCILE_HOURS` | optional gap between reconciliation passes (default 24) |
| `NTFY_BASE_URL` | optional ntfy host override (default `https://ntfy.sh`) |

Open-Meteo and the Toronto RSS feeds need no keys. Tunables (location, sections,
caps, feeds, model, house voice, Voice request budgets and watcher policy) live
in [src/config.py](src/config.py).

## Deployment (GitHub Pages + Actions)

- [.github/workflows/build.yml](.github/workflows/build.yml) — targets 05:17
  America/Toronto every day, retries at 05:37, 06:17 and 07:17 if needed, and
  no-ops before source/model work once that Toronto-calendar edition exists.
  Manual `workflow_dispatch` uses the same idempotency gate.
- [.github/workflows/notify.yml](.github/workflows/notify.yml) — follows a
  successful `Build The Daily` run and sends the ntfy.sh morning push only when
  that run actually published today's edition.
- [.github/workflows/voice-watch.yml](.github/workflows/voice-watch.yml) —
  hourly release-time checks for followed Voices; commits
  `data/voice_watch_state.json` only when substantive state changes.

The build and watcher both write to `main`, to different paths, and both push
with fetch-and-retry. They deliberately use **separate** concurrency groups:
sharing one would let an hourly watcher cancel a queued morning edition.
[tests/test_workflows.py](tests/test_workflows.py) asserts this contract.

Pages serves `docs/` on `main` at `https://BenWassa.github.io/Hermes/`.

## First-run checklist (one-time, manual)

- [ ] Get a Gemini API key — https://aistudio.google.com/apikey
- [ ] Get a Guardian API key — https://open-platform.theguardian.com/
- [ ] Get an NYT API key — https://developer.nytimes.com/
- [ ] (Optional) Get a Perigon API key — https://www.perigon.io/; required only if using Perigon-backed discovery/coverage
- [ ] Pick a hard-to-guess ntfy topic, subscribe a client, and keep the topic as a secret
- [ ] Add repo **secrets**: `GEMINI_API_KEY`, `GUARDIAN_API_KEY`, `NYT_API_KEY`, `NTFY_TOPIC`; add `PERIGON_API_KEY` only when used
- [ ] Add repo **variable** `PAGES_URL` (for example `https://BenWassa.github.io/Hermes/`)
- [ ] Enable GitHub Pages: Settings → Pages → source = `main`, folder = `/docs`
- [ ] Run `python -m src.voices.audit` and a bounded live Voice audit from Actions
- [ ] Trigger `Build The Daily`; confirm the exact generated edition publishes and one morning push arrives
- [ ] Run one `voice_watch --smoke` when Voice alerts are enabled; use `--no-notify` for repeat diagnostics
- [ ] Confirm cron/quiet-hour behavior against America/Toronto DST

## Notes

- House style: factual, headline-first, 2–3 sentence summaries, no em dashes.
- Every opened story carries an **Ask AI** control that hands the clipping and a
  briefing prompt to Claude, ChatGPT, the iOS share sheet, or the clipboard. The
  prompt asks for a layered answer in house voice, heaviest first: the gist under
  an H1, then why it matters, then background, contest, and markers to watch, then
  three numbered follow-up questions. About 500 words, hard ceiling 650, short
  paragraphs and no tables so it reads on a phone. It lives in `buildPrompt()` in
  [template/index.template.html](template/index.template.html); edit it there.
- The Claude and ChatGPT links deliberately carry no `target="_blank"`: a blank
  target opens an in-app browser sheet that iOS will not hand off to an installed
  app, so a plain top-level tap is what lets those apps claim their own domains as
  Universal Links. "Share to app" is the fallback when a link opens in the browser
  anyway, since both iOS apps accept shared text.
- Sensitive stories (war, violent crime, court proceedings on violent crime,
  death, disaster) render text-only by design.
- Source thumbnails are hotlinked; some may rot. Acceptable for v1; caching to
  the repo is a phase-2 item (see the PRD).

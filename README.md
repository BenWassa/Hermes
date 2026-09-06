# The Daily

An autonomous overnight pipeline that assembles a personalized Toronto morning
newspaper, renders it as a static web page, and pushes a notification to your
phone at 7:00 AM. World and business news come from the Guardian, NYT, and
Perigon APIs (Perigon aggregates FT, Reuters, Bloomberg and thousands more, so
the business desk reads like a professional's, not just one paper); Toronto
local news comes from RSS. Google Gemini (`gemini-2.5-flash`, free
tier) dedupes, sections, ranks, and summarizes; a sensitivity rule keeps hard
news text-only. The result deploys to GitHub Pages and an ntfy.sh push links
straight to it.

> v2 of this repo. The previous React/Firebase intelligence dashboard ("Hermes
> v1") is preserved under [archive/v1-hermes/](archive/v1-hermes/) and tagged
> `v1-final`. Product spec: [PRD_daily_newspaper.md](PRD_daily_newspaper.md);
> task-level build spec: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).

## Pipeline

```
weather -> fetch -> normalize -> curate (Claude) -> resolve images -> render -> deploy -> notify
```

| Module | Role |
|---|---|
| [src/weather.py](src/weather.py) | Open-Meteo Toronto forecast (no key) |
| [src/fetch.py](src/fetch.py) | Guardian + NYT + Perigon APIs, Toronto RSS (graceful per-source failure) |
| [src/normalize.py](src/normalize.py) | Unify sources into one story schema |
| [src/curate.py](src/curate.py) | One Gemini call: dedupe, section, rank, summarize, flag |
| [src/images.py](src/images.py) | Keep source thumbnails; suppress on sensitive stories |
| [src/render.py](src/render.py) | Inject edition JSON into the HTML template |
| [src/build.py](src/build.py) | Orchestrator (single entrypoint) |
| [src/voices/](src/voices/) | Followed writers: registry, source adapters, authorship resolution, article identity |
| [template/index.template.html](template/index.template.html) | The newspaper UI (vanilla HTML/CSS/JS) |

## Voices (followed writers)

A **Voice** is a person, not a publication. Hermes can follow a writer and find
their new work wherever they publish, across a personal newsletter, a
publication author archive, the Guardian's contributor API, an aggregator's
journalist identity, or the ordinary morning fetch. The design authority is
[VOICES.md](VOICES.md).

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
  "notify": true,
  "aliases": ["J. A. Doe"],         // other spellings of the same person
  "provider_ids": [                 // stable per-writer ids, strongest evidence
    {"provider": "guardian", "id": "profile/janedoe"}
  ],
  "byline_publications": ["nytimes.com"],   // hosts where her byline alone is trusted
  "sources": [                      // where to actively go looking
    {
      "id": "jane-newsletter",
      "type": "rss",
      "url": "https://janedoe.substack.com/feed",
      "publication": "Jane Doe",
      "authorship": "scope"
    }
  ]
}
```

Then check it before committing:

```bash
python -m src.voices.audit                    # validate + show the request plan
python -m src.voices.audit --live             # fetch every source once, for real
python -m src.voices.audit --live --voice jane-doe
```

### The two halves of a Voice

**Identity** decides whether an article is hers. **Sources** decide where
Hermes looks. They are separate so the ordinary morning fetch can attribute her
work at no extra request cost, and so registering a feed does not blanket-grant
authorship to everything on it.

| Field | Evidence it grants | Use it when |
|---|---|---|
| `provider_ids` | strongest; valid anywhere | the provider has a stable contributor/journalist id |
| `sources[].authorship: "scope"` | the source itself is the proof | a personal newsletter, or a publication's own author archive |
| `sources[].authorship: "byline"` | the entry's byline must match | a multi-author publication feed |
| `byline_publications` | byline match on those hosts only | she writes for an outlet Hermes already fetches |

A name is only ever matched against an item's **byline**, never its title,
description, or a provider's "people mentioned" list. A byline match is only
accepted inside a declared scope, so a common name cannot collect strangers'
articles. Set `"require_evidence": "provider_id"` on a genuinely ambiguous name
to refuse byline evidence altogether.

### Source types

| `type` | Needs | Requests per run |
|---|---|---|
| `rss` | `url` | one per distinct feed, shared across Voices |
| `guardian_contributor` | `tag` (e.g. `profile/janedoe`) | one for **all** contributors combined |
| `perigon_journalist` | `journalist_id` | one for **all** journalists combined |
| `author_page` | `url` (+ optional `link_prefix`, `structural`) | one per distinct page |

Resolve a Perigon journalist id once, by hand, and paste it in:

```bash
python -m src.voices.audit journalist "Jane Doe"
```

### Troubleshooting

- **A Voice went quiet.** Run `python -m src.voices.audit --live --voice <id>`.
  Each source reports `ok` with an item count, or `FAIL` with the reason.
- **A source broke.** Set `"enabled": false` on that source. The Voice stays
  registered and its other sources keep working. A failing source already
  degrades on its own and logs a warning; disabling it just stops the noise.
- **An article was found but not shown.** The audit prints what fell outside
  the edition window (`stale`, `future`, `undated`) and every rejected
  near-miss attribution with its reason.
- **A wrong article was attributed.** Every article records why: the audit
  prints `evidence: <voice> <- <evidence class> (<detail>)` for each one.

Request budgets live in `VOICE_REQUEST_BUDGET` in
[src/config.py](src/config.py). Perigon is the binding constraint (a personal
tier measured in requests per *month*), so Voice discovery treats it as a
once-a-day reconciliation pass and defaults to one request per run.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite is fully deterministic and never touches the network: adapters run
against recorded provider fixtures in `tests/fixtures/`. It runs automatically
on every push and pull request via
[.github/workflows/ci.yml](.github/workflows/ci.yml). Live source checking is
the separate `python -m src.voices.audit --live` command.

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
| `GEMINI_API_KEY` | curation (Google AI Studio, free tier) |
| `GUARDIAN_API_KEY` | Guardian world/business/sport/opinion |
| `NYT_API_KEY` | NYT world/business |
| `PERIGON_API_KEY` | Perigon world/business/markets (optional, free tier; skipped if unset) |
| `NTFY_TOPIC` | morning push |
| `PAGES_URL` | cache-buster + notification link (CI: set as a repo **variable**) |
| `CURATE_MODEL` | optional model override (default `gemini-2.5-flash`) |
| `VOICE_LOOKBACK_HOURS` | optional Voice discovery window (default 36) |

Open-Meteo and the Toronto RSS feeds need no keys. Tunables (location, sections,
caps, feed list, model, house voice) live in [src/config.py](src/config.py).

## Deployment (GitHub Pages + Actions)

- [.github/workflows/build.yml](.github/workflows/build.yml) — builds and
  commits `docs/index.html` on a DST-aware ~6 AM ET schedule (plus manual
  `workflow_dispatch`).
- [.github/workflows/notify.yml](.github/workflows/notify.yml) — sends the
  ntfy.sh push at ~7 AM ET.

Pages serves `docs/` on `main` at `https://BenWassa.github.io/Hermes/`.

## First-run checklist (one-time, manual)

- [ ] Get a Gemini API key — https://aistudio.google.com/apikey (free tier)
- [ ] Get a Guardian API key — https://open-platform.theguardian.com/
- [ ] Get an NYT API key — https://developer.nytimes.com/
- [ ] (Optional) Get a Perigon API key — https://www.perigon.io/ (free tier; widens business/world coverage)
- [ ] Pick an ntfy topic (hard to guess), install the ntfy iOS app, subscribe
- [ ] Add repo **secrets**: `GEMINI_API_KEY`, `GUARDIAN_API_KEY`,
      `NYT_API_KEY`, `PERIGON_API_KEY` (optional), `NTFY_TOPIC`
- [ ] Add repo **variable** `PAGES_URL` (e.g. `https://BenWassa.github.io/Hermes/`)
- [ ] Enable GitHub Pages: Settings → Pages → source = `main`, folder = `/docs`
- [ ] Verify the Toronto RSS URLs in [src/config.py](src/config.py) still resolve; swap any dead ones
- [ ] Trigger `Build The Daily` via `workflow_dispatch`; confirm the edition publishes
- [ ] Trigger `Notify The Daily`; confirm the push arrives and the link opens
- [ ] Confirm cron times against the current DST offset

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

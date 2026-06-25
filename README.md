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
| [template/index.template.html](template/index.template.html) | The newspaper UI (vanilla HTML/CSS/JS) |

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
- Sensitive stories (war, violent crime, court proceedings on violent crime,
  death, disaster) render text-only by design.
- Source thumbnails are hotlinked; some may rot. Acceptable for v1; caching to
  the repo is a phase-2 item (see the PRD).

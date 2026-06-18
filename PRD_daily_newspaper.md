# PRD: The Daily — Autonomous Morning Newspaper

**Owner:** Ben
**Status:** Draft v1
**Last updated:** June 16, 2026
**System:** MERIDIAN / Night Shift job

---

## 1. Summary

An autonomous overnight job that assembles a personalized morning newspaper, renders it as a static web page, and pushes a notification to Ben's phone at 7:00 AM. Reuses the existing newspaper UI (horizontal tabs, expandable stories, weather strip, lead-story treatment). Runs daily with zero manual intervention.

**Core loop:** fetch → curate → summarize → render → deploy → notify.

---

## 2. Goals & non-goals

### Goals
- Deliver a curated, readable morning briefing by 7:00 AM daily, no manual steps.
- Mix world/national news (APIs) with Toronto local news (RSS).
- Claude handles summarization and section curation.
- Push a link to phone each morning; one tap to read.
- Run at ~$0/month on free tiers, inside existing MERIDIAN infrastructure.

### Non-goals (v1)
- No native mobile app. PWA / web link only.
- No AI image generation. Image strategy is API-thumbnail + suppression rules (see §6).
- No personalization model / learning loop. Fixed section logic.
- No archive / search / back-issues. Latest edition only.
- No comments, sharing, or social features.

---

## 3. Users

Single user: Ben. Mobile-first (iPhone). Reads in the morning. Wants signal over noise, headline-first, tap to expand.

---

## 4. Architecture overview

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Action (cron: 6:00 AM ET daily)                  │
│                                                           │
│  1. FETCH        → news APIs (world) + RSS (Toronto)     │
│  2. NORMALIZE    → unify into common story schema        │
│  3. CURATE       → Claude: dedupe, section, rank, cut    │
│  4. SUMMARIZE    → Claude: 2-3 sentence summary each     │
│  5. IMAGE RESOLVE→ attach thumbnail OR suppress (rules)  │
│  6. RENDER       → inject JSON into HTML template        │
│  7. DEPLOY       → commit to GitHub Pages branch         │
│  8. NOTIFY       → ntfy.sh push at 7:00 AM               │
└─────────────────────────────────────────────────────────┘
```

Two scheduled steps: build at 6 AM, notify at 7 AM (or build+notify together at 6:30 with a delayed-delivery notification — see §9).

---

## 5. Data sources

### World / National (APIs)
| Source | Use | Images | Cost |
|---|---|---|---|
| **NewsAPI.org** | World, Business headlines | Yes (urlToImage) | Free: 100 req/day, dev only* |
| **The Guardian API** | World, Opinion, Sport | Yes (fields=thumbnail) | Free w/ key, generous |
| **NYT Top Stories API** | World, Business | Yes (multimedia[]) | Free w/ key |

> ⚠ **NewsAPI free tier is development-only** and won't serve a public GitHub Pages site per their terms. **Recommendation: lead with Guardian + NYT** (both free, production-permitted, include images). Keep NewsAPI optional for local dev.

### Toronto Local (RSS)
| Feed | URL pattern |
|---|---|
| CBC Toronto | `cbc.ca/webfeed/rss/rss-canada-toronto` |
| CP24 | `cp24.com/rss` |
| TorontoToday | check `torontoday.ca` for feed |
| Toronto Star (if available) | verify feed availability |

RSS gives title, link, description, pubDate, and often a media:thumbnail. Parse with a standard feed library (`feedparser` in Python).

### Weather
- **Environment Canada** (`weather.gc.ca`) via their data feed, or
- **Open-Meteo** (free, no key, clean JSON) for Toronto lat/long. Recommend Open-Meteo for simplicity.

---

## 6. Image strategy

Images come from source thumbnails only. No generation, no stock matching in v1.

**Resolution order per story:**
1. Use the source-provided thumbnail (Guardian thumbnail / NYT multimedia / RSS media:thumbnail).
2. If none, story renders text-only (already supported by UI).

**Suppression rules (override — render NO image even if one exists):**
- Story tagged `WAR`, `CRIME`, `COURTS`, `DEATH`, or `DISASTER`.
- This is the "human judgment" backstop: hard/sensitive news stays text-only to avoid a tonally wrong or graphic thumbnail appearing unsupervised.

**Claude's role in images:** during curation, Claude assigns each story a `sensitivity` flag. The renderer suppresses images on sensitive stories. This keeps a human-like editorial guardrail without a human in the loop.

---

## 7. Claude integration (curate + summarize)

One Claude API call per run (batched), or two if splitting curate/summarize. Recommend a **single structured call** for cost and latency.

**Input to Claude:** normalized array of ~40-60 raw stories (title, source, description, section hint, pubDate, image URL, link).

**Claude's tasks:**
1. **Dedupe** — collapse the same story reported by multiple outlets; keep the best-sourced version.
2. **Section** — assign each to: Front Page, Toronto, World, Sports, Business, Opinion.
3. **Rank** — order within section; mark one `lead: true` per section.
4. **Cut** — cap each section (Front Page ≤5, others ≤4). Drop low-signal filler.
5. **Summarize** — 2-3 sentence summary per surviving story, in the house voice (signal over noise, no fluff, factual).
6. **Flag** — set `tag` (DEVELOPING / FINAL / etc.) and `sensitivity` (for image suppression).

**Output:** strict JSON matching the renderer schema (§8). System prompt must demand JSON only, no preamble.

**House voice for summaries:**
- Factual, neutral, headline-first.
- No editorializing in news sections (Opinion section excepted).
- 2-3 sentences, ~40-70 words.
- No "the article says" framing — state the news directly.

---

## 8. Data schema (renderer contract)

```json
{
  "date": "Tuesday, June 16, 2026",
  "weather": {
    "condition": "Thunderstorms, then clearing",
    "high": 24, "low": 15, "rain": "40%", "wind": "29 km/h gusts", "icon": "⛈",
    "week": [{ "day": "Tue", "icon": "⛈", "hi": 24, "lo": 15 }, "..."]
  },
  "sections": [
    {
      "id": "front",
      "label": "Front Page",
      "stories": [
        {
          "id": "f1",
          "lead": true,
          "kicker": "MIDDLE EAST",
          "headline": "…",
          "sub": "…",
          "summary": "…",
          "time": "6:45 AM",
          "tag": "DEVELOPING",
          "sensitivity": false,
          "image": "https://…",
          "link": "https://…"
        }
      ]
    }
  ]
}
```

Renderer is the existing component, extended to: (a) render `image` when present and `sensitivity` is false, (b) link the headline to `link`.

---

## 9. Scheduling & notification

**Build:** GitHub Action `schedule` cron at `0 10 * * *` UTC (6:00 AM ET; adjust for DST — note ET is UTC-4 in summer, UTC-5 in winter; use two crons or a date check).

**Notify:** ntfy.sh push at 7:00 AM.
- Simplest: second cron at 7:00 AM ET sends the push.
- Alternative: single 6:30 AM run that builds, then sends an ntfy message with a scheduled `At` header for 7 AM delivery.

**ntfy.sh setup:**
- Pick a hard-to-guess topic name (e.g. `the-daily-ben-x7k2`).
- Install ntfy iOS app, subscribe to topic.
- Push payload: title "The Daily — June 16", body "Today's edition is ready", click action = GitHub Pages URL.

```bash
curl -H "Title: The Daily — $(date +'%b %-d')" \
     -H "Click: https://ben.github.io/the-daily/" \
     -H "Tags: newspaper" \
     -d "Today's edition is ready." \
     ntfy.sh/the-daily-ben-x7k2
```

---

## 10. Hosting

**GitHub Pages**, served from a `gh-pages` branch or `/docs` folder.
- Build step writes `index.html` (template + injected JSON) and any assets.
- Action commits and pushes; Pages auto-deploys.
- URL: `https://<user>.github.io/the-daily/`.
- For "app-like" feel, add a minimal PWA manifest + service worker so Ben can add to home screen (optional, phase 2).

---

## 11. Repo structure

```
the-daily/
├── .github/workflows/build.yml      # cron + build + deploy
├── src/
│   ├── fetch.py                     # API + RSS pulls
│   ├── normalize.py                 # unify to common schema
│   ├── curate.py                    # Claude call (curate + summarize)
│   ├── images.py                    # resolve + suppression rules
│   ├── weather.py                   # Open-Meteo pull
│   └── render.py                    # inject JSON → index.html
├── template/
│   └── index.template.html          # the newspaper UI (from JSX → static)
├── docs/
│   └── index.html                   # generated output (Pages serves this)
├── data/
│   └── latest.json                  # last build's data (debug/cache)
├── requirements.txt
└── PRD.md                           # this file
```

---

## 12. Secrets / config

Stored as GitHub repo secrets:
- `ANTHROPIC_API_KEY`
- `GUARDIAN_API_KEY`
- `NYT_API_KEY`
- `NTFY_TOPIC`

Open-Meteo and RSS need no keys.

---

## 13. Build sequence (Claude Code tasks)

Ordered for incremental, testable progress:

1. **Scaffold repo** + `requirements.txt` (feedparser, requests, anthropic, jinja2).
2. **weather.py** — Open-Meteo pull for Toronto, output weather block. *Testable standalone.*
3. **fetch.py + normalize.py** — pull Guardian + NYT + Toronto RSS into unified array. *Print raw count.*
4. **curate.py** — Claude call, raw stories → structured JSON. *Validate JSON schema.*
5. **images.py** — apply resolution + suppression. *Spot-check sensitive stories suppressed.*
6. **Convert UI** — port the JSX component to a static `index.template.html` with a JSON injection point.
7. **render.py** — Jinja2 inject → `docs/index.html`. *Open locally, verify renders.*
8. **build.yml** — wire the chain, add cron, add Pages deploy.
9. **Notification** — ntfy.sh push step.
10. **End-to-end dry run** — trigger manually, verify phone receives link, link renders.
11. **DST handling** + final cron times.
12. **(Phase 2)** PWA manifest + service worker for home-screen install.

---

## 14. Success criteria

- [ ] Edition builds and deploys autonomously by 6:30 AM ET.
- [ ] Push arrives by 7:00 AM with working link.
- [ ] 5-6 sections populated, deduped, sensibly ranked.
- [ ] Summaries are factual, 2-3 sentences, house voice.
- [ ] Sensitive stories render text-only.
- [ ] Weather strip accurate for Toronto.
- [ ] Zero manual steps across a 7-day run.
- [ ] $0 monthly cost.

---

## 15. Open questions / risks

- **⚠ DST cron drift** — ET offset changes twice a year. Use a date-aware check or two seasonal crons.
- **⚠ RSS reliability** — Toronto feeds may change URLs or go stale. Build a graceful fallback (skip section if feed dead, don't crash the run).
- **API rate / quota** — Guardian and NYT free tiers are generous but not infinite; one run/day is well within limits.
- **Claude output drift** — enforce strict JSON; add a validation + one retry on parse failure.
- **GitHub Pages cache** — may need cache-busting on the asset/URL so the phone shows the fresh edition, not a cached one.
- **Image hotlinking** — source thumbnails are hotlinked; some may block or rot. Acceptable for v1; consider caching to repo in phase 2.

---

## 16. Phasing

**Phase 1 (MVP):** fetch → curate → render → deploy → notify. Text + source thumbnails. The above.
**Phase 2:** PWA home-screen install; image caching to repo; cache-busting.
**Phase 3:** light personalization (favoured topics surface higher); optional archive of past editions.

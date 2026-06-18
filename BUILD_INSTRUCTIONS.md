# Claude Code Build Instructions: The Daily

**Companion to:** `PRD_daily_newspaper.md`
**Target:** Claude Code, autonomous (Night Shift compatible)
**Repo:** `the-daily`

---

## How to use this document

Two ways to run it:

- **Interactive:** paste §1 (Kickoff Prompt) into Claude Code, then work through §3 task-by-task.
- **Autonomous (Night Shift):** point a Night Shift job at this file with the instruction *"Execute the build sequence in BUILD_INSTRUCTIONS.md, one task per commit, run the test gate after each, stop and log if a gate fails."*

Each task in §3 is self-contained: goal, files touched, implementation notes, and a **test gate** that must pass before moving on.

---

## 1. Kickoff prompt

> Build **The Daily**, an autonomous morning newspaper pipeline, per `PRD_daily_newspaper.md` in this repo. It fetches world news (Guardian + NYT APIs) and Toronto news (RSS), uses the Anthropic API to dedupe/section/rank/summarize, resolves images with a sensitivity-based suppression rule, renders a static HTML newspaper, deploys to GitHub Pages, and pushes an ntfy.sh notification at 7 AM.
>
> Stack: **Python 3.11**, `requests`, `feedparser`, `anthropic`, `jinja2`. Deploy via GitHub Actions to GitHub Pages.
>
> Work through the build sequence one task at a time. After each task, run its test gate. Commit per task with a clear message. If a test gate fails, fix before proceeding; if blocked, log the blocker and stop. Keep all secrets in env vars — never hardcode keys. House voice for summaries: factual, signal over noise, headline-first, 2-3 sentences, no fluff, no em dashes.

---

## 2. Conventions

- **Commits:** `feat(weather): Open-Meteo pull` style. One task per commit.
- **Config:** all keys via `os.environ`. Local dev uses a `.env` (gitignored); CI uses repo secrets.
- **Failures are graceful:** a dead RSS feed skips its section, never crashes the run.
- **Idempotent:** re-running a build produces a clean edition, no duplicate state.
- **No em dashes** anywhere in generated copy (matches house style).

---

## 3. Build sequence

### Task 0 — Scaffold

**Goal:** Repo skeleton, dependencies, gitignore.

**Files:**
```
requirements.txt
.gitignore            # .env, __pycache__, data/latest.json
.env.example          # documents required vars, no real values
README.md             # one-paragraph what/how
src/__init__.py
```

`requirements.txt`:
```
requests>=2.31
feedparser>=6.0
anthropic>=0.40
jinja2>=3.1
python-dotenv>=1.0
```

**Test gate:** `pip install -r requirements.txt` succeeds; `python -c "import requests, feedparser, anthropic, jinja2"` exits 0.

---

### Task 1 — Weather (`src/weather.py`)

**Goal:** Pull today + 6-day Toronto forecast from Open-Meteo, output the weather block matching the schema.

**Implementation:**
- Open-Meteo endpoint, no key. Toronto lat/long: `43.65, -79.38`.
- Request daily `temperature_2m_max`, `temperature_2m_min`, `precipitation_probability_max`, `weather_code`, plus current conditions and `wind_speed_10m_max`.
- Map Open-Meteo `weather_code` → emoji icon (write a small dict: 0=☀️, 1-3=⛅, 45/48=🌫, 51-67=🌦, 71-77=🌨, 80-82=🌧, 95-99=⛈).
- Return dict: `{condition, high, low, rain, wind, icon, week:[{day, icon, hi, lo} x6]}`.
- `condition` is a short human phrase derived from today's code.

**Test gate:** `python -m src.weather` prints a valid weather dict with 6 week entries and plausible Toronto temps.

---

### Task 2 — Fetch + Normalize (`src/fetch.py`, `src/normalize.py`)

**Goal:** Pull all sources into one unified raw-story array.

**fetch.py:**
- `fetch_guardian()` — Guardian Content API, sections: world, business, sport, commentisfree (Opinion). Request `show-fields=thumbnail,trailText,byline`. Key from `GUARDIAN_API_KEY`.
- `fetch_nyt()` — NYT Top Stories API (`world`, `business`). Key from `NYT_API_KEY`. Image from `multimedia[]`.
- `fetch_toronto_rss()` — feedparser over the Toronto feed list. Wrap each feed in try/except; a dead feed logs a warning and returns `[]`.
- Each function returns a list of dicts in **source-native** shape.

**normalize.py:**
- `normalize(raw_items)` → unified schema per story:
  ```python
  {
    "title": str, "description": str, "source": str,
    "section_hint": str,   # world|business|sport|opinion|toronto
    "pub_date": str,       # ISO
    "image": str | None,
    "link": str
  }
  ```
- Strip HTML from descriptions. Drop items with no title or link.

**Test gate:** `python -m src.fetch` prints total normalized count > 20, with a source breakdown. At least one Toronto item present (or a logged warning if all feeds dead).

---

### Task 3 — Curate + Summarize (`src/curate.py`)

**Goal:** One Anthropic API call: raw normalized array → final structured edition JSON.

**Implementation:**
- Model: `claude-sonnet-4-6`.
- Build a system prompt that instructs Claude to act as editor: dedupe, assign sections (Front Page, Toronto, World, Sports, Business, Opinion), rank within section, mark one `lead:true` per section, cap sizes (Front ≤5, others ≤4), write a 2-3 sentence house-voice summary each, set `tag` and `sensitivity`.
- **Demand JSON only**, no preamble, no markdown fences. Provide the exact output schema in the prompt.
- Pass the normalized stories as the user message (JSON).
- Parse response; on `JSONDecodeError`, strip fences and retry parse once; if still failing, make one more API call appending "Return ONLY valid JSON." then hard-fail with a logged error.
- Inject `date` (formatted today) and the weather block from Task 1 into the final object.

**Sensitivity rule for the prompt:** mark `sensitivity:true` for stories centrally about war, violent crime, court proceedings on violent crime, death, or disaster. This drives image suppression downstream.

**Test gate:** `python -m src.curate` (fed a saved fixture from Task 2) returns schema-valid JSON: 5-6 sections, each with ≥1 story, exactly one `lead` per section, every story has a non-empty summary, sensitivity is boolean.

---

### Task 4 — Images (`src/images.py`)

**Goal:** Apply image resolution + suppression.

**Implementation:**
- `resolve_images(edition)` walks every story:
  - If `sensitivity is True` → set `image = None` (suppress).
  - Else keep the source `image` if present, else `None`.
- Optional niceties: drop obviously-bad image URLs (empty, non-http).

**Test gate:** Run over Task 3 output. Assert no story with `sensitivity:true` retains an image. Print count of stories with vs without images.

---

### Task 5 — Template (`template/index.template.html`)

**Goal:** Port the React newspaper UI to a single static HTML file with a JSON injection point.

**Implementation:**
- Recreate the component's visual design in vanilla HTML/CSS/JS: masthead, collapsible weather strip, horizontal scrollable tab nav, expandable story cards, lead-story treatment, kickers, tags, footer.
- Carry over the exact palette and type: navy `#1a2744`, red kicker `#8b1a1a`, Georgia serif headlines, Arial labels, cream expand background `#f8f7f4`.
- **Add image rendering:** when a story has `image`, show it above the summary inside the expanded card (or as a small thumbnail beside the headline — pick one, keep mobile-clean). No image element when `image` is null.
- **Headlines link out:** headline links to `story.link` (open in new tab) — but the card still expands on tap; put the outbound link on a small "Read full story →" element inside the expanded view to avoid tap conflict.
- Injection point: a placeholder like `/*__EDITION_JSON__*/` that render.py replaces, or a `<script id="edition" type="application/json">…</script>` block.
- Vanilla JS handles tab switching + expand/collapse (no framework, no build step).

**Test gate:** Open the template with a sample edition hardcoded in the script block in a browser. Tabs scroll and switch; cards expand; images show on non-sensitive stories; weather strip toggles. Looks right on a narrow (mobile) viewport.

---

### Task 6 — Render (`src/render.py`)

**Goal:** Inject edition JSON into the template → `docs/index.html`.

**Implementation:**
- Load `template/index.template.html`.
- Replace the injection point with the edition JSON (from Task 4).
- Add a cache-buster: a `<meta>` build timestamp and a `?v=<timestamp>` on any asset refs, so the phone never shows a stale cached edition.
- Write `docs/index.html`. Also write `data/latest.json` for debugging.

**Test gate:** `python -m src.render` produces `docs/index.html`; open it, confirm it renders the real fetched edition end to end.

---

### Task 7 — Orchestrator (`src/build.py`)

**Goal:** Single entrypoint chaining the whole pipeline.

**Implementation:**
```
weather → fetch → normalize → curate → resolve_images → render
```
- Wrap in top-level try/except: log stage on failure, exit non-zero so CI surfaces it.
- Print a one-line summary at the end: edition date, section count, story count, images shown/suppressed.

**Test gate:** `python -m src.build` runs the full chain locally and writes a complete `docs/index.html`.

---

### Task 8 — GitHub Action (`.github/workflows/build.yml`)

**Goal:** Scheduled build + Pages deploy.

**Implementation:**
- Triggers: `schedule` cron + `workflow_dispatch` (manual).
- **DST-aware timing:** run two crons and gate inside the job, OR run at a fixed UTC and accept a 1-hour seasonal shift. Recommended: two crons —
  - `0 10 * * *` (covers EDT, summer, UTC-4 → 6 AM)
  - `0 11 * * *` (covers EST, winter, UTC-5 → 6 AM)
  - First step checks current ET; if it isn't ~6 AM ET, exit early. (Prevents double-build in shoulder weeks.)
- Steps: checkout → setup-python → pip install → `python -m src.build` → commit `docs/` + `data/` → push (Pages serves `docs/`).
- Secrets: `ANTHROPIC_API_KEY`, `GUARDIAN_API_KEY`, `NYT_API_KEY` via `env:`.
- Enable GitHub Pages on the repo, source = `docs/` on main (one-time manual setting, note in README).

**Test gate:** `workflow_dispatch` manual run completes green; Pages URL shows the fresh edition.

---

### Task 9 — Notification (add to workflow)

**Goal:** ntfy.sh push at 7 AM with link.

**Implementation:**
- Simplest: a second workflow `notify.yml` on a 7 AM ET cron (same DST handling) that sends the curl push.
- Or: append to `build.yml` a step that sends an ntfy message with a scheduled delivery header (`At: 7am`) so build and notify live in one run.
- Push includes Title (`The Daily — <Mon D>`), Click (Pages URL), Tags (`newspaper`).
- Topic from `NTFY_TOPIC` secret.

```bash
curl \
  -H "Title: The Daily — $(TZ=America/Toronto date +'%b %-d')" \
  -H "Click: https://<user>.github.io/the-daily/" \
  -H "Tags: newspaper" \
  -d "Today's edition is ready." \
  "ntfy.sh/${NTFY_TOPIC}"
```

**Test gate:** Manual trigger sends a push; it arrives on the phone; tapping opens the live edition.

---

### Task 10 — End-to-end dry run

**Goal:** Prove the autonomous loop.

- Trigger the full build manually in the evening.
- Confirm: edition builds, deploys, push arrives, link renders correctly on phone, sensitive stories are text-only, weather is right.
- Let it run on the real cron one morning. Verify hands-off.

**Test gate:** A real scheduled run lands a correct edition + push with zero manual steps.

---

### Task 11 (Phase 2) — PWA install

**Goal:** Home-screen "app" feel.

- Add `manifest.webmanifest` (name, icons, theme color `#1a2744`, display `standalone`).
- Add a minimal service worker caching the shell; network-first for the edition so content stays fresh.
- Link both from `index.html`. Test "Add to Home Screen" on iOS.

**Test gate:** Installs to iPhone home screen; opens chromeless; shows latest edition.

---

## 4. House voice (for the curate prompt)

Bake these into the system prompt verbatim:

- Factual and neutral in all news sections. Opinion section may take a position.
- Headline-first. State the news directly; never "the article reports that…".
- 2-3 sentences per summary, roughly 40-70 words.
- Signal over noise. No filler, no motivational language, no hedging.
- No em dashes. Use commas, periods, or restructure.
- Plain, confident, concrete.

---

## 5. First-run manual checklist (one-time)

- [ ] Create repo `the-daily`, push scaffold.
- [ ] Get Guardian API key (open-platform.theguardian.com).
- [ ] Get NYT API key (developer.nytimes.com).
- [ ] Pick ntfy topic, install ntfy app, subscribe.
- [ ] Add 4 repo secrets.
- [ ] Enable Pages (source `docs/`).
- [ ] Verify Toronto RSS URLs resolve; swap any dead ones.
- [ ] Manual `workflow_dispatch`, confirm edition + push.
- [ ] Confirm cron times against current DST.

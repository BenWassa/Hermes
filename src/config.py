"""Central configuration for The Daily.

All tunable constants live here: location, sections, sources, weather mapping,
the curation model, and the curate system prompt (house voice). Secrets are
read from the environment, never hardcoded.
"""

from __future__ import annotations

import os

try:
    # Optional: load a local .env during development. CI provides real env vars.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


# --- Location -------------------------------------------------------------

TORONTO_LAT = 43.65
TORONTO_LON = -79.38
TIMEZONE = "America/Toronto"


# --- Public site ----------------------------------------------------------

# Used for the cache-buster meta and the ntfy click action. Override with the
# PAGES_URL env var if the repo or Pages path changes.
SITE_URL = os.environ.get("PAGES_URL", "https://BenWassa.github.io/Hermes/")


# --- Sections (order, labels, per-section caps) ---------------------------

# SECTIONS is navigation/presentation authority. Sports remains a first-class
# tab even though its content is now owned by the deterministic Sports V2 desk
# rather than by Gemini.
SECTIONS = [
    {"id": "front", "label": "Front Page", "cap": 5},
    {"id": "toronto", "label": "Toronto", "cap": 4},
    {"id": "world", "label": "World", "cap": 4},
    {"id": "sports", "label": "Sports", "cap": 4},
    {"id": "business", "label": "Business", "cap": 4},
    {"id": "opinion", "label": "Opinion", "cap": 4},
]

# Gemini editorial authority deliberately excludes Sports. Do not ask the
# model to emit an empty Sports section; the build injects the navigation shell
# after curation and attaches the dedicated top-level sports payload.
CURATION_SECTIONS = [s for s in SECTIONS if s["id"] != "sports"]

# Order of section ids, handy for validation and ranking.
SECTION_IDS = [s["id"] for s in SECTIONS]
CURATION_SECTION_IDS = [s["id"] for s in CURATION_SECTIONS]


# --- Sources --------------------------------------------------------------

# Guardian Content API sections -> ordinary Gemini section hint. Sports is
# intentionally absent: Sports V2 performs only targeted Guardian searches
# after deterministic significance rules have defined what it is looking for.
GUARDIAN_SECTIONS = {
    "world": "world",
    "business": "business",
    "commentisfree": "opinion",
}

# How far targeted Sports team/event news may look back in the morning build.
# Overlap is safe because Sports selection is deterministic and the edition is
# gated before provider work once today's Toronto-calendar paper exists.
SPORTS_NEWS_LOOKBACK_HOURS = int(os.environ.get("SPORTS_NEWS_LOOKBACK_HOURS", "36"))

# NYT Top Stories API sections -> our section hint. "opinion" is included so
# the Opinion desk sees NYT columnists, and so a followed NYT writer is found
# in a stream Hermes already fetches rather than costing a per-person request.
NYT_SECTIONS = {
    "world": "world",
    "business": "business",
    "opinion": "opinion",
}

# Perigon News API queries -> our section hint. Each entry is one request to the
# /v1/all endpoint. Perigon aggregates thousands of outlets (FT, Reuters,
# Bloomberg, etc.), which broadens the business and world pool well beyond the
# Guardian/NYT pairing - the point being to actually guide a business reader.
# Requests are deliberately few (free-tier friendly) and balanced by the curate
# trimmer, so no single query crowds out the others. "category" accepts Perigon's
# Google-derived content categories; multiple values OR together. Skipped
# gracefully when PERIGON_API_KEY is unset.
PERIGON_QUERIES = [
    {
        "label": "world",
        "hint": "world",
        "params": {"category": ["Politics", "General"], "country": ["us", "gb", "ca"]},
    },
    {
        "label": "business",
        "hint": "business",
        "params": {"category": ["Business", "Finance"]},
    },
    {
        "label": "markets",
        "hint": "business",
        "params": {"q": "markets OR economy OR earnings OR central bank", "category": ["Finance"]},
    },
]

# Toronto local RSS feeds. A dead feed is skipped gracefully (never crashes the
# run); verify these resolve and swap any that rot.
TORONTO_RSS = [
    {"name": "CBC Toronto", "url": "https://www.cbc.ca/webfeed/rss/rss-canada-toronto"},
    {
        "name": "Toronto Star GTA",
        "url": "https://www.thestar.com/search/?f=rss&t=article&c=news/gta*&l=50&s=start_time&sd=desc",
    },
]


# --- Voices (followed writers) --------------------------------------------

# The followed-Voice registry is repository-backed and reviewed: adding or
# removing a writer is a config change, not an in-app toggle. See VOICES.md.
VOICES_REGISTRY_PATH = "data/voices.json"

# How far back a build looks for new work by a followed Voice. Wider than one
# calendar day so a piece indexed late still lands, and safe to overlap because
# article identity already prevents a repeat.
VOICE_LOOKBACK_HOURS = int(os.environ.get("VOICE_LOOKBACK_HOURS", "36"))

# Timestamps beyond this far in the future are treated as invalid rather than
# as tomorrow's news.
VOICE_FUTURE_SKEW_MINUTES = 120

# Following stays finite. At most VOICE_FOLLOWING_CAP pieces in the morning
# block, and at most VOICE_MAX_PER_VOICE from any one writer before the
# remaining slots are filled by recency, so a prolific writer cannot take the
# whole block. Lower these if the morning read gets long; do not raise them
# automatically because a Voice got busy.
VOICE_FOLLOWING_CAP = 6
VOICE_MAX_PER_VOICE = 2

# Per-run provider request allowances for Voice discovery. The architecture
# must not cost "voices x providers x polls": sources are deduplicated and
# batched (all Guardian contributor tags in one query, all Perigon journalist
# ids in one query, a shared feed fetched once), so these ceilings are an
# alarm for a registry mistake rather than a normal limit.
#
# Perigon is the binding constraint. Its personal tier is documented in
# requests per month (150 as of 2026-09-05), so Voice discovery uses it as a
# once-a-day reconciliation pass, never a poller. Treat live provider limits as
# authoritative and re-check them when tuning.
VOICE_REQUEST_BUDGET = {
    "rss": 24,
    "guardian": 3,
    "perigon": 1,
    "author_page": 8,
}


# --- Release-time Voice watcher -------------------------------------------
#
# The watcher (src/voice_watch.py) is a small, separate job: it looks for new
# work by a followed Voice and sends one quiet ntfy alert for it. It never
# rebuilds the edition. Everything below is operational tuning; the watcher's
# correctness does not depend on any of it. See VOICES.md section 20.

# Durable seen state. Repository-backed, because a git push is a
# compare-and-swap on a ref, which is exactly the primitive at-most-once
# alerting needs, and because this one-reader product already keeps its
# configuration in the repo. Never contains article bodies.
VOICE_WATCH_STATE_PATH = "data/voice_watch_state.json"

# How far back a watcher run will alert. Shorter than the morning edition's
# window: a piece older than this is the morning paper's job, not an alert's.
VOICE_WATCH_LOOKBACK_HOURS = int(os.environ.get("VOICE_WATCH_LOOKBACK_HOURS", "24"))

# Seen state is bounded twice over: entries older than the retention window are
# dropped, and the newest MAX_ENTRIES survive whatever happens. Retention must
# stay comfortably longer than the lookback window, or a still-alertable
# article could be forgotten and alerted twice; a test asserts the margin.
VOICE_WATCH_RETENTION_DAYS = 14
VOICE_WATCH_MAX_ENTRIES = 500

# A finished paper does not buzz six times. Anything beyond this many new
# pieces in one run is recorded as seen and left for the morning edition
# rather than sent, so a feed that dumps its backlog cannot become a burst.
VOICE_WATCH_MAX_ALERTS_PER_RUN = 5

# Quiet hours, in TIMEZONE, as [start, end). Runs inside this range do nothing
# at all: no provider requests, no state writes, no alerts. Work published
# overnight is picked up by the first run after the window closes. Set to None
# to alert around the clock.
VOICE_WATCH_QUIET_HOURS = (23, 6)

# Which providers a frequent (hourly) run may poll, and which are held for the
# once-a-day reconciliation pass. This is the request-budget control that
# matters: Perigon's personal tier is measured in requests per month, so
# polling it hourly would spend a month's allowance in a week. RSS and a
# batched Guardian contributor query are cheap enough to run every hour.
#
# Keys are provider names (adapter.provider), values "frequent" or
# "reconcile". An adapter missing from this map is treated as "reconcile",
# so a new adapter is conservative until someone decides otherwise.
VOICE_WATCH_CADENCE = {
    "rss": "frequent",
    "guardian": "frequent",
    "author_page": "frequent",
    "perigon": "reconcile",
}

# How stale the last reconciliation pass may get before the next run includes
# the reconcile-tier providers. Driven by durable state rather than by a
# second cron entry, so a missed run self-heals instead of skipping a day.
VOICE_WATCH_RECONCILE_HOURS = int(os.environ.get("VOICE_WATCH_RECONCILE_HOURS", "24"))

# Per-run provider allowances for a watcher run. Tighter than the build's,
# because a watcher runs many times a day: the ceiling exists so a registry
# mistake shows up as a logged budget error instead of a quota incident.
VOICE_WATCH_REQUEST_BUDGET = {
    "rss": 24,
    "guardian": 2,
    "author_page": 8,
    "perigon": 1,
}

# Bounded git push retries when the watcher's state commit races the morning
# build's edition commit. Each attempt re-reads state from the remote and
# re-checks what is still unclaimed, so a lost race can never re-alert.
VOICE_WATCH_PUSH_ATTEMPTS = 5


# --- ntfy (the one push channel) ------------------------------------------

# The morning edition push and the Voice watcher share this channel. Override
# the base URL only for a self-hosted ntfy or a test double.
NTFY_BASE_URL = os.environ.get("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")


# --- Gemini (curation model) ----------------------------------------------

# Google Gemini, free tier via an AI Studio key. Override with CURATE_MODEL
# (e.g. "gemini-2.0-flash" or "gemini-2.5-flash-lite") if you hit free limits.
CURATE_MODEL = os.environ.get("CURATE_MODEL", "gemini-2.5-flash")
CURATE_MAX_TOKENS = 16000
# Cap raw stories sent to the model (PRD targets ~40-60), balanced across
# section hints so Toronto and the wire sections all stay represented.
CURATE_MAX_INPUT = 60
# Reasoning budget for the curate call (2.5-series models). A modest budget lets
# the model actually weigh, dedupe, rank, and synthesize rather than paraphrase,
# which is what lifts the lead summaries and the "why it matters" analysis. Set
# to 0 to disable thinking (fastest, cheapest) or -1 for a dynamic budget. One
# call per day, so the extra latency/tokens are immaterial on the free tier.
CURATE_THINKING_BUDGET = int(os.environ.get("CURATE_THINKING_BUDGET", "1024"))


# --- Weather (Open-Meteo weather_code mapping) ----------------------------

def weather_icon(code: int) -> str:
    """Map an Open-Meteo weather_code to an emoji icon."""
    if code == 0:
        return "☀️"  # clear
    if code in (1, 2, 3):
        return "⛅"  # partly cloudy
    if code in (45, 48):
        return "\U0001f32b"  # fog
    if 51 <= code <= 67:
        return "\U0001f326"  # drizzle / rain showers
    if 71 <= code <= 77:
        return "\U0001f328"  # snow
    if 80 <= code <= 82:
        return "\U0001f327"  # rain
    if 95 <= code <= 99:
        return "⛈"  # thunderstorm
    return "⛅"


def weather_condition(code: int) -> str:
    """Short human phrase for today's weather_code."""
    phrases = {
        0: "Clear",
        1: "Mostly sunny",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Freezing fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Freezing rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy rain showers",
        95: "Thunderstorms",
        96: "Thunderstorms with hail",
        99: "Severe thunderstorms",
    }
    return phrases.get(code, "Mixed")


# --- House voice + curate system prompt -----------------------------------

HOUSE_VOICE = """House voice for all summaries:
- Factual and neutral in news sections. The Opinion section may take a position.
- Headline-first. State the news directly; never write "the article reports that".
- Signal over noise. No filler, no motivational language, no hedging.
- No em dashes anywhere. Use commas, periods, or restructure.
- Plain, confident, concrete. Prefer specifics (numbers, names, stakes) over
  abstractions. Every sentence should earn its place.
- Titles and offices (President, Prime Minister, CEO, etc.) must reflect who
  holds them as of the edition date given below, not a title recalled from
  training data or copied from a stale source dateline. If a story describes
  someone exercising an office's authority (ordering military action, signing
  legislation, addressing the nation as its leader), their title must match
  that authority; do not call a sitting official "former". When genuinely
  unsure of someone's current title, state the name without a title
  qualifier rather than risk an incorrect one.
  This rule applies in every section, Opinion included: Opinion's license to
  take a position covers argument and framing, never a person's factual
  title. If a source op-ed's own text uses a stale or wrong title, correct it
  in the summary rather than reproducing the source's error.
  Titles must also be internally consistent across the whole edition: if any
  story anywhere in this batch shows a person actively holding an office,
  every other story mentioning that same person must use that same current
  title, even when summarizing a different, unrelated story about them.

Summary depth by role:
- LEAD stories: 3 to 4 sentences, roughly 70 to 110 words. Go beyond the
  what: include the how and the stakes. Weave in context from other raw
  stories about the same event when it sharpens the picture.
- Supporting stories: 2 to 3 sentences, roughly 40 to 70 words. Tight and
  scannable.

Analysis ("why it matters", lead stories only):
- 1 to 2 sentences, roughly 25 to 50 words, in the "analysis" field.
- This is synthesis, not summary: connect the story to the larger pattern,
  what it changes, or what to watch next. Draw on the whole day's raw pool,
  a market move can explain a political story and vice versa.
- Never restate the summary. If there is no genuine insight, use null rather
  than manufacturing one."""


def build_curate_system_prompt(today=None) -> str:
    """The editor system prompt for the single curate+summarize Gemini call.

    `today` grounds the model against its own training-data priors (e.g. who
    currently holds an office); without it the model has no signal that the
    edition date may postdate its knowledge cutoff and will default to
    stale titles ("former President X") even when the story it's summarizing
    describes that person actively exercising the office.
    """
    import datetime as _dt

    today = today or _dt.date.today()
    section_lines = "\n".join(
        f'  - "{s["id"]}" ({s["label"]}, max {s["cap"]} stories)'
        for s in CURATION_SECTIONS
    )
    return f"""You are the editor of The Daily, a Toronto morning newspaper. Today's edition is dated {today.strftime("%A, %B %-d, %Y")}. You are given a JSON array of raw news stories pulled from wire APIs and Toronto RSS feeds. Produce the finished edition.

This date may be after your training cutoff. Do not assume an officeholder,
title, or ongoing situation matches what you last learned; defer to what the
source stories themselves describe as current. If a story shows someone
actively exercising an office, they hold that office now, regardless of what
you recall about their status.

Your tasks:
1. DEDUPE: collapse the same event reported by multiple outlets into one story; keep the best-sourced, most complete version.
2. SECTION: assign every surviving story to exactly one section:
{section_lines}
3. RANK: order stories within each section by importance; mark exactly one story per section with "lead": true.
4. CUT: respect the per-section caps above. Drop low-signal filler.
5. SUMMARIZE: write a summary for each surviving story in the house voice below. Lead stories get the deeper treatment and an "analysis" field; supporting stories stay tight and "analysis" is null.
6. FLAG: set "tag" to a short uppercase label when warranted (e.g. DEVELOPING, FINAL, WAR, EDITORIAL) or null. Set "sensitivity" to true when the story is centrally about war, violent crime, court proceedings on violent crime, death, or disaster; otherwise false. This drives downstream image suppression.

{HOUSE_VOICE}

Output STRICT JSON only. No preamble, no markdown fences, no commentary. Match this exact schema:
{{
  "sections": [
    {{
      "id": "front",
      "label": "Front Page",
      "stories": [
        {{
          "id": "f1",
          "lead": true,
          "kicker": "MIDDLE EAST",
          "headline": "...",
          "sub": "...",
          "summary": "...",
          "analysis": "... or null",
          "time": "6:45 AM",
          "tag": "DEVELOPING",
          "sensitivity": false,
          "image": "https://... or null",
          "link": "https://..."
        }}
      ]
    }}
  ]
}}

Rules:
- Include every section id listed above, in that order, each with at least one story when source material allows.
- "kicker" is a short uppercase topic label derived from the story (e.g. "UKRAINE", "MARKETS").
- "analysis" is present only on lead stories; null everywhere else.
- "image" and "link" come from the source story; preserve them. If no image, use null.
- "time" is a short human time/day string from the story's publish time (e.g. "6:45 AM", "Yesterday").
- "id" values are short and unique within the edition.
- Return ONLY the JSON object."""

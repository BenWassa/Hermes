"""Central configuration for The Daily.

All tunable constants live here: location, sections, sources, weather mapping,
the Anthropic model, and the curate system prompt (house voice). Secrets are
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

SECTIONS = [
    {"id": "front", "label": "Front Page", "cap": 5},
    {"id": "toronto", "label": "Toronto", "cap": 4},
    {"id": "world", "label": "World", "cap": 4},
    {"id": "sports", "label": "Sports", "cap": 4},
    {"id": "business", "label": "Business", "cap": 4},
    {"id": "opinion", "label": "Opinion", "cap": 4},
]

# Order of section ids, handy for validation and ranking.
SECTION_IDS = [s["id"] for s in SECTIONS]


# --- Sources --------------------------------------------------------------

# Guardian Content API sections -> our section hint.
GUARDIAN_SECTIONS = {
    "world": "world",
    "business": "business",
    "sport": "sports",
    "commentisfree": "opinion",
}

# NYT Top Stories API sections -> our section hint.
NYT_SECTIONS = {
    "world": "world",
    "business": "business",
}

# Toronto local RSS feeds. A dead feed is skipped gracefully (never crashes the
# run); verify these resolve and swap any that rot.
TORONTO_RSS = [
    {"name": "CBC Toronto", "url": "https://www.cbc.ca/webfeed/rss/rss-canada-toronto"},
    {"name": "CP24", "url": "https://www.cp24.com/rss"},
    {"name": "CTV News Toronto", "url": "https://toronto.ctvnews.ca/rss/ctv-news-toronto-1.822319"},
]


# --- Anthropic ------------------------------------------------------------

CURATE_MODEL = "claude-sonnet-4-6"
CURATE_MAX_TOKENS = 8000


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
- 2 to 3 sentences per summary, roughly 40 to 70 words.
- Signal over noise. No filler, no motivational language, no hedging.
- No em dashes anywhere. Use commas, periods, or restructure.
- Plain, confident, concrete."""


def build_curate_system_prompt() -> str:
    """The editor system prompt for the single curate+summarize Claude call."""
    section_lines = "\n".join(
        f'  - "{s["id"]}" ({s["label"]}, max {s["cap"]} stories)' for s in SECTIONS
    )
    return f"""You are the editor of The Daily, a Toronto morning newspaper. You are given a JSON array of raw news stories pulled from wire APIs and Toronto RSS feeds. Produce the finished edition.

Your tasks:
1. DEDUPE: collapse the same event reported by multiple outlets into one story; keep the best-sourced, most complete version.
2. SECTION: assign every surviving story to exactly one section:
{section_lines}
3. RANK: order stories within each section by importance; mark exactly one story per section with "lead": true.
4. CUT: respect the per-section caps above. Drop low-signal filler.
5. SUMMARIZE: write a 2 to 3 sentence summary for each surviving story in the house voice below.
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
- "image" and "link" come from the source story; preserve them. If no image, use null.
- "time" is a short human time/day string from the story's publish time (e.g. "6:45 AM", "Yesterday").
- "id" values are short and unique within the edition.
- Return ONLY the JSON object."""

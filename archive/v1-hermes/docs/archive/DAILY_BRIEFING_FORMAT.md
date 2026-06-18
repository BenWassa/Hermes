# Daily Briefing Format

Developer reference for the Hermes daily briefing schema.

> **Looking for the ChatGPT prompt?** See [DAILY_BRIEFING_PROMPT.md](./DAILY_BRIEFING_PROMPT.md) — the paste-ready prompt optimised for daily use.

The app imports one daily briefing as a JSON object with the following structure.

## Required Fields

- `id`: string in `YYYY-MM-DD` format. This is the unique record key.
- `date`: human-readable display date.
- `today_in_60_seconds`: array of headline tiles.

## Recommended Full Schema

```json
{
  "id": "2026-03-13",
  "date": "March 13, 2026",
  "driver": "ENERGY",
  "system_status": {
    "condition": "ELEVATED",
    "indicator": "VOLATILE"
  },
  "today_in_60_seconds": [
    {
      "id": "story-energy-hormuz",
      "icon": "🛢️",
      "headline": "Oil volatility spikes",
      "domain": "ENERGY",
      "summary": "Short apex summary.",
      "signal_type": "SIGNAL_SHIFT",
      "status": "ESCALATING",
      "target": "Strait of Hormuz",
      "metric": "+17.1% VOL"
    },
    {
      "id": "story-global-rates",
      "icon": "📉",
      "headline": "Markets reprice inflation risk",
      "domain": "MACRO",
      "signal_type": "CONTINUING_SIGNAL",
      "status": "VOLATILE",
      "target": "Front-End Yields",
      "metric": "REPRICING"
    }
  ],
  "what_changed": {
    "new": [
      "Insurers widened Gulf shipping premiums overnight."
    ],
    "intensified": [
      "Oil-linked inflation risk is spreading into developed-market rate pricing."
    ],
    "eased": [
      "Immediate fears of a sustained supply halt moderated after partial rerouting."
    ],
    "changed_meaning": [
      "The story is no longer just regional security; it is now a global macro transmission channel."
    ]
  },
  "major_developments": [
    {
      "id": "dev-1",
      "story_id": "story-energy-hormuz",
      "domain": "ENERGY",
      "region": "MIDDLE EAST",
      "impact": "HIGH",
      "icon": "🛢️",
      "driver": "Iran naval posture shift following US carrier redeployment to the Gulf",
      "change_type": "escalating",
      "story_stage": "peak",
      "headline": "Oil Shock and War Risk",
      "why_it_matters_now": "The disruption has started repricing inflation, shipping, and central-bank expectations simultaneously.",
      "executive_summary": "Short executive summary.",
      "key_facts": [
        "Brent briefly crossed $100",
        "De-escalation signals caused reversal"
      ],
      "next_watchpoints": [
        "Commercial transit volumes through Hormuz in the next 24 hours",
        "Whether shipping insurers widen exclusions again"
      ],
      "tags": ["energy", "shipping", "inflation", "middle-east"],
      "sources": [
        { "name": "Reuters", "url": "https://example.com/reuters-story" },
        { "name": "Bloomberg", "url": "https://example.com/bloomberg-story" }
      ]
    }
  ],
  "timeline_context": {
    "title": "Middle East Escalation Sequence",
    "events": [
      {
        "date": "MARCH 12, 2026",
        "headline": "Strait of Hormuz Disruption",
        "details": "Commercial vessels rerouted following unconfirmed drone activity near major shipping lanes."
      }
    ]
  },
  "risk_matrix": {
    "title": "24-Hour Threat Map",
    "risks": [
      {
        "id": "risk-1",
        "label": "Hormuz transit shock",
        "probability": 0.82,
        "impact": 0.93,
        "details": "Could hit energy, inflation expectations, and shipping simultaneously."
      }
    ]
  },
  "macro_indicators": [
    {
      "id": "ind-01",
      "title": "Brent Crude",
      "metric": "7-DAY VOLATILITY",
      "currentValue": "$98.40",
      "trendValue": "+4.2%",
      "trendDirection": "up",
      "data": [79.2, 79.5, 80.1, 81.0, 78.5, 82.4, 84.5],
      "details": "Spike driven by overnight supply chain disruptions in the Red Sea corridor. Risk premium holding."
    }
  ],
  "analyst_consensus": {
    "consensus": [
      "Energy shock could delay rate cuts globally."
    ],
    "friction": [
      "Some analysts believe the oil spike will reverse rapidly if conflict cools."
    ]
  },
  "strategic_context": [
    "Energy shocks are reintroducing geopolitics into macroeconomic expectations.",
    "Persistent oil elevation could force central banks to maintain tighter policy despite slowing growth."
  ],
  "watchlist": "What to monitor next in the next 24 to 72 hours."
}
```

## Field Notes

- `today_in_60_seconds`: short, high-signal scan layer for the home Bento grid.
- `today_in_60_seconds[].id`: recommended stable link to the matching `major_developments[].story_id` or story thread.
- `system_status`: optional global HUD state shown in the header.
- `driver`: optional top-level header pill label. Prefer a **single uppercase word** such as `ENERGY`, `RATES`, `TRADE`, `WAR`, `AI`, or `CHINA`. This is a compact dashboard label, not the causal sentence used inside `major_developments[].driver`.
- `system_status.condition`: primary posture tier. Five levels, highest to lowest: `CRITICAL` (rose), `SEVERE` / `HIGH` (orange), `ELEVATED` / `VOLATILE` (amber), `GUARDED` / `MODERATE` (blue), `NOMINAL` / `LOW` (cyan).
- `system_status.indicator`: secondary mood descriptor shown below the condition. Examples: `VOLATILE`, `STABLE`, `TRANSITIONING`, `WATCH`, `ESCALATING`.
- `today_in_60_seconds[].domain`: optional routing bucket for pulse tiles. When present, tapping a pulse tile opens the matching development in a modal overlay.
- `today_in_60_seconds[].summary`: optional dense summary text, best used on the apex tile.
- `today_in_60_seconds[].signal_type`: recommended continuity marker for scan speed. Use `NEW_SIGNAL`, `CONTINUING_SIGNAL`, or `SIGNAL_SHIFT`.
- `today_in_60_seconds[].status`: optional live status label for the tile dot indicator. Matches the same 5-tier color system as `system_status.condition`: `CRITICAL` / `ESCALATING` (rose), `SEVERE` / `HIGH` (orange), `ELEVATED` / `VOLATILE` / `MONITOR` (amber), `GUARDED` / `WATCH` (blue), `STABILIZING` / `HOLD` / `NOMINAL` (cyan).
- `today_in_60_seconds[].target`: optional target asset, entity, or region label shown in the tile footer.
- `today_in_60_seconds[].metric`: optional hard metric or state tag shown in the tile footer.
- `what_changed`: **required** daily delta layer for continuity. Distinguish what is new, what intensified, what eased, and what changed in meaning since the prior briefing. The importer will warn if this section is absent.
- `major_developments`: each item renders as an expandable story card.
- `major_developments[].id`: stable story identifier within the day.
- `major_developments[].story_id`: stable cross-day identifier for a persistent narrative thread.
- `major_developments[].domain`: used to match pulse tiles to story modals. Use strict uppercase buckets such as `GEOPOLITICS`, `MACRO`, `TECH`, `ENERGY`, or `DEFENSE`.
- `major_developments[].region`: optional scanning anchor shown above the card headline. Example values: `GLOBAL`, `US`, `EUROPE`, `MIDDLE EAST`, `ASIA`.
- `major_developments[].impact`: optional scanning anchor for visual priority. Recommended values: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `major_developments[].driver`: **required** — one sentence stating what is actually moving this story today. Not what happened, but what is driving it. Keep it causally specific.
- `major_developments[].change_type`: **required** cross-day state change. Lowercase. Use exactly: `new`, `escalating`, `stabilizing`, `resolving`, or `unchanged`.
- `major_developments[].story_stage`: **required** lifecycle marker. Lowercase. Use exactly: `emerging`, `active`, `peak`, `winding-down`, or `resolved`.
- `major_developments[].why_it_matters_now`: one concise line explaining why today changed the importance of the story.
- `major_developments[].next_watchpoints`: short forward-looking triggers or milestones to monitor over the next 24 to 72 hours.
- `major_developments[].tags`: free-form tags for search, clustering, and cross-day synthesis.
- `major_developments[].sources`: short source labels or URLs. Three supported formats: plain string `"Reuters"` (static label), URL string `"https://..."` (rendered as a clickable link), or object `{"name": "Reuters", "url": "https://..."}` (named link). Use URLs when you want direct follow-up access to the original article.
- `timeline_context`: optional chronology block for conflict, policy sequencing, or escalation chains.
- `timeline_context.events`: up to 8 nodes, ordered newest first.
- `risk_matrix`: optional 2x2 risk grid for daily threat concentration.
- `risk_matrix.risks[].probability`: numeric score from `0` to `1`.
- `risk_matrix.risks[].impact`: numeric score from `0` to `1`.
- `macro_indicators`: optional native-SVG sparkline cards for market or macro series.
- `macro_indicators[].trendDirection`: `up`, `down`, or `flat`, used to theme the HUD colors.
- `macro_indicators[].data`: ordered numeric values for a 7-day or 30-day sparkline.
- `macro_sparklines`: legacy fallback still supported by the UI, but new prompt outputs should use `macro_indicators`.
- `analyst_consensus.consensus`: areas of broad agreement.
- `analyst_consensus.friction`: areas of disagreement or uncertainty.
- `strategic_context`: paragraph-level context blocks, ordered from most important to least important.
- `watchlist`: one concise forward-looking analyst note.

## Prompt Output Rules

- Return valid JSON only.
- Do not wrap the JSON in markdown code fences.
- Keep `id` aligned to the actual briefing date.
- Keep headlines short enough to fit mobile cards cleanly.
- Keep summaries dense and analytical, not conversational.
- Keep top-level `driver` to one uppercase word only. Do not use a phrase or sentence there.
- **Every `major_developments` item must include `story_id`, `driver`, `change_type`, and `story_stage`.** These are required for the continuity system to function.
- **`driver` must be causal, not descriptive.** Write what is moving the story today, not just what happened. Bad: “Iran fired drones.” Good: “Iran's renewed naval posture is raising the cost of commercial Hormuz transit for the second time this quarter.”
- **`change_type` must be one of:** `new`, `escalating`, `stabilizing`, `resolving`, `unchanged` (lowercase exactly).
- **`story_stage` must be one of:** `emerging`, `active`, `peak`, `winding-down`, `resolved` (lowercase exactly).
- Always include `what_changed` at the top level. Distinguish what is new, what intensified, what eased, and what changed in meaning.
- Prefer continuity over novelty. When a story persists, update its existing `story_id` and set `change_type` appropriately — do not invent a new ID.
- Keep `major_developments[].domain` MECE where possible so each story fits one primary bucket.
- Prefer consistent uppercase values for `domain`, `region`, and `impact`.
- Prefer full dates such as `”MARCH 12, 2026”` in timeline fields.
- Use the optional visual-stream fields only when they materially improve scan speed; do not force them into every story.
- For `timeline_context.events`, keep each `headline` short and each `details` line specific enough to justify expansion.
- For `risk_matrix`, reserve the top-right quadrant for genuinely high-impact, high-probability scenarios.
- Use standard JSON double quotes: `”`, not smart quotes like `”` or `”`.

## Paste Handling

The importer now sanitizes a few common paste issues before parsing:

- Smart double quotes are converted to standard JSON quotes.
- Smart single quotes are normalized.
- Markdown code fences such as ````json` ... ``` ` are stripped.
- Non-breaking spaces and zero-width characters are removed.

This makes pasted output from chat tools and rich-text editors more tolerant, but the payload still needs to be valid JSON after normalization.

## Minimal Valid Example

```json
{
  "id": "2026-03-13",
  "date": "March 13, 2026",
  "today_in_60_seconds": [
    { "icon": "🌍", "headline": "Macro pressure intensifies" }
  ]
}
```

## Current Implementation Note

The importer validates the following **required** fields and will block import if they are missing:

- `id`
- `date`
- `today_in_60_seconds`

The importer also surfaces **warnings** (non-blocking) when any of the following are absent on a `major_developments` item:

- `story_id`
- `driver`
- `change_type`
- `story_stage`

And a warning when `what_changed` is absent at the top level.

### Pulse → Story matching

When a pulse tile is tapped, the app matches to a development modal in this order:

1. `major_developments[].id === pulse item id`
2. `major_developments[].story_id === pulse item id`
3. `major_developments[].domain === pulse item domain` (fallback)

For the most reliable deep-linking, set the pulse tile's `id` to the same value as the matching development's `story_id`.

### Thread and archive views

The archive can now be browsed by date or by thread. Thread view groups all `major_developments` by `story_id` across all briefings. Story view shows the full cross-day arc of a single `story_id` including `change_type`, `story_stage`, and `driver` per day. Search indexes `story_id`, `driver`, `tags`, `domain`, and `change_type`.

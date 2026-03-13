# Daily Briefing Format

This app imports one daily briefing as a JSON object.

The current UI expects the following structure.

## Required Fields

- `id`: string in `YYYY-MM-DD` format. This is the unique record key.
- `date`: human-readable display date.
- `today_in_60_seconds`: array of headline tiles.

## Recommended Full Schema

```json
{
  "id": "2026-03-13",
  "date": "March 13, 2026",
  "today_in_60_seconds": [
    { "icon": "🛢️", "headline": "Oil volatility spikes" },
    { "icon": "📉", "headline": "Markets reprice inflation risk" }
  ],
  "major_developments": [
    {
      "id": "dev-1",
      "domain": "GEOPOLITICS",
      "region": "MIDDLE EAST",
      "impact": "HIGH",
      "icon": "🛢️",
      "headline": "Oil Shock and War Risk",
      "executive_summary": "Short executive summary.",
      "key_facts": [
        "Brent briefly crossed $100",
        "De-escalation signals caused reversal"
      ],
      "sources": ["Reuters", "Bloomberg", "FT"]
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
- `major_developments`: each item renders as an expandable story card.
- `major_developments[].id`: stable story identifier within the day.
- `major_developments[].domain`: required for the Tactical Breakdown filter bar. Use strict uppercase buckets such as `GEOPOLITICS`, `MACRO`, `TECH`, `ENERGY`, or `DEFENSE`.
- `major_developments[].region`: optional scanning anchor shown above the card headline. Example values: `GLOBAL`, `US`, `EUROPE`, `MIDDLE EAST`, `ASIA`.
- `major_developments[].impact`: optional scanning anchor for visual priority. Recommended values: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `major_developments[].sources`: short source labels only.
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
- Keep `major_developments[].domain` MECE where possible so each story fits one primary bucket.
- Prefer consistent uppercase values for `domain`, `region`, and `impact`.
- Use the optional visual-stream fields only when they materially improve scan speed; do not force them into every story.
- For `timeline_context.events`, keep each `headline` short and each `details` line specific enough to justify expansion.
- For `risk_matrix`, reserve the top-right quadrant for genuinely high-impact, high-probability scenarios.
- Use standard JSON double quotes: `"`, not smart quotes like `“` or `”`.

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

The importer currently validates only:

- `id`
- `date`
- `today_in_60_seconds`

The rest of the fields should still be included, because the UI is built to render the full briefing shape.

The current UI also expects `major_developments` to be present for the Tactical Breakdown section. If `domain` values are supplied, the interface generates filter tabs automatically from those values.

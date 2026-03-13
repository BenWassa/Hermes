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
- `major_developments[].sources`: short source labels only.
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

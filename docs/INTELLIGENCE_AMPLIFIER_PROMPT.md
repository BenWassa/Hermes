# Intelligence Amplifier Prompt

This is the Step 2 prompt for generating a Hermes Intelligence Amplifier.

**Run this after Step 1** (daily briefing) is already imported into Hermes.

The prompt is automatically copied from the Workflow tab with today's briefing JSON embedded — you do not need to manually append the briefing data.

Copy everything between the `---` markers and paste it as your message. Today's briefing data is pre-included.

---

You are a senior strategic intelligence analyst. You have received today's structured daily briefing. Your job is to produce an Intelligence Amplifier — a higher-order analytical layer that transforms "what happened" into "what drives it, where it goes, and what it touches downstream."

Do not re-narrate facts already in the briefing. Amplify causality, forward scenarios, and second-order consequences only.

Today's briefing is appended below. Analyse it fully before writing your output.

Return a single valid JSON object matching the schema below. No commentary, no markdown code fences, no explanation — only the JSON.

## Required output structure

```json
{
  "type": "amplifier",
  "id": "amp-YYYY-MM-DD",
  "briefing_id": "YYYY-MM-DD",
  "date": "Month D, YYYY",
  "delta_lens": {
    "system_shifts": [
      "What is now structurally true that was not true yesterday — a durable change in the system, not a news event."
    ],
    "threshold_crossings": [
      "What crossed a meaningful line today — a point of no return, a policy trigger, a market level."
    ],
    "invalidations": [
      "What prior assumption, consensus view, or scenario no longer holds after today."
    ]
  },
  "driver_decomposition": [
    {
      "story_id": "story-kebab-id-matching-briefing",
      "driver": "The true underlying causal force — what is actually moving this story, not what happened on the surface.",
      "classification": "structural"
    }
  ],
  "system_map": [
    {
      "chain": ["Originating event or pressure", "Intermediate transmission mechanism", "Downstream consequence"],
      "summary": "One sentence describing the full causal chain."
    }
  ],
  "scenarios": {
    "base": {
      "probability": 0.55,
      "path": "Most likely path over the next 48–96 hours.",
      "trigger": "What event or signal would confirm this path is unfolding.",
      "invalidator": "What development would rule out this path."
    },
    "escalation": {
      "probability": 0.25,
      "path": "Adverse or accelerating path.",
      "trigger": "What event would push toward escalation.",
      "invalidator": "What would prevent escalation."
    },
    "de_escalation": {
      "probability": 0.20,
      "path": "Stabilising or unwinding path.",
      "trigger": "What would drive de-escalation.",
      "invalidator": "What would prevent de-escalation."
    }
  },
  "second_order": [
    {
      "domain": "MACRO",
      "effect": "A downstream consequence not immediately obvious — policy responses, market spillovers, system stress propagation.",
      "timing": "instant"
    }
  ],
  "transmission_map": [
    {
      "from": "Source driver or event",
      "to": "Target asset, region, or system",
      "channel": "Mechanism of transmission (e.g. supply shock, sentiment, sanctions, credit conditions)",
      "timing": "lagged",
      "magnitude": "HIGH"
    }
  ],
  "decision_layer": {
    "what_matters_now": [
      "The single most important signal or dynamic to understand right now — compressed to one actionable statement."
    ],
    "watch_next": [
      "The most important forward trigger to monitor in the next 24–72 hours."
    ]
  }
}
```

## Hard rules

- `type` must be exactly `"amplifier"`
- `id` format: `amp-YYYY-MM-DD` — use today's date
- `briefing_id` must match the briefing `id` exactly
- `scenarios` probabilities must sum to `1.0`
- `driver_decomposition[].story_id` must match a `story_id` value from the briefing's `major_developments` — do not invent IDs
- `driver_decomposition[].classification` must be one of: `structural`, `cyclical`, `tactical`, `signaling`
- `second_order[].domain` must be uppercase: `GEOPOLITICS`, `MACRO`, `ENERGY`, `DEFENSE`, `TECH`, `FINANCE`, `CLIMATE`
- `second_order[].timing` must be one of: `instant`, `lagged`
- `transmission_map[].timing` must be one of: `instant`, `lagged`
- `transmission_map[].magnitude` must be one of: `HIGH`, `MEDIUM`, `LOW`
- `decision_layer` is mandatory — always produce it, even if other sections are sparse
- Do not re-narrate Step 1 facts — amplify causality and forward paths only
- Keep all string values compact — this is a mobile-first product, not a report
- Return valid JSON only. No markdown. No code fences. No commentary.

## Priority order

1. `decision_layer` — always the highest signal output; produce this first
2. `delta_lens` — what changed at the system level today
3. `scenarios` — three forward paths with concrete triggers and invalidators
4. `driver_decomposition` — causal clarity per story, one entry per major development
5. `transmission_map` — how events propagate to markets and systems
6. `second_order` — edge vs consensus downstream consequences
7. `system_map` — only include when cross-domain causal chains are clearly present

---

## Usage notes

- The prompt is automatically populated with today's briefing JSON when copied from the Workflow tab in Hermes.
- Import the JSON response via the Import screen. The app will detect `type: "amplifier"` and route it to the correct store.
- The Intel Layer button (⚡) appears on the Home screen once an amplifier is imported for the current briefing.
- `system_map` is optional — skip it on routine days. Include it when multiple stories share a clear causal chain.
- The amplifier is stateless: it does not require prior days' data and should never reference them.

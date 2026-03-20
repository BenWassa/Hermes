// Prompt text for clipboard copy — keep in sync with docs/DAILY_BRIEFING_PROMPT.md
// and docs/SYNTHESIS_PROMPT.md

export function getDailyPrompt(dateStr) {
  // dateStr: "March 16, 2026" or similar human-readable
  return `You are a senior geopolitical and macroeconomic intelligence analyst. Your job is to produce a structured daily briefing covering the most consequential developments in global affairs, markets, and security as of today.

Today's date: **${dateStr}**

Return a single valid JSON object matching the schema below. No commentary, no markdown code fences, no explanation — only the JSON.

REQUIRED OUTPUT SCHEMA:

{
  "id": "YYYY-MM-DD",
  "date": "Month D, YYYY",
  "system_status": {
    "condition": "ELEVATED",
    "indicator": "VOLATILE"
  },
  "today_in_60_seconds": [
    {
      "id": "story-kebab-id",
      "icon": "🛢️",
      "headline": "Short scan headline",
      "domain": "ENERGY",
      "summary": "One-sentence apex summary (apex tile only).",
      "signal_type": "SIGNAL_SHIFT",
      "status": "ESCALATING",
      "target": "Target asset or region",
      "metric": "+4.2% VOL"
    }
  ],
  "what_changed": {
    "new": ["What is genuinely new since yesterday."],
    "intensified": ["What got worse or accelerated."],
    "eased": ["What de-escalated or moderated."],
    "changed_meaning": ["What story shifted in interpretation or implication."]
  },
  "major_developments": [
    {
      "id": "dev-1",
      "story_id": "story-kebab-id",
      "domain": "ENERGY",
      "region": "MIDDLE EAST",
      "impact": "HIGH",
      "icon": "🛢️",
      "driver": "One causal sentence: what is moving this story today, not just what happened.",
      "change_type": "escalating",
      "story_stage": "peak",
      "previous_brief_refs": ["YYYY-MM-DD"],
      "headline": "Story headline",
      "why_it_matters_now": "Why today specifically changed the importance of this story.",
      "executive_summary": "2–3 sentence analytical summary.",
      "key_facts": ["Specific, verifiable fact.", "Another fact."],
      "next_watchpoints": ["Forward-looking trigger to monitor in the next 24–72 hours.", "Second watchpoint."],
      "tags": ["tag1", "tag2"],
      "sources": [{ "name": "Reuters", "url": "https://..." }]
    }
  ],
  "timeline_context": {
    "title": "Escalation Sequence Title",
    "events": [
      {
        "date": "MONTH D, YYYY",
        "headline": "Short event headline",
        "details": "One specific detail that justifies including this node."
      }
    ]
  },
  "risk_matrix": {
    "title": "24-Hour Threat Map",
    "risks": [
      {
        "id": "risk-1",
        "label": "Risk label",
        "probability": 0.75,
        "impact": 0.90,
        "details": "Why this occupies this quadrant today."
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
      "details": "One sentence on what is driving the move."
    }
  ],
  "analyst_consensus": {
    "consensus": ["Area of broad agreement among analysts."],
    "friction": ["Area of active disagreement or uncertainty."]
  },
  "strategic_context": [
    "Most important paragraph of broader strategic framing.",
    "Second-order implication or structural context."
  ],
  "watchlist": "One concise forward-looking note: what to monitor in the next 24–72 hours."
}

HARD RULES:

- story_id must be STABLE ACROSS DAYS. Use the same kebab-case ID for the same underlying story every day. Never rename a story that has already appeared.
- driver must be CAUSAL, not descriptive. State what is moving the story, not what happened. Bad: "Iran fired drones." Good: "Iran's renewed naval posture is raising the cost of commercial Hormuz transit for the second time this quarter."
- change_type must be exactly one of: new, escalating, stabilizing, resolving, unchanged
- story_stage must be exactly one of: emerging, active, peak, winding-down, resolved
- system_status.condition must be exactly one of: CRITICAL, SEVERE, HIGH, ELEVATED, VOLATILE, GUARDED, MODERATE, NOMINAL, LOW
- today_in_60_seconds[].signal_type must be one of: NEW_SIGNAL, CONTINUING_SIGNAL, SIGNAL_SHIFT
- macro_indicators[].trendDirection must be one of: up, down, flat
- domain values must be uppercase: GEOPOLITICS, MACRO, ENERGY, DEFENSE, TECH, FINANCE, CLIMATE
- impact values must be uppercase: LOW, MEDIUM, HIGH, CRITICAL
- timeline_context.events ordered newest first, maximum 8 nodes
- All dates in timeline fields use full format: "MARCH 12, 2026"
- The apex tile (first in today_in_60_seconds) should be the highest-signal story. Include summary on apex tile only.
- Include 4–6 items in today_in_60_seconds and 3–6 major_developments.
- what_changed is required. Never skip it.
- Only include timeline_context, risk_matrix, and macro_indicators when they materially improve clarity.
- Return valid JSON only. No markdown. No code fences. No commentary.`;
}

export function getSynthesisPrompt(fromDateStr, toDateStr, briefings) {
  // fromDateStr / toDateStr: "YYYY-MM-DD"
  const briefingBlock = briefings
    .map((b) => JSON.stringify(b, null, 2))
    .join('\n\n---\n\n');

  return `You are a senior strategic intelligence analyst reviewing a sequence of daily briefings. Your job is to produce a synthesis overlay — a cross-day analysis that identifies persistent story threads, narrative arcs, phase shifts, and risk deltas across the briefing period.

The date range you are analysing: **${fromDateStr} to ${toDateStr}**

The daily briefings are appended below. Review all of them before writing your output.

Return a single valid JSON object matching the schema below. No commentary, no markdown code fences, no explanation — only the JSON.

REQUIRED OUTPUT SCHEMA:

{
  "type": "synthesis",
  "id": "synth-${fromDateStr}-to-${toDateStr}",
  "date_range": {
    "from": "${fromDateStr}",
    "to": "${toDateStr}"
  },
  "active_threads": [
    {
      "story_id": "story-kebab-id",
      "title": "Human-readable story title",
      "status": "active",
      "phase": "escalation",
      "first_seen": "YYYY-MM-DD",
      "last_seen": "YYYY-MM-DD",
      "summary": "2–3 sentence arc summary: what this story did over the review period."
    }
  ],
  "thematic_arcs": [
    "Cross-cutting structural pattern that connects multiple stories.",
    "Second arc or system-level dynamic that emerged across the period."
  ],
  "story_clusters": [
    {
      "label": "Cluster label",
      "story_ids": ["story-id-1", "story-id-2"],
      "rationale": "Why these stories belong together thematically or causally."
    }
  ],
  "delta_risks": [
    {
      "story_id": "story-kebab-id",
      "description": "How the risk profile of this story changed over the period.",
      "direction": "increasing"
    }
  ],
  "phase_shifts": [
    {
      "story_id": "story-kebab-id",
      "from": "emerging",
      "to": "active",
      "date": "YYYY-MM-DD",
      "reason": "What caused the phase transition."
    }
  ],
  "dominant_system": "One phrase naming the dominant geopolitical or macro system driving events this period.",
  "coverage_bias": "Honest assessment of what may be underweighted or missing from the briefings reviewed.",
  "meta_findings": "2–3 sentences on what the period reveals about the broader environment that a single daily briefing would miss."
}

HARD RULES:

- type must be exactly "synthesis"
- id must follow format: synth-YYYY-MM-DD-to-YYYY-MM-DD
- active_threads[].story_id must match story_id values from the briefings exactly — do not invent new IDs
- active_threads[].phase must be one of: emerging, escalation, peak, stabilising, resolution
- active_threads[].status must be one of: active, dormant, resolved
- delta_risks[].direction must be one of: increasing, decreasing, stable
- phase_shifts[].from and .to must be one of: emerging, active, peak, winding-down, resolved
- Do not overwrite or contradict the factual record of any individual daily briefing
- Return valid JSON only. No markdown. No code fences. No commentary.

PRIORITISE:
1. Thread continuity — which stories ran across multiple days and how did they evolve?
2. Identity repair — if the same story appeared under different story_id values, note it in meta_findings
3. Phase detection — look for stories that changed lifecycle stage
4. Risk deltas — which risks got materially worse or better?
5. System dominance — what single system was most structurally significant?
6. Coverage gaps — what important dynamics were underweighted?

--- DAILY BRIEFINGS ---

${briefingBlock}`;
}

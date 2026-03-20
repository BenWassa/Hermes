# Upgrades Backlog

Planned and considered improvements, ordered roughly by priority.

---

## Current Priority

The backlog below predates the March 19, 2026 intelligence review and is now secondary to the schema and workflow upgrades documented in [INTELLIGENCE_REVIEW_2026-03-19.md](/Users/benjaminhaddon/Github Repos/Hermes/docs/INTELLIGENCE_REVIEW_2026-03-19.md).

The near-term sequence is:

1. stabilize the daily briefing schema
2. add a separate synthesis overlay schema
3. make persistent thread identity operational in the UI
4. add validation and tests around import and continuity

---

## Views

### Archive View
Allow browsing of historical briefings by date. Entries displayed as a chronological list. Selecting a date opens the same briefing interface as the Home screen.

### Search View
Full-text and tag-based search across all stored briefings. Useful for surfacing recurring themes, tracking named entities, or finding past developments by keyword (e.g. "China", "rate cuts", "Hormuz").

---

## Features

### Story continuity model
Introduce persistent `story_id` tracking so daily developments become updates to long-running narratives rather than isolated one-day items.

### What changed since yesterday
Add a compact delta layer near the top of the briefing that explicitly marks what is new, what intensified, what weakened, and what meaningfully changed since the prior day.

### Story pages / narrative threads
Allow opening a persistent story view that shows the full cross-day arc of a theme, including linked developments, chronology, and shifts in analyst framing.

### Pulse tile → modal: expand to all developments in domain
Currently the modal shows the first matching development. If multiple developments share a domain, add a swipe or pagination control inside the modal to navigate between them.

### Apex pulse tiles: tap-to-expand quick-view panel
Make the top three `today_in_60_seconds` tiles (the home bento grid) tappable to open a lightweight quick-view panel rather than the full development modal. Panel should surface:
- Story date, local time, and key timeline dates relevant to this development
- `driver` field — the one causal sentence explaining what is moving the story
- Key factors and risk rationale (`why_it_matters_now`, `key_facts`)
- `next_watchpoints` as a compact forward-looking list
- A "Full story →" link to the development modal for the complete detail view
Optimised for a 5-second scan: no scrolling needed to get the signal.

### Briefing import via URL / API
Supplement the manual JSON paste flow with a fetch-from-URL option, enabling automated daily ingestion from a self-hosted or external endpoint.

### Offline support / PWA
Cache the current and recent briefings so the app is usable without connectivity.

### Push / scheduled notifications
Optional daily reminder at a user-set time when a new briefing is available.

### Weekly synthesis view
A rollup card or panel that surfaces cross-briefing patterns from the past 7 days. Group by persistent story thread, not just by date. Could be generated from stored briefings or supplied as an extra JSON field.

### Theme and story clustering
Group related developments across multiple days by tag or keyword. Visualise recurring signals as a connected thread rather than isolated daily entries.

### Trend tracking
Plot `macro_indicators` values across multiple days to show movement over time rather than a single-day sparkline.

---

## UX / UI

### Swipe to dismiss modal
Allow the story modal to be dismissed with a downward swipe gesture on mobile.

### Haptic feedback on tile tap
Light haptic response when a pulse tile is tapped on supported devices.

### Reduced-motion preference
Respect `prefers-reduced-motion` to disable glow animations and slide-in transitions.

### Dark / light theme toggle
The current visual direction is dark-only. A high-contrast light mode would improve readability in bright environments.

---

## Data / Schema

### `today_in_60_seconds[].id` matching
Add stable `id` values to pulse tile items so modal matching is exact rather than relying on domain fallback.

### Persistent `story_id` on `major_developments`
Add a stable cross-day identifier so recurring developments can be linked into a single narrative thread across archive, search, and synthesis views.

### Separate synthesis overlay artifact
Introduce a second import type for multi-day analysis so cross-day memory objects do not have to live inside the daily briefing payload.

### Canonical story identity rules
Define stricter rules for canonical story IDs and thread repair so recurring narratives stop fragmenting across days.

### Change-state metadata on developments
Add fields such as `change_type`, `story_stage`, and `previous_brief_refs` so each daily item can express whether it is new, escalating, stabilizing, or resolving relative to prior briefings.

### Required daily driver field
Add a required `driver` field so each daily briefing or major development states what is moving the system, not just what happened.

### Cross-day memory objects
Support durable objects such as `active_threads`, `thematic_arcs`, `phase_shifts`, and `delta_risks` as first-class data rather than optional one-off additions.

### Multi-day briefing bundle format
A single JSON import that contains multiple days, for bulk backfill of the archive.

### Tags field on `major_developments`
Free-form tag array to enable cross-briefing search and clustering without being constrained to the primary domain bucket.

### Risk delta tracking
Extend the risk schema with trend and delta fields such as `delta_probability`, `delta_impact`, and `trend`.

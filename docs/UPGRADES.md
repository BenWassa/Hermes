# Upgrades Backlog

Planned and considered improvements, ordered roughly by priority.

---

## Views

### Archive View
Allow browsing of historical briefings by date. Entries displayed as a chronological list. Selecting a date opens the same briefing interface as the Home screen.

### Search View
Full-text and tag-based search across all stored briefings. Useful for surfacing recurring themes, tracking named entities, or finding past developments by keyword (e.g. "China", "rate cuts", "Hormuz").

---

## Features

### Pulse tile → modal: expand to all developments in domain
Currently the modal shows the first matching development. If multiple developments share a domain, add a swipe or pagination control inside the modal to navigate between them.

### Briefing import via URL / API
Supplement the manual JSON paste flow with a fetch-from-URL option, enabling automated daily ingestion from a self-hosted or external endpoint.

### Offline support / PWA
Cache the current and recent briefings so the app is usable without connectivity.

### Push / scheduled notifications
Optional daily reminder at a user-set time when a new briefing is available.

### Weekly synthesis view
A rollup card or panel that surfaces cross-briefing patterns from the past 7 days. Could be generated from stored briefings or supplied as an extra JSON field.

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

### Multi-day briefing bundle format
A single JSON import that contains multiple days, for bulk backfill of the archive.

### Tags field on `major_developments`
Free-form tag array to enable cross-briefing search and clustering without being constrained to the primary domain bucket.

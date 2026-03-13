# Commission: GlobalBrief Mobile Intelligence Interface

## Project Objective
Design a mobile-first application interface that renders daily AI-generated geopolitical and macroeconomic briefings from structured JSON into a clean, highly readable intelligence dashboard.

The system prioritizes:
- signal over noise
- fast situational awareness
- visual clarity
- minimal friction in adding new daily briefings

The application will function as a personal intelligence console rather than a traditional news reader.

---

# Core Experience Philosophy

The interface should feel like checking a daily situational awareness panel, not reading an article.

The experience is optimized for three speeds of engagement:

3 seconds - Scan
User sees the Bento grid and instantly understands the day’s key signals.

30 seconds - Understand
User taps a development card to see executive summaries and key facts.

3 minutes - Think
User reads the strategic context and analyst consensus.

---

# App Structure

The application consists of three primary views:

1. Home (Today’s Briefing)
2. Archive (Historical Briefings)
3. Search

---

# View 1 - Home (Today)

## Purpose
This is the primary screen of the app. It always prioritizes today’s intelligence briefing.

### Header

Top bar layout:

GlobalBrief  
Daily Intelligence Briefing

Under the title:

Date: March 9, 2026

---

## State 1 - No Briefing Loaded

If the user has not pasted today's JSON entry:

The screen becomes a minimal prompt interface.

Hero section:

Add Today's Briefing

Large central button:

Add Briefing

Below the button:

Paste the JSON generated from your daily intelligence prompt.

Secondary action:

View Yesterday's Briefing

This ensures the interface is never empty.

---

## State 2 - Briefing Loaded

Once JSON is added, the Home screen renders the full briefing.

The layout uses progressive disclosure. The top-level screen stays clean and fast to scan, while heavier context is revealed through expandable panels.

---

# Component 1 - Daily Pulse (Bento Grid)

This visualizes today_in_60_seconds.

Layout:

Two-column grid of tiles.

Each tile includes:

icon  
headline  
(optional signal metric)

Example:

🛢️ Oil volatility spikes  
📉 Markets reprice inflation risk  
🤖 China accelerates AI push  
⚖️ Pentagon-AI tension emerges  
🌍 Energy shock dominates macro outlook

Interaction:

Tap tile -> opens related story card.

Purpose:

Immediate situational awareness.

---

# Component 2 - Major Developments (Modal)

Tapping any pulse tile in the Bento grid opens a centered modal overlay with the full story detail for the matching development.

The modal contains:

Region / Domain / Impact metadata
Icon + Headline
Executive summary
Key facts (bullet list)
Sources

Dismiss by tapping the backdrop, pressing Escape, or the close button.

Matching logic: the UI first tries to match by `major_developments[].id` against the pulse item's `id`, then falls back to matching by `domain`.

JSON requirement:

Each `major_developments` item should include a primary `domain` value. `region` and `impact` should also be included when available to strengthen scanning anchors. Use stable `id` values to enable direct matching from pulse tiles.

---

# Component 3 - Signal Architecture

Section title:

Signal Architecture

Purpose:

Convert dense chronology, threat clustering, and macro trend movement into compact visual frameworks before the user reads longer-form text.

This layer is rendered inside an expandable disclosure panel and may include any combination of the following optional streams:

Escalation Timeline  
Vertical chronology with 4 to 8 events.  
Best for conflict, policy sequencing, and diplomatic or military escalation.

2x2 Risk Matrix  
Quadrant view of probability versus impact.  
Best for fast prioritization of the day’s threats.

Macro Indicators  
Native SVG sparkline cards with current value, trend delta, and directional color logic.  
Best for rates, commodities, FX, or other compact market signals.

JSON requirement:

These visuals are driven by optional fields such as `timeline_context`, `risk_matrix`, and `macro_indicators`.

---

# Component 4 - Analyst Consensus

Section title:

Analyst Consensus & Disagreements

Rendered as two-column matrix cards.

Left column:

Consensus

Right column:

Points of Friction

Example:

Consensus  
Energy shock could delay rate cuts.

Friction  
Some analysts believe the spike will reverse if conflict cools.

This makes disagreement visually explicit.

---

# Component 5 - Strategic Context

Section title:

Strategic Context

Rendered as a clean reading block.

Each paragraph appears as its own spaced element.

Example:

Theme: Conflict-Driven Inflation

---

# Upgrade Priorities

The current direction is strong, but the next round of work should focus on balance, density, and clearer visual separation across the Home view.

## Header Balance

- Rename the top title from `GlobalBrief` to `Hermes`.
- Rebalance the header so the title feels intentional rather than oversized and floating.
- Use horizontal placement more effectively: date and system status should anchor the left and right edges while the title remains clearly legible in the center.
- Reduce visual mess by making the header read like a clean HUD strip rather than a stacked badge cluster.

## Section Framing

- Move toward shorter section labels where possible. Example: `Pulse` instead of `60-Second Pulse`.
- Add a subtle vertical color line or edge marker on the left side of major sections to improve separation without consuming meaningful width.
- Keep the separators narrow and atmospheric rather than heavy-handed.

## Pulse Tile Density

- The lower four pulse cards currently over-compress on smaller viewports.
- Remove overlapping footer content from those smaller cards; if only one footer item survives, prioritize the right-side takeaway / metric.
- Increase icon size slightly so scan anchors are easier to catch at a glance.
- Continue optimizing the pulse grid for true mobile readability rather than desktop-style symmetry.

## Signal Architecture Enhancements

- Preserve the Signal Architecture section, but make each stream feel more clearly separated through stronger labeling and color identity.
- Use larger framing labels such as `Timeline`, `Threat Map`, and a clearer quantitative / financial label for the sparkline block.
- Simplify titles where possible. Example: `Threat Map` instead of `24-Hour Threat Map`.
- Expand the macro / quantitative block with additional indicators so the visual layer carries more analytical weight.

## Lower-Screen Content Redesign

- Revisit the disclosure-panel pattern used for `Network Consensus`, `Strategic Context`, and related sections.
- The current collapsible treatment feels weak and should be replaced or redesigned.
- Future options may include pinned summary cards, denser matrix layouts, or permanently open modular sections with stronger hierarchy.

## Story Detail Follow-Up

- Sources in the story detail view should become clickable links to the original articles.
- This should support direct follow-up research instead of treating sources as static labels only.

## Guiding Principle For Upgrades

- Favor signal over decorative spacing.
- Use every component to carry meaning.
- Optimize for fast operator scan first, then richer drill-down second.

• Energy shocks are reintroducing geopolitics into macroeconomic expectations.

• Persistent oil elevation could force central banks to maintain tighter policy despite slowing growth.

Typography should emphasize readability.

---

# Component 6 - Watchlist

Highlighted insight block.

Label:

Watchlist

Example:

Strait of Hormuz shipping flows over the next 48 hours may determine whether energy volatility persists.

This is designed to feel like an analyst note.

---

# View 2 - Archive

Purpose:

Allow browsing of historical briefings.

Layout:

Chronological list.

Example:

March 9 2026  
March 8 2026  
March 7 2026

Selecting a date opens the same structured interface as the Home screen.

Archive entries should be stored locally or in a simple JSON store.

---

# View 3 - Search

Purpose:

Allow exploration of historical intelligence.

Search options:

By keyword  
By tag  
By theme

Example queries:

AI  
Energy  
China  
Rate cuts

Results show matching briefings and stories.

---

# Data Input UX

Since the system relies on manual JSON paste, the interface must make this extremely simple.

Add Briefing flow:

1. Open Archive
2. Tap Import Briefing
3. Paste JSON
4. Press Import

The app validates JSON format.

If valid:

The briefing becomes today's entry.

---

# Visual Design Principles

The visual system should follow these guidelines:

Minimal color palette  
Soft background tones  
Clear typography hierarchy  
Large readable text  
Consistent iconography

Suggested feel:

calm  
analytical  
professional

Not flashy.

## Current UI Direction (March 2026)

The active visual direction is a Stark-style mobile HUD: futuristic, high-contrast, and glass-based while still preserving readability and information hierarchy.

Design rules for this mode:

Deep obsidian base with subtle radial glow  
Translucent floating panels (`bg-white/5`, `backdrop-blur`)  
Cyan/amber accent lighting for priority and state  
Rounded aerodynamic surfaces instead of harsh terminal rails  
Depth expressed through emitted light and glow, not heavy gray shadows  

Tone target:

premium  
technical  
responsive  
cinematic, but disciplined

---

# Icon Strategy

Icons are embedded in the JSON and rendered directly.

Common categories:

Energy - 🛢️  
Markets - 📉  
Technology - 🤖  
Conflict - ⚔️  
Policy - ⚖️  
Global systems - 🌍

This avoids frontend classification complexity.

---

# Empty-State Design

If today has no entry:

Display:

Add Today's Briefing

Plus button centered on screen.

Below:

Or view yesterday’s briefing.

---

# Future Expansion Possibilities

Trend tracking  
Story clusters  
Weekly synthesis  
Theme visualization

The JSON schema already supports these via:

tags  
ids  
metadata  
timeline_context  
risk_matrix  
macro_indicators

---

# Design North Star

The interface should feel like opening a personal geopolitical dashboard.

Not a news reader.

Not a social feed.

A calm, high-signal panel that answers:

What happened?  
Why does it matter?  
What should I watch next?

---

End of Commission.

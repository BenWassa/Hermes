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

The layout flows through four structured UI components.

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

# Component 2 - Major Developments

Below the Bento grid.

Stories appear as stacked cards inside a filterable tactical module.

Above the cards, the interface exposes a horizontally scrolling MECE filter bar generated from the story taxonomy.

Default tab:

ALL

Example domain tabs:

GEOPOLITICS  
MACRO  
TECH  
ENERGY

Purpose:

Move from visual scan into structured exploration without overwhelming the user.

Card structure:

Region / Domain / Impact metadata  
Icon  
Headline  
Executive summary

Expanded view reveals:

Key facts (bullet list)

Sources

Example layout:

🛢️ Oil Shock and War Risk

Oil surged nearly 30% before reversing as geopolitical tensions escalated.

Key Facts  
• Brent briefly crossed $100  
• De-escalation signals caused reversal  
• Market volatility spread to equities

Sources  
Reuters · Bloomberg · FT

Interaction:

Tap -> expand / collapse.

Filter interaction:

Tap domain tab -> isolate only stories in that sector.

JSON requirement:

Each `major_developments` item should include a primary `domain` value. `region` and `impact` should also be included when available to strengthen scanning anchors.

---

# Component 3 - Analyst Consensus

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

# Component 4 - Strategic Context

Section title:

Strategic Context

Rendered as a clean reading block.

Each paragraph appears as its own spaced element.

Example:

Theme: Conflict-Driven Inflation

• Energy shocks are reintroducing geopolitics into macroeconomic expectations.

• Persistent oil elevation could force central banks to maintain tighter policy despite slowing growth.

Typography should emphasize readability.

---

# Component 5 - Watchlist

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

1. Tap Add Briefing
2. Paste JSON
3. Press Import

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

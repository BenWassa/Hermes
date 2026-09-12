# Sports V2 — Rendering Contract

**Status:** production authority  
**Date:** 2026-09-11  
**Parent:** #33  
**Related:** `SPORTS_V2.md`, `SPORTS_V2_MAJOR_EVENTS.md`, `SPORTS_V2_PERFORMANCE.md`, `DESIGN.md`

## Purpose

Sports is a dedicated deterministic desk inside the existing Hermes tab system. It consumes normalized Sports state and does not fetch sports data, classify stories or call Gemini in the browser.

## Page hierarchy

The section reads as three editorial chapters:

1. **HOME TEAMS / Toronto** — permanent Leafs, Raptors, Blue Jays rows.
2. **GLOBAL BOARD / Major Events** — active bounded competitions such as Champions League, World Cup or Olympics.
3. **THE READ / Major Headlines** — exceptional already-qualified developments only.

Each chapter begins with a heavy navy rule, small red editorial kicker, larger serif title and short deck. The page remains a broadsheet rather than a dashboard.

## Toronto rows

Fixed reader order is Leafs → Raptors → Blue Jays.

An active row may contain:

- official-hosted decorative mark plus mandatory text name;
- league and season phase;
- last result and opponent;
- current record / compact standing context;
- next opponent and Toronto-local time;
- at most one deterministic major team headline.

Offseason teams collapse quietly; unavailable providers retain the team row with an explicit unavailable state. Stale previous-season record/standing is not used as filler.

### Identity

Remote marks are enhancement only. Hermes references official/league-hosted assets but does not copy a logo pack into the repository.

- Leafs — NHL-hosted SVG, light/dark variants.
- Raptors — NBA-hosted SVG.
- Blue Jays — MLB-hosted SVG.

The name remains visible and authoritative. Marks live in a shared optical slot rather than dictating layout from intrinsic logo dimensions.

## Major Events

Finished matches show settled scores; upcoming fixtures show Toronto-local times. Canada is emphasized where supplied by the domain. Event mode may expand coverage within the hard caps from `SPORTS_V2_MAJOR_EVENTS.md`.

### Champions League

The current league-phase treatment is deliberately compact:

- competition heading;
- one common `League Phase` stage line when all selected matches share it;
- bounded recent results/next fixtures;
- compact standing view showing positions 1, 2, 3, 8 and 9;
- an explicit `Positions 4–7 omitted` row so the compact selection cannot look like missing data;
- a visible qualification boundary between 8 and 9;
- note explaining top 8 direct qualification and positions 9–24 playoff status.

Club crests are derived from the existing ESPN responses and remain subordinate to names/scores.

## Visual rules

Sports uses the Morning Broadsheet system:

- ruled, not boxed;
- warm paper / lamplight dark mode;
- Press Navy for structure, Masthead Red for restrained editorial emphasis;
- serif reading/display type plus uppercase sans-serif furniture;
- tabular numerals for scores/tables;
- no gradients, shadows, betting UI, score carousel or team-colour dashboard chrome;
- static score rows are not fake buttons;
- headline targets remain at least 44 px;
- no horizontal overflow at supported phone widths.

Logos have more visual presence than the original #38 text-only baseline, but they do not become the page hierarchy. Production sizes and loading behavior are defined in `SPORTS_V2_PERFORMANCE.md`.

## Loading and fallback

The final renderer directly emits optional identity fields from the Sports payload. There is no preview MutationObserver/decorator layer.

- Toronto marks reserve 48 × 48 optical boxes (42 × 42 narrow phone).
- Match crests use 30 × 30 boxes; table crests 24 × 24.
- Text/scores render immediately.
- Small neutral placeholders occupy only mark geometry while images settle.
- Failed/slow Toronto marks resolve to typographic initials in the same box.
- Club crest failure never removes the visible club name.
- Reduced-motion users get static loading furniture.

## Rendering seam

`src.sports.presentation.build_sports_payload()`:

- requires all three permanent Toronto snapshots;
- enforces reader order;
- attaches each favourite-team headline once;
- adds the optional trusted Toronto mark contract;
- carries serialized Major Events including optional trusted crest URLs;
- caps Major Headlines at four.

`src.render` inlines:

- `template/sports.css` — editorial layout;
- `template/sports-performance.css` — remote identity/performance furniture;
- `template/sports.js` — deterministic Sports rendering.

These assets are injected only when an edition contains a top-level `sports` payload. Non-Sports editions retain the legacy renderer unchanged.

## Production boundary

Sports V2 is build-owned. Gemini no longer owns the Sports section, broad generic Sport ingestion is retired, and the empty Sports navigation shell is inserted by final edition assembly while the dedicated top-level `sports` payload owns what the reader sees.

The initial production Sports path remains zero-Gemini.

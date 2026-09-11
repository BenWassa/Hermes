# Sports V2 — Rendering Contract

**Status:** issue #38 implementation authority  
**Date:** 2026-09-11  
**Parent:** #33  
**Related:** `SPORTS_V2.md`, `SPORTS_V2_SOURCE_AUDIT.md`, `SPORTS_V2_MAJOR_EVENTS.md`, `SPORTS_V2_PERFORMANCE.md`, `DESIGN.md`

## Purpose

This note defines how the deterministic Sports domain appears inside the existing Sports tab. It does not move production ownership away from the current morning pipeline; #39 owns that final wiring and retirement of generic Sports curation.

The renderer consumes the already-normalized #35/#36/#37 domain contracts. It does not fetch sports data, classify news, rank events, call Gemini, or create a second copy of sports state.

## Page composition

The Sports tab has up to three editorial layers in this order:

1. **Toronto** — always present, with Leafs, Raptors and Blue Jays in that fixed reader order.
2. **Major Events** — present only when an active event has meaningful structured content, or when an active event-mode tournament must explicitly report that verified event data is unavailable.
3. **Major Headlines** — optional, for already-qualified exceptional global/event articles.

A qualifying favourite-team headline is attached directly beneath its Toronto team row. It is not repeated in Major Headlines.

## Toronto rows

### Active team

An active row may contain:

- text identity and league;
- season phase;
- last result and opponent when available;
- current record;
- compact standing context;
- next opponent and Toronto-local date/time;
- at most one already-qualified major team headline.

The row is factual and non-interactive. Only an attached external headline link is interactive.

### Offseason

Offseason teams collapse to a quiet line and the next known game/date if available. They do not preserve stale records or standings merely to fill space.

### Provider failure

The team remains in its permanent position with a restrained unavailable line. One provider outage does not visually remove a favourite team or imply that the team has no games.

## Team identity

The #38 production baseline deliberately uses Hermes-authored text identity (`LEAFS`, `RAPTORS`, `BLUE JAYS`) plus the existing Press Navy/Masthead Red system.

No official league/team logo, traced mark, official colour palette, downloaded brand asset or remote team image was part of #38. The source audit's original permission decision therefore remains the authority for the #38 baseline.

During #39 branch acceptance, remote official/league-hosted Toronto marks and ESPN-hosted Champions League club crests were explored successfully without copying those assets into Hermes. That experiment is **not** production authority. Issue #55 / `SPORTS_V2_PERFORMANCE.md` owns any promotion of remote marks, including loading priority, skeleton/fallback behavior, URL allowlisting, cache policy, request-budget preservation and performance acceptance.

Until #55 is complete, visible text identity remains mandatory and sufficient when any remote mark is absent.

## Major Events

Event snapshots retain the priority and hard caps from #37.

- Finished matches show settled scores.
- Upcoming fixtures show Toronto-local date/time.
- Postponed/cancelled states are labelled rather than rendered as fake scores.
- Canada receives typographic emphasis where the domain marks `canada_involved` or a standing row as Canadian.
- Compact tables render only the selected rows supplied by #37; the UI does not reconstruct a full competition table.
- Olympics-style highlights render as a short ruled list.
- Event mode may expand the amount of content but remains within #37's finite payload.

The renderer does not infer tournament significance from names or scores.

## Major Headlines

Major Headlines accepts only the already-qualified event/global exceptions supplied by the deterministic Sports layer. It is a conventional editorial list with source and description where available. It does not invoke the ordinary story-card interaction model merely to make the section look busier.

## Visual rules

Sports remains part of The Morning Broadsheet:

- ruled, never boxed;
- warm paper / lamplight dark mode from existing design tokens;
- Press Navy for structure and Masthead Red only for true editorial emphasis;
- serif reading text with small uppercase sans-serif furniture;
- no gradients, shadows, score tiles, horizontal carousels, betting treatments or team-colour dashboard chrome;
- tabular numerals for scores and tables;
- no horizontal page overflow at phone widths;
- interactive headline links maintain a 44px minimum target;
- static score rows do not pretend to be buttons.

If #55 promotes remote identity, loading states must preserve these rules: fixed quiet mark slots, no full-card skeletons, no spinner wall, no layout shift and reduced-motion-safe behavior.

## Rendering seam

`src.sports.presentation.build_sports_payload()` is the only new composition layer. It:

- requires all three permanent Toronto snapshots;
- enforces the fixed Leafs → Raptors → Blue Jays order;
- attaches each favourite-team headline once;
- carries the existing `MajorEventsDesk` serialization;
- caps global Major Headlines at four;
- contains no #38 logo/palette contract.

`src.render` inlines `template/sports.css` and `template/sports.js` only when the edition has a top-level `sports` payload. Editions without that payload use the existing renderer without loading or executing Sports-specific presentation code.

The Sports script takes over the stories column only while the existing Sports tab is active. Masthead, weather, tab behavior, service worker and every other section remain owned by the existing template.

## #39 boundary

#38 deliberately does **not**:

- fetch live Toronto or event data during render;
- replace the generic production Sports pipeline;
- change Gemini curation inputs;
- remove broad Sport source configuration;
- add build-time cost telemetry;
- claim live production/device acceptance.

#39 must assemble the production `sports` payload, make Sports V2 the sole production Sports authority, retire generic Sport curation, and run end-to-end live/mobile verification.

## #55 performance boundary

#55 is a focused follow-on rather than an excuse to keep adding preview code to #39. It owns:

- productionizing optional remote Toronto/Champions League identity if retained;
- zero-extra-provider-request crest extraction;
- native image lazy loading / decoding / intrinsic geometry;
- restrained mark skeletons and deterministic fallback;
- Sports first-frame interaction/rendering performance;
- third-party connection strategy;
- service-worker cache narrowing for remote assets;
- performance/Web Vitals regression evidence;
- deletion of the branch-only decorators and duplicate crest-fetch experiment.

The Sports V2 parent should remain open through #55 even if #39 production integration lands first.
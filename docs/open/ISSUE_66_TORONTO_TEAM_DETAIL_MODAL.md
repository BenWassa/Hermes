# Issue #66 — Toronto team detail modal

**Status:** open design/execution spec  
**Issue:** https://github.com/BenWassa/Hermes/issues/66  
**Date:** 2026-09-16  
**Parent product:** Sports V2 / #33  
**Relevant authority:** `SPORTS_V2.md`, `SPORTS_V2_RENDERING.md`, `SPORTS_V2_PERFORMANCE.md`, `DESIGN.md`, `docs/ISSUE_TRACKING.md`

## Product decision

The three permanent Toronto favourite-team rows should become deliberately interactive.

Activating **Maple Leafs**, **Raptors**, or **Blue Jays** opens a **centered modal** with a bounded second layer of team context:

1. current edition-time standing/rank and record;
2. recent scores;
3. next game when available;
4. latest bounded team news.

The compact Sports page remains the primary morning scan. The modal is optional depth for a reader who taps a team; it must not turn the main Sports desk into a dashboard.

This is still a static morning newspaper. “Latest” means the freshest data serialized into the current Daily edition. Opening the modal does not start live polling or call a provider.

## Why this fits the current product

Sports V2 already separates the page into a permanent Toronto block plus bounded major-event/headline layers. The favourite-team row currently carries the latest result, record/standing context, next game and at most one major update. That is the correct first layer.

The missing layer is a compact place to answer the next questions a reader naturally has after seeing a team row:

- Where exactly are they in the standings?
- What have the last few games looked like?
- What is next?
- What has been written about them recently?

Putting those details directly on the Sports page would conflict with the finite broadsheet composition. A modal preserves the existing scan while providing more depth on demand.

## Current implementation evidence

### Structured team state

Current production adapters already fetch schedule history plus standing/record data:

- Leafs: NHL club season schedule + current standings;
- Raptors: ESPN team schedule + team detail;
- Blue Jays: MLB bounded schedule window + standings.

The adapters parse multiple provider games into provider-independent `GameSummary` values, then currently reduce those to one `last_game` and one `next_game` in `TeamSnapshot`.

Therefore, recent-score detail should normally be derived from bytes Hermes already fetched. Do not issue a second schedule call just because the summary model currently discards history.

### Team news

`src/sports/desk.py` already calls `fetch_guardian_team_candidates()` once during the morning Sports build. `src/sports/headlines.py` performs one narrow Guardian search per favourite team, with a default page size of 8 and the current bounded Sports lookback (`SPORTS_NEWS_LOOKBACK_HOURS`, default 36 hours).

The main Sports page then runs the conservative significance gate and promotes at most one major winner per team.

The modal can reuse the **raw targeted candidates already in memory**. This is important: modal detail may include ordinary recent team coverage because the reader explicitly asked for more detail, while the main Sports page keeps the existing high-significance filter.

Baseline target:

- **0 additional structured provider requests**;
- **0 additional Guardian requests**;
- **0 Gemini calls / 0 Sports records in Gemini**.

If live evidence later shows Guardian-only team news is too sparse, source expansion requires explicit evidence rather than silently adding another feed/provider.

## Interaction model

### Trigger anatomy

The Toronto team summary area becomes an accessible button-like trigger.

Do not make the entire `<article>` blindly clickable if it contains the existing major-story anchor. A link inside a button is invalid and creates ambiguous touch behavior.

Preferred DOM relationship:

```text
sports-team article
  team-detail trigger       # team identity + compact structured state
  optional major story link # remains a normal anchor
```

Requirements:

- trigger is at least 44px high and visually spans the natural summary region;
- Enter and Space activate it;
- visible focus is clear in existing Press Navy;
- major-story link remains separately focusable/clickable;
- the row remains fully understandable when never activated;
- do not add a persistent app-style chevron unless Pixel testing shows the row otherwise fails discoverability.

A quiet text cue such as `TEAM DETAIL` may be tested if needed, but it should use existing label furniture and not become a badge.

## Modal design

### Container

A true centered modal is the intended product, including on phone. Do not translate it into a bottom sheet.

Initial sizing target:

- width: `min(92vw, 680px)`;
- max-height: approximately `80–84dvh`;
- internal vertical scroll only when needed;
- safe-area aware;
- on very narrow screens preserve a visible paper margin rather than touching all four viewport edges.

No box shadow. Separation comes from the backdrop, rules, paper tint and edge treatment.

### Header

Use existing Sports identity, not a new team-branded component.

Suggested content:

```text
TORONTO / NHL                 ×
MAPLE LEAFS
32–21–8 · 3rd Atlantic
As of 05:xx Toronto
```

- team wordmark/plain text remains authoritative;
- optional existing approved mark remains decorative/redundant;
- league/phase uses label/meta furniture;
- record + standing are strong but not oversized;
- fetched/edition context is quiet metadata;
- close button is an explicit 44x44 target inside the dialog.

### Section 1 — Standing

Show the team's own standing context, not a full league table.

Examples:

- `3rd Atlantic · 32–21–8`
- `2nd AL East · 1.5 GB`
- `4th Eastern Conference` where the provider only exposes that useful context.

Do not invent a normalized cross-sport “power ranking.” “Ranking” means provider-backed standing/rank within the sport-appropriate scope.

If no standing is available, preserve record/phase and omit the absent fact rather than calculating a fake rank.

### Section 2 — Recent scores

Show the last **5 completed games**, newest first, bounded.

Suggested row:

```text
SEP 15   W   5–2   vs Boston
SEP 13   L   2–4   @ Montréal
```

Rules:

- use tabular numerals;
- result letter may take Press Navy/ink weight, not green/red win/loss colours;
- home/away remains `vs` / `@`;
- date is compact Toronto-local metadata;
- final scores only in the completed list;
- postponed/cancelled games may appear only when needed to explain sequence, with explicit text rather than a fake score;
- do not show stale prior-season games as “recent” in offseason merely to fill five rows.

### Section 3 — Next

One compact next-game line is enough because the modal is not a schedule browser.

```text
NEXT · Thu Sep 17 · 7:30 PM · @ Ottawa
```

Reuse the existing Toronto-local time conversion and postponed/cancelled semantics.

### Section 4 — Latest news

Up to **3** items.

Each item:

- headline;
- source + publication time;
- optional short public description/trail text when it adds value;
- external story link.

Selection baseline:

1. start from already-fetched raw Guardian team candidates;
2. keep only the correct team;
3. canonicalize URLs;
4. collapse obvious duplicates / same-event duplicates;
5. order primarily by recency, with an optional deterministic boost for an item that already passed the existing significance classifier;
6. take at most 3.

Do not require each modal-news item to pass the existing major-headline significance gate. That gate controls **promotion onto the main paper**, not what a reader may see after explicitly opening team detail.

If zero items survive, show either nothing under the news heading or one restrained line such as `No recent team news in this edition.` Do not manufacture filler.

## Visual style research and translation

### External sports-product pattern

Sports products commonly separate team content into dedicated `Games`, `News`, and `Standings` destinations/tabs. That pattern is efficient for deep sports apps but would add another navigation system inside Hermes.

Hermes should borrow the **information hierarchy** but not the app chrome:

- identity and current standing first;
- compact recent results second;
- news last;
- one bounded vertical composition, no internal tab bar.

The modal should read like a clipped sports-page insert rather than a mini ESPN/theScore surface.

### Hermes design translation

Preserve the existing Morning Broadsheet system:

- warm paper and lamplight dark mode;
- Georgia for reader-facing text;
- Arial uppercase for furniture/meta;
- Press Navy structure;
- Masthead Red only where existing editorial meaning warrants it;
- 1px rules between subsections;
- no rounded score cards;
- no gradients;
- no drop shadow;
- no team-colour backgrounds;
- no green/red result semantics;
- no carousel;
- no horizontally scrolling results strip.

The modal itself is a container by necessity, but its contents should still be **ruled rather than carded**.

## Accessibility research

Prefer the native HTML `<dialog>` element with `showModal()` unless production-browser evidence requires a fallback.

Relevant current W3C guidance:

- WCAG Technique H102: https://www.w3.org/WAI/WCAG22/Techniques/html/H102
- ARIA Authoring Practices modal dialog pattern: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/

Native `<dialog>` is attractive here because browser behavior covers several failure-prone modal responsibilities: modal background inertness, focus movement, focus return in common cases, and Escape dismissal.

Acceptance behavior remains explicit regardless of implementation:

- focus moves into the modal;
- semantic dialog has a visible accessible name;
- background is inert;
- Tab/Shift+Tab do not leak into the paper;
- Escape closes;
- visible close button exists inside the modal;
- focus returns to the exact team trigger that opened it;
- page scroll position is preserved;
- the underlying page does not scroll while the modal is open;
- modal content itself can scroll when taller than the bounded viewport.

Do not rely on `aria-modal=true` alone while leaving background controls operational.

## Data contract

Avoid a second provider schema. Reuse the current domain types.

A reasonable serialized direction is:

```text
sports.toronto[]
  snapshot
    team
    phase
    last_game
    record
    standing
    next_game
    fetched_at
  headline
  mark
  detail
    recent_games[]
    latest_news[]
```

Notes:

- `record`, `standing`, `next_game` remain canonical in `snapshot` and are reused by the modal; do not duplicate them under `detail` unless serialization ergonomics clearly justify a read-only projection.
- `detail.recent_games[]` should be provider-independent `GameSummary` data.
- `detail.latest_news[]` should contain only the bounded source/public metadata required for rendering.
- no raw provider objects in `data/latest.json`.
- no hidden client fetch URLs or API credentials in the page.

### Domain implementation options

Preferred direction is to refactor provider parsing so a schedule payload is parsed once and both summary + recent-game projection are derived from the same normalized game list.

Acceptable shapes include:

- a small provider-independent `TeamState`/`TeamBuild` object containing `snapshot` plus bounded recent games; or
- provider functions that expose a normalized games helper to orchestration while retaining `TeamSnapshot` as the compact state.

Avoid three parallel team-specific “modal” parsers.

## News reuse contract

Change orchestration so `raw_team_news` can serve two consumers:

```text
Guardian targeted team searches
  -> raw candidates
     -> conservative significance gate -> main-row max-one major headline
     -> bounded detail selector        -> modal max-three recent team items
```

This preserves one discovery path and makes the distinction between **promotion** and **detail** explicit.

The detail selector must never feed Gemini.

## Performance contract

Opening the modal should be effectively instant because its content is already serialized in the edition.

Hard requirements:

- no provider request on click;
- no Gemini request on click;
- no new image fan-out beyond assets already allowed by the Sports identity contract;
- modal DOM may be built lazily on first open or pre-rendered hidden; choose the simpler path that protects Sports-tab INP;
- if dynamically built, preserve current scroll position and avoid rebuilding the full Sports section;
- modal close/open must not disturb PWA/offline behavior.

`SPORTS_V2_PERFORMANCE.md` only needs updating if implementation materially changes request/load behavior.

## Failure states

### Team provider unavailable

The team row already remains present with an unavailable state. Modal behavior should remain useful and truthful:

- header/identity still opens;
- scores/standing show a quiet unavailable state;
- independently available team news may still render;
- do not suppress the modal merely because structured data failed.

### News unavailable

Scores/standing still render. No broad fallback feed is triggered on click.

### Partial structured data

Render the available facts independently. Do not hide scores because standing failed or vice versa.

### Offline

The modal works from the serialized cached edition. External news links may of course require network connectivity, but their metadata remains readable.

## Tests

### Domain / serialization

- Leafs/Raptors/Jays derive last five final games correctly from existing provider payloads.
- Ordering is newest first and hard-capped at five.
- Phase boundaries do not pull prior-season filler into an offseason detail panel.
- Postponed/cancelled games are not misrepresented as final scores.
- Snapshot last/next/record/standing truth remains unchanged.
- Detail selector returns max three news items per team.
- Team news cannot leak across Toronto teams.
- Canonical URL/title dedupe is deterministic.
- A major headline may also appear in modal detail once, not as a duplicate pair.
- Empty news is valid.
- Sports model payload remains empty.
- baseline request counters do not increase.

### Browser / interaction

- each Toronto trigger opens the matching modal;
- no Sports API/network request is caused by opening it;
- modal is centered on supported phone/desktop viewports;
- close button, Escape, and optional backdrop-close behavior work;
- keyboard focus enters and remains inside;
- focus returns to the invoking team;
- article links remain independently operable;
- background does not scroll;
- dialog content scrolls when needed;
- no horizontal overflow;
- light/dark mode;
- reduced motion;
- 125% text / enlarged type;
- phone portrait, narrow phone and landscape;
- cached/offline edition still opens the modal.

### Pixel acceptance

Before closing #66, inspect exact production output on the owner Pixel/PWA:

- discoverability of team-row tap;
- modal centering/proportions;
- one-thumb close action;
- recent-score readability;
- news density;
- underlying page scroll restoration;
- no feeling of an unrelated sports app embedded in the newspaper.

## Documentation closeout

When implementation ships:

- update `SPORTS_V2_RENDERING.md` with the team-detail interaction and final composition;
- update `DESIGN.md` only if a centered modal becomes a reusable Hermes component rather than a Sports-local exception;
- update `SPORTS_V2.md` / `SPORTS_V2_PERFORMANCE.md` only where the final data/request contract changes existing truth;
- move this file to `docs/closed/ISSUE_66_TORONTO_TEAM_DETAIL_MODAL.md` after merged-main and required production/Pixel verification;
- close #66 in the same closeout pass.

Do not leave a duplicate planning document after the durable authority is reconciled.

## Non-goals

- live scores;
- client-side provider polling;
- full schedule browser;
- full league standings table;
- player stats or rosters;
- injury database;
- betting/fantasy data;
- team chat/social feed;
- a new team-specific colour system;
- bottom sheet;
- full-screen sports mini-app;
- another Guardian query per team;
- broad Sports feed;
- Gemini sports summarization.

## Acceptance criteria

- [ ] Leafs, Raptors and Blue Jays summary areas open a centered team-detail modal.
- [ ] Modal shows provider-backed current standing/rank and record where available.
- [ ] Modal shows up to five truthful recent completed scores, newest first.
- [ ] Modal shows the next game when available.
- [ ] Modal shows up to three bounded recent team-news items derived from the existing targeted discovery results.
- [ ] Main Sports row and major-headline policy remain unchanged when modal is never opened.
- [ ] Opening the modal causes zero provider/Gemini requests.
- [ ] Baseline daily request budget does not increase.
- [ ] No duplicate/parallel team-provider parsing path is created.
- [ ] Keyboard, screen-reader, focus-return and background-inert behavior meet modal accessibility requirements.
- [ ] Pixel/narrow mobile, landscape, dark mode, enlarged text and offline/cached-paper checks are green.
- [ ] Existing Sports provider-failure isolation and Daily publication safety are preserved.
- [ ] Durable docs are reconciled and this spec is archived only after merged-main production verification.

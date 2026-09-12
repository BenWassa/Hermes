# Sports V2 — Performance and Media Loading

**Status:** production authority for #55  
**Parent:** #33  
**Related:** #39, `SPORTS_V2.md`, `SPORTS_V2_RENDERING.md`, `DESIGN.md`

## Purpose

Sports V2 uses remote official/league-hosted marks to add identity without turning Hermes into a live-score app. Those marks are enhancement only: team names, scores, records, standings and fixtures are the product and must remain immediate and complete when every image is slow, blocked or offline.

This document defines the production loading, cache and performance contract.

## Locked principles

1. **Text never waits for imagery.** Sports state is build-time data embedded in the edition; opening the tab performs no sports-data fetch.
2. **Identity has fixed geometry.** Remote marks reserve their final optical box before the request settles, so arrival cannot move score/text layout.
3. **Above-fold and below-fold have different priority.** Toronto marks are allowed to load immediately after Sports activation; competition crests use native lazy loading and low fetch priority.
4. **No presentation-only provider calls.** Crest URLs come from the same ESPN scoreboard/standings responses already required for structured state.
5. **Trusted remote origins only.** HTTPS identity URLs are normalized through a narrow allowlist in `src/sports/identity.py`.
6. **Remote assets are not PWA shell assets.** The service worker does not retain cross-origin logo responses in its cache.
7. **Failure is quiet.** A failed/slow Toronto mark resolves to a stable typographic fallback; a failed club crest leaves its reserved box without broken-image furniture.
8. **Reduced motion is respected.** The small loading placeholder becomes static under `prefers-reduced-motion: reduce`.
9. **One production path.** Branch preview decorators, duplicate ESPN enrichment calls and preview workflows are not part of production.
10. **Gemini remains zero.** None of this changes the Sports model budget.

## Production identity contract

### Toronto

`src/sports/presentation.py` adds optional `mark` metadata to the three permanent Toronto rows.

Current remote sources:

- Maple Leafs — NHL-hosted SVG; light/dark variants.
- Raptors — NBA-hosted SVG.
- Blue Jays — MLB-hosted SVG.

The assets are referenced remotely; Hermes does not copy or redistribute a logo pack.

Each mark has:

- trusted HTTPS URL;
- optional dark-mode URL;
- typographic fallback;
- fixed 48 × 48 optical slot (42 × 42 on narrow phones);
- explicit HTML width/height attributes;
- async decode;
- no high-priority fetch hint.

### Champions League / ESPN-backed event identity

`src/sports/espn_events.py` extracts the smallest useful presentation identity from the existing response:

- `home_logo_url` / `away_logo_url` on matches;
- `logo_url` on selected standing rows.

Direct provider logo URLs are accepted only if trusted. If ESPN supplies a team id but no acceptable direct logo URL, the adapter derives the known ESPN CDN URL deterministically. This does **not** create another HTTP request during the build.

Rendered crests use:

- 30 × 30 optical match box;
- 24 × 24 table box;
- slightly smaller narrow-phone boxes;
- `loading="lazy"`;
- `decoding="async"`;
- `fetchpriority="low"`;
- `object-fit: contain`.

## Loading furniture

Only the identity box has a loading state. Scores and text are never skeletonized.

The placeholder:

- uses existing Hermes neutral/tint tokens;
- is fixed-size from first paint;
- uses a restrained opacity breathe rather than a moving shimmer;
- is static under reduced motion;
- settles with a short opacity transition after a successful image decode;
- times out after a bounded interval rather than animating forever.

A timeout/error cannot change row geometry.

## Sports activation

Sports DOM remains absent before the Sports tab is active, so remote Sports imagery cannot request during ordinary Front Page reading.

On clear Sports intent, the client may warm only the high-fan-out ESPN crest origin. It does not globally preconnect to NHL, NBA and MLB CDNs.

Lower Major Events / Major Headlines desks use `content-visibility: auto` with intrinsic sizing so supporting content does not compete unnecessarily with the first Toronto frame on supporting browsers.

No framework, virtualization, infinite scrolling or arbitrary delay is introduced.

## PWA cache policy

`docs/sw.js` now uses an explicit same-origin strategy:

- navigation: network-first, cached-paper fallback;
- same-origin shell/static assets: cache-first;
- cross-origin resources: network/browser HTTP cache only.

The service worker therefore no longer places every non-navigation request into one generic unbounded cache. Provider-hosted marks can fail offline without harming the readable cached edition.

Cache version: `the-daily-v2`.

## Performance targets

Hermes uses the standard good Core Web Vitals envelopes as product targets rather than treating a single lab score as truth:

- LCP ≤ 2.5 s;
- INP ≤ 200 ms;
- CLS ≤ 0.1.

Sports-specific acceptance:

- zero remote Sports image requests before Sports activation;
- Toronto text/state paints without waiting for image success;
- crest arrival contributes effectively zero layout movement;
- no extra structured provider request is made solely to obtain identity;
- below-fold competition crests remain native-lazy/low-priority;
- failed CDN assets do not expose broken-image UI;
- dark mode, narrow phone, landscape and enlarged text remain stable;
- cached/offline paper remains understandable with zero remote marks.

A Lighthouse/mobile report may be retained as informational evidence, but hardware-sensitive aggregate scores are not a sole merge gate.

## Verification authority

Deterministic coverage lives in:

- `tests/test_sports_identity.py` — trusted origins, existing-response crest extraction, pre-activation behavior, fixed mark geometry and service-worker policy;
- `tests/test_sports_render_browser.py` — responsive/dark/large-text composition;
- `tests/test_sports_league_phase_render.py` — compact League Phase semantics and qualification cut;
- provider and production-integration tests — request budget, failure isolation and zero-model contract.

The final gate is the full repository suite plus owner mobile acceptance. The owner approved the final Sports visual direction on September 11, 2026.

## External basis

Implementation follows browser-native guidance rather than adding an image-loading library:

- MDN `<img>` loading/decoding/intrinsic dimensions;
- web.dev Core Web Vitals guidance;
- web.dev resource-hint guidance;
- web.dev PWA caching guidance.

The durable contract is this repository document; external guidance informs it but does not override Hermes product/design authority.

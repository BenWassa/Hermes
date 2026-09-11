# Sports V2 — Performance and Media Loading

Status: scoped for Issue #55. No implementation authority yet.

## Purpose

Sports V2 now has enough visual identity that performance is a product concern rather than a cosmetic cleanup.

The branch preview proved that official/league-hosted Toronto marks and Champions League club crests materially improve the section. It also exposed the cost of adding many small third-party images to a deliberately simple static newspaper: opening the Sports tab feels slower and the marks arrive progressively without a coherent loading treatment.

This note defines the production performance contract before that preview experiment is promoted.

The goal is not to make Sports behave like a live-score app. The goal is to preserve the finished-paper feeling while making the structured Sports page feel immediate on a phone.

## Product principles

1. **Text is the product; marks are enhancement.** Scores, team names, standing context and next fixtures must never wait for a remote image.
2. **Sports opens immediately.** The first visible Toronto block should paint inside a normal responsive interaction envelope even on a cold mobile load.
3. **Remote identity arrives quietly.** No row should jump because a logo arrives late.
4. **Below-fold work stays below the fold.** Opening Sports must not eagerly fetch and decode every Champions League crest.
5. **No new request pressure for presentation metadata.** Crest identity must be derived from provider responses already fetched for Sports state.
6. **Offline remains useful.** A cached edition with zero remote logos must still be complete and understandable.
7. **One production path.** The temporary preview decorators, duplicate ESPN crest calls and branch-only CSS/JS are disposable evidence, not architecture.

## Current architecture and audit

### What is already good

- Sports data is generated at build time and embedded in the static edition.
- No client sports-data fetch is required when the reader taps Sports.
- `template/sports.js` delays Sports DOM creation until the Sports tab is active.
- The section is finite and bounded.
- Text names remain visible alongside all identity marks.
- The current Champions League preview already uses native `loading="lazy"` and `decoding="async"` for club crests.
- Existing Playwright coverage exercises phone portrait, narrow phone, landscape, dark mode and enlarged type.

### What is currently weak

#### 1. Activation is still one large synchronous render

The tab handler ultimately replaces `#stories.innerHTML` with the full Toronto + Major Events + Major Headlines markup in one operation.

The content volume is not enormous, so this may be acceptable once image loading is fixed, but it is currently unmeasured. The lower event/table subtree should not be allowed to delay the first visible Toronto frame.

#### 2. Preview identity is post-render decoration

The Toronto mark experiment and Champions League crest experiment live in the temporary branch preview builder. A `MutationObserver` waits for Sports markup and then decorates it.

That was appropriate for visual exploration because it avoided contaminating production contracts. It is not the desired final architecture. Production rendering should know about optional image identity directly.

#### 3. Intrinsic image geometry is inconsistent

CSS defines optical boxes, but remote `<img>` elements do not consistently carry HTML `width` and `height` attributes.

Explicit dimensions let the browser reserve geometry before the asset arrives and are especially important for lazy-loaded images.

#### 4. No coherent loading state

A remote image currently either appears or disappears on error. There is no deliberately designed unsettled state, no bounded slow-load fallback and no reduced-motion contract.

#### 5. Third-party origin fan-out

Toronto identity currently spans NHL, NBA and MLB origins. Champions League crests are served from ESPN identity infrastructure. Opening Sports can therefore require multiple DNS/TLS connections on a cold phone.

The correct response is not to globally preconnect to every league CDN. Most readers may not open Sports in a given session, and unnecessary preconnects consume connection resources.

#### 6. Service-worker caching is too broad

`docs/sw.js` currently uses one `the-daily-v1` cache and cache-firsts every non-navigation request after a cache lookup.

That means cross-origin images can be retained in the same generic cache without an explicit freshness, origin or entry-count policy. This was tolerable when Hermes owned almost all its visual assets. It becomes a poor contract once provider-hosted team marks are deliberately introduced.

#### 7. No performance regression budget

Hermes has correctness and responsive rendering gates but no explicit performance acceptance. A change can therefore preserve layout tests while significantly increasing network work or interaction latency.

#### 8. Preview crest enrichment duplicates ESPN requests

The branch-only `_attach_champions_logo_preview()` makes a second scoreboard call and a second standings call solely to recover team presentation fields discarded by the normalized production adapter.

That is exploration debt. The production solution must capture the small identity fields required from the existing two ESPN responses instead.

## Browser-performance basis

The implementation should use browser-native primitives before custom code.

### Core Web Vitals

Current good thresholds are:

- Largest Contentful Paint (LCP): <= 2.5 s
- Interaction to Next Paint (INP): <= 200 ms
- Cumulative Layout Shift (CLS): <= 0.1

Reference: https://web.dev/articles/vitals

Hermes is a personal application rather than a search-driven public product, but these thresholds remain useful user-centered budgets.

### Native image loading

For below-fold imagery, use native `loading="lazy"` rather than a JavaScript lazy-loading library.

Every image should have explicit dimensions so geometry exists before load. Non-critical dynamically inserted imagery should use asynchronous decoding.

References:

- https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/img
- https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Lazy_loading
- https://web.dev/learn/design/responsive-images

### Fetch priority

`fetchpriority` should remain a measured hint, not a blanket performance switch.

Decorative event crests are not LCP resources and should never be promoted to high priority merely because they are visible eventually.

Reference: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/fetchpriority

### Connection hints

`preconnect` can remove DNS/TCP/TLS setup time, but unnecessary preconnects consume sockets and can delay more important work.

Hermes should only preconnect when an origin is likely to be used imminently, ideally after clear Sports intent.

References:

- https://web.dev/learn/performance/resource-hints
- https://web.dev/articles/preconnect-and-dns-prefetch

### Offscreen rendering

If DOM/style work remains material after image fixes, `content-visibility: auto` is the preferred low-complexity option for genuinely offscreen Major Events/Headline sections, paired with a realistic `contain-intrinsic-size`.

Reference: https://web.dev/articles/content-visibility

### Interaction work

Large synchronous DOM updates can increase presentation delay and hurt INP. The first response to a tap should do only the work needed to show the next frame.

References:

- https://web.dev/articles/optimize-inp
- https://web.dev/articles/dom-size-and-interactivity

## Production identity contract

### Toronto teams

The three permanent marks may use official/league-hosted remote assets already proved by the branch preview.

Required fields should be configuration-owned and intentionally small, for example:

```text
team key
light logo URL
dark logo URL when genuinely required
text fallback
optical scale override only when visual QA proves necessary
```

Do not copy third-party SVG files into the repository as if Hermes owned them.

### Champions League

ESPN scoreboard/standings team objects already contain team identity sufficient to derive a crest URL or team ID.

The normalized event contract may gain only the optional fields the renderer needs, for example:

```text
home_logo_url
away_logo_url
standing row logo_url
```

The adapter should populate them from the exact response already in hand. If only a stable ESPN team ID is available, deterministic construction of the known ESPN crest URL is acceptable.

Do not retain whole raw team objects.

### URL safety

Remote identity is presentation data, but it still enters HTML.

Production should:

- require `https://`;
- accept only explicitly documented official/provider image origins;
- reject/omit anything else;
- keep `referrerpolicy="no-referrer"` where appropriate;
- escape all ordinary text independently of image identity.

A site-wide Content Security Policy is not required by Issue #55, but the asset-origin list should be structured so a later `img-src` CSP can adopt it cleanly.

## Loading hierarchy

### Before the Sports tab is opened

Expected remote Sports-image requests: **zero**.

Do not make Sports identity part of the initial Daily critical rendering path.

### On Sports activation

The reader should immediately get:

1. `TORONTO` heading;
2. Leafs row;
3. Raptors row;
4. Blue Jays row.

Their text and structured state must not wait on remote identity.

The three Toronto logo slots may start loading on activation because they are permanent first-screen furniture. They should use:

- explicit dimensions;
- asynchronous decoding;
- `object-fit: contain`;
- fixed optical slots;
- ordinary/auto priority unless measurement proves otherwise.

### Major Events / Champions League

Crests below the visible viewport use:

- fixed 20–24 px optical slot;
- explicit dimensions;
- `loading="lazy"`;
- `decoding="async"`;
- `fetchpriority="low"` only if browser testing shows it behaves as intended;
- fixed text layout independent of image completion.

Opening Sports must not start every far-below-fold crest request at once.

## Skeleton / loading-state design

Hermes should use **mark skeletons**, not content skeletons.

The Sports data itself already exists locally, so hiding real scores behind gray bars would make the experience slower, not faster.

### Visual treatment

- fixed box exactly matching the final logo slot;
- neutral/tinted paper treatment using existing Hermes tokens;
- no rounded app-card container;
- no moving gradient shimmer;
- optional subtle opacity pulse only;
- mark is decorative, so no loading announcement to assistive technology.

### Reduced motion

Under `prefers-reduced-motion: reduce`, the skeleton is static.

### Settling

A successful image may fade from placeholder to mark over a very short interval if visual QA prefers it. This is polish, not required feedback.

A failed or excessively slow asset must settle into the text/initial fallback rather than pulse forever. The timeout should be bounded and chosen through testing rather than an arbitrary long delay.

### Geometry

Placeholder -> mark -> fallback must preserve the same box dimensions. Crest loading should therefore contribute effectively zero layout shift.

## Rendering strategy

Use evidence to choose the smallest intervention.

### Step 1 — image work only

First implement correct lazy loading, image geometry and skeleton settlement. Re-measure Sports-tab interaction.

### Step 2 — offscreen containment if required

If lower content still affects the interaction, apply `content-visibility: auto` to coarse Sports subsections, not individual tiny nodes. Give them a realistic intrinsic-size estimate so scrollbar geometry does not jump.

Likely candidates:

- `.sports-events`
- `.sports-headlines`

Do not apply it to the first Toronto block.

### Step 3 — split-frame rendering only if still necessary

If measurement still shows a poor first Sports frame, render Toronto synchronously and schedule the lower blocks after the browser has had a chance to paint.

Do not introduce arbitrary delays, virtualization or an application framework.

## Connection strategy

Do not put four global preconnect tags in the Daily `<head>`.

The likely useful optimization is an **intent-driven preconnect** to the high-fan-out ESPN crest origin when the reader focuses, presses or otherwise signals intent on the Sports tab.

Requirements:

- one high-value origin at most unless measurement proves another;
- no duplicate hints;
- no effect on sessions that never approach Sports;
- measure cold-network improvement before keeping it.

The three Toronto one-off origins are not automatically worthy of preconnect because each supplies only one small mark.

## Service-worker policy

The current service worker should be narrowed while this work is done.

### Keep

- network-first navigation;
- cached edition fallback for offline reading;
- deliberate same-origin app-shell caching.

### Change

Do not treat every non-navigation request on the internet as a permanent app-shell asset.

Default production direction:

- same-origin GET assets: explicit/cacheable strategy;
- cross-origin sports marks: bypass the Hermes service-worker cache and rely on provider/browser HTTP caching;
- text fallback makes remote logos non-essential offline.

This avoids opaque-response accumulation and stale official marks.

If later evidence supports a dedicated Sports mark cache, it needs all of:

- explicit origin allowlist;
- separate cache name/version;
- bounded entry count;
- bounded freshness semantics;
- activation cleanup;
- tests for provider failure/offline behavior.

Do not build that complexity speculatively in #55.

## Measurement contract

### Deterministic Playwright gates

Add tests that prove behavior rather than only appearance.

Required assertions:

1. no remote Sports-image request before Sports activation;
2. text/structured Toronto state appears even when every logo route is delayed;
3. far-below-fold Champions League crests are not all requested immediately on activation;
4. scrolling toward those crests initiates their loading;
5. image load completion does not change row position/height beyond a negligible pixel tolerance;
6. 404/failed image settles to intended fallback with no broken-image icon;
7. deliberately slow image does not leave an endless skeleton;
8. `prefers-reduced-motion` disables skeleton animation;
9. dark mode, 125% root text and 320 px width remain overflow-free;
10. offline/cached document is understandable without remote marks;
11. production no longer needs the branch preview `MutationObserver` decorators.

### Performance timing

Instrument the generated page in lab tests with small, explicit marks around Sports activation.

Suggested measurement:

```text
sports-open-start
sports-toronto-painted
sports-desk-settled (optional diagnostic, not interaction gate)
```

The key product measurement is open -> Toronto paint, not "all remote crests finished".

The target should fit inside the <=200 ms INP-good envelope in a representative lab/Pixel run, with enough CI headroom that normal runner jitter does not create flakes.

### Core Web Vitals

Keep the overall page goals:

- LCP <= 2.5 s
- INP <= 200 ms
- CLS <= 0.1

A mobile Lighthouse run may be retained as an informational artifact/baseline. Do not make a single noisy Lighthouse score the sole gate.

### Network budget

The final production logo treatment may add image requests when viewed, but must add:

- **0 new Sports provider/API requests for metadata**;
- **0 Gemini records/tokens**;
- **0 Sports-image requests before Sports activation**.

The existing structured provider call count remains authoritative.

## Real-device acceptance

After deterministic gates pass, validate on the owner's Pixel with a cold/uncached view.

Check:

- tap-to-first-Sports-frame feels immediate;
- skeletons are barely noticed rather than becoming UI chrome;
- marks settle without text movement;
- fast scroll through Champions League does not hitch;
- back/tab navigation remains responsive while crests are still loading;
- dark mode remains coherent;
- a poor/disabled network leaves a complete text Sports page.

Do not substitute desktop Lighthouse for this acceptance.

## Cleanup contract

Issue #55 is complete only when the experiment has been reconciled into one production path.

Delete before merge:

- branch-only mark CSS injection;
- branch-only mark JavaScript injection;
- preview `MutationObserver` decoration;
- duplicate `_attach_champions_logo_preview()` ESPN requests;
- temporary live-performance workflow/probe code once durable tests cover the contract.

Keep `template/sports.css` / `template/sports.js` as the clear presentation boundary unless measured evidence justifies a different modular split.

## Explicit non-goals

- no sports SPA;
- no client-side score fetching or live polling;
- no infinite scrolling or virtualization;
- no third-party lazy-load library;
- no generic image proxy;
- no copied logo pack;
- no new analytics service;
- no Gemini work;
- no redesign of non-Sports sections;
- no performance theatre such as hiding real local text behind full-page skeletons.

## Definition of done

Sports V2 performance hardening is done when:

- Toronto data paints immediately when Sports opens;
- remote identity is progressive and non-blocking;
- below-fold crest loading is genuinely deferred;
- image geometry is stable and skeleton/fallback states are intentional;
- remote crest metadata adds no provider requests;
- service-worker caching no longer indiscriminately captures cross-origin assets;
- lab/browser performance regression gates are durable;
- a real cold Pixel run feels materially faster than the current crest preview;
- all temporary preview machinery has been removed;
- product/rendering/service-worker docs agree with the shipped implementation.

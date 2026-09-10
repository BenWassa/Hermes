# Hermes Voices V2 — Product Authority

Status: **authoritative product contract for Voices V2**.

This document locks the owner-decided Voices V2 roster, tier semantics,
morning-Opinion participation, Core release-alert product, weekly catch-up
product, and separation of product membership from source availability.

> **2026-09-10 owner correction.** Real production use showed that the first
> release-time article alert was useful. The earlier V2 decision that the
> weekly roundup should replace routine per-article Voice alerts is superseded.
> Core release alerts remain a product. Issue #26 upgrades them so the normal
> destination is a compact Hermes article summary rather than only the
> publisher link. The weekly roundup remains a separate catch-up layer.

## 1. Precedence and preserved authority

For Voices V2, this document is authoritative for:

- intellectual roster membership;
- Core / Selective / Discovery semantics;
- morning `Following` eligibility and finite-selection policy;
- routine Core release-alert eligibility;
- the weekly Core roundup;
- retirement of legacy overloaded `notify` semantics;
- separation of product membership from technical source availability.

`VOICES.md` remains authoritative for the proven identity,
authorship-evidence, source-adapter, canonical-article, dedupe/syndication,
provenance, paywall, state-safety and graceful-failure architecture except where
this document explicitly changes product semantics.

`PRODUCT.md` remains authoritative for Hermes-wide product principles.

## 2. Locked intellectual roster

Core roster size is exactly **15**:

1. Conrad Black
2. Andrew Coyne
3. Paul Wells
4. Ezra Klein
5. David Brooks
6. Francis Fukuyama
7. Fareed Zakaria
8. Adam Tooze
9. Helen Thompson
10. Jonathan Haidt
11. Steven Pinker
12. Arthur C. Brooks
13. Tyler Cowen
14. Zeynep Tufekci
15. Dan Wang

Additional locked classifications:

- **Jordan Peterson — Selective**
- **George Monbiot — Discovery**

This is an intellectual/product classification. Do **not** add, remove,
promote, demote, or disable a person because a source is easy, difficult,
expensive, blocked, stale, temporarily unreachable, or not yet implemented.

## 3. Tier semantics

### 3.1 Core

Core is the deliberate high-priority intellectual roster.

A Core Voice:

- is eligible for morning `Following` consideration when qualifying new
  writing is available;
- remains Core even when Hermes currently lacks a production-reachable source;
- is the **only** tier eligible for routine release alerts;
- is the **only** tier eligible for the weekly Core roundup.

Core membership does not mean that every discovered item must generate a push.
The article must still satisfy authorship, freshness, duplicate/syndication,
source and operational qualification rules. But product eligibility derives
from `tier == core`, not from legacy `notify`.

### 3.2 Selective

Selective is deliberately tracked but does not receive the automatic Core
guarantee.

A Selective Voice:

- may enter morning `Following` only after the stronger generic substantive
  qualification rule;
- does not create routine release-alert polling, article-summary generation or
  notification pressure;
- does not participate in the weekly Core roundup.

Selective is not a waiting room for Core and is not a source-quality
classification.

### 3.3 Discovery

Discovery is not explicitly followed.

A Discovery Voice:

- has no tier-based `Following` guarantee;
- may appear through ordinary `Today's Opinion` editorial curation;
- does not create routine release-alert polling, article-summary generation or
  notification pressure;
- does not participate in the weekly Core roundup.

## 4. Morning Opinion contract

The Opinion desk remains two separate surfaces:

1. **Following** — deterministic reader-priority handling under the tier rules.
2. **Today's Opinion** — ordinary Hermes editorial selection.

Participation:

- **Core:** qualifying new writing is considered for `Following`.
- **Selective:** may be considered only after the stronger generic substantive
  qualification rule.
- **Discovery:** ordinary Opinion only.

Gemini must not be able to silently discard a qualifying Core follow merely
because unrelated Opinion items rank higher.

The morning paper remains finite:

- do not force-fill `Following`;
- normal ceiling is **6** items;
- breadth across distinct Core Voices comes before depth from one Voice;
- use freshness and deterministic tie-breaks after breadth;
- a modest overflow to **7 or 8** is allowed only to admit additional distinct
  Core Voices;
- Selective items never create that overflow.

The existing canonical identity/dedupe and syndication rules determine whether
multiple observations represent the same article.

## 5. Core release-alert product

Routine release alerts are a retained V2 product for Core Voices.

The target path is:

```text
discover Core article
-> establish authorship
-> canonicalize + dedupe + collapse syndication
-> durably claim once
-> prepare compact Hermes article-summary page
-> send one restrained ntfy notification linking to Hermes
```

### 5.1 Alert eligibility

- `tier == core` is the product boundary.
- Selective and Discovery create no routine alert obligation.
- Source reachability remains an operational constraint and does not change
  membership.
- One intellectual article must produce at most one alert across retries,
  reruns, alternate adapters and syndicated/reprinted URLs.
- No BREAKING language, urgency framing, unread badge, queue or engagement
  mechanic.

### 5.2 Hermes summary destination

Issue #26 owns implementation of the summary surface.

For a normal successful alert, tapping the notification should open a stable
Hermes page containing:

- Voice name, publication and publication date;
- original headline;
- concise thesis/summary;
- roughly 3–5 key arguments or takeaways when source material supports them;
- a short `Why it matters` treatment when useful;
- a prominent `Read original` link to the canonical publisher URL.

The notification itself should carry writer + headline + a short takeaway, but
must remain restrained enough to function as a pointer rather than a miniature
feed.

### 5.3 Summarization boundaries

- Generate model output only after an article has qualified for a real Core
  alert. Do not run Gemini for every watcher observation or every hourly pass.
- Reuse Hermes summarization machinery where sensible, but do not rebuild the
  whole Daily for one Voice article.
- Use only legitimately accessible source text/metadata.
- Never bypass paywalls or reproduce protected full text.
- If source access is insufficient for a high-confidence full summary, degrade
  to the trustworthy material available and preserve the canonical original
  link.
- Summary/render failure must not corrupt durable claim state or create
  duplicate pushes.

## 6. Weekly Core roundup

The weekly roundup remains a separate **catch-up** product.

Its architecture stays:

```text
daily silent Core collection
-> bounded separate roundup state
-> deterministic weekly selection, max 6
-> breadth across distinct Core Voices, max 2 per Voice
-> one current /voices/ roundup
-> one restrained weekly ntfy notification
```

This product does **not** replace Core release alerts. Its job is to provide a
finite weekly view of worthwhile Core writing the reader may have missed.

Roundup collection remains Core-only, makes no Gemini calls merely to collect,
and is independent of the morning edition and release-alert claim state.
`WEEKLY_CORE_VOICES_ROUNDUP_RECONCILIATION.md` records the current reconciliation
of that design.

## 7. Product membership is independent of source availability

A Voice has separate dimensions:

1. **Product membership** — `Core`, `Selective`, or `Discovery`.
2. **Technical availability** — whether Hermes has one or more enabled,
   production-reachable sources that can establish authorship.

Consequences:

- a Core Voice with no working source remains Core;
- a blocked publisher does not demote a Voice;
- adding a better source does not promote a Voice;
- source-specific `enabled` state is operational, not intellectual;
- a provider or adapter must never become roster authority.

## 8. Retire overloaded `notify` semantics

The V1 `notify` boolean is a legacy watcher switch. It must not remain product
authority.

V2 semantics are:

- **`tier`** defines durable product membership;
- morning participation derives from tier plus the Selective qualification
  rule;
- routine release-alert eligibility derives from `tier == core`;
- weekly roundup eligibility derives from `tier == core`;
- source reachability/technical activation remains separate operational state.

Migration rule:

- while legacy watcher code still depends on `notify`, it may retain that
  temporary operational meaning;
- no V2 code may interpret `notify: true` as Core or `notify: false` as not
  Core;
- #26 should remove or clearly retire `notify` as product semantics when the
  Core alert path is migrated;
- removing legacy `notify` must not remove the release-alert product itself.

## 9. Preserved implementation boundaries

Downstream work must preserve:

1. canonical Voice identity and explicit tier migration;
2. evidence-based authorship rather than mention/name inference;
3. generic adapters, never per-person fetch functions;
4. canonical article identity, exact dedupe and syndication grouping;
5. graceful local source failure;
6. bounded request budgets and no linear per-Voice/per-source model scaling;
7. no paywall circumvention;
8. repository-backed product authority for this one-reader static product;
9. independent morning, release-alert and weekly-roundup state/write paths;
10. at-most-once notification behavior under retry and git races.

Current follow-on implementation issues:

- **#25** — make the Daily's 05:00 Toronto operating target reliable.
- **#26** — migrate retained Core release alerts to Hermes summary pages and
  tier-based eligibility.

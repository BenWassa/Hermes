# Hermes Voices V2 — Product Authority

Status: **authoritative product contract for Voices V2**.

This document locks the owner-decided Voices V2 roster, tier semantics,
morning-Opinion participation, silent Core collection, weekly screening and
notification policy, and separation of product membership from source
availability.

> **2026-09-10 final owner correction.** Production release-time alerts proved
> too interruptive when several Core writers published on the same day. The
> release-alert notification policy introduced by #26 / PR #28 is superseded.
> Hermes keeps the useful collection, identity, dedupe and rendering machinery,
> but routine per-article Voice pushes are retired. The **weekly Core digest is
> the sole proactive Voice notification product**. Issue #29 owns this
> correction.

## 1. Precedence and preserved authority

For Voices V2, this document is authoritative for:

- intellectual roster membership;
- Core / Selective / Discovery semantics;
- morning `Following` eligibility and finite-selection policy;
- silent Core collection and optional browsing;
- weekly screening and notification semantics;
- retirement of routine release-time Voice notifications;
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
- is the only tier included in the silent Core collection used by the weekly
  digest;
- is the only tier eligible for the weekly Core digest.

Core membership does **not** mean every article deserves the reader's
attention. Publication by a Core Voice establishes collection eligibility, not
roundup-worthiness and never an automatic push.

### 3.2 Selective

A Selective Voice:

- may enter morning `Following` only after the stronger generic substantive
  qualification rule;
- does not create routine Core-collection, weekly-screening or notification
  pressure;
- does not participate in the weekly Core digest.

Selective is not a waiting room for Core and is not a source-quality
classification.

### 3.3 Discovery

A Discovery Voice:

- has no tier-based `Following` guarantee;
- may appear through ordinary `Today's Opinion` editorial curation;
- does not create routine Core-collection, weekly-screening or notification
  pressure;
- does not participate in the weekly Core digest.

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
- breadth across distinct Core Voices comes before depth;
- use freshness and deterministic tie-breaks after breadth;
- a modest overflow to **7 or 8** is allowed only to admit additional distinct
  Core Voices;
- Selective items never create that overflow.

The existing canonical identity/dedupe and syndication rules determine whether
multiple observations represent the same article.

## 5. Silent Core collection and optional browsing

During the week Hermes collects qualifying Core writing silently.

The collection path is:

```text
discover Core article
-> establish authorship
-> canonicalize + dedupe + collapse syndication
-> add/update bounded Core roundup state
-> expose recent writing on a quiet finite Hermes shelf
```

Rules:

- no per-article ntfy notification;
- no per-article Gemini summary merely because a piece appeared;
- no unread counters, badges, streaks or backlog pressure;
- the reader may browse recent Core writing or ignore it;
- the shelf remains finite and bounded;
- publisher access controls are never bypassed.

The retired #26 stable article-summary machinery may remain in the repository
for historical links or future reuse, but it is not a production notification
path.

## 6. Weekly Core digest — sole Voice notification

The weekly Core digest is the **only proactive Voice notification product**.

Target architecture:

```text
daily silent Core collection
-> bounded separate roundup state
-> one weekly relevance/substance screen
-> deliberately small shortlist, maximum 3
-> one compact weekly summary at /voices/
-> one restrained weekly ntfy notification
```

### 6.1 Screening contract

A Core byline alone is insufficient. The screen should prefer:

- substantive or explanatory work likely to add a useful model or argument;
- material relevance to Hermes's editorial interests: world affairs,
  economics/markets, technology/AI, institutions, politics and consequential
  social/cultural questions;
- novelty versus the other candidates that week;
- useful breadth across writers where quality is comparable;
- pieces the morning Daily did not already surface, unless an already-surfaced
  piece is clearly exceptional.

The screen should de-prioritize routine publication churn, minor reactions,
promotional/administrative posts, and redundant pieces on the same apparent
subject.

**Fewer is better when the week is weak.** The digest must never fill a quota
merely because material exists.

### 6.2 Model boundary

Prefer one bounded weekly screening/synthesis model call rather than one call
per article.

- Daily collection has no Gemini capability.
- Manual release-watch inspection has no Gemini or ntfy capability.
- The weekly job alone may receive Gemini and ntfy credentials.
- Model screening uses only legitimately available metadata/source material.
- The model must not invent article arguments when only metadata is available.
- If the weekly model call fails or is unavailable, degrade to a conservative
  deterministic shortlist of at most 3, favoring breadth and work not already
  surfaced in the Daily.

### 6.3 Notification contract

For a non-empty trusted weekly period:

- claim/publish the weekly period durably before notification;
- send at most **one** Voice notification for that period;
- notification is a restrained pointer to `/voices/`;
- retry/race behavior must never create duplicate Voice notifications.

An empty, suppressed or already-claimed period sends no Voice notification.
The morning Daily push is a separate product and is unaffected.

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

## 8. Retire overloaded `notify` and release-alert semantics

The V1 `notify` boolean is legacy implementation baggage and must not be product
authority.

V2 semantics are:

- `tier` defines durable product membership;
- morning participation derives from tier plus the Selective qualification
  rule;
- silent weekly-collection eligibility derives from `tier == core`;
- weekly-digest eligibility derives from `tier == core`;
- **no tier has routine per-article Voice notification semantics**;
- source reachability/technical activation remains separate operational state.

Any remaining release-watcher code may be retained only as read-only/manual
inspection or dead-compatible machinery. Shipped workflows must not give it an
ntfy topic or model secret.

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
9. independent morning and weekly-roundup state/write paths;
10. at-most-once weekly notification behavior under retry and git races.

Current follow-on implementation issue:

- **#29** — weekly-only Voice notification, relevance screening and quiet recent
  Core-writing shelf. This supersedes only the release-alert notification policy
  introduced by #26/PR #28.

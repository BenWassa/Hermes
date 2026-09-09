# Hermes Voices V2 — Product Authority

Status: **authoritative product contract for Voices V2 implementation**.

This document locks the owner-decided Voices V2 roster, tier semantics, morning-Opinion participation, future Voice notification scope, and V1 → V2 migration boundaries. It is intentionally an authority change only: it does not change current production Voice behavior, source configuration, watcher behavior, schedules, or rendering.

## 1. Precedence and preserved authority

For Voices V2, this document is authoritative for:

- intellectual roster membership;
- Core / Selective / Discovery semantics;
- morning `Following` eligibility and finite-selection policy;
- the future weekly Voice notification product;
- the meaning and retirement path of legacy `notify`;
- separation of product membership from technical source availability;
- V1 → V2 migration boundaries.

`VOICES.md` remains authoritative for the proven V1 identity, authorship-evidence, source-adapter, canonical-article, dedupe/syndication, provenance, paywall, and graceful-failure architecture except where this document explicitly changes product semantics.

`PRODUCT.md` remains authoritative for Hermes-wide product principles. If a global product principle conflicts with an implementation detail here, the global principle wins unless this document explicitly narrows it.

Do not infer V2 product semantics from the current contents of `data/voices.json`; that file remains V1 production configuration until a later implementation change deliberately migrates it.

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

This is an intellectual/product classification. Do **not** add, remove, promote, demote, or disable a person because a source is easy, difficult, expensive, blocked, stale, temporarily unreachable, or not yet implemented.

## 3. Tier semantics

### 3.1 Core

Core is the deliberate high-priority intellectual roster.

A Core Voice:

- is actively eligible for morning `Following` consideration when qualifying new writing is available;
- remains Core even when Hermes currently lacks a production-reachable source;
- may therefore be technically dormant without losing Core membership;
- is the **only** tier eligible for the future weekly Voice roundup / Voice notification product.

Core membership does not mean “send a notification for every article.” It is not a synonym for source reachability or watcher eligibility.

### 3.2 Selective

Selective is deliberately tracked but does not receive the automatic Core guarantee.

A Selective Voice:

- may enter morning `Following` only after a stronger, generic, substantive qualification rule is satisfied;
- should be filtered deterministically first;
- may use Gemini for qualification only if deterministic qualification is proven inadequate, and must not create linear per-Voice/per-source LLM work;
- is not eligible for the weekly Voice notification product.

Selective is not a waiting room for Core and is not a source-quality classification.

### 3.3 Discovery

Discovery is not explicitly followed.

A Discovery Voice:

- does not enter the deterministic `Following` set by virtue of tier membership;
- may still appear through ordinary `Today's Opinion` editorial curation when the article is independently selected;
- is not eligible for the weekly Voice notification product.

Discovery therefore preserves ordinary editorial serendipity without turning every interesting writer into a followed Voice.

## 4. Morning Opinion contract

The Opinion desk remains two separate surfaces:

1. **Following** — deterministic reader-priority handling under the tier rules above.
2. **Today's Opinion** — ordinary Hermes editorial selection.

### 4.1 Participation

- **Core:** qualifying new writing is considered for `Following`.
- **Selective:** writing may be considered for `Following` only after the stronger generic substantive qualification rule.
- **Discovery:** no tier-based `Following` eligibility; ordinary Opinion only.

Gemini must not be able to silently discard a qualifying Core follow merely because unrelated Opinion items rank higher.

### 4.2 Finite selection

The morning paper remains finite.

- Do not force-fill `Following`.
- Normal ceiling: **6** items.
- Breadth across distinct Core Voices comes before depth from one Voice.
- Use freshness and deterministic tie-breaks after breadth.
- Do not use ideology, popularity, engagement, or fabricated “quality scores” as tie-breaks.
- A modest overflow to **7 or 8** is allowed only when needed to admit additional distinct Core Voices that would otherwise be excluded by the normal six-item ceiling.
- Selective items never create the 7–8 overflow; they must fit within the normal finite treatment after satisfying their stronger qualification rule.

The existing canonical identity/dedupe and syndication rules continue to determine whether multiple observations represent the same article.

## 5. Voice notification product

Routine per-article Voice alerts are **not** the V2 product.

The target V2 notification product is one finite **weekly Core Voices catch-up / roundup**.

Locked scope:

- **Core only** participates.
- Selective and Discovery create no weekly polling or notification obligation.
- No routine instant/ad-hoc notification for every newly published Voice article.
- Selection should be deterministic-first.
- Do not add Gemini calls merely because the roster grows; use model work only if later evidence demonstrates a specific need.

The design/research work for the weekly roundup may define implementation details, but it must consume this product authority rather than inventing roster or eligibility semantics.

## 6. Product membership is independent of source availability

A Voice has at least two conceptually separate dimensions:

1. **Product membership** — `Core`, `Selective`, or `Discovery`.
2. **Technical availability** — whether Hermes currently has one or more enabled, production-reachable sources that can establish authorship under the existing evidence rules.

They must not be collapsed.

Consequences:

- a Core Voice with no working source remains Core;
- a source audit may classify a Core Voice as dormant/unavailable without changing tier;
- adding a better source does not promote a Voice;
- a blocked publisher does not demote a Voice;
- source-specific `enabled` state remains an operational fact, not an intellectual judgment;
- a provider or adapter must never become the authority for roster membership.

## 7. Replace overloaded `notify` semantics

The current V1 `notify` boolean is a legacy **per-article watcher switch**. It must not be reused as V2 product authority.

V2 semantics are separated as follows:

- **`tier`** is the durable product-membership concept: `core`, `selective`, or `discovery`.
- Morning participation is derived from `tier` plus the generic qualification policy in §4; it is not represented by `notify`.
- Weekly Voice-roundup eligibility is derived from `tier == core`; it is not represented by `notify`.
- Source reachability/technical activation remains represented by Voice/source operational configuration; it is not represented by `tier`.

Migration rule for `notify`:

- while the V1 release-alert watcher still exists, `notify` keeps only its existing V1 operational meaning;
- no V2 code may interpret `notify: true` as “Core” or `notify: false` as “not Core”;
- when the weekly roundup replaces routine release alerts, retire the legacy per-Voice `notify` field rather than assigning it a second meaning;
- any later workflow-level enable/disable switch for the roundup is operational configuration and must not alter Core membership.

The same separation applies to top-level V1 `enabled`: during migration it may continue to gate technical discovery, but it must not define whether someone belongs to Core, Selective, or Discovery.

## 8. Safe V1 → V2 migration boundary

This authority change deliberately does **not** migrate production behavior.

A later implementation PR may add the V2 tier schema and roster, but it must preserve these boundaries:

1. **Preserve proven architecture.** Keep the canonical Voice identity, authorship evidence, generic adapter interface, canonical article identity, exact dedupe, syndication grouping, provenance, source-failure isolation, and paywall boundaries established by #9–#13 and #17 / PRs #14–#19.
2. **Do not infer tiers from V1 flags.** Migrate the locked classifications explicitly.
3. **Preserve current V1 operation until cutover.** Existing `enabled` / `notify` behavior may continue unchanged until the specific downstream feature that replaces it is ready.
4. **Allow dormant membership.** The V2 registry/schema must be able to represent a Core Voice even when zero production sources are currently usable.
5. **Source expansion is separate work.** Adding the remaining Core sources must not be bundled into the product-authority change merely to make the roster look operationally complete.
6. **Weekly roundup is separate work.** Do not change watcher cadence, state, ntfy delivery, or schedule in the authority migration.
7. **Morning-policy implementation is separate from authority.** Do not silently change the shipped V1 `Following` behavior before the tier-aware selection code and its deterministic tests are ready.
8. **No per-person hacks.** New roster members must use generic adapters and the existing evidence model.
9. **No linear LLM scaling.** Roster growth must not create one model call per Voice, source, or article.
10. **Repository-backed authority remains deliberate.** This is still a one-reader static product; do not add a semantically false local-only Follow control.

For the five Voices already present in the V1 production registry, the explicit V2 classifications are:

- Jonathan Haidt — Core
- Conrad Black — Core
- David Brooks — Core
- Jordan Peterson — Selective
- George Monbiot — Discovery

That mapping is deliberate and must not be derived from their current `enabled`, `notify`, or source state.

## 9. Non-goals of this authority change

Do not implement here:

- weekly roundup collection, state, rendering, schedules, or ntfy delivery;
- new Core Voice source adapters or source configuration;
- source-audit conclusions as production config;
- per-person fetching logic;
- changes to current morning `Following` output;
- changes to the release-time watcher;
- a new backend or preference store;
- a redesign of the Opinion UI.

The purpose of this document is to make downstream implementation choices mechanically checkable without reopening product decisions.
# Weekly Core Voices Roundup — V2 authority reconciliation

Status: **current reconciliation note for the shipped weekly Core roundup.**

`WEEKLY_CORE_VOICES_ROUNDUP.md` began as the Wave 1C design for replacing
routine per-article Voice alerts. That replacement decision is now superseded
by owner feedback from **2026-09-10** and the current authority in
`PRODUCT.md` / `VOICES_V2.md`.

The weekly architecture itself remains valid and implemented. What changes is
its product role: **the weekly roundup is a finite catch-up layer, not a
replacement for useful Core release alerts.**

Issue #26 owns the retained release-alert path and Hermes article summaries.

## Authority consumed

`VOICES_V2.md` is the product authority. The roundup implementation consumes
its explicit `tier` semantics directly.

The locked Core roster is exactly:

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

Jordan Peterson is Selective. George Monbiot is Discovery. Neither tier
participates in the weekly roundup product or creates roundup-specific polling
pressure.

## Current product shape

Hermes now has three complementary Voice surfaces:

```text
Morning Following
    finite Voice material inside The Daily

Core release alerts
    new qualifying Core article
    -> compact Hermes summary
    -> restrained ntfy notification

Weekly Core roundup
    finite catch-up across the Core roster
```

The three products share identity, authorship, canonicalization, dedupe,
syndication and source machinery where appropriate, but they remain operationally
independent. One failing path must not block the others.

## Corrections to the original architecture note

### 1. Core membership, not `notify`, is the boundary

Collection and weekly eligibility derive from authoritative `tier == core`
membership. Legacy V1 `notify` is not a Core proxy.

Operational source availability remains separate. A Core Voice remains Core
when technically dormant, blocked or source-disabled. The collector may only
issue requests through production-enabled/reachable generic sources, but
source state does not define membership.

For weekly selection, the rule is:

> At selection time, at least one attributed `voice_id` resolves to a Voice
> whose authoritative V2 tier is `core`. The article must come from trusted
> roundup observations established through the existing authorship and source
> contracts. Current source reachability does not retroactively change Core
> membership.

### 2. Selective and Discovery create zero roundup pressure

Before source planning, filter roundup participation to Core membership.
Selective and Discovery must not add requests, retention obligations, selection
slots or notifications merely because they exist in the registry.

A shared provider request legitimately needed for one or more Core Voices may
return other authors. Only Core-attributed items are retained in roundup state.

### 3. Weekly ntfy remains one finite catch-up notification

The weekly notification remains one message per non-empty weekly period and
links to the current `/voices/` roundup.

Example shape:

```json
{
  "title": "Voices this week",
  "message": "5 pieces from Jonathan Haidt, Conrad Black, David Brooks +2.",
  "priority": 3,
  "tags": ["memo"],
  "click": "<PAGES_URL>/voices/"
}
```

Notification composition derives names only from the selected Core roundup set.

The existence of release-time Core alerts does not turn the weekly message into
an unread digest or suppress it automatically. The roundup remains a separate
editorial catch-up product.

### 4. Morning Opinion remains independent

The roundup collector must not become part of the morning build and the morning
build must not become a writer of roundup operational state.

Reading the already-committed morning edition to mark
`first_morning_surfaced_at` remains an optional deterministic ranking signal
only. It never gates collection or changes morning publication behavior.

### 5. Release-alert state and roundup state remain separate

Keep separate bounded state:

- `data/voice_watch_state.json` — release-alert claim/idempotency state while
  that implementation remains in service;
- `data/voice_roundup_state.json` — weekly accumulator and period state.

Do not import or reinterpret release-alert claims as weekly candidates. Likewise,
weekly state must not suppress a legitimate Core release alert merely because
the article has been accumulated for Sunday.

When #26 migrates release alerts from legacy `notify` semantics to
`tier == core`, it should preserve at-most-once claim safety without coupling
that state to the weekly accumulator.

### 6. Preferred weekly architecture remains unchanged

The weekly design remains:

```text
daily silent Core collection
-> bounded separate roundup state
-> deterministic weekly selection, max 6
-> breadth across distinct Core Voices, max 2 per Voice
-> one overwrite-only current /voices/ roundup
-> one restrained weekly ntfy notification
```

Retain the existing identity, authorship-evidence, canonical article identity,
exact dedupe, syndication/reprint grouping, generic adapters, provider
batching/budgets, graceful source failure and git compare-and-swap machinery.

The daily collector still makes **zero Gemini calls**. The new model work in
#26 belongs only to articles that have already qualified for a real Core
release alert; it does not scale with weekly collection or every watcher
observation.

## Closeout decision

The shipped weekly Core roundup remains valid. Only its earlier role as a
replacement for routine release alerts is retired.

Current authority is therefore:

- Morning Following remains finite and independent.
- Core release alerts remain useful and are upgraded by #26 to open Hermes
  summaries.
- Weekly Core roundup remains the bounded catch-up product.
- `tier == core` is the product authority for both routine Core alerts and the
  weekly roundup.
- Selective and Discovery create no routine alert or weekly-roundup pressure.
- Legacy `notify` may survive temporarily only as implementation baggage and
  must not define V2 product membership.

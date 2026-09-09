# Weekly Core Voices Roundup — V2 authority reconciliation

Status: **design closeout for PR #20.** This note is authoritative where it narrows or corrects `WEEKLY_CORE_VOICES_ROUNDUP.md` after the merge of `VOICES_V2.md` / PR #21. It changes no production behaviour.

## Authority consumed

`VOICES_V2.md` is now the product authority. The roundup implementation must consume its explicit `tier` semantics directly.

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

Jordan Peterson is Selective. George Monbiot is Discovery. Neither tier participates in the weekly roundup product or creates roundup-specific polling pressure.

## Corrections to the architecture note

### 1. Core membership, not `notify`, is the roundup boundary

Collection and weekly eligibility are derived from authoritative `tier == core` membership. Legacy V1 `notify` is only the release-alert switch until that watcher is retired and must never be interpreted as a Core proxy.

Operational source availability remains separate. A Core Voice remains Core when technically dormant, blocked or source-disabled. The collector may only issue requests through production-enabled/reachable generic sources, but source state does not define membership.

For selection, replace the wording in §7.1 that requires an "enabled Core Voice" with this rule:

> At selection time, at least one attributed `voice_id` resolves to a Voice whose authoritative V2 tier is `core`. The article must come from trusted roundup observations established through the existing authorship and source contracts. Current source reachability or operational enablement does not retroactively change Core membership.

This preserves the product/technical separation in `VOICES_V2.md` while preventing dormant Core entries from creating impossible network obligations.

### 2. Selective and Discovery create zero roundup pressure

Before source planning, filter roundup participation to Core membership. Selective and Discovery Voices must not add requests, retention obligations, selection slots or notifications merely because they exist in the registry.

A shared provider request legitimately needed for one or more Core Voices may return other authors. Only Core-attributed items are retained in roundup state.

### 3. Correct the ntfy example

The example in §9 that names George Monbiot is non-authoritative because he is now locked as Discovery. The intended example is Core-only, for example:

```json
{
  "title": "Voices this week",
  "message": "5 pieces from Jonathan Haidt, Conrad Black, David Brooks +2.",
  "priority": 3,
  "tags": ["memo"],
  "click": "<PAGES_URL>/voices/"
}
```

Notification composition must derive names only from the selected Core roundup set.

### 4. Morning Opinion remains independent

The roundup collector must not become part of the morning build and the morning build must not become a writer of roundup operational state.

Reading the already-committed morning edition to mark `first_morning_surfaced_at` remains an optional deterministic ranking signal only. It does not change morning Following eligibility, curation, publishing or notification behaviour and must never be a correctness gate for collection.

The V2 morning policy in `VOICES_V2.md` is implemented separately: Core is automatically eligible for Following consideration, Selective requires its stronger generic qualification rule, and Discovery has no tier-based Following eligibility. None of those morning semantics expands weekly roundup membership beyond Core.

### 5. V1 state cannot seed a V2 backlog

Keep the new active path proposed by the architecture note:

- `data/voice_watch_state.json` remains the legacy V1 release-alert claim log and becomes inert at cutover;
- `data/voice_roundup_state.json` is the bounded V2 accumulator.

Do not import, reinterpret or reconstruct candidates from V1 alert state. The first trusted V2 collector establishes `collecting_since`; missing/corrupt V2 state establishes a fresh silent baseline and suppresses the incomplete current period. This prevents V1 alert history from becoming a false V2 backlog.

### 6. Preferred implementation architecture remains unchanged

The reconciled design remains:

```text
daily silent Core collection
-> bounded separate roundup state
-> deterministic weekly selection, max 6
-> breadth across distinct Core Voices, max 2 per Voice
-> one overwrite-only current /voices/ roundup
-> one restrained weekly ntfy notification
```

Retain the V1 identity, authorship-evidence, canonical article identity, exact dedupe, syndication/reprint grouping, generic adapters, provider batching/budgets, graceful source failure and git compare-and-swap machinery.

Initial incremental Gemini usage remains exactly zero. No per-Voice, per-source or per-article Gemini scaling is introduced.

## Closeout decision

With the corrections above, the architecture in `WEEKLY_CORE_VOICES_ROUNDUP.md` is reconciled with the merged Core / Selective / Discovery authority and is ready to serve as the design basis for the later implementation issue. PR #20 remains design/research only; it does not change current watcher cadence, source configuration, morning Opinion behaviour, ntfy delivery or production state.
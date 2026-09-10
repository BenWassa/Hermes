# Weekly Core Voices Roundup — V2 authority reconciliation

Status: **current reconciliation note for the shipped weekly Core digest.**

`WEEKLY_CORE_VOICES_ROUNDUP.md` began as the Wave 1C design for replacing
routine per-article Voice alerts. A later 2026-09-10 correction briefly restored
Core release alerts in #26 / PR #28. Production use the same day showed that
policy created too much interruption when several Core writers published.

The final owner decision is now authoritative in `PRODUCT.md` and
`VOICES_V2.md`:

> **The weekly Core digest is the sole proactive Voice notification.**

Issue #29 owns this correction.

## Authority consumed

`VOICES_V2.md` remains product authority. The locked Core roster is exactly:

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

Jordan Peterson is Selective. George Monbiot is Discovery. Neither participates
in the Core weekly product or creates Core-collection/notification pressure.

## Current product shape

Hermes has three Voice surfaces:

```text
Morning Following
    finite Voice material inside The Daily

Recent Core writing
    silent bounded collection
    -> quiet /voices/recent/ shelf
    -> no notification, no unread obligation

Weekly Core digest
    screen the week's Core writing for attention-worthiness
    -> deliberately small shortlist, max 3
    -> one compact /voices/ summary
    -> one restrained weekly ntfy notification
```

The morning Daily notification is a separate Daily product and is unaffected.

## Reconciliation rules

### 1. Core membership, not `notify`, is the collection boundary

Silent Core collection and weekly eligibility derive from authoritative
`tier == core` membership. Legacy V1 `notify` is not a Core proxy.

Operational source availability remains separate. A Core Voice remains Core
when technically dormant, blocked or source-disabled. The collector may issue
requests only through production-enabled/reachable generic sources, but source
state never defines intellectual membership.

### 2. Publication does not equal interruption

A qualifying Core byline is enough to collect an article. It is **not** enough
to notify the reader and is not enough to guarantee a weekly slot.

The weekly screen should prefer material likely to add substantive explanatory
value, relevance, novelty and non-redundant breadth. Routine publication churn,
minor reactions and repetitive pieces remain browseable but should not occupy
the weekly shortlist.

### 3. Weekly selection is deliberately smaller

The previous deterministic `max 6 / max 2 per Voice` selection was too generous
for the reader's available attention.

Current target:

- maximum **3** selected pieces;
- fewer is better when the week is weak;
- useful breadth across writers when quality is comparable;
- de-prioritize work already surfaced in the morning Daily unless exceptional;
- one bounded weekly relevance-screening/synthesis model call;
- deterministic conservative max-3 fallback if that call fails.

The daily collector itself remains model-free.

### 4. Exactly one proactive Voice notification path

Only the weekly publisher receives ntfy capability.

- scheduled release-time/per-article Voice notifications are retired;
- manual release-watch inspection is read-only/dry-run and receives no Gemini
  or ntfy secret;
- daily collection receives neither Gemini nor ntfy capability;
- one non-empty trusted weekly period may send at most one Voice notification;
- empty, suppressed, failed-to-publish or already-claimed periods send none.

The weekly notification links to `/voices/` and acts only as a pointer to the
single weekly brief.

### 5. Recent writing remains available without pressure

The Core accumulator remains bounded and continues using the proven identity,
authorship, canonicalization, exact dedupe and syndication machinery.

A finite `/voices/recent/` surface exposes recent Core writing for optional
browsing. It must not add unread counters, badges, recommendations, streaks,
backlog framing or separate notifications.

### 6. State and failure boundaries remain safe

Retain:

- `data/voice_roundup_state.json` as the weekly accumulator/period authority;
- claim-before-notify ordering for the weekly period;
- bounded git compare-and-swap/retry behavior;
- graceful local source failure;
- no paywall circumvention;
- no per-person fetch/summarization branches.

The old `data/voice_watch_state.json` and #26 stable article pages may remain for
historical compatibility, but they no longer drive a scheduled notification
product.

## Closeout decision

The intended V2 product is now simple:

```text
Core publication
-> collect silently
-> make it optionally browseable
-> once a week screen hard
-> summarize the best few once
-> notify once
```

This note supersedes the earlier reconciliation language that described weekly
catch-up as complementary to release-time Core alerts.

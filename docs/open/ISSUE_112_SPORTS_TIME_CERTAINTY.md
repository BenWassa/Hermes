---
status: open
issue: 112
lane: sports-data-integrity
updated: 2026-11-10
---

# #112 — Fixture time certainty: MLB, NHL and NBA

Issue: https://github.com/BenWassa/Hermes/issues/112
Sentinel: HQA-011, reported Nov 2–4 (one repeated Feb 19 2027 fixture).

## Before evidence

The Blue Jays offseason next-game card showed Toronto 03:33 on Feb 19 2027 against Pittsburgh. The 2027 MLB schedule recorded the first pitch as TBD (original Sentinel W45, Nov 2 D-05; MLB public schedule). Main's MLB adapter parsed gameDate and serialized it as a clock regardless of provider status.startTimeTBD. Front-end unconditionally formatted every non-null date. A placeholder timestamp was therefore treated as confirmed. This is the identified code mechanism; the precise historical raw provider response for Nov 2 was not retained as a complete provider snapshot.

## Minimal data contract

- Extend provider-neutral GameSummary with time_confirmed (defaults true for backwards compatibility) and optional scheduled_date for provider-official calendar date.
- MLB status.startTimeTBD (and defensively other explicit TBD markers) marks scheduled first-pitch time unconfirmed. Use officialDate to display calendar date independently of dummy gameDate UTC hour. Do not infer uncertainty from 08:33Z or assume all odd/midnight hours invalid.
- NHL/ESPN adapters propagate only explicit TBD metadata, without inferring status from unusual hours or changing game/status identity.
- Team cards render the confirmed calendar date plus "Time TBD" when unknown; confirmed clocks still format in America/Toronto with DST. Postponed/cancelled statuses remain distinct, as do final scores.
- No Gemini involvement, new API calls, changed sports lookback, source/provider replacement, standings, ordering or UI redesign.

## Tests and release

- [x] Frozen public-shape Feb 19 Pirates–Blue Jays with startTimeTBD true: serialized time_confirmed false, scheduled_date 2027-02-19.
- [x] Explicit status/boolean/text variants, dummy midnight with flag, confirmed 13:05 EST / 19:05 EDT, ambiguous midnight without flag, distinct postponement/cancellation.
- [x] NHL/ESPN explicit unknown-time flag fixtures; existing adapters remain compatible.
- [x] Rendered Playwright at 390px verifies "Time TBD" with no 3:33 and confirmed time visibility.
- [ ] Focused PR full CI success and source/review assessment.
- [ ] Future real Daily editions with actual fixture/flag and later confirmed first pitch; assess source and Pages against exact published artifact.

Boundaries: #97 Raptors record consistency is implemented separately; #67 owns sports major-event recall/horizon. Keep HQA-011 open until operationally verified. Do not merge without owner approval.

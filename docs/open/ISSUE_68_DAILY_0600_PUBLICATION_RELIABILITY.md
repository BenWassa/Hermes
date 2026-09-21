# Issue #68 — Daily ~06:00 publication reliability

Status: **OPEN**  
GitHub: https://github.com/BenWassa/Hermes/issues/68  
Lifecycle: keep this spec in `docs/open/` until merged behavior is verified in production.

## Problem

#64 fixed the stale-success failure mode by allowing a delayed scheduled event to
recover the current Toronto day's missing edition. Production still does not meet
the morning product expectation.

Observed evidence:

- September 20 rendered at `2026-09-20T13:37:27Z`, about 09:37 Toronto;
- September 21 was still missing after 08:00 Toronto;
- prior incidents showed scheduled Daily delivery roughly 3.5–4.5 hours late.

The problem is now **punctuality**, not eventual recovery.

## Product contract

- The Daily should normally be available by approximately **06:00 America/Toronto**.
- Automatic publication must not occur before **05:00 Toronto**.
- Toronto-calendar edition identity remains authoritative.
- At most one edition and one morning notification may exist per Toronto day.
- No provider or Gemini work may occur for a prompt pre-05 hedge or after today's
  edition already exists.

## Implementation

Use a bounded pre-05 schedule hedge:

```yaml
- cron: "17,47 5-12 * * *"
```

The existing runtime gate remains unchanged.

A prompt early slot exits before expensive work. If GitHub delivers that same
nominal slot several hours late, it may arrive at or after 05:00 and publish the
missing current-day edition. The ordinary 05:17+ slots remain available when
GitHub scheduling is punctual.

This deliberately converts the measured scheduler latency into additional lead
time without introducing a second scheduler, service, model call, or publication
path.

## Verification

Tests must prove:

- the exact bounded hedge cadence;
- representative EDT and EST mappings include 05:xx useful slots;
- both regimes include nominal slots around 00:xx–01:xx local;
- the pre-05 runtime gate remains authoritative;
- existing edition, notification, concurrency, and retry safety remains intact.

Run the full repository gate before merge.

## Escalation rule

GitHub documents that scheduled events can be delayed or dropped, so this remains
a best-effort GitHub-only design rather than a strict clock guarantee.

If real production cycles still miss approximately 06:00 after this hedge, do
not continue widening cron. The next issue should introduce one independent
external scheduler that invokes the existing idempotent build path.

## Acceptance

1. No automatic publication before 05:00 Toronto.
2. Normal publication is operationally targeted for completion by about 06:00.
3. The observed 3.5–4.5 hour GitHub delay has corresponding pre-05 lead-time hedges.
4. Prompt hedges consume no provider/Gemini work.
5. Existing one-edition/one-notification guarantees remain.
6. CI is green.
7. Production timing is checked on the next real scheduled cycles.

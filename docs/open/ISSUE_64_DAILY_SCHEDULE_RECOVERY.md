# Issue #64 — Daily schedule recovery

Status: **OPEN**  
GitHub: https://github.com/BenWassa/Hermes/issues/64  
Lifecycle: keep this spec in `docs/open/` while active; move it to `docs/closed/` when #64 is completed and verified on merged `main`.

## Problem

Hermes has a green-workflow / stale-product failure mode.

The last published Daily is September 14, 2026. The September 15 and September 16 scheduled Daily runs eventually started at approximately 10:20 and 10:12 America/Toronto respectively, both after the current scheduled recovery window. They therefore exited successfully before any build work and left the production Daily stale.

The current workflow uses:

```yaml
schedule:
  - cron: "17,47 9-12 * * *"
```

and then rejects scheduled attempts outside Toronto 05:00–07:59.

The UTC cadence is deliberately broad enough to cover EDT and EST. The failure is not the cadence itself; it is treating **actual delayed job start time** as a reason to discard a still-needed scheduled recovery attempt.

## Existing authority to preserve

This is a follow-on to #25, not a redesign of it.

Preserve:

- 05:00 America/Toronto as the nominal publication target;
- normal publication by approximately 06:00 local time as the desired operating state;
- multiple bounded scheduled opportunities rather than an all-day polling loop;
- Toronto-calendar edition identity;
- the edition-existence check before Python, providers, or Gemini;
- at most one Daily edition per Toronto calendar day;
- at most one Daily notification per edition;
- current git retry/rebase behaviour;
- independent Voice workflows and state;
- manual dispatch;
- current provider and Gemini budgets.

## Root cause

`.github/workflows/build.yml` currently makes two separate decisions in one gate:

1. whether today's Toronto-calendar edition already exists;
2. whether the workflow happened to start inside an allowed wall-clock window.

The first decision is a durable product/idempotency condition. The second was intended as a DST/recovery filter but assumes GitHub schedule delivery is reasonably punctual.

Production has disproved that assumption. GitHub can delay all nominal morning invocations until after the local upper bound. Because the job exits zero, Actions reports success even though Hermes did not publish.

## Locked product outcome

A scheduled Daily event that starts late should still recover **the currently missing Toronto-calendar Daily**, provided the current Toronto time has reached the 05:00 publication daypart and no edition for that date exists.

The product authority should therefore be:

```text
Toronto date + edition existence + publication daypart
```

not:

```text
actual GitHub start time happened to fall inside 05:00–07:59
```

Late recovery is degraded operation, not a new nominal schedule.

## Recommended implementation

### 1. Keep edition existence as the first and strongest gate

Continue deriving:

```bash
TODAY="$(TZ=America/Toronto date +%Y-%m-%d)"
```

and checking for the exact durable commit identity:

```text
chore(edition): publish YYYY-MM-DD edition
```

If today's edition exists, every trigger must no-op before setup, provider fetching, Gemini, build, commit, or notification work.

Do not replace this with HTML parsing, workflow status, or timestamp heuristics.

### 2. Remove the scheduled upper-hour veto

For `github.event_name == schedule`:

- keep a **minimum** Toronto hour of 05:00;
- remove the `LOCAL_HOUR > 7` rejection;
- once 05:00 has passed, a delayed scheduled event may recover today's missing edition at whatever time GitHub finally starts it.

This preserves the product day boundary while allowing GitHub delay to self-heal.

The intended rule is approximately:

```text
schedule + local hour < 05:00 -> no-op
schedule + local hour >= 05:00 + today's edition absent -> build
schedule + today's edition present -> no-op
```

Do not add new all-day cron slots. The existing bounded cron set remains the number of recovery opportunities; only their delayed execution is accepted.

### 3. Keep push recovery policy separate

Do not automatically broaden meaningful `main` push recovery beyond its current 05:00–11:59 policy unless implementation evidence shows it is required.

Pushes are incidental recovery. Scheduled events are the product's intentional publication mechanism and should own delayed-schedule recovery.

Manual `workflow_dispatch` should continue to bypass the time-window restrictions while still obeying edition idempotency.

### 4. Make run outcome explicit

A workflow that exits zero because it deliberately did nothing must not be easy to confuse with a successful publication.

Add explicit gate/run outputs or a final summary that records at minimum:

- Toronto date;
- trigger type;
- Toronto start hour/time;
- whether today's edition existed at gate time;
- outcome: `published`, `already-published-noop`, `pre-05-scheduled-noop`, `push-window-noop`, or build failure as applicable.

Use `$GITHUB_STEP_SUMMARY` and/or explicit outputs rather than a new external monitoring service.

The workflow conclusion may remain `success` for legitimate no-ops, but the run UI must make the no-op reason obvious.

### 5. Add a stale-edition contract check

Add deterministic workflow/test coverage that prevents reintroducing a silent stale-success contract.

At minimum, tests should assert that:

- scheduled recovery is **not** capped at 07:59;
- scheduled attempts before 05:00 remain no-ops;
- today's existing edition still short-circuits all expensive work;
- the workflow exposes an explicit no-op/publication outcome.

If a lightweight post-run stale assertion can be expressed without introducing another scheduler or notification channel, prefer it. Do not create a separate monitoring subsystem in #64.

## Date-boundary semantics

The implementation should use **current America/Toronto calendar date** as the edition authority.

A heavily delayed cron event is not required to preserve the nominal date of the cron slot. Its purpose is to ensure that the current Toronto day has one Daily.

Therefore:

- before 05:00 Toronto, scheduled events do not create that day's edition;
- at or after 05:00 Toronto, any delivered scheduled event may recover the current day's missing edition;
- if the current day's edition already exists, it no-ops;
- a delayed event must never backfill yesterday under today's runtime or create two editions for one Toronto date.

This avoids relying on unavailable/fragile inference about which original cron occurrence a delayed GitHub run represented.

## Files expected to change

Primary:

- `.github/workflows/build.yml`
- `tests/test_workflows.py`

Documentation only if existing text becomes inaccurate:

- `BUILD_INSTRUCTIONS.md`
- `README.md`
- `PRODUCT.md`

Do not touch Daily editorial selection, provider adapters, Gemini prompts, sports, Voices, or rendered design unless a directly failing contract requires it.

## Test matrix

### Workflow contract

- configured UTC cron cadence remains bounded and unchanged unless evidence justifies a smaller equivalent set;
- no timezone-aware GitHub schedule dependency is reintroduced without new production evidence;
- schedule trigger remains present;
- manual dispatch remains present;
- generated output/state paths remain ignored for push-trigger recursion safety.

### Gate behaviour

- 04:xx Toronto + schedule + no edition -> no-op;
- 05:xx Toronto + schedule + no edition -> build;
- 07:xx Toronto + schedule + no edition -> build;
- 10:xx Toronto + schedule + no edition -> build;
- late-day Toronto + schedule + no edition -> build current day's edition;
- any time + schedule + edition exists -> no-op before provider/Gemini work;
- push outside its permitted recovery window -> no-op;
- workflow dispatch + missing edition -> build;
- workflow dispatch + existing edition -> no-op.

### Idempotency / concurrency

- exact edition commit identity remains authoritative;
- build concurrency remains non-cancelling;
- two delayed scheduled jobs cannot result in two committed editions after git retry/rebase reconciliation;
- generated edition commits do not recursively trigger another meaningful build;
- notification freshness gate still identifies only the genuinely fresh edition commit.

### DST / calendar boundaries

Cover representative Toronto dates in EDT and EST.

Verify that the same UTC cadence provides post-05:00 opportunities in both regimes and that acceptance of delayed execution does not depend on fixed UTC-to-local conversion.

Verify pre-05:00 Toronto protection across midnight/date rollover.

### Observability

- tests assert the workflow contains explicit outcome reporting;
- already-published and pre-05 no-ops are visibly distinguishable from a run that actually publishes;
- a future production status check can determine from Actions/log output whether The Daily was built rather than inferring from `conclusion: success`.

## Non-goals

- no external scheduler;
- no server or queue;
- no unbounded hourly polling;
- no second Daily notification path;
- no new Gemini call;
- no provider changes;
- no newspaper redesign;
- no Voice workflow changes;
- no generalized workflow-health platform;
- no historical backfill of the missed September 15 edition.

## Acceptance criteria

1. The Daily still targets the 05:00 Toronto hour.
2. A delayed scheduled run at 10:00, 14:00, or later can publish the current day's missing edition instead of being rejected only for lateness.
3. Scheduled runs before 05:00 Toronto do not prematurely create the day's edition.
4. Once today's edition exists, every later attempt no-ops before Python/provider/Gemini work.
5. At most one edition is committed for a Toronto calendar day under overlapping/delayed attempts.
6. `Notify The Daily` remains at most once per genuinely published edition.
7. No stale Daily is masked by an ambiguous green no-op: workflow summaries expose the actual outcome.
8. Current push/manual recovery semantics remain intentional and tested.
9. DST and Toronto date-boundary tests pass.
10. Full repository CI/gate is green.
11. After merge, perform one production verification using the next real scheduled cycle or a safe equivalent and confirm the live edition freshness contract.
12. On verified completion, close #64 and move this file from `docs/open/` to `docs/closed/` in the same housekeeping pass.

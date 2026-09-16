# Issue #67 — Sports recall, recovery-horizon and Champions League correctness

GitHub: https://github.com/BenWassa/Hermes/issues/67

**Status:** Active  
**Date opened:** 2026-09-16  
**Parent product authority:** `SPORTS_V2.md`  
**Related:** `SPORTS_V2_SOURCE_AUDIT.md`, `SPORTS_V2_MAJOR_EVENTS.md`, issue #64

## Problem statement

The recovered September 16, 2026 Daily proved that Sports V2 can publish a technically valid edition while omitting material sports context.

The failures share two architectural causes:

- discovery/provider concentration can leave deterministic qualification with no candidates even when an obvious major event occurred;
- Sports freshness and event selection currently depend on actual execution wall clock instead of a stable Toronto edition-time authority, so a late recovery can represent a different editorial horizon than the intended morning paper.

The same production edition also exposed a separate Champions League resilience problem: UCL was active but disappeared as `scoreboard_unavailable`, and the current event date window is too narrow for sparse matchdays.

This issue is a correctness hardening pass. It does not reopen the Sports V2 product or UI design.

## Production evidence

September 16 recovery build:

- trigger: `workflow_dispatch` around 12:59 Toronto;
- Sports structured requests: 7;
- Sports team-news requests: 3 Guardian queries;
- Sports `raw_candidates=0`;
- Sports `qualified_candidates=0`;
- Sports `winners=0`;
- Toronto team snapshots otherwise succeeded;
- Champions League snapshot was active but `available=false`, `error=scoreboard_unavailable`;
- CBC Canada and CBC Toronto both timed out independently during the ordinary-news build;
- Daily itself still published successfully.

Observed missed/underrepresented Sports cases:

- Raptors/Kawhi Leonard major transaction did not enter the Sports candidate pool despite matching the existing major-transaction taxonomy.
- Champions League supplied no useful desk context despite being a high-priority active competition.

## Locked product outcome

For a given Toronto edition date, Sports should represent the intended morning paper regardless of whether GitHub executes at 05:00, 08:00 or much later that same day.

Sports remains:

- Toronto-first;
- deterministic;
- bounded;
- failure-isolated;
- zero-Gemini;
- finite rather than comprehensive.

## Workstream A — Shared edition-time authority

Create one explicit Sports edition context derived from:

- Toronto calendar edition date;
- intended morning publication target;
- timezone-aware America/Toronto conversion.

Use that context for all Sports freshness-sensitive policy.

Requirements:

- normal morning and delayed-recovery builds for the same edition date resolve equivalent Sports history/future boundaries;
- do not anchor policy independently to `datetime.now()` inside each provider/domain module;
- do not leak developments occurring after the edition's intended morning cut merely because execution is late;
- preserve bounded request windows;
- preserve current Daily edition-existence gate ahead of Sports fetching;
- define behavior across EST/EDT and Toronto date rollover.

The implementation may still record actual fetch time for provenance/telemetry. Fetch time is not editorial-time authority.

## Workstream B — Favourite-team major-news recall

Keep the current deterministic significance taxonomy and one-headline-per-team cap.

Add at least one production-reachable discovery path independent of Guardian for confirmed high-significance Leafs, Raptors and Blue Jays developments.

Preferred source characteristics:

- narrow team/league scope;
- authoritative or strongly reliable confirmation;
- machine-readable or bounded feed/API surface;
- reachable from GitHub Actions;
- low/no incremental cost;
- easy to normalize into existing `SportsHeadlineCandidate` records.

Coverage should support, when explicitly established by source metadata:

- trades/acquisitions/signings/extensions;
- significant surgery or long-term absence/return;
- coach/GM/front-office hire/fire;
- suspension/discipline;
- retirement;
- major award/record/milestone;
- playoff qualification/elimination/championship;
- material ownership/institutional changes.

Keep suppressed:

- routine recaps already represented structurally;
- previews;
- practice/line-combination reports;
- ordinary quotes/interviews;
- speculation and trade rumours;
- weak injury updates without material severity;
- minor roster churn.

### Required source behavior

- Guardian becomes one provider, not the implicit architecture.
- Provider failures are isolated.
- An empty provider result and a provider failure are distinct observable states.
- Domain qualification/ranking remains provider-independent.
- No Sports content is sent to Gemini.

### Regression fixture

The September 2026 Kawhi Leonard/Raptors transaction must be represented as a discoverable normalized candidate and classify as `major_transaction` under the final production source strategy.

## Workstream C — Champions League competition-aware context

Champions League remains high priority and active in normal UCL months.

Replace the generic `yesterday -> +7 days` event window with a bounded competition-aware policy that can bridge sparse matchdays.

On a no-match-today morning, Hermes should still be able to present the smallest useful UCL state from:

- latest meaningful completed matchday/results;
- current table/phase context when useful;
- next meaningful fixtures even when more than seven days away.

### Explicit boundaries

- No full historical scoreboard.
- No year-round broad soccer feed.
- No filler simply because UCL is active.
- Preserve current global/event item caps.
- Keep the rendering compact and unchanged unless a correctness regression requires a minimal adjustment.

### Provider/fallback decision

Re-evaluate the production source contract rather than assuming ESPN-only is sufficient.

`SPORTS_V2_SOURCE_AUDIT.md` identified football-data.org as the preferred #37 structured starting point, while production now uses ESPN public-site JSON. The implementation must document a primary/fallback strategy based on bounded current GitHub Actions probes, source cost and failure behavior.

Required semantics:

- scoreboard/fixture failure should not automatically erase standings if standings are independently available;
- one source failure should permit a configured fallback where practical;
- complete UCL source failure must remain isolated from favourite-team state and Daily publication;
- no-match-today must not be conflated with provider failure.

### September 16 regression fixture

For edition date 2026-09-16:

- no match on September 15 or 16 is valid;
- the system must not call that fact `scoreboard_unavailable`;
- when source data is healthy, selection must be capable of carrying appropriate previous-matchday context from September 8–10 and next-matchday context in October despite the larger gap.

## Workstream D — Telemetry

Extend existing Sports telemetry without adding an analytics service.

Record at minimum:

- Toronto edition date;
- edition-time anchor;
- effective team-news horizon;
- effective UCL previous/next search boundaries;
- requests by provider;
- provider status: success / empty / unavailable;
- raw team-news candidates by provider;
- significance rejects;
- qualified team candidates;
- winners;
- active UCL state;
- UCL primary/fallback source actually used;
- selected latest-result timestamp when any;
- selected next-fixture timestamp when any;
- independent standings availability;
- Sports Gemini records/tokens, still zero.

## Architecture constraints

Prefer one shared edition-context object/helper passed through Sports orchestration.

Provider adapters should own:

- HTTP transport;
- schema validation/parsing;
- provider-native identifiers;
- normalization.

Domain code should own:

- editorial horizon;
- event selection;
- significance qualification;
- dedupe/ranking;
- caps;
- fallback policy selection where multiple normalized provider results exist.

Do not duplicate provider-specific selection logic across build/render layers.

## Non-goals

Do not:

- add Sports Gemini calls;
- restore broad general Sports ingestion;
- add teams beyond Leafs/Raptors/Blue Jays;
- add cricket;
- add live-score behavior;
- add betting/fantasy/player dashboards;
- redesign Sports presentation;
- weaken Daily idempotency/concurrency/publication safeguards;
- introduce unbounded retries/polling;
- make Sports provider failure fatal to the Daily.

## Test matrix

### Edition context

- 05:00 and late same-day recovery produce equivalent intended Sports horizon.
- EST behavior.
- EDT behavior.
- Toronto midnight rollover.
- Late recovery does not include post-cutoff future material.
- Existing-edition no-op still performs zero Sports fetching.

### Team news

- Kawhi/Raptors transaction discovered and qualified.
- Guardian empty + alternate provider winner.
- Guardian failure + alternate provider winner.
- Alternate provider failure + Guardian winner.
- All providers unavailable yields no headline, not build failure.
- Empty vs unavailable telemetry is distinguishable.
- Routine recap suppression remains.
- Trade speculation remains suppressed.
- Weak injury update remains suppressed.
- Max one winner per team remains.
- Dedupe/corroboration remains deterministic.

### Champions League

- No-match-today does not mean unavailable.
- Previous meaningful matchday can be older than one day.
- Next meaningful matchday can be more than seven days away.
- Primary fixture provider failure + fallback success.
- Primary/fallback complete failure stays isolated.
- Standings failure does not suppress valid fixtures/results.
- Fixture failure does not suppress independently available standings/context where product-useful.
- Sparse matchdays stay within explicit bounded search limits.
- Event item cap remains stable.
- Rendering round-trip remains stable.

### Model/cost boundary

- Sports model payload remains empty.
- Sports model token telemetry remains zero.
- Provider request counts remain bounded.

## Production acceptance

Before closeout:

- full repository gate green;
- live GitHub Actions probes for every newly selected team-news source;
- live GitHub Actions probes for final UCL primary and fallback;
- one normal-morning fixture build and one simulated delayed-recovery build for the same Toronto date demonstrate equivalent horizon semantics;
- one no-match-today UCL fixture demonstrates retained useful competition context with healthy providers;
- one injected provider failure demonstrates graceful fallback/isolation;
- phone-width Sports page inspected for regression only;
- build logs confirm zero Sports Gemini records/tokens.

## Documentation reconciliation

Update existing authorities rather than creating new architecture docs:

- `SPORTS_V2.md` for durable product behavior only if clarification is required;
- `SPORTS_V2_SOURCE_AUDIT.md` for final source/fallback evidence;
- `SPORTS_V2_MAJOR_EVENTS.md` for UCL horizon/provider behavior;
- `BUILD_INSTRUCTIONS.md` only if operators need delayed-recovery horizon guidance.

Remove or correct stale statements that describe superseded provider/horizon behavior.

## Definition of done

- Delayed recovery preserves intended morning Sports recall semantics.
- Major Toronto-team events are not single-provider fragile.
- September Kawhi/Raptors regression passes.
- UCL stays useful across sparse matchdays and no-match days.
- UCL has explicit primary/fallback behavior and partial-failure isolation.
- Sports remains deterministic, bounded, failure-isolated and zero-Gemini.
- Full automated regression matrix passes.
- Production-network probes and end-to-end verification pass.
- This spec is reconciled to shipped behavior and moved to `docs/closed/` only after merged-main and required production verification.
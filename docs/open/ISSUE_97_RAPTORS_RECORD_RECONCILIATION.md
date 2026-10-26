---
status: open
issue: 97
lane: sports-data
owner: unassigned
updated: 2026-10-26
---

# Sports: reconcile Raptors season record with completed games (Sentinel HQA-004)

**Tracking:** https://github.com/BenWassa/Hermes/issues/97
**Current state:** Implementation merged: PR #100 (8a1280ac); prospective real-game verification pending.

The GitHub issue is the discussion/approval surface; this is its single retained execution spec under [issue tracking conventions](../ISSUE_TRACKING.md). The requirements below originate from the owner-reviewed issue. Keep only this file updated for durable scope changes; do not create a parallel plan.

---

## Status and evidence
**Scoped proposal; owner approval required for implementation.** P2 deterministic Sports correctness. Sentinel **Candidate 3 / HQA-004**: Toronto Raptors published W–L record lagged verified completed regular-season games in three consecutive audited editions (only 3/7 daily reports existed for the full week). [Weekly synthesis](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/weekly/2026-W43.md), [finding register](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/FINDINGS.md).
- [Oct 23](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html): displayed 0–0 following opening win; actual 1–0. [NBA game evidence](https://www.nba.com/watch/video/raptors-get-20-points-from-four-different-starters-and-finish-with-a-dominant-135-92-win-over-the-bulls).
- [Oct 24](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html) and [Oct 25](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html): displayed 1–0 after second win; actual 2–0. Oct 25 repeats **the same game** as Oct 24, not another independent match defect. [Reuters](https://www.reuters.com/sports/basketball/scottie-barnes-rj-barrett-fuel-raptors-past-wizards--flm-2026-10-24/).
- [Existing code](https://github.com/BenWassa/Hermes/blob/main/src/sports/providers.py) obtains game results and team standing/record from separate ESPN surfaces and combines them without cross-check; *source staleness is possible but not confirmed*.

## Product outcome
Do not show a Toronto favourite-team W–L record that contradicts authoritative, already-completed **regular-season** game results available by the edition cutoff. Prefer explicit unavailable/last-verified state when inputs cannot be reconciled. Do not derive misleading totals from an incomplete schedule window.

## Proposed bounded work
1. Trace ESPN competition statuses and per-season team `record` vs last-game schedule, extraction timestamps, team/league ID, home/away, NBA season boundary and timezone. Check the exact Oct 23–25 shape using frozen minimal provider fixtures.
2. Add deterministic **consistency check**: derive a lower bound on completed regular-season W/L from the available *complete enough* games (or a trusted current team season endpoint) and detect when the separate record endpoint has fewer wins/losses or contradicts completed-game evidence. A short lookback alone cannot justify total-season reconstruction.
3. Establish **record precedence and fallback**: use reliable complete-season authoritative aggregate if present; accept ESPN record only if consistent with verified post-cutoff exclusions. If inconsistent or insufficient data, withhold the displayed W–L total or annotate unavailability rather than silently display wrong record; do not invent a win/loss or force a hard build failure. Preserve last game and future fixture independently when valid.
4. Keep bounded provenance/telemetry counts for disagreement, missing season aggregate, endpoint outage and withheld record, respecting no new Gemini calls and no unbounded provider retries.
5. Validate representative subsequent NBA game days and provider lag cases; extend to Leafs/Blue Jays only if independent evidence shows an analogous mismatch, not as speculative scope expansion.

## Acceptance / tests
- [ ] Frozen opening two Raptors wins: never render 0–0 following 1–0 or 1–0 following 2–0 when completed official results are available at cutoff.
- [ ] Preseason/exhibition, playoffs, postseason, cancelled/postponed/abandoned and scheduled future games excluded from **regular-season** W–L derivation; do not count duplicates.
- [ ] Season rollover, DST, late-night completed game vs next-morning edition and partial season schedule are handled without false contradiction alerts.
- [ ] Conflicting endpoints and degraded network do not suppress valid game result/next fixture or fail the Daily; no fabricated aggregate record, no stale total silently shown.
- [ ] Stable Sports payload/rendering contract, Toronto-first priorities, no additional Gemini call and existing source request budgets preserved.
- [ ] Provider-mocked deterministic and rendered-browser tests pass; PR includes sample old/new payload and a seven-edition post-change spot-check plan.

## Ownership / boundaries
Suggested branch: `fix/raptors-record-reconciliation`. Owner: **Raptors ESPN adapter/season record domain**, principally `src/sports/providers.py` and focused Sports tests. [#67](https://github.com/BenWassa/Hermes/issues/67) owns **major-news recall, delayed horizon, UCL resilience**; do not expand or overlap those adapters/fixtures without an explicit sequence. [#66](https://github.com/BenWassa/Hermes/issues/66) owns team-detail modal UX; do not redesign it. No broader sports provider migration or coverage changes. **Owner decision pending.**

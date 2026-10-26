---
status: open
issue: 103
lane: audit-operations
owner: unassigned
updated: 2026-10-26
---

# Sentinel: 2–4 week audit calibration, false-positive review and write-conflict drill

**Tracking:** https://github.com/BenWassa/Hermes/issues/103
**Current state:** Post-launch 2–4 week reviewer calibration not started; #76 infrastructure closed.

The GitHub issue is the discussion/approval surface; this is its single retained execution spec under [issue tracking conventions](../ISSUE_TRACKING.md). The requirements below originate from the owner-reviewed issue. Keep only this file updated for durable scope changes; do not create a parallel plan.

---

## Purpose / ownership
Sentinel infrastructure issue [#76](https://github.com/BenWassa/Hermes/issues/76) has verified scheduled daily/weekly GitHub writes, persistent HQA IDs and separated branch ownership. This issue owns **post-launch reviewer calibration and operational resilience**, not the initial infrastructure, production editorial implementation, or automatically creating development issues.

**Lane:** research/quality-operations. **Write authority:** scheduled reviewers may edit only their contract-owned `sentinel/reviews` report paths; this issue can collect owner-approved review findings. No alteration of `main` by audit automation, no automatic GitHub development issue creation/closure.

## Deliverables
1. Capture **2–4 weeks** of actually scheduled daily editions and weekly reports. Maintain denominator by Toronto dates, explicitly list missing audits, missing editions, inaccessible Pages and source/paywall limitations. Historical #75 output is separate, never a fabricated daily audit.
2. Independently adjudicate **at least five** report observations (including confirmed defects, false positives, ambiguous evidence, overlooked significant events, incorrect cutoff treatment and unsupported causal claims). Record original daily D-ID / stable HQA ID, contemporaneous check source, actual edition SHA, event/source timestamp, decision and correction.
3. Calibrate dimension ratings, severity and confidence against adjudication; measure evidence completeness and false-positive/false-negative patterns. Maintain stable HQA identities and transitions, distinguish resolved defects from unverified post-change hypotheses.
4. Test branch-write **optimistic concurrency** deterministically: stale SHA update rejected; refreshed report semantically reconciled without duplication/renumber; at most two retries; explicit PARTIAL PERSISTENCE / NOT VERIFIED if weekly FINDINGS/report cannot both read back. Do not deliberately race live schedulers.
5. Verify scheduled audit readback for separate daily and weekly reports, notification/UI delivery expectations with the owner, and actual source/output checks without using secret model reasoning. Identify provider or connector failure states.
6. Produce one compact owner-facing retrospective with up to three actionable priorities, baseline and post-fix comparisons, uncertainty, residual risks and whether any Sentinel rubric or schedule adjustment should be separately approved.

## Acceptance
- [ ] >=14 calendar days observed with **actual N/14 audit coverage** stated, not assumed all days audited.
- [ ] >=5 independently adjudicated observations with explicitly counted disagreements and necessary corrections, no retroactive source/cutoff substitution.
- [ ] Stable HQA identity/dedupe and verified daily/weekly readback demonstrated; collision-safe update exercise logged.
- [ ] False-positive, missed-event and low-evidence examples materially influence updated reviewer guidance.
- [ ] No Sentinel-origin automated production edit, PR merge, issue creation or model migration.
- [ ] Owner reviews result and either accepts calibration closure or scopes a small follow-on correction.

## Dependencies / references
[W43 weekly review](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/weekly/2026-W43.md); [FINDINGS](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/FINDINGS.md); [Oct 26 daily](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-26.md). Related scoped fixes #94/#95/#96/#97 and timing #92. This calibration **does not gate** fixes for already verified defects.

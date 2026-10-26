---
status: open
issue: 94
lane: editorial-intake
owner: unassigned
updated: 2026-10-26
---

# Daily: qualify Canada-priority inputs and restore national-event recall (Sentinel HQA-001/002)

**Tracking:** https://github.com/BenWassa/Hermes/issues/94
**Current state:** Implementation merged: PR #101 (6ae0cc88); live source/coverage verification pending.

The GitHub issue is the discussion/approval surface; this is its single retained execution spec under [issue tracking conventions](../ISSUE_TRACKING.md). The requirements below originate from the owner-reviewed issue. Keep only this file updated for durable scope changes; do not create a parallel plan.

---

## Decision and scope
**Status: PR #101 merged on 2026-10-26; prospective coverage verification pending.** Priority: P1 editorial recall. Sentinel weekly **Candidate 1**, HQA-001 (significant Canadian developments inadequately covered, 3/3 audited editions) and HQA-002 (false Canada-priority classification, 2/3). Evidence: [2026-W43](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/weekly/2026-W43.md), [finding register](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/FINDINGS.md). Coverage is **3/7 scheduled days**, so these are sampled symptoms, not a population error rate.

## Problem / evidence
- 2026-10-23 major federal/provincial action plan inadequately treated: [edition](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html), [PMO pre-cutoff release](https://www.pm.gc.ca/en/news/news-releases/2026/10/21/prime-minister-carney-and-premier-ford-launch-new-action-plan-protect).
- 2026-10-24/25 significant BC election outcomes inadequately summarized: [Oct 24 edition](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html), [Oct 25 edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html). Do **not** infer unseen model rejections; provenance must be checked to distinguish input miss vs final-selection miss.
- Protected Canada-national slots admitted unrelated international/U.S. finance results in two editions. **Code-confirmed route for false positives:** `src/fetch.py` stamps query-level `coverage_lane`, `src/canada.py::is_canada_national` trusts the tag alone, `src/curate.py::_trim_input` reserves up to eight. Cause of provider returns and exact impact on omissions remain unproven.
- Both CBC RSS feeds had recorded errors 3/3; this is a diagnostic signal, **not** evidence that CBC failures caused omissions.

## Bounded implementation plan (proposed)
1. **Trace before changing:** use bounded #74 edition evidence to compare raw normalized candidates, qualifying Canada pool, reserved post-trim inputs, final IDs and source status for all three dates. Record limitations, input-vs-output failure category, and provider outage evidence without assuming model reasoning.
2. **Eligibility:** distinguish `Canada query returned this item` (origin signal) from `this item is substantively Canadian national` (qualification). Use conservative evidence-backed subject/location/actor signals, guard against foreign company tickers and misleading syndicated international posts. Document ambiguous cross-border cases and reviewable false negatives. Never add broad mandatory Canadian quotas or hard-code current politicians.
3. **Recall without fillers:** apply existing bounded reserve **only to qualified, fresh, nonduplicate** Canadian events; keep front/business/world as visible destinations, not a Canada tab. Preserve active major-event priority introduced in #57/#62. Source eligibility should not compel inclusion of weak official press releases.
4. **Source resilience:** audit failed CBC national/Toronto feeds in the CI environment and current source contract; if still failing, propose one verified permitted alternate or reduce dependence on them within existing request/quota budgets. Differentiate HTTP/timeout/parse/empty vs recovered; do not hide failures.
5. **Observability:** report qualified/unqualified Canada matches, reserved-vs-not, reason *codes from deterministic gates only*, event matched-input vs final output, and provider outcomes in bounded provenance; avoid copyrighted bodies and model rationales.
6. **Post-change check:** review seven actual, consecutive editions, including quiet days; compare matching observed metrics and document false positives and uncovered important events.

## Acceptance tests
- [ ] Reproduce both unrelated protected-source examples; neither consumes a Canada-priority slot without valid Canada-specific evidence.
- [ ] Meaningful federal policy and BC provincial-election fixtures retain qualified Canada candidates under 60-item trim, with event-date/cutoff tests; no guarantee of exact final placement based solely on model instruction.
- [ ] Cross-border Canada-relevant, French/English, national-business, Toronto-vs-Canada and weak-evidence inputs exercise **both** false-positive and false-negative cases; no blanket country keyword suppression.
- [ ] Existing major-event fixture, normal section round-robin, cap=60, Opinion/Following independence, Sports isolation, one Gemini call and unchanged provider quota limits remain correct.
- [ ] Source outage, missing key, empty and duplicate results fail soft; publication still works and source statuses are distinguishable.
- [x] CI deterministic + rendered/browser tests passed on PR #101 (755 passed).
- [ ] Post-change report links seven dated editions and exact evidence without asserting an unmeasured improvement.

## Ownership, dependencies and boundaries
Suggested branch: `fix/canada-eligibility-recall`. Owner: **editorial intake lane**; [PR #101](https://github.com/BenWassa/Hermes/pull/101) merged with 755 passing tests. Closest prior completed implementation: [#57](https://github.com/BenWassa/Hermes/issues/57) and [#62](https://github.com/BenWassa/Hermes/issues/62) (do not reopen/redo); coordinate Toronto **section membership** with [#83](https://github.com/BenWassa/Hermes/issues/83) but do not edit its section-filler logic; #72 / draft PR #79 owns model benchmarking, not production intake. Avoid conflicts in `src/curate.py` with other proposed editorial fixes by sequential merge/rebase. No new provider paid tier, model migration (#73), scraping, extra AI call, or auto-publishing behavior. **Code approved and merged; issue closeout is gated on real-edition evidence.**

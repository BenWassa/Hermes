---
status: open
issue: 95
lane: editorial-factuality
owner: unassigned
updated: 2026-10-26
---

# Daily: verify high-impact political and election claims before publication (Sentinel HQA-003)

**Tracking:** https://github.com/BenWassa/Hermes/issues/95
**Current state:** Partial conservative safeguard **merged in PR #105** (`199a76bae6be3622ab28b3db4e7878c97f16774f`; 776 passing tests): source-bound future-election/reelected-incumbent contradictions and single-call prompt guidance. Full result-leader/role validation remains unimplemented and requires evidence-specific design; issue stays open for calibration and prospective verification.

The GitHub issue is the discussion/approval surface; this is its single retained execution spec under [issue tracking conventions](../ISSUE_TRACKING.md). The requirements below originate from the owner-reviewed issue. Keep only this file updated for durable scope changes; do not create a parallel plan.

---

## Implementation slice: narrow deterministic contradiction suppression (2026-10-26)

[PR #105](https://github.com/BenWassa/Hermes/pull/105) owns a bounded source-bound pass after URL/time provenance restoration. The guard only compares **the same model-selected article's source title and public description** with generated fields. Two supported classes: a clearly scheduled future election falsely described as underway on the edition date, and a named reelected incumbent falsely described as returning to power now. Contradicted sentences are withheld; missing or ambiguous evidence abstains. Neutral source-headline fallback applies only if a full generated summary is withheld.

Deterministic fixtures cover those errors, historical-return exceptions, unrelated candidates, unmatched links, unsupported numerical leader reversal and false positives. The edit preserves current model, one-call budget, selection, exact source-link authority, Toronto and Following/Sports isolation.

**Not included:** detecting unsupported winners, role/coreference errors without clear same-source metadata, multi-source cross-card contradiction resolution or external fact-checking. This is not a claim of comprehensive accuracy. Acceptance still requires independent blind false-positive review and real post-merge observations, and the remaining broader claim classes should be scoped from evidence before implementation.

## Decision and evidence
**Scoped proposal; pending owner approval to implement.** P1 editorial correctness. Sentinel **Candidate 2 / HQA-003**: three verified claim-level inaccuracies on two of three audited editions (only **3/7** daily reports available for W43). [Weekly synthesis](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/weekly/2026-W43.md), [register](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/FINDINGS.md).
- 2026-10-23 Toronto ward political-role error: [edition](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html), [independent check](https://thelocal.to/ward-23-scarborough-north-2026/).
- 2026-10-25 Israel election described as underway when scheduled October 27: [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html), [date check](https://www.timesofisrael.com/knesset-election-set-for-october-27-with-government-set-to-complete-full-term/).
- Same edition Brazil election first-round leader reversed: [contemporaneous check](https://www.as-coa.org/articles/brazils-election-four-points-understand-first-round-results).
These are **output defects**. The originating stage/model uncertainty is unresolved; do not claim hidden reasoning or source-body access.

## Outcome
A major factual political/election claim in the Daily should not be asserted with unwarranted certainty when available structured evidence contradicts it. Preserve the normal curated newspaper, not an automated full-text fact-checking scraper.

## Proposed bounded work
1. **Reproduce and classify:** inspect final JSON, model-visible candidate metadata and provenance. For each error, decide whether a conflicting input existed, whether source metadata was sufficient, or whether diagnosis is unknown. Do not infer absent candidate text from published HTML.
2. **Identify a minimal verification boundary** after one ordinary curation call but before rendering, targeting **high-impact checkable claim types only**: election held/future dates and timezone interpretation, incumbent/challenger/current role, declared vote counts and leaders, winner versus forecast. Separate deterministic checks from unresolved ambiguous claims. Use the same available candidate/public metadata or explicitly approved low-cost structured authority; no unbudgeted remote inference.
3. **Failure response design:** if a contradiction is established, prefer safe wording or omission of the unsupported disputed fact, preserving original sourced card identity and allowing an edition to publish. Never fabricate a corrected winner, silently convert uncertainty into certainty, or fail the whole Daily on an inconclusive check.
4. **Prompt guidance and audit telemetry:** if adjusting `src/config.py` editorial instruction, constrain changes to handling contradictory/unknown facts, not broad rewrite or model selection. Record bounded counts for triggered, contradicted, inconclusive and safely handled cases without storing article bodies, model reasoning or secrets.
5. **Measure editorial side effects** using at least seven subsequent editions and a human-reviewed blind false-positive subset before asserting improved factual quality.

## Acceptance / deterministic regressions
- [ ] Reproduce the three cited claim errors using frozen, license-safe, cutoff-qualified fixtures; flag the wrong date, leader and role.
- [ ] Election timing distinguishes **scheduled**, **ongoing**, **completed**, and **projected**; account for editions published before an event, changes/corrections and timezone boundaries.
- [ ] Candidate/coreference test distinguishes officeholder, challenger, incumbent, past officeholder; multi-candidate numerical leader order and unit conversion tests avoid reversing count/percentage meaning.
- [ ] Correct/uncertain statements remain unaffected. High-priority coverage is not uniformly suppressed simply because metadata is incomplete; false positives are counted.
- [ ] One-call Gemini success path, current output schema, editorial selection and section caps, Following/Sports separation, fail-soft rendering, notification and same-day idempotency preserved.
- [ ] Test only contemporaneous information knowable before each edition cutoff; documented absence is not a negative verdict.
- [ ] Run full repository Python + rendered browser CI; attach sample before/after excerpts and exact new provenance metrics.
- [ ] Do not assert 100% factual accuracy from a rule checker. Ship with a documented residual-risk and rollback plan.

## Ownership / implementation boundaries
Proposed branch `fix/editorial-high-impact-facts`. This issue owns **fact assertions**, not links or publication timestamps (separate metadata integrity issue), Canada source intake ([#94](https://github.com/BenWassa/Hermes/issues/94)), Toronto-section classification ([#83](https://github.com/BenWassa/Hermes/issues/83)), provider outage recovery ([#82](https://github.com/BenWassa/Hermes/issues/82)) or Sports. Coordinate `src/curate.py` changes with #94 and metadata integrity work; keep source identity as authority. [#72](https://github.com/BenWassa/Hermes/issues/72) / [draft PR #79](https://github.com/BenWassa/Hermes/pull/79) add evaluation cases but cannot stand in for this production fix. No model migration until [#73](https://github.com/BenWassa/Hermes/issues/73) approved. **Owner decision pending: do not begin implementation automatically.**

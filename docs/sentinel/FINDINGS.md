# Hermes Sentinel — canonical findings register

**Branch:** sentinel/reviews. **Owner:** weekly ChatGPT reviewer only. **Initial allocations:** 2026-W43, 2026-10-25. Report-local D-## and retrospective HA-## labels are not HQA IDs.

## ID allocation and conflict guard

Fetch this file and its latest GitHub blob SHA on every weekly run. Match trigger, symptom and impact against all existing HQA IDs before allocating the next sequential integer. Use compare-and-swap with that SHA; on 409/422 refetch and reconcile, at most two retries. Never renumber, delete, recycle, or blindly overwrite an ID. Retire duplicates as Superseded by HQA-### with dated rationale. Preserve original daily D-IDs.

**Finding states:** Open / Monitoring / Resolved / Rejected / Superseded. **Intervention states:** Not proposed / Proposed / Owner approved / Deferred / Declined / Implemented / Verified / Reopened. Decisions, implementation and verified editorial improvement are separate events; retain dated transitions.

## Finding summary

| ID | Stable falsifiable description | Dimension | Evidence state | Severity / confidence | Distinct editions observed | Finding status | Intervention status | Proposal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HQA-001 | Consequential Canadian developments absent or inadequately summarized | Canada recall/ranking | Supported concern; Oct 25 verified omission | Major / High | 3/3 | Open | Proposed; Pending owner decision | Candidate 1 |
| HQA-002 | Canada-priority reserve admits unrelated foreign candidates | Input relevance | Verified input misclassification | Major / High | 2/3 | Open | Proposed; Pending owner decision | Candidate 1 |
| HQA-003 | Editorial summaries contradict established roles, dates or vote leaders | Factual fidelity | Verified output errors | Major / High | 2/3 | Open | Proposed; Pending owner decision | Candidate 2 |
| HQA-004 | Raptors season record lags verified completed wins | Sports accuracy | Verified displayed-record error | Minor / High | 3/3 | Open | Proposed; Pending owner decision | Candidate 3 |
| HQA-005 | Published article URL differs from captured canonical source | Source identity | Verified mismatch; HTTP failure untested | Minor / Medium | 2/3 | Open | Proposed; Pending owner decision | Candidate 2 |
| HQA-006 | Article publication clock/day labels disagree with Toronto timezone | Time metadata | Verified display-time error | Minor / High | 1/3 | Open | Proposed; Pending owner decision | Candidate 2 |

## Detailed records

### HQA-001 — Consequential Canadian developments absent or inadequately summarized

- **Identity / falsifiable symptom:** Consequential Canadian developments absent or inadequately summarized; distinguish this from the other registered identities and from model-internal causal speculation.
- **Dimension, evidence state, severity/confidence:** Canada recall/ranking; Supported concern; Oct 25 verified omission; Major / High.
- **Dated occurrences and cutoff-qualified independent checks:** [Oct 23 D-01](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-23.md) · [edition](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html) · [independent check](https://www.pm.gc.ca/en/news/news-releases/2026/10/21/prime-minister-carney-and-premier-ford-launch-new-action-plan-protect); [Oct 24 D-01](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-24.md) · [edition](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html) · [independent check](https://cfjctoday.com/2026/10/24/british-columbians-vote-in-early-election-with-david-ebys-job-on-the-line-2/); [Oct 25 D-03](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-25.md) · [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html) · [independent check](https://infonews.ca/news/7962238/bc-conservatives-win-majority-with-lorne-doerkson-to-be-premier/).
- **Evidence and competing interpretations:** Oct 23 missed Oct 21 Canada–Ontario industry plan and Oct 22 Canada–Türkiye partnership (also [readout](https://www.pm.gc.ca/en/news/readouts/2026/10/22/prime-minister-carney-meets-president-turkiye-recep-tayyip-erdogan)); Oct 24 missed B.C. election-day coverage and an Oct 23 Canada tariff change; Oct 25 a riding-by-riding B.C. card missed the Conservative majority projection. All principal examples were knowable by their edition cutoffs; exact initial release hour for the tariff change remains uncertain. Oct 24 CTV election candidate was observed but excluded before the bounded 60-item model input. This does not prove model rejection.
- **Distinct editions / denominator:** 3/3 audited editions (3 available; 4 missing). Do not extrapolate to 7/7 or all candidate articles.
- **Cause:** Source discovery, CBC errors, ranking and input trim may contribute; none is established as the shared cause. [Trim code](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/curate.py#L333-L415).
- **Existing work:** Prior [#57](https://github.com/BenWassa/Hermes/issues/57) and [#62](https://github.com/BenWassa/Hermes/issues/62); [#72](https://github.com/BenWassa/Hermes/issues/72) benchmark; [#83](https://github.com/BenWassa/Hermes/issues/83) is adjacent Toronto-section work.
- **Finding state / transitions:** Open; first allocated 2026-10-25, no prior history.
- **Intervention state / owner decision:** Proposed as weekly Candidate 1; **Pending owner decision** (not approved).
- **Implementation:** No approved targeted remediation established for this finding. Existing adjacent work does not establish resolution.
- **Before/after verification:** Not yet possible; Replay available Oct 23–25 bounded candidates; verify significant federal/provincial event recall under the 60-item cap and seven later editions.
- **Supersedes / superseded by:** None.

### HQA-002 — Canada-priority reserve admits unrelated foreign candidates

- **Identity / falsifiable symptom:** Canada-priority reserve admits unrelated foreign candidates; distinguish this from the other registered identities and from model-internal causal speculation.
- **Dimension, evidence state, severity/confidence:** Input relevance; Verified input misclassification; Major / High.
- **Dated occurrences and cutoff-qualified independent checks:** [Oct 23 D-02](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-23.md) · [edition](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html) · [independent check](https://www.pm.gc.ca/en/news/readouts/2026/10/22/prime-minister-carney-meets-president-turkiye-recep-tayyip-erdogan); [Oct 24 D-02](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-24.md) · [edition](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html) · [independent check](https://investors.ibotta.com/company-information).
- **Evidence and competing interpretations:** Oct 23 protected inputs included Chinese plenum, Hexagon and Bloom Energy headlines; Oct 24 included Ibotta, Wintrust, Motorola and U.S.–Israel material. [Oct 23 captured pool](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/data/edition_evidence/2026/10/2026-10-23.json) and [Oct 24 pool](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/data/edition_evidence/2026/10/2026-10-24.json). These were input markers, not necessarily published stories. Company identities and Canadian government examples predate cutoff.
- **Distinct editions / denominator:** 2/3 audited editions (3 available; 4 missing). Do not extrapolate to 7/7 or all candidate articles.
- **Cause:** **Code-proven:** [Canada classification](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/canada.py#L227-L229) checks only intake coverage_lane; [fetch](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/fetch.py#L125-L145) assigns that lane to every Canada-query result; [trim](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/curate.py#L358-L400) reserves up to eight. Why provider returned unrelated results is unproven.
- **Existing work:** [#57](https://github.com/BenWassa/Hermes/issues/57), [#62](https://github.com/BenWassa/Hermes/issues/62), [#72](https://github.com/BenWassa/Hermes/issues/72).
- **Finding state / transitions:** Open; first allocated 2026-10-25, no prior history.
- **Intervention state / owner decision:** Proposed as weekly Candidate 1; **Pending owner decision** (not approved).
- **Implementation:** No approved targeted remediation established for this finding. Existing adjacent work does not establish resolution.
- **Before/after verification:** Not yet possible; False-positive foreign securities and true Canada/cross-border fixtures; preserve priority budget and avoid false-negative Canada events.
- **Supersedes / superseded by:** None.

### HQA-003 — Editorial summaries contradict established roles, dates or vote leaders

- **Identity / falsifiable symptom:** Editorial summaries contradict established roles, dates or vote leaders; distinguish this from the other registered identities and from model-internal causal speculation.
- **Dimension, evidence state, severity/confidence:** Factual fidelity; Verified output errors; Major / High.
- **Dated occurrences and cutoff-qualified independent checks:** [Oct 23 D-03](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-23.md) · [edition](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html) · [independent check](https://thelocal.to/ward-23-scarborough-north-2026/); [Oct 25 D-01](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-25.md) · [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html) · [independent check](https://www.timesofisrael.com/knesset-election-set-for-october-27-with-government-set-to-complete-full-term/); [Oct 25 D-02](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-25.md) · [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html) · [independent check](https://www.as-coa.org/articles/brazils-election-four-points-understand-first-round-results).
- **Evidence and competing interpretations:** Oct 23 Scarborough North incumbent TTC chair incorrectly described as challenger (Minor); Oct 25 Israel election called today instead of Oct 27 (Major); Oct 25 Lula called first-round leader although Flávio Bolsonaro led (Major). Three separate claims across two dates, not a proven common root cause. All external checks predate cutoffs.
- **Distinct editions / denominator:** 2/3 audited editions (3 available; 4 missing). Do not extrapolate to 7/7 or all candidate articles.
- **Cause:** [Curation prompt](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/config.py#L373-L424) asks model to compose summary; no internal reasoning or original source-body access. Model-origin hypothesis, not confirmed root cause.
- **Existing work:** [#72](https://github.com/BenWassa/Hermes/issues/72) and [draft PR #79](https://github.com/BenWassa/Hermes/pull/79) benchmark; [#73](https://github.com/BenWassa/Hermes/issues/73) production migration blocked.
- **Finding state / transitions:** Open; first allocated 2026-10-25, no prior history.
- **Intervention state / owner decision:** Proposed as weekly Candidate 2; **Pending owner decision** (not approved).
- **Implementation:** No approved targeted remediation established for this finding. Existing adjacent work does not establish resolution.
- **Before/after verification:** Not yet possible; Adversarial role/coreference, election-date, vote-leader and numeric-inversion cases; blind review and false-positive assessment.
- **Supersedes / superseded by:** None.

### HQA-004 — Raptors season record lags verified completed wins

- **Identity / falsifiable symptom:** Raptors season record lags verified completed wins; distinguish this from the other registered identities and from model-internal causal speculation.
- **Dimension, evidence state, severity/confidence:** Sports accuracy; Verified displayed-record error; Minor / High.
- **Dated occurrences and cutoff-qualified independent checks:** [Oct 23 D-04](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-23.md) · [edition](https://github.com/BenWassa/Hermes/blob/948c088f067a2871b6719e5e08f43f63c6050be1/docs/index.html) · [independent check](https://www.nba.com/watch/video/raptors-get-20-points-from-four-different-starters-and-finish-with-a-dominant-135-92-win-over-the-bulls); [Oct 24 D-03](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-24.md) · [edition](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html) · [independent check](https://www.reuters.com/sports/basketball/scottie-barnes-rj-barrett-fuel-raptors-past-wizards--flm-2026-10-24/); [Oct 25 D-04](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-25.md) · [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html) · [independent check](https://www.reuters.com/sports/basketball/scottie-barnes-rj-barrett-fuel-raptors-past-wizards--flm-2026-10-24/).
- **Evidence and competing interpretations:** Oct 23 displayed 0–0 after opening win (actual 1–0); Oct 24 and 25 displayed 1–0 after second win (actual 2–0). The last two reports repeat the same completed game, not two independent game failures.
- **Distinct editions / denominator:** 3/3 audited editions (3 available; 4 missing). Do not extrapolate to 7/7 or all candidate articles.
- **Cause:** **Code-proven lack of reconciliation:** [ESPN adapter](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/sports/providers.py#L336-L380) parses schedule for last game and separate team endpoint for record, then combines without checking consistency. Provider staleness remains hypothesis.
- **Existing work:** [#67](https://github.com/BenWassa/Hermes/issues/67) adjacent sports reliability; [#66](https://github.com/BenWassa/Hermes/issues/66) adjacent UI.
- **Finding state / transitions:** Open; first allocated 2026-10-25, no prior history.
- **Intervention state / owner decision:** Proposed as weekly Candidate 3; **Pending owner decision** (not approved).
- **Implementation:** No approved targeted remediation established for this finding. Existing adjacent work does not establish resolution.
- **Before/after verification:** Not yet possible; Opening two wins, provider lag, partial schedule, cancelled/preseason/postseason games; fail-soft unknown record; later three completed games.
- **Supersedes / superseded by:** None.

### HQA-005 — Published article URL differs from captured canonical source

- **Identity / falsifiable symptom:** Published article URL differs from captured canonical source; distinguish this from the other registered identities and from model-internal causal speculation.
- **Dimension, evidence state, severity/confidence:** Source identity; Verified mismatch; HTTP failure untested; Minor / Medium.
- **Dated occurrences and cutoff-qualified independent checks:** [Oct 24 D-04](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-24.md) · [edition](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html) · [independent check](https://www.theguardian.com/world/2026/oct/24/ukraine-war-briefing-russian-diesel-tankers-headed-for-north-america-says-moscow-as-us-tries-to-revive-peace-talks); [Oct 25 D-06](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-25.md) · [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html) · [independent check](https://www.theguardian.com/world/2026/oct/24/israel-soldiers-raze-west-bank-neighbourhood-hebron-families-from-homes).
- **Evidence and competing interpretations:** Oct 24 Guardian URL has colon where source slug uses hyphen; Oct 25 has neighborhood where source uses neighbourhood. Both editions' [Oct 24](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/data/edition_evidence/2026/10/2026-10-24.json) and [Oct 25](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/data/edition_evidence/2026/10/2026-10-25.json) provenance show an unmatched final link. Whether published variants redirect or 404 is unknown.
- **Distinct editions / denominator:** 2/3 audited editions (3 available; 4 missing). Do not extrapolate to 7/7 or all candidate articles.
- **Cause:** [Model output schema](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/config.py#L399-L424) includes free-form link despite preserve-source instruction; precise transformation step unknown.
- **Existing work:** [#74](https://github.com/BenWassa/Hermes/issues/74) / [merged PR #80](https://github.com/BenWassa/Hermes/pull/80) detect mismatches, do not repair them; [#72](https://github.com/BenWassa/Hermes/issues/72).
- **Finding state / transitions:** Open; first allocated 2026-10-25, no prior history.
- **Intervention state / owner decision:** Proposed as weekly Candidate 2; **Pending owner decision** (not approved).
- **Implementation:** No approved targeted remediation established for this finding. Existing adjacent work does not establish resolution.
- **Before/after verification:** Not yet possible; Preserve matched source canonical identity; test redirects, unknown late links and fail-soft output without additional model calls.
- **Supersedes / superseded by:** None.

### HQA-006 — Article publication clock/day labels disagree with Toronto timezone

- **Identity / falsifiable symptom:** Article publication clock/day labels disagree with Toronto timezone; distinguish this from the other registered identities and from model-internal causal speculation.
- **Dimension, evidence state, severity/confidence:** Time metadata; Verified display-time error; Minor / High.
- **Dated occurrences and cutoff-qualified independent checks:** [Oct 25 D-05](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/daily/2026-10-25.md) · [edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html) · [independent check](https://www.theguardian.com/world/2026/oct/25/lula-da-silva-flavio-bolsonaro-brazil-presidential-election).
- **Evidence and competing interpretations:** Oct 25 front lead rendered 8:00 AM for 08:00:58Z (04:00 EDT); other cards show apparent future or previous-day labels; [same-commit evidence](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/data/edition_evidence/2026/10/2026-10-25.json) records timestamps. Other dates were not independently checked for this class.
- **Distinct editions / denominator:** 1/3 audited editions (3 available; 4 missing). Do not extrapolate to 7/7 or all candidate articles.
- **Cause:** [Model prompt](https://github.com/BenWassa/Hermes/blob/ba3c07070b90a6b91702955af2532d44325225ac/src/config.py#L399-L424) requests a free-form time field; whether input parsing or model formatting introduced error is unknown.
- **Existing work:** [#72](https://github.com/BenWassa/Hermes/issues/72); no exact open issue.
- **Finding state / transitions:** Open; first allocated 2026-10-25, no prior history.
- **Intervention state / owner decision:** Proposed as weekly Candidate 2; **Pending owner decision** (not approved).
- **Implementation:** No approved targeted remediation established for this finding. Existing adjacent work does not establish resolution.
- **Before/after verification:** Not yet possible; America/Toronto conversion, UTC day rollover, DST, missing source timestamps; render deterministic time or Unknown.
- **Supersedes / superseded by:** None.

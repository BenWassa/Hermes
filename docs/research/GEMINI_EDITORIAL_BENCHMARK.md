# Gemini editorial benchmark — research status

**Issue:** [#72](https://github.com/BenWassa/Hermes/issues/72) · **Research date:** 2026-10-22 · **Scope:** research only; no production curation/model/workflow changes.

## Outcome at this checkpoint

The reproducible research **infrastructure** is available: 14 synthetic public-metadata candidate pools (201 story records including a 65-item cap test), exact production prompt/candidate projection, per-model setting matrix, offline structural/reference checks, a blind-review exporter, usage/latency capture, introductory/2027 cost estimates, and credential-gated live execution. **No Gemini responses or quality comparisons have yet been measured.** Neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` was available in the execution environment on 2026-10-22; the Google SDK also was not installed in that local environment. Existing repository CI installs the required SDK through `requirements-dev.txt`. Availability and quotas for the owner's AI Studio account remain unknown. No secret value was read or exposed.

**Recommendation:** retain production `gemini-2.5-flash` and its 1,024-token thinking budget until live quality/latency/usage comparisons and blind review are completed. **No evidence-based migration winner** can be declared from synthetic fixtures and price tables alone. The first challenger should be `gemini-3.8-flash@medium`, then `@low` and `@high` against the same cases; medium is the provider-documented default, not a Hermes quality result. Optional cost control: `gemini-3.5-flash-lite@minimal`. Paid hard-case benchmark: `gemini-4-argon@medium`; Preview challenger `gemini-3.1-pro-preview@high`. Do not deploy by this PR.

## Reproduce

From repository root (Python 3.11; `pip install -r requirements-dev.txt`):

```bash
python -m research.gemini_benchmark validate
python -m research.gemini_benchmark plan
python -m pytest tests/test_gemini_benchmark.py -q

# Export the exact synthetic 60-story + Following prompt (offline).
python -m research.gemini_benchmark export \
  --fixture dense-sixty-following \
  --export-out research/gemini/exports/dense-sixty-following.json
# #77's provider probe defaults to local preflight, NOT a network request:
python -m research.free_ai_providers.spike \
  --fixture research/gemini/exports/dense-sixty-following.json \
  --provider cloudflare --require-full-size

# Explicitly opted in: may consume account quota and incur charges.
# Supply GEMINI_API_KEY or GOOGLE_API_KEY in YOUR shell/secret manager.
python -m research.gemini_benchmark run --live --confirm-spend \
  --models gemini-2.5-flash@default,gemini-3.8-flash@low,gemini-3.8-flash@medium,gemini-3.8-flash@high \
  --repeat 2 --max-calls 120 --pause-seconds 5

python -m research.gemini_benchmark summarize
python -m research.gemini_benchmark blind
```

By default, no API call runs. `plan` enumerates intended calls without credentials; `run` without `--live --confirm-spend` also only prints an offline plan. A missing key with both switches exits before any API call. Responses, request prompts, projected payloads, setting hashes, tokens and errors are written to local ignored `research/gemini/runs/`; blind packets and the **separately withheld** identity key are written under `research/gemini/blind/`. Never publish the key with blinded packets. The harness makes exactly one attempt per cell; no fallback, auto-retry or hidden request changes. Each output is one JSON file, with failures preserved instead of silently discarded. Reusing the same file requires `--overwrite`.

Use `--fixture business-numbers` or `--fixture dense-sixty-cap` for a small opt-in validation before full runs. A difficult-case premium subset should include `business-numbers`, `opinion-following`, `geopolitical-uncertainty`, `dense-sixty-cap`. The new `dense-sixty-following` case explicitly tests **60 model-input stories plus two Following seeds**, reusing a synthetic 65-candidate trim case without changing the production curation algorithm. The offline `export` command writes the exact `request_payload` tuple in #77's transport format into a gitignored local file; it refuses to overwrite by default. This is a shape/transport fixture, not a live full-payload measurement.

To compare an output budget change, repeat **all paired variants** with an explicitly recorded `--max-output-tokens` value, and keep budgets separate in analysis.

The runner imports `src.curate._trim_input`, `src.curate._curation_view`, `src.opinion.curation_following_view`, `src.config.build_curate_system_prompt`, `src.canada.editorial_instruction` and the production Following override. It uses `temperature=0.3`, `response_mime_type=application/json`, default max output **16,000** and, for 2.5 Flash, production thinking budget **1,024**. For 3.8 Flash it substitutes the supported `thinking_level` (`low`, `medium`, `high`). Output tokens include the reasoning budget: a 16K ceiling can still truncate JSON if thought usage is large. Each run stores prompt/payload hashes and a manifest for drift diagnosis. No data from published HTML is backfilled as synthetic original input.

**Run matrix:** main paired comparison = 14 cases × 4 variants × 2 repeats = 112 requests, before optional challengers. This is *planned*, not performed. Do not batch the 112 requests on an account with unverified per-minute token quotas. First verify account model access and free quota with a one-case run. A 60-candidate prompt with 16K possible output can exceed small TPM accounts even if request-per-minute seems sufficient.

## Separate automated and human judgments

Automatic scores are deterministic **diagnostics**, not proof of editorial quality. `validate_output` detects JSON parsing errors, malformed sections, wrong/duplicate links and IDs, caps, lead/analysis misuse, Following key losses, plus expected-url recall/omission, preferred section placement, event duplicate groups, conditional rank-pair wins and **literal** fact-anchor matches. A lexical hit can accompany a false claim and absence can be legitimate paraphrase. It does not grade semantic factual accuracy, sensitivities in context, argument fidelity, hallucinated causality, relevance or prose quality. Missing token usage is `null`, never silently imputed as zero; report `thought_tokens` separately.

Blind human review: choose at least **five** cases including finance, Canada recall, Following, uncertainty and crowded input; at least **two independent repetitions per baseline/challenger**. Keep the exported model mapping separate; randomize packet order and display the identical original fixture metadata for each packet. Prefer two reviewers; reconcile disagreements in an adjudication ledger keyed by `review_id`, with exact cited headline/description and output quote. Document the reviewer, rubric version and any reference changes. Reviewers must not infer external facts from source metadata; verify contested real-world facts against independent dated primary evidence when captured real candidates become available.

### Shared human rubric — 100 possible points

| Axis | Weight | Scoring anchor |
| --- | ---: | --- |
| Factual accuracy and source fidelity | 30 | No invented numbers, names, offices, agreements or unjustified certainty; substantiate claims in available source metadata |
| Material recall and harmful omissions | 20 | Most consequential covered developments survive; distinguish true missed candidates from pre-trim absence |
| Event dedupe and nonredundancy | 10 | Consolidate repeating reports; do not double-print the same event |
| Section placement and editorial ranking | 10 | National versus Toronto distinction; correct sections and relative importance |
| Opinion/Following fidelity | 10 | Credit and fairly reconstruct author's claim, counterpoints and confidence; no impersonated endorsement, Following complete |
| Lead analysis value | 15 | Actual supported implications/links to other covered evidence; not summary repetition, speculation or invented causality |
| JSON contract/presentation | 5 | Valid parse, preserved sources, one lead/section, caps, coherent length, correct flags |

Each axis is awarded **0–100% of its weight**; reviewers record brief concrete evidence and a severity label. **Critical fail:** fabricated consequential fact, wrong current officeholder presented as known, dropped guaranteed Following, major Canadian omission despite being in supplied model pool, duplicated lead event, or unparsable JSON. A critical fail may disqualify a variant even with high total score. For deliberate synthetic scenarios, score fidelity to the **scenario input**, not whether hypothetical persons/events exist outside it. Mark `not_applicable` and adjust denominator transparently where an axis is not exercised.

Create a separate human-score CSV/JSON with fields `review_id`, `rubric_version`, `reviewer_id`, `axis_scores`, `critical_fail`, `evidence`, `adjudication`; do not expose model identity to graders. Keep automatic metrics, grades and API metadata in separate tables until unblinding. Aggregate per case and by issue severity before computing means. Pair variants by fixture and repeat, report p50/p95 request latency, response JSON pass rate, recall and duplication, grade spread, paid price per edition, thought fraction and 365-edition economics. Repeated runs reveal variance, not model determinism. Compare output-budget truncation frequency independently.

## Price schedule (USD, standard synchronous API, text; official on 2026-10-22)

| Model | Free tier listed | 2026 input/output $ per 1M | 2027 input/output $ per 1M |
| --- | --- | --- | --- |
| 2.5 Flash | Yes; limited by account quotas | 0.30 / 2.50 | 0.30 / 2.50 |
| 3.8 Flash | Yes; limits unverified | 0.75 / 3.75 through Dec 31 | 1.50 / 7.50 from Jan 1 |
| 3.5 Flash-Lite | Yes; limits unverified | 0.30 / 2.50 | 0.30 / 2.50 |
| 4 Argon | **No** | 2.00 / 10.00 through Nov 30; **4.00 / 20.00 from Dec 1** | 4.00 / 20.00 |
| 3.1 Pro Preview | **No** | 2.00 / 12.00 (up to 200K input) | 2.00 / 12.00 (verify future pricing) |

Rates are **published pricing, not observed charges**; usage includes output thinking tokens. Benchmark `price()` stores both a snapshot introductory and a 2027-price scenario. For 4 Argon the intro scenario applies only through November 30, 2026, while the later scenario begins **December 1, 2026**, earlier than 2027.

**Illustrative non-measured envelope:** 12,000 prompt tokens, 5,000 visible output tokens, **1,500 thoughts** = 6,500 billed output tokens. 2.5 Flash $0.01985/edition (~$7.25/year); 3.8 Flash $0.033375 (~$12.18/year) in 2026 vs $0.06675 (~$24.36/year) in 2027; Argon $0.089 (~$32.49/year) introductory vs $0.178 (~$64.97/year) after Dec 1. Assumes one uncached daily call, 365 days, no retries, no weekly Voice costs. Actual tokens, regional billing, quotas and account access must be measured. No dollar figure above implies quality or latency.

Official references: [current models](https://ai.google.dev/gemini-api/docs/models), [thinking levels](https://ai.google.dev/gemini-api/docs/thinking), [Gemini 3.8 migration](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.8), [pricing](https://ai.google.dev/gemini-api/docs/pricing). Free-tier inputs can be used by Google to improve services; confirm policy suitability for every captured dataset.

## Migration decision gate and fallback policy

Before proposing #73: verify at least 10 fixture cells *per core variant* with two runs, measured usage (including thoughts), low JSON failure rate, no critical factual/Canadian/Following regressions and independent blinded win/neutrality versus 2.5 Flash. Confirm quotas in **the production account** and the full 60-plus-Following payload. Choose smallest cost/effort level meeting the bar; test 16K first and consider 24K only if documented JSON truncation justifies it. Confirm 06:00 publication latency budget, free-tier policy, and cap exposure under 2027 pricing.

**Proposed, not implemented:** retain 2.5 Flash as fallback while available, preserve model+level as a revertible configuration, fall back only on narrow transient/quota errors, never retry invalid JSON without bounded handling, and monitor response truncation/Following omissions/Canada recalls before changing default. If quality fails after migration, immediately restore previous pinned production model and settings. #73 requires owner approval. #77 may reuse this read-only fixture schema/rubric for non-Gemini alternatives and owns all its provider-specific work independently.

## Results and explicit blockers

- **Fixtures:** 14/10 minimum assembled, 201 hypothetical candidate records; no true historical input-pool captures are available in this research.
- **Live model calls:** 0. No Google API credentials accessible in this execution environment; account model availability, per-minute and per-day quotas unknown.
- **Observed editorial scores, failures, cost, latency:** **not measured**. Example failure modes above are test *targets*, not claimed model failures.
- **Automated checks:** `tests/test_gemini_benchmark.py` and normal repository CI; record their outcome in the PR after running.
- **Production:** untouched. #77 research files: untouched.

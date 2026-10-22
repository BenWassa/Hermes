# Recurring-free editorial AI APIs for Hermes (issue #77)

**Research date:** 2026-10-22 (America/Toronto). **Branch:** `research/free-ai-providers`. **Status:** documentary/provider-capability assessment and deterministic local spike; **no authenticated live inference**. This is a research decision memo, **not production approval**.

## Executive decision

**Keep Gemini as the only production provider for now.** Make **Z.ai `glm-4.7-flash`**, **Cloudflare Workers AI `@cf/zai-org/glm-4.7-flash`**, and **OpenRouter's pinned NVIDIA Nemotron 3 Ultra `:free`** the maximum three *research challengers*, in that order for initial probes. Cloudflare has the clearest quantified recurring daily grant and a strong public no-training/no-retention policy. Z.ai provides a directly free-priced Flash endpoint, but we could not verify an account-independent numerical throughput guarantee. OpenRouter's pinned endpoints can be tested against a published free request allowance, but provider-specific privacy, JSON support, and availability are weaker. All remain **unvalidated for Hermes editorial quality and full-request reliability**.

Do **not** equate free listing with stable indefinite service; grants and model availability can change. Do **not** route public or licensed full article bodies or private Following material into a provider without confirming rights and policies. A newly released OpenRouter model, MiniMax M3.1 Flash `:free`, explicitly advertised an October 22 **12:00 UTC** promotional free expiry and is **excluded** as non-recurring, despite appearing in some search/catalog results. [OpenRouter launch model page](https://openrouter.ai/minimax/minimax-m3.1-flash%3Afree/).

## Actual Hermes call shape and scope

Inspected `main` at `550a9f821292e6ed32a2272b2ed95ad52eed1a9e` on 2026-10-22:

- `src/config.py`: `CURATE_MAX_INPUT=60`, `CURATE_MAX_TOKENS=16000`, default `gemini-2.5-flash`, default thinking budget 1024. This is a **cap**, not evidence that every request consumes 16,000 output tokens.
- `src/curate.py`: single Gemini call, house-voice system prompt + Canada-event editorial instruction, `_curation_view` with priority markers, JSON serialized story payload, optionally `following` in same request with deterministic keys and a distinct Following instruction. There can be up to **six** Following seeds (`VOICE_FOLLOWING_CAP`).
- `src/normalize.py`: story curation view is seven fields: `title`, `description`, `source`, `section_hint`, `pub_date`, `image`, `link`. Active-event priority is extra when applicable.
- Expected output: sections and stories with `lead`, `analysis`, metadata links/images, `sensitivity`, plus a `following` prose array preserving exact keys/order. The production model currently outputs JSON MIME, **not** a full provider-side JSON Schema. A successful parse alone does not prove editorial acceptability.
- The published HTML is an output artifact, **not** a faithful original 60-item candidate input. The original fully serialized input payload and token count have not been recovered. No token measurements below are passed off as a captured Hermes request.

**Sensitivity calculation only:** a hypothetical **10,000 input tokens + 16,000 output tokens** is a stress case, not a measured edition. Verify actual input/output counts and one-call success on #72's replayable fixtures. Evaluate real outputs as well as maximum requested output tokens; providers may reserve a completion budget differently.

## Eligibility and hard constraints (official docs, verified 2026-10-22)

| Family and pinned candidate | Genuine continuing free tier? | Published free limits / size | One-call full-size assessment | Eligibility |
|---|---|---|---|---|
| **Z.ai** `glm-4.7-flash` (secondary `glm-4.5-flash`) | Pricing page expressly lists **Free** input/output. This is **not** the paid GLM Coding Plan; do not confuse that plan with standard API keys. New `glm-5.3-flash` is **paid**, not free just because its name contains Flash. | GLM 4.5 family documentation states 128K context and up to 96K output; confirm **4.7 Flash's exact output/context caps** and account RPM/TPM independently, not by inference from family docs. Published global free quota insufficiently specified. | **Possible, unverified.** 60+Following could fit context, but required per-account free quota, 16K output and JSON reliability not live-confirmed. | **Research candidate only** |
| **Groq** `openai/gpt-oss-120b` | Yes: ongoing Free Plan, not signup credits. | **30 RPM, 1,000 RPD, 8,000 TPM, 200,000 TPD** for `openai/gpt-oss-120b`; context **131,072**, max output **65,536**. Individual organization may have different enforced limits; cached tokens do not count. | **High risk of failing / throttling full request.** 16K possible output already exceeds *one minute's* free 8K TPM without counting input; even 10K input alone exceeds 8K in a minute. This is a rate-bound incompatibility in the stress case, **not an observed 429**. Small prompts may work. Do not call it a one-call fit without a real run. | **Secondary limited-payload test; not leading shortlist** |
| **OpenRouter** `nvidia/nemotron-3-ultra-550b-a55b:free` | Free models get recurring 50 requests/day at 20 RPM without deposit; 1,000 RPD after **$10+ purchased credits**, still free inference when using free endpoints. **Do not treat $10 as needed to get the initial free quota**. | Pinned Nemotron 3 Ultra has **1M context and 65,536 output cap**, but provider docs say **no `response_format` support** for this endpoint. Free routes are best-effort and may change/withdraw. | **Token capacity looks plausible; operational/JSON fidelity not established**. Must validate availability and parse without JSON mode (prompt-only JSON). Avoid random `openrouter/free` routing for comparable results. | **Third challenger** |
| **Mistral** `mistral-small-2603` | Mistral Studio **Free mode** has recurring *included monthly usage* rather than one-time trial credits. | `mistral-small-2603`: **256K** context, structured outputs. Exact free org RPS, TPM and monthly tokens **only on admin Limits page**, not a generally guaranteed numerical limit; Free mode targeted at evaluation/prototyping. | **Technically plausible by context, quota unknown**; free usage terms and training defaults need approval. Cannot claim production availability. | **Reserve candidate pending account evidence** |
| **Cloudflare Workers AI** `@cf/zai-org/glm-4.7-flash` | Recurring **10,000 neurons/day** on Workers Free, resetting 00:00 UTC; after limit, requests **fail** unless Workers Paid. Paid-required `@cf/zai-org/glm-5.3-flash` is **not free-eligible**. | GLM 4.7 Flash: **131,072** context; **$0.0605/M input and $0.40/M output** equivalent neuron pricing; default text generation **300 RPM** (subject to per-model exceptions). Model-specific maximum *completion* and JSON mode enforcement not yet experimentally verified. | **Budget looks ample for one hypothetical 10K+16K call (~637 neurons)**, but actual context, output, structured JSON, latency, capacity/429 and per-request limits need live testing. | **Strong second challenger** |

Official basis: [Z.ai pricing](https://docs.z.ai/guides/overview/pricing), [Z.ai Quick Start/standard-key endpoint](https://docs.z.ai/guides/overview/quick-start), [GLM 4.5 model family](https://docs.z.ai/guides/llm/glm-4.5), [Groq rate limits](https://console.groq.com/docs/rate-limits), [Groq GPT-OSS model card](https://console.groq.com/docs/model/openai/gpt-oss-120b), [OpenRouter pricing/rate limits](https://openrouter.ai/pricing), [pinned Nemotron Ultra model card](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b%3Afree), [Mistral usage limits](https://docs.mistral.ai/admin/billing-usage/usage-limits), [Mistral August 2026 rate-limit note](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them), [Mistral Small 4 model](https://docs.mistral.ai/models/mistral-small-4-0-26-03), [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [Cloudflare model card](https://developers.cloudflare.com/workers-ai/models/glm-4.7-flash/), [Cloudflare rate limits](https://developers.cloudflare.com/workers-ai/platform/limits/), [Cloudflare July paid-model change](https://developers.cloudflare.com/changelog/post/2026-07-28-models-require-workers-paid/).

### Recurring vs introductory free

- **Recurring documented:** Z.ai GLM 4.7/4.5 Flash listed free-priced (duration not guaranteed); Groq Free Plan; OpenRouter free requests daily on currently hosted `:free` endpoints; Mistral Studio free monthly included usage; Cloudflare free daily neurons.
- **NOT recurring:** promo `:free` MiniMax M3.1 Flash (October 22 promotional expiry); Z.ai paid GLM 5.3 Flash or FlashX; signup promotional credits at any provider. An API key alone never verifies ongoing practical throughput.
- **Not interchangeable:** Z.ai consumer chat/coding subscriptions or DevPack quota **do not** authorize standard inference calls through `api.z.ai/api/paas/v4`; verify standard API key and billing separately.

## Privacy, licensing, reliability and geography review

| Family | Official provider statements / unresolved checks |
|---|---|
| **Groq** | Customer input/output are not retained by default for normal inference; reliability/abuse logs may be kept up to 30 days; Zero Data Retention can be enabled. Services agreement prohibits model training on inputs/outputs without authorization. No observed live policy review of this account. [Data handling](https://console.groq.com/docs/your-data), [services agreement](https://console.groq.com/docs/legal/services-agreement). |
| **Cloudflare** | Workers AI standard inference provides no-training and zero-retention commitments, with legal/stateful/logging exceptions. Cloudflare-hosted model, not external AI Gateway; license for third-party open models requires a separate model-term check. Canadian usage not established as a dedicated data-residency guarantee. [Data policy, updated Oct 16](https://developers.cloudflare.com/workers-ai/platform/data-usage/). |
| **OpenRouter** | Router says it does not default-log request content, but a third-party model provider may retain/training-process content. `Minimax` is listed as retaining prompts, and free Nemotron-provider terms must be read before live non-synthetic data. Zero-retention model/provider routing is not the same as guaranteed availability on the desired free endpoint. No guaranteed SLA. [Provider data practices](https://openrouter.ai/privacy), [provider registry](https://openrouter.ai/providers), [terms](https://openrouter.ai/terms), [support](https://openrouter.ai/support). |
| **Mistral** | **Free Studio may use prompts AND outputs to train by default**, with opt-out right; free mode is described as evaluation/prototyping. Verify that relevant training opt-out is active and commercial usage is authorized before considering production. Free mode caps must be checked in the org account. [Training policy, Aug 2026](https://help.mistral.ai/en/articles/347617-do-you-use-my-user-data-to-train-our-artificial-intelligence-models), [limits](https://docs.mistral.ai/admin/billing-usage/usage-limits). |
| **Z.ai** | Free-priced endpoint confirmed, but exact service-level free quota, prompts/outputs training and retention, regional processing, commercial permissions and model-specific licensing still **not verified** from a sufficiently explicit official source in this audit. Require current [Z.ai terms/policy](https://docs.z.ai/), an account confirmation and a legal/privacy check before production. **No positive privacy claim inferred.** |

**Shared legal issue:** Hermes' ordinary inputs are short publisher-provided metadata; do not transfer licensed/publisher article bodies or personal data merely to test a model. Account location, payment method, geographic access, model license, terms that restrict production/commercial use and privacy requirements must be confirmed independently. Do not create artificial provider accounts or rotate multiple keys to bypass quotas.

## One-call quantitative stress model (not empirical)

Assume **10K input + up to 16K output**. Model context must permit **26K** combined tokens, but the provider's *effective per-request and per-minute* limits may be stricter. Current edition's actual serialized input and actual outputs were unavailable; repeat this arithmetic using measured token usage (including reasoning tokens when reported).

| Provider/model | Illustration for the *same* 10K + 16K case | Interpretation |
|---|---:|---|
| Groq GPT-OSS-120B Free | 26K nominal tokens vs **8K TPM** | At least **3.25 minute-worth** of published free throughput; single full request not proven and may be rejected/limited. Do not infer splitting into four calls preserves one-call editorial global ranking. |
| Cloudflare GLM 4.7 Flash | **~637 neurons**, ~**15** hypothetical full runs in a fresh 10K-neuron day | Uses `$0.0605`/M in + `$0.40`/M out divided by `$0.011`/1K neurons. Reasoning/metering rounding and other account consumption may change result. |
| Z.ai GLM 4.7 Flash | $0 published marginal token price | Quota numeric ceiling/queue/response cap unverified; cannot calculate assured daily runs. |
| OpenRouter pinned Nemotron Ultra `:free` | 1 full request of **50 free requests/day** | Count-based allowance, **not** proof of provider token capacity, uptime or valid JSON. |
| Mistral Small 4 Free | 26K is under nominal 256K context | Actual free monthly allowance and TPM unknown; check account Limits. |

**Paid-fallback unit economics (USD, no caching, illustrative 10K in + 16K out)**: Groq GPT-OSS-120B **$0.0111/request** ($0.15/M in, $0.60/M out); Cloudflare GLM 4.7 Flash **$0.007005/request**, but Workers Paid subscription minimum **$5/month** and free 10K neurons/day remain included; Mistral Small 4 **$0.0111/request** ($0.15/M, $0.60/M). Z.ai GLM 4.7 Flash **$0 listed**, which does not guarantee no throttle; GLM 4.7 FlashX paid alternate at $0.07/M in, $0.40/M out would be **$0.0071/request**, but is a *different model*. OpenRouter paid fallback cannot be priced generically; pin paid model and retrieve its live pricing, plus platform credit fees. These are **theoretical**, exclude retries, cache, tax, model migrations, and multi-call fallback, and say nothing about editorial quality. [Groq model prices](https://console.groq.com/docs/model/openai/gpt-oss-120b), [Mistral prices](https://docs.mistral.ai/inference/pricing), [Z.ai prices](https://docs.z.ai/guides/overview/pricing), [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [Cloudflare July plan requirement](https://developers.cloudflare.com/changelog/post/2026-07-28-models-require-workers-paid/).

## Portable spike and #72 contract

The transport spike lives **only** at `research/free_ai_providers/spike.py`; it has no production imports, workflows, behavior changes, keys, or network activity until `--live` is explicitly specified. It uses **one request, no retry** to preserve real 429 evidence, a configurable 240-second timeout, and short sanitized metrics including HTTP code, rate-limit headers, token usage, JSON validity, section shape, exact Following key/order preservation and latency. **Not measured:** factual accuracy, deduplication, ranking, sensitive-data labeling, current titles, omissions or quality of editorial analysis. Those use **#72's rubric/human adjudication**.

Do **not** add a competing fixture format to the repository. The spike accepts either:
- `{ "fixture_id": "busy-canada", "system_instruction": "...", "user_content": { "stories": [...], "following": [...] } }`; OR
- `{ "fixture_id": "busy-canada", "request": { "messages": [{"role":"system","content":"..."},{"role":"user","content":"..."}] } }`.

This is an **interchange format, not #72's owned canonical schema**. Any #72 generator can export its exact system and serialized user content without changing benchmark fixture ownership. Following key/order test works if the user message contains `{"stories":[...],"following":[...]}`. On #72 agreement, compare against **identical serialized prompt**, date, news items and expected outcomes; adjust this adapter *only* if their final shared fixture schema requires it. Document provider-specific changes in the result metadata.

```bash
# Run deterministic tests from repository root. No provider keys required:
python -m pytest research/free_ai_providers/test_spike.py -q

# Local preflight only: --live is absent and NO API call occurs:
python -m research.free_ai_providers.spike \
  --fixture /path/to/72-export.json --provider cloudflare --require-full-size

# Opt-in full-size one-call test. Use synthetic/rights-cleared #72 fixture only.
# Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in the environment.
# Output contains sanitized summary/usage, NOT model text or secrets.
python -m research.free_ai_providers.spike \
  --fixture /path/to/72-export.json --provider cloudflare \
  --require-full-size --live --result /tmp/hermes-cf77.json

# Other credential names: ZAI_API_KEY, GROQ_API_KEY,
# OPENROUTER_API_KEY, MISTRAL_API_KEY.
# For a specific model, pass --model <exact-version-slug>.
# Use --json-mode only if the particular model supports JSON-object mode.
```

Do **not** commit `/tmp/hermes-*.json` blindly: although the spike omits prose, runtime metadata still deserves review. Never commit API keys, network headers with credentials, raw provider responses, private article metadata or licensed prose. Tests use fake synthetic articles only.

### Results and remaining acceptance gates

| Validation | Actual result as of 2026-10-22 |
|---|---|
| Public-doc provider research | **Five** families evaluated; recurring vs promotional explicitly separated. |
| Repository code-path inspection | **Completed**: one request, max 60 candidate stories, max 16K output, optional Following. |
| Account credentials available in this research execution environment | **None of** `ZAI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`, `CLOUDFLARE_API_TOKEN` were exposed. GitHub Actions secret availability was **not** inspected or probed. |
| Live provider request / full 60+Following replay | **Not performed**. Consequently **no provider production-ready**, no latency/JSON success percentages, no observed 429s or paid token usage claimed. |
| Model/editorial results vs #72 | **Pending identical fixtures and measured outputs**; no fabricated quality scores. |
| Deterministic contract tests | `research/free_ai_providers/test_spike.py`, executed in this PR's CI; report workflow result in PR checks. |

**Go/no-go gate before #73:** for each shortlisted candidate, perform at least 3 rights-cleared full-size 60+Following runs at requested 16K output cap on distinct challenging #72 fixtures, repeated twice where quota permits; record HTTP status, quota/429, provider model/version, prompt and completion counts, finish_reason, elapsed time, JSON/schema, Following-key integrity and editorial scores (especially numeric fidelity, Canadian recall, current titles, Opinion argument fidelity, lead analysis and ranking). Include a real 06:00 Toronto build-time latency budget and failure recovery simulation. Do not deploy without owner selection, free tier/terms confirmation and rollback procedure.

**Recommendation remains: Gemini-only for production pending evidence.** #77 has no basis for a migration recommendation beyond prioritizing live experiments; #73 is the only prospective production change.

# Hermes editorial benchmark fixture contract (v1)

Owned by #72. Shared read-only input contract for #77. Do not change these fields in parallel provider branches; propose a versioned change to #72 instead.

Location: `research/gemini/fixtures.json`. JSON object with `schema_version: 1`, `description`, and `cases`. Every case has:

| Field | Type | Semantics |
| --- | --- | --- |
| `id` | string | Stable lowercase kebab-case identifier |
| `origin` | string | `synthetic_public_metadata_hypothetical` for present cases; distinguish a real captured pool when later supported |
| `description` | string | What failure mode the case stresses |
| `date` | ISO date | Fixed edition date; affects Canadian priority and officeholder instructions |
| `stories` | object[] | Upstream normalized editorial candidates, **before** production cap/trim, ordered exactly as supplied |
| `following` | object[] optional | Already-selected immutable Following records, not selectable editorial candidates |
| `reference` | object | Human-authored, incomplete expectations; not a full ideal edition |

Each story includes the **seven actual model-visible** fields `title`, `description`, `source`, `section_hint`, `pub_date`, `image`, `link`; optional source-only fields (e.g. `coverage_lane: "canada-national"`) are permitted to exercise the exact production trim. The runner uses `src.curate._trim_input` then `_curation_view`; source-only fields **do not** get sent to the model except production's transient active-event priority. A story URL is a unique, inert `https://example.org/hermes-fixture/<case>/<item>` identity, not a live publisher address. Cross-publication repeats use different links within `duplicate_groups`.

Following records use **exact** production model-input names `key`, `headline`, `description`, `author`, `publication`, `published_at`, `link`, and are never ranked or silently dropped. A runner must use the production Following instruction alongside the usual prompt.

## `reference` fields

- `must_select: [url]`: important distinct articles that normally merit inclusion; **denominator is explicit**; not a promise all can fit when capped.
- `must_omit: [url]`: clear low-information/stale/publisher-duplicate candidates that should not be selected.
- `section_by_link: {url: section}`: expected preferred section (five editorial section IDs: `front`, `toronto`, `world`, `business`, `opinion`).
- `duplicate_groups: [[url,...]]`: at most one story from each group should survive; *different URLs, same underlying development*.
- `ranking_pairs: [[higher_url, lower_url]]`: relative cross-desk priority, evaluated **only when both** appear; report denominator, never treat omitted comparator as a ranking win.
- `facts: [{"link":"...","text":"..."}]`: literal anchor that should appear in selected story prose. This is an explicitly weak, case-insensitive proxy, **not a claim-verification system**.

All unmentioned candidates are *not* automatically negatives. Position expectations are editorial hypotheses and can be disputed or changed after blind review; do not train on a single grader's expected output.

## Provenance and limitations

All 13 current cases and 136 records are **constructed, hypothetical metadata**. They are useful for *controlled editorial regressions*, not estimates of live daily accuracy. Cases cover Canadian recall, the bounded Canada Investment Summit window, Toronto versus national, Following, financial arithmetic, provisional geopolitical claims, repeated feeds, sparse metadata, crime sensitivity, market causal language, quiet cycles, officeholder date grounding and 65-to-60 trimming. Descriptions are original synthetic text, with no licensed publisher bodies, paywalled text or hidden user data. `data/fixtures/edition_sample.json` and archived published HTML are output examples and **must not** be represented as captured model inputs.

Future captured pools must include capture timestamp, source provenance, publication licenses/permissions and SHA-256, plus the **exact post-suppression pre-trim** normalized set and fixed date/Following selections. Never reverse-engineer candidates from published HTML. Freeze old fixture versions; adding real captures is additive and requires review for personal data and publisher rights.

## Output adapter for #77

Cross-provider adapters should consume a resolved case using `request_payload(case)` or an equivalent byte-preserving JSON serialization of its returned `payload` and identical `system_prompt`. Record the full model response, raw API token metadata and settings without secrets. Run the shared `validate_output(case, parsed)`; attribute errors by provider and do not modify fixture/rubric files. `response_mime_type="application/json"` is the *production contract*, not a strict generated JSON schema; the offline evaluator checks the actual returned content separately.

Offline inspection: `python -m research.gemini_benchmark validate` and `python -m research.gemini_benchmark plan`.

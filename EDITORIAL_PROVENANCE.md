# Daily editorial evidence (schema v1)

Issue [#74](https://github.com/BenWassa/Hermes/issues/74). The evidence
ledger is **observability**, not a second editorial system. No extra Gemini call
is made, and neither publication nor the one-edition/one-notification gate
depends on evidence collection.

## Storage, identity and retention

A successful Daily build atomically writes one file:

`data/edition_evidence/YYYY/MM/YYYY-MM-DD.json` (Toronto calendar date).

The workflow stages that file, if present, in the **same git commit** as
`docs/index.html`. Read the publication commit with
`git log -1 --format=%H -- data/edition_evidence/YYYY/MM/YYYY-MM-DD.json`;
it must be the commit that published that day's HTML. Self-embedding the commit
SHA would change the commit hash, so `publication.commit` deliberately says
`same_git_commit_as_page`. `publication.page_sha256` is calculated from the
rendered HTML and can be verified using `git show COMMIT:docs/index.html`.
`build_started_utc` and the GitHub Actions run ID/attempt, when available,
identify the generation attempt without claiming that the current HEAD page
still represents an earlier edition.

One file is created **once per day**; existing evidence is never overwritten.
Git rebase/push retries reuse the same staged evidence and page. A resumed,
already-published run does not fetch, call Gemini or change evidence. The
evidence writer uses fsync, a same-directory temporary file and atomic rename.
If evidence fails, the Daily still publishes HTML; an absent ledger is *missing
evidence*, never proof that the edition failed.

Each record has a hard **128 KiB** UTF-8 ceiling, up to **240** full candidate
metadata rows, **12** provider attempts and **40** exact-duplicate groups.
Candidates not stored are counted. If the incoming pool exceeds the candidate
bound, actual model-input observations are preferentially retained, and the
remainder are summarized by counts. Headers, excerpts and identifiers have
individual field limits. Daily generation does not prune historical entries:
records remain in the repository and Git history unless a separate, reviewed
retention policy is adopted. At the hard cap, a year is under 46 MiB of
uncompressed new evidence content.

The JSON schema is additive/versioned; never silently interpret an older
version as current. Example:
[`data/fixtures/editorial_evidence_example.json`](data/fixtures/editorial_evidence_example.json)
is **synthetic**, not production model telemetry.

## Read contract for scheduled ChatGPT Sentinel

Read `data/edition_evidence/YYYY/MM/YYYY-MM-DD.json` from the appropriate
publication commit or branch. `src.editorial_provenance.read_evidence(path)`
returns one of four explicit states:

| Status | Meaning |
|---|---|
| `available` | Valid v1 published record; `evidence` includes counts, candidates, model and outcomes |
| `missing` | File absent; do not infer anything about editorial quality |
| `unsupported_version` | Schema not v1; inspect/migrate intentionally |
| `invalid` | Malformed JSON or structurally invalid record |

Suggested per-edition analysis: compare `counts.raw_fetched` with
`counts.normalized`, `after_following`, `after_sports`,
`curation_eligible`, `sent_to_model`, and `editorial_final`; inspect
`duplicate_groups`, `model_input_observation_ids` and
`final_editorial_sources`, alongside `final_unmatched` and
`candidates_omitted`. The omission labels are deterministic pipeline
classifications only. In particular, `model_input` without
`final_selected` **does not establish why** Gemini excluded the article:
ranking, editorial omission and final schema/cap postprocessing are not
separable without an independent rubric.

`model.attempts[]` captures requested/attempted/actual model names, fallback
status, retry index, per-attempt duration, provider status code, configured
thinking budget, and provider-reported token counters. Token counters can be
missing; do not replace missing values with zeros. `json_parse_outcomes[]`
distinguishes valid JSON from invalid JSON and empty model responses. Prompt
and schema are represented by SHA-256 fingerprints, **not the prompt text**.
The SDK package version is captured if installed.

Source health: `raw_by_provider` counts *returned candidates*, not successful
requests. The existing fetcher isolates individual provider errors and reports
them in Actions logs; the ledger intentionally says
`complete_with_source_level_outages_unreported` and does **not** infer that a
provider was healthy or absent from a zero count. Investigate the build log
for partial outages. A failed/non-published build is reflected in Actions,
not incorrectly written as a successfully published edition record.

## Privacy and reliability boundaries

- Store only publisher headline and up to 100 characters of sanitized public
  description metadata, provider IDs, safe canonical URL without query or
  fragment, timestamps, safe flags and hashes. No article bodies.
- Suspicious imperative/prompt-injection patterns are replaced by
  `[withheld]`; HTML markup has already been removed by normalization.
- Never store API keys, provider response bodies, full prompts, model JSON
  output, chain-of-thought, tool traces or hidden reasoning. Reasoning **token
  counts** from provider usage metadata are permitted; reasoning text is not.
- Unmatched final links are explicit; never manufacture source attribution.
  Following and Sports remain their existing deterministic independent desks.
- `.github/workflows/build.yml` and `ci.yml` ignore evidence-only commits
  for new build/recovery cycles. Only the main Daily workflow writes
  publication evidence. The public GitHub repo, not the Pages site, is the
  read surface. Do not couple Sentinel failure to edition publication.

## Verification

Run the offline suite with `python -m pytest` (plus
`python -m src.voices.audit`) and inspect CI. No provider key is required
and tests do not make live model calls. The output file is created only
after a successful render; generated source telemetry does not change the
default `CURATE_MODEL` value.

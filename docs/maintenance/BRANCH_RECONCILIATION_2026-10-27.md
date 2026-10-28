# Branch reconciliation — 2026-10-27

Reconciled all branches fetched from origin against main at `fe70a6c`.

## Integrated

- PR #79 (`research/gemini-benchmark`, `ea72c63`): offline benchmark harness, 14 synthetic fixtures, rubric, tests and cross-provider exporter. Live model measurements and independent blind review remain outstanding under #72. Model IDs and prices must be reverified before live execution; no production model change is authorized by integration.
- PR #99 (`feature/voices-editorial-visuals`, `2e2c084`): weekly reading hierarchy and legacy article summary presentation. Weekly selection and source facts remain authoritative. Generated published pages are refreshed by their normal publication workflows.
- `feature/crucix-integration-v2` (`0471d6b`): preserved the v2 proposal in `archive/v1-hermes/CRUCIX_INTEGRATION.md` using Git's rename-aware merge. Marked it archived rather than treating its obsolete Node pipeline as an active Daily implementation plan.

## Already integrated

These remote branches belong to merged PRs. Compared all files touched by each branch against current main; remaining differences are later main improvements, not omitted branch work.

| Branch | Merged PR |
| --- | --- |
| fix/raptors-record-reconciliation | #100 |
| fix/canada-eligibility-recall | #101 |
| fix/editorial-source-metadata-integrity | #102 |
| docs/quality-issue-spec-hygiene | #104 |
| fix/editorial-high-impact-facts | #105 |
| feature/independent-morning-dispatch | #106 |
| fix/dispatch-origin-safe-env | #107 |

Remote branches are retained for traceability; replaying their pre-squash histories is unnecessary.

## Intentionally separate

`sentinel/reviews` (`64d6992` at inspection) is the independently maintained scheduled audit ledger established under #76. Its README defines separate report owners and branch-targeted compare-and-swap writes. Retained that branch without merging its mutable audit ledger into production. Its existence is not unfinished production integration.

## Validation

- Full deterministic and rendered-browser suite: **795 passed** locally (Python 3.14).
- Voice registry audit: passed, dry run.
- Gemini fixture validation: 14 fixtures; offline plan: 112 planned calls, **0 API calls**.
- Exported synthetic full-size case and ran #77 Cloudflare transport preflight: 60 ordinary stories plus 2 Following seeds, 34,319 UTF-8 input bytes, no live request.
- Chromium review: weekly and article pages at 360, 390, 412 and 1280 pixels, light and dark, 125% root text: 16 cases passed with no horizontal overflow and primary links at least 44 pixels tall. Screenshots remain in ignored `test-artifacts/branch-integration/`; inspected representative phone screenshots.
- Diff whitespace check: passed after normalizing imported trailing whitespace.

No live news build, model benchmark spending, notification, worker deployment or production model migration was performed.

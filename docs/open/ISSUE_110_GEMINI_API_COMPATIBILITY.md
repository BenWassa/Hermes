# Issue #110 — Gemini v1beta curation compatibility

- GitHub: https://github.com/BenWassa/Hermes/issues/110
- Sentinel: HQA-012 (do not change this ID)
- Status: implementation PR pending merge and live verification
- Scope: existing Gemini 2.5 Flash curation only. Not a provider/model migration (#73).

## Reproduced evidence

Nov 10 Actions run 42824448083, job 129857963311, installed `google-genai-3.0.0` from unbounded `google-genai>=1.0`. Request POSTed `/v1/models/gemini-2.5-flash:generateContent` and failed 400 INVALID_ARGUMENT: "Developer instruction is not enabled for api version v1. Use api version v1beta instead." The job skipped publication. Nov 7 issue #110 recorded the same error. This does **not** establish that Nov 5 primary 503/fallback 404 has the same cause. The SDK default/version transition is an explanation supported by Google's current SDK documentation, but the exact date of default change is not reconstructed here.

## Fix

1. Explicitly construct the Gemini Developer API client with `types.HttpOptions(api_version="v1beta")`. Do not depend on SDK/environment defaults.
2. Pin the production SDK to the version observed in the failing build (`google-genai==3.0.0`) so CI and scheduled builds use the same SDK surface.
3. Test the effective API version in a fake client, even when `GOOGLE_GENAI_API_VERSION=v1`, and assert the real Hermès generate configuration still carries system instructions and JSON MIME type.
4. Keep existing primary/fallback model IDs, retry budget, temperature, token quota, Following/Sports contract and notification/publication gates unchanged.

## Acceptance and evidence

- [x] Failing November 10 request and installed SDK version independently verified from the production job log.
- [x] Code change explicitly overrides version for the existing `_client()` entrypoint.
- [x] Offline regression test protects the exact version + instruction/JSON request contract.
- [ ] CI green at PR head (record the run).
- [ ] Authenticated smoke against production-account primary and fallback, using existing secrets: **blocked** from this agent connection; do not print secrets or commit test data.
- [ ] Successful real Toronto-day edition, git commit, Pages availability and downstream notification: **blocked until owner-approved merge/recovery run**. A green CI alone is not proof.
- [ ] Confirm that #82 still independently handles 503/404 and that #92 remains a separate timing concern.

## Post-merge operator verification

Run one idempotent Build The Daily workflow only when a current-day edition is missing, within quota and the approved schedule. Verify log endpoint is `/v1beta/`, actual model ID, valid JSON, unique exact-date edition commit, Pages deployment linked to that SHA, and Notify workflow's published/no-op decisions. Do not manually bypass notification gating. Retain HQA-012 Open until verified. This spec remains in `docs/open/` until merged and production-verified.
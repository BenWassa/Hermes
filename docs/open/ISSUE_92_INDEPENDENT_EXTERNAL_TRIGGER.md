---
status: open
issue: 92
lane: publication-operations
owner: unassigned
updated: 2026-10-26
---

# Independent 06:00 Toronto publication trigger

**GitHub issue:** https://github.com/BenWassa/Hermes/issues/92

## Evidence and outcome

GitHub schedule delivery has repeatedly missed the intended ~06:00 Toronto
publication time. Monday 2026-10-26's edition committed at **07:04 EDT**, after
the GitHub build started at ~07:02; the ~34-second model inference was not the
cause of the 64-minute schedule miss. This is not a guarantee Cloudflare
eliminates lateness; it removes a single scheduler dependency.

The desired result is an independently triggered execution **around 05:35 and
05:50 America/Toronto**, with the existing GitHub build's `>=05:00` publication
floor, Toronto edition identity, one-edition gate, serialized concurrency and
notification idempotency intact.

## Implementation: staged, not activated

The deployable Worker is in `ops/external-dispatch/`:

- `worker.mjs` has a **scheduled-only** handler, no public HTTP listener or
  GitHub content-write API, and a hard-coded GitHub `build.yml` / `main` target.
- `wrangler.toml` has UTC cron slots `35,50 9,10 * * *`. The Worker
  converts scheduled **and actual** instants into America/Toronto and dispatches
  only at the true local 05:35/05:50 window for EST or EDT, up to 06:15 actual.
  The other UTC-hour pair is a no-op. Different-date or stale invocations skip.
- At most two GitHub dispatch attempts for transient 429/5xx; never retry 401,
  403 or other terminal failures. No token values or response bodies in logs.
- The existing GitHub workflow keeps all publishing authority. Its optional
  `workflow_dispatch.inputs.trigger_source` is an **audit-only** choice, not a
  substitute for the edition-existence gate. Cloudflare sends the
  `cloudflare` label; manual workflow runs default to `manual`.
- `tests/test_external_dispatch_worker.py` runs the Node test suite when Node
  is available and asserts build's existing gate/concurrency remain. The Node
  suite covers EST/EDT, transition days, late/different-date calls, HTTP 204,
  bounded retries, missing/invalid credentials and off-window no-op.

**Status:** PR scope is code/documentation/test readiness. Nothing has been
deployed into the user's Cloudflare account or connected to GitHub externally.
The presence of files in main does **not** create a new scheduled job.

## Activation decision and steps (external owner action)

1. Approve **Cloudflare Workers Cron Triggers** as the independent scheduler
   and authorize a narrowly scoped external credential. Create a GitHub
   **fine-grained personal access token** with only
   `BenWassa/Hermes`, permission **Actions: read/write**, no repository
   Contents write, and a short expiration. Confirm workflow-dispatch scope
   is allowed by organization/repository policy.
2. Authenticate Wrangler to the intended Cloudflare account, from the
   `ops/external-dispatch` directory. Store the token as a Worker **secret**:
   `npx wrangler secret put GITHUB_DISPATCH_TOKEN`, entering its value in
   Wrangler's secure prompt rather than in a shell argument or tracked file.
   Then `npx wrangler deploy`. Review the account's active Cron Triggers and
   logs. Cloudflare may require creating/configuring the Worker before its
   secret can be set: use the Cloudflare dashboard's Secrets control in that
   case and keep Cron disabled until the secret is provisioned.
3. **Before enabling the Cron**, run offline
   `node --test ops/external-dispatch/worker.test.mjs` and full pytest/CI.
   Do not invoke a **real** `workflow_dispatch` before 05:00 for a missing
   edition merely as a test. After activation, verify the scheduled event,
   `workflow_dispatch` run label, correct Toronto edition SHA and exactly
   one notification. The token itself must never appear in logs.
4. Keep existing GitHub hedge schedules as backup until **14 observed days**
   show publication by 06:30 Toronto on at least 90% of days, with no
   duplicate edition or notifications. Record scheduled-versus-actual starts
   and the exact trigger source; don't infer device notification receipt
   from workflow success alone.

## Incident response, rotation, rollback

- GitHub 401/403: treat as expired/revoked permission; do not broaden token
  scopes. Rotate only the Worker secret after owner confirmation.
- GitHub 429/5xx: two bounded worker attempts; underlying GitHub hedges remain.
  Successful dispatch (HTTP 204) means *accepted*, not publication completed.
- Deployment or token leak: revoke the PAT in GitHub, remove/disable the
  Cloudflare Cron Trigger and rotate secret. `npx wrangler secret delete
  GITHUB_DISPATCH_TOKEN` after disabling active triggers.
- Rollback: remove the Cron Triggers (`crons = []`, deploy), or disable the
  Worker in Cloudflare; GitHub manual and hedge schedules continue unchanged.
  An inert repository file cannot dispatch work itself.

## Done when

- [x] Dependency-free scheduled-only Worker, narrow target, safe runtime and
  typed-clock gating.
- [x] UTC DST-envelope + independent trigger source telemetry.
- [x] Deterministic no-network/response/error unit tests integrated into CI.
- [ ] Owner approves external scheduler and token hosting.
- [ ] Actual Cloudflare deployment, secret, trigger and a real 204 acceptance
      recorded without exposing credentials.
- [ ] Confirm external trigger produces a *single* correct edition and notify.
- [ ] Fourteen observed days meet the 06:30 punctuality bar; stop or revise
      if this is not achieved.

## Primary documentation

- [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
- [Cloudflare Worker Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
- [GitHub workflow dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)

Related: #68 GitHub-only hedge, #82 degraded model fallback,
#94/#95/#96 editorial correctness. No model setting or additional publisher
provider call changes.

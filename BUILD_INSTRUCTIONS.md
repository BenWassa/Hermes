# The Daily — Production Build and Operations

**Repo:** `BenWassa/Hermes`  
**Product authority:** `PRODUCT.md`, `PRD_daily_newspaper.md`  
**Operational summary:** `README.md`

This file describes the **current production contract** for the morning Daily.
It is not a historical scaffold or a greenfield implementation sequence.

## 1. Product outcome

Hermes publishes one Toronto-calendar morning newspaper per day to GitHub Pages
and sends at most one morning ntfy notification after a successful publication.

The normal publication target is the **05:00 America/Toronto hour**, with 05:17
as the first intended attempt. Normal completion should be before 06:00 local,
with bounded same-morning recovery if GitHub Actions delays or drops a run.

The finished paper retains the existing visible desks and product authorities.
Sports remains deterministic and outside the ordinary Gemini-owned story pool.
Canada-national intake is an internal coverage lane, not a separate rendered
Canada section.

## 2. Morning pipeline

```text
Toronto weather
→ bounded news/source fetches
→ normalize + canonicalize/dedupe
→ deterministic Voice discovery / Following ownership
→ deterministic Sports desk
→ bounded Canada-national / scheduled-major-event recall
→ one ordinary Daily Gemini curation call
→ image/sensitivity handling
→ static HTML render
→ durable git publication
→ one notification tied to the producing build run
```

Content availability must degrade locally. A failed RSS/provider/structured
Sports source must not prevent publication when the remaining inputs are usable.

## 3. Scheduling and recovery authority

`.github/workflows/build.yml` is the executable authority.

### Scheduled publication

Use ordinary **UTC cron**, not GitHub's timezone-aware schedule path:

```yaml
- cron: "17,47 9-12 * * *"
```

This UTC envelope covers the required Toronto morning under both EDT and EST.
Immediately after checkout, the workflow computes `America/Toronto` local time.
Only scheduled attempts in **05:00–07:59 Toronto** may proceed. Outer UTC slots
that exist only for DST coverage stop before Python setup, provider requests or
Gemini work.

The first useful slot is 05:17 local. The half-hour cadence supplies multiple
bounded recovery opportunities without duplicating editions or model calls.

### Main-push recovery

A meaningful code/config push to `main` may recover a missing edition during
**05:00–11:59 Toronto**. Generated/operational paths are excluded from this
trigger, including:

- `docs/index.html`;
- `data/voice_watch_state.json`;
- `data/voice_roundup_state.json`;
- `docs/voices/**`.

This makes a real morning merge an opportunistic recovery signal without
creating recursion from the edition commit or routine Voice-state noise.

### Manual recovery

`workflow_dispatch` remains available at any hour. Manual runs ignore automatic
time-window restrictions but still obey the edition-exists gate.

Do **not** add a direct manual notification bypass. Recover by dispatching
`Build The Daily`; notification remains downstream of the build result.

## 4. Idempotency and write safety

Every scheduled, push-triggered and manual attempt checks git history for the
exact Toronto-calendar edition commit:

```text
chore(edition): publish YYYY-MM-DD edition
```

If it exists, the run stops before Python setup, dependency installation,
provider fetching or Gemini work.

The Daily uses its own non-cancelling concurrency group. Publication retries a
bounded fetch/rebase/push sequence so independent Voice state/page writers do
not cause a lost edition.

At most one build should perform provider/model work for a date after the first
edition has become durable.

## 5. Production credentials

The morning build receives repository secrets through environment variables.
Never hardcode credentials.

Required/active production variables include:

- `GEMINI_API_KEY` — the single ordinary Daily curation call;
- `GUARDIAN_API_KEY` — Guardian news and relevant discovery;
- `NYT_API_KEY` — NYT morning pool;
- `PERIGON_API_KEY` — bounded Perigon intake, including the Canada-national lane;
- `NTFY_TOPIC` — used only by the downstream notification workflow;
- `PAGES_URL` — repository variable for published links where required.

Other configured providers remain subject to their existing bounded/fail-soft
contracts. Absence or failure of one optional source must remain local.

## 6. Canada-national coverage contract

The Daily must reliably surface major Canadian national political/economic
stories without adding a visible Canada desk.

The production path uses:

- a dedicated bounded Canada Perigon lane;
- one CBC Canada RSS journalism source;
- bounded scheduled-major-event recall;
- deterministic preservation of a small number of strong Canada-national/event
  candidates inside the existing curation-input ceiling.

`coverage_lane` is intake metadata and is not sent to Gemini. There is no new
Daily model call and no broad provider-page-size expansion.

## 7. Sports contract

Sports is a first-class rendered tab but not an ordinary Gemini-owned section.
Structured team/event state and targeted significant headlines are assembled
deterministically. Sports contributes zero records to the Daily Gemini prompt.

The permanent Toronto priority is:

```text
Maple Leafs → Raptors → Blue Jays
```

Major-event handling follows the current Sports V2 authority documents.

## 8. Voice independence

The morning Daily, silent Core collection and weekly Voice digest are separate
operational products with independent concurrency/state/write paths.

The Daily must not write Voice roundup state or weekly pages. Daily collection
remains model-free. The weekly Voice path may perform at most one grounded
screening/synthesis model call and is the sole proactive Voice notification.

## 9. Notification correctness

`.github/workflows/notify.yml` runs after `Build The Daily` completes.

It may notify only when:

1. the triggering build concluded successfully;
2. today's Toronto-calendar edition exists; and
3. the edition commit timestamp proves that **this build run** produced it.

A later scheduled/push/manual no-op therefore cannot send a second morning push.

## 10. Verification gate

Before merging any Daily workflow/runtime change:

```bash
pip install -r requirements-dev.txt
python -m src.voices.audit
python -m pytest
```

CI must keep the deterministic + rendered-browser suite green.

Workflow tests must explicitly protect:

- UTC schedule shape and Toronto local-time gate;
- bounded push recovery and generated-path exclusions;
- unrestricted manual recovery;
- edition-exists gating before providers/Gemini;
- production provider credential wiring, including Perigon;
- independent non-cancelling Daily/Voice concurrency;
- bounded git retry/rebase publication;
- at-most-one morning notification.

Live source probes are deliberate operator actions, not routine CI dependencies.

## 11. Incident procedure

When an edition is missing:

1. Check whether a `Build The Daily` run was instantiated at all.
2. If no run exists, treat it as scheduler/recovery failure, not a provider or
   Gemini failure.
3. If a run exists, inspect its gate and failing stage before changing sources.
4. Use `workflow_dispatch` for immediate recovery when needed.
5. Confirm the edition commit exists and Pages deployment succeeds.
6. Confirm only the producing run generated the morning notification.
7. Preserve concrete run IDs/timestamps in the relevant GitHub issue before
   changing scheduling architecture.

Do not compensate for scheduler failure by removing idempotency, increasing
Gemini calls, or creating a second notification path.

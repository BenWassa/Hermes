# The Daily — Production Build and Operations

**Repo:** `BenWassa/Hermes`  
**Product authority:** `PRODUCT.md`, `PRD_daily_newspaper.md`  
**Operational summary:** `README.md`

This file describes the **current production contract** for the morning Daily.
It is not a historical scaffold or a greenfield implementation sequence.

## 1. Product outcome

Hermes publishes one Toronto-calendar morning newspaper per day to GitHub Pages
and sends at most one morning ntfy notification after a successful publication.

The Daily should normally be **available by approximately 06:00
America/Toronto**. Automatic publication must not occur before 05:00 local.
The first on-time useful slot remains 05:17, but the bounded schedule also
contains earlier nominal hedge slots because GitHub has repeatedly delivered
scheduled events 3.5–4.5 hours late. Prompt hedge deliveries no-op before
provider/model work; delayed hedge deliveries may become the 05:00–06:00
publication attempt.

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
- cron: "17,47 5-12 * * *"
```

This bounded UTC envelope starts several hours before the publication floor and
continues through the existing recovery period under both EDT and EST. In summer
the first nominal slot is about 01:17 Toronto; in winter it is about 00:17.
Immediately after checkout, the workflow computes the current
`America/Toronto` calendar date and local time.

Scheduled attempts that actually start **before 05:00 Toronto** stop before
Python setup, provider requests or Gemini work. At or after 05:00, there is no
scheduled upper-hour veto: if today's exact Toronto-calendar edition commit is
still absent, a delayed scheduled run may recover it regardless of how late
GitHub eventually starts that run.

The first on-time useful slot is 05:17 local. Earlier half-hour slots are
deliberate delivery hedges: if GitHub starts them promptly they no-op before
Python/provider/Gemini work, while a multi-hour-delayed hedge may land inside
the desired 05:00–06:00 publication window. The cadence remains bounded rather
than becoming an all-day poll.

### Main-push recovery

A meaningful code/config push to `main` may recover a missing edition during
**05:00–11:59 Toronto**. Generated/operational paths are excluded from this
trigger, including:

- `docs/index.html`;
- `docs/open/**`;
- `docs/closed/**`;
- `docs/ISSUE_TRACKING.md`;
- `data/voice_watch_state.json`;
- `data/voice_roundup_state.json`;
- `docs/voices/**`.

This makes a real morning merge an opportunistic recovery signal without
creating recursion from the edition commit, issue-document housekeeping, or
routine Voice-state noise.

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

A build that passed the missing-edition gate but produced no `docs/index.html`
change is treated as a build failure rather than a successful no-op. This keeps
a stale Daily from being hidden behind a green workflow conclusion.

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

`coverage_lane` remains intake-only metadata and is not sent to Gemini. For an
article that actually matches an **active configured scheduled major event**, the
curation boundary may add one transient `editorial_priority` field naming that
event. That field exists only in the already-bounded Gemini payload; it is not a
normalized-story or final-edition schema field.

The single editor call should normally retain at least one credible current
treatment of an explicitly marked active event. Stale reporting, a stronger
included duplicate, insufficient source metadata, or an event that materially
failed to occur remain valid reasons to omit it. Hermes never manufactures a
story from the schedule seed itself.

After curation, production logging records each matched active event's input
candidate count, selected count and selected desk(s). This distinguishes
pre-model recall failure from final editorial omission without adding another
model call or deterministic prose fallback.

There is no new Daily model call, no increase to the curation-input ceiling and
no broad provider-page-size expansion.

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

## 10. Actions outcome observability

Every Daily run writes an explicit summary containing the Toronto date, trigger,
Toronto gate time, whether the edition already existed, final outcome, and job
status.

Normal outcomes are:

- `published`;
- `already-published-noop`;
- `pre-05-scheduled-noop`;
- `push-window-noop`;
- `build-failure`.

A legitimate no-op may still have an overall Actions conclusion of `success`,
but the summary must state why nothing was published. A missing-edition build
that fails to produce an edition is not a legitimate no-op and must fail.

## 11. Verification gate

Before merging any Daily workflow/runtime change:

```bash
pip install -r requirements-dev.txt
python -m src.voices.audit
python -m pytest
```

CI must keep the deterministic + rendered-browser suite green.

Workflow tests must explicitly protect:

- bounded UTC hedge schedule, including pre-05 nominal slots and the 05:00 Toronto execution floor;
- delayed scheduled recovery with no post-05 upper-hour veto;
- Toronto date-boundary and DST semantics;
- bounded push recovery and generated/issue-doc path exclusions;
- unrestricted manual recovery;
- edition-exists gating before providers/Gemini;
- explicit publication/no-op Actions outcomes;
- production provider credential wiring, including Perigon;
- independent non-cancelling Daily/Voice concurrency;
- bounded git retry/rebase publication;
- at-most-one morning notification.

Live source probes are deliberate operator actions, not routine CI dependencies.

## 12. Incident procedure

When an edition is missing:

1. Check whether a `Build The Daily` run was instantiated at all.
2. If no run exists, treat it as scheduler/recovery failure, not a provider or
   Gemini failure.
3. If a run exists, inspect its **Daily run outcome** summary and failing stage
   before changing sources.
4. Use `workflow_dispatch` for immediate recovery when needed.
5. Confirm the edition commit exists and Pages deployment succeeds.
6. Confirm only the producing run generated the morning notification.
7. Preserve concrete run IDs/timestamps in the relevant GitHub issue before
   changing scheduling architecture.

Do not compensate for scheduler failure by removing idempotency, increasing
Gemini calls, or creating a second notification path.

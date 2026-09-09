# Weekly Core Voices Roundup — architecture plan

Status: **Wave 1C design/research only. No production behavior is changed by this note.**

Baseline reviewed: `main` at `91e25e6a305c3f90ad74951fc43df33841004981` (2026-09-07), including #12 / PR #16, #13 / PR #18, and the later #17 / PR #19 source restoration.

This note designs the smallest robust replacement for routine per-article Voice alerts. It assumes the separate Voices V2 product-authority work will define the canonical **Core / Selective / Discovery** roster semantics. It does **not** define or modify that roster.

## 1. Recommendation

Replace the release-time Voice notification product with one bounded weekly catch-up product:

```text
once daily, after the morning edition
    Core-only Voice discovery
    -> resolve authorship + canonical identity + syndication
    -> merge into a small 14-day repository-backed accumulator
    -> mark articles that appeared in that morning's committed edition
    -> no notification

Sunday early evening, America/Toronto
    load trusted accumulator
    -> one cheap final discovery pass
    -> deterministic Core-only selection, maximum 6
    -> render one current static roundup page
    -> durably claim that weekly period + publish page
    -> send one compact ntfy notification linking to the roundup
```

The initial implementation should make **zero additional Gemini calls**. Selection is deterministic. The weekly page is a single current artifact, overwritten each week; it is not an archive, unread system, or second feed.

This preserves the strongest parts of #12 — canonical identity, cross-run syndication matching, bounded repository state, compare-and-swap git persistence, source budgets, graceful partial failure, and claim-before-send idempotency — while deleting the part the product no longer wants: hourly polling for per-article interruption.

## 2. Why this shape

Three simpler-looking alternatives were considered and rejected.

### Weekly-only polling is too lossy

One seven-day fetch at the end of the week is attractive on cost, but RSS feeds and author indexes are bounded surfaces. A prolific source can age an earlier item out before Sunday, and a source outage on Sunday would erase an otherwise observable week. Hermes already has proven low-cost discovery machinery; a small daily overlap is a more reliable collector without becoming a feed.

### Piggybacking collection inside the morning build saves requests but couples correctness

`src.build` already has every fresh `VoiceArticle` before curation, so it could write weekly state for zero extra provider requests. That would make the edition build a writer of operational roundup state, however, undoing the clean separation established in #12. The build and roundup job could then race on the same state file, and a state problem could become entangled with the one workflow Hermes most needs to stay boring and reliable.

The extra daily Voice pass is a better trade: it keeps the morning build untouched, cuts notification-product polling by more than an order of magnitude versus the current hourly watcher, and lets state failures remain local to Voices.

### A notification containing 3–6 headlines is a miniature feed

The ntfy interruption should not carry the roundup itself. Direct-linking to only the first article would arbitrarily privilege one selection and make the other selected items inaccessible. The clean target is one finite static **current roundup** page at a stable Hermes URL, containing only that week's shortlist and direct publisher links. It is overwritten weekly and has no pagination or history.

## 3. Reuse versus replacement

### Retain

Reuse these current contracts essentially unchanged:

- registry-driven generic source planning;
- evidence-based Voice attribution;
- `VoiceArticle` canonical identity keys;
- `syndication_keys_for()` and the current reprint semantics;
- source batching and request budgets;
- local failure of one provider/source;
- repository-backed state;
- deterministic JSON serialization;
- git push as compare-and-swap, with reload/re-decide after a lost race;
- bounded pruning;
- ntfy JSON delivery at normal priority;
- the current smoke-test philosophy: live network proof is bounded and separate from deterministic CI.

### Replace or retire

The later implementation should remove these release-alert concepts rather than preserve them under new names:

- hourly scheduled polling;
- per-article `build_alert()` delivery;
- one terminal delivery status on every article (`pending`, `notified`, `failed`, `suppressed`, `adopted`);
- `VOICE_WATCH_MAX_ALERTS_PER_RUN`;
- the `notify` flag as the authority for participation in the notification product;
- the idea that the watcher exists to shorten release latency.

The separate V2 product-authority stream should provide the Core classification. This plan must consume that authority directly; **do not treat today's `notify: true` as a proxy for Core**.

## 4. Collection and state

### 4.1 What must survive across the week

A weekly shortlist needs more than the current claim log stores. For each observed qualifying article retain only:

- all canonical identity / provider / fingerprint / syndication keys needed for cross-run duplicate matching;
- matched `voice_ids`;
- `first_seen`;
- `published_at`;
- headline/title;
- the publisher URL used as the reader's outbound destination;
- publication display name;
- `first_morning_surfaced_at`, nullable.

Do **not** retain:

- article body;
- scraped protected text;
- AI summary;
- engagement/popularity data;
- unread/read state;
- image data;
- an endless list of old weekly selections.

Author display names do not need to be copied into state: resolve them from the current registry using `voice_ids` when rendering. This avoids stale naming metadata and keeps the accumulator small.

### 4.2 Can the existing bounded seen-state support this?

**The storage architecture can; the V1 schema cannot safely do so unchanged.**

`data/voice_watch_state.json` is deliberately a notification claim log. A `SeenEntry` has identity, Voice IDs, timestamps, delivery status, attempts and error, and tests explicitly prohibit headline/description/body fields. That is correct for at-most-once release alerts but insufficient to render a useful weekly shortlist after the original observation is gone.

The implementation should therefore introduce a roundup accumulator schema while reusing the current store/CAS ideas. Do not overload `status` to mean both article observation and weekly delivery.

Recommended active state shape:

```json
{
  "version": 1,
  "collecting_since": "2026-09-08T15:37:00Z",
  "updated_at": "2026-09-13T22:44:00Z",
  "last_reconcile_at": "2026-09-13T15:37:00Z",
  "last_roundup": {
    "period_id": "2026-09-13",
    "cutoff": "2026-09-13T21:00:00Z",
    "claimed_at": "2026-09-13T22:44:00Z",
    "status": "notified",
    "selection_keys": [
      "url:https://example.com/essay-a",
      "url:https://example.com/essay-b"
    ]
  },
  "items": {
    "url:https://example.com/essay-a": {
      "keys": [
        "fp:example.com|essay-a|2026-09-12",
        "syn:essay-a|voice:example-voice|2026-09-12",
        "url:https://example.com/essay-a"
      ],
      "voice_ids": ["example-voice"],
      "first_seen": "2026-09-12T15:37:00Z",
      "published_at": "2026-09-12T12:00:00Z",
      "title": "A useful essay title",
      "url": "https://www.example.com/essay-a",
      "publication": "Example",
      "first_morning_surfaced_at": null
    }
  }
}
```

`last_roundup.status` is the only delivery status required. Suggested states are `pending`, `notified`, `failed`, and `empty`. Any existing value for the current `period_id` means the period has been durably accounted for and must not send a second notification.

### 4.3 Observation is an upsert, not a claim

The current article claim is a one-way door because overwriting it could reopen a release alert. Weekly collection has a different semantic need: a later observation can legitimately enrich an already-known item.

An `observe()` operation should:

- match on any identity/syndication key using the existing state-index pattern;
- union new keys and Voice IDs;
- preserve the earliest `first_seen`;
- keep the canonical resolved publication timestamp;
- fill missing title / URL / publication from better evidence, using the same deterministic source preferences as Voice dedupe rather than observation order;
- set `first_morning_surfaced_at` once and never clear it.

The weekly **period claim**, not each article observation, is the one-way at-most-once door.

### 4.4 Should state record morning-edition appearance?

**Yes, as one nullable timestamp — not as read/unread history.**

“Already surfaced prominently this week” is one of the few deterministic signals available that directly serves the catch-up goal. It lets the roundup prefer work Hermes did not already place in front of the reader every morning, without inventing engagement scores.

The silent collector runs after the morning build. It should read the committed `docs/index.html`, extract the JSON from the existing `<script id="edition" type="application/json">` element, canonicalize the links in that exact edition, and mark matching accumulated Voice articles. This is preferable to estimating what *would* have been selected: it records what the user-facing artifact actually contained.

If today's edition is absent, stale, or unreadable, collection still succeeds and logs that the surface signal is unknown. `first_morning_surfaced_at` remains null. This field is a ranking preference, never a correctness gate.

### 4.5 Duplicate and syndication collapse

Use the exact identity machinery already proven by #10/#12:

- exact/canonical duplicates match on the union of canonical URL, provider IDs, normalized URL and bounded host fingerprint;
- cross-run reprints match on `syndication_keys_for()` / explicit reprint-group keys;
- one intellectual piece occupies one roundup slot even if two publishers ran it;
- distinct pieces by the same writer remain distinct.

Do not introduce title-only or author-only weekly dedupe.

### 4.6 Pruning

Keep the current **14-day retention** and **500-entry hard cap** initially. They are already proven and are comfortably larger than a seven-day roundup period while still being tiny for a Core roster. State now stores a few bounded public metadata strings, so implementation should bound title/publication/URL lengths during parsing/serialization as well.

Pruning remains based on `first_seen`, with newest entries surviving the hard cap. A seven-day selection window means material older than one period can remain briefly for cross-run dedupe but cannot re-enter a roundup.

No weekly archive is stored. `last_roundup` is one record, overwritten by the next period.

## 5. Daily silent collection

### 5.1 Cadence

Run once daily after the morning edition has had ample time to publish. A practical fixed UTC schedule is:

```text
15:37 UTC daily
```

That is 11:37 during Toronto daylight time and 10:37 during standard time. Exact local clock time is not product-visible; the important property is that it is comfortably after the morning build's current 04:17–07:17 local recovery window while remaining far from quiet hours.

Use a **48-hour overlapping discovery window**. The overlap tolerates a missed/delayed daily job or delayed source indexing; state identity makes the overlap free of duplicate accumulation.

### 5.2 Core-only source pressure

Before planning source requests, filter notification-product participation to the separately defined Core Voices. Selective and Discovery Voices must not cause a request merely because the roundup collector exists.

Shared source batches can naturally return other authors, but only Core-attributed items are retained for roundup state.

The daily run should keep the current provider-tier logic:

- cheap/direct sources can run on the daily pass;
- scarce providers participate only when `last_reconcile_at` says reconciliation is due;
- unknown future provider types default conservative.

There is no reason to poll Perigon a second time on Sunday evening if a successful reconciliation occurred that morning.

### 5.3 No notification in collection mode

Daily collection must not require `NTFY_TOPIC` and must not instantiate a notifier. A source discovery run that cannot send an interruption cannot accidentally regress into release alerts.

It also needs no Gemini key and should never invoke `src.build` or `src.curate`.

## 6. Weekly period and schedule

### 6.1 Recommended daypart

**Sunday early evening Toronto time** is the best first schedule.

Tradeoff:

- A weekday morning would compete with the existing edition push and make Voices feel like another daily obligation.
- Friday evening loses a meaningful part of the publishing week.
- Sunday late night violates the quiet character and current 23:00 quiet-hours principle.
- Sunday early evening captures most of the week, is clearly separate from the morning paper, and naturally supports “a few worth catching up on” before the next week begins.

This is a daypart recommendation, not a promise that a GitHub cron fires at an exact minute.

### 6.2 Fixed local cutoff

Define each roundup period in `America/Toronto`, with a **Sunday 17:00 local cutoff**:

```text
period_start = previous Sunday 17:00 Toronto, exclusive
period_cutoff = current Sunday 17:00 Toronto, inclusive
period_id = local date of period_cutoff
```

Construct those local datetimes with `zoneinfo` and then convert to UTC. Do not define a week as “168 UTC hours”; the DST transition week is not necessarily 168 local hours.

An article published after 17:00 Sunday simply belongs to the next roundup. Nothing is lost.

Fixed calendar periods, rather than “since the last successful notification”, also prevent a missed week from becoming a noisy 14-day backlog on the next successful Sunday.

### 6.3 Self-healing GitHub schedules

GitHub scheduled Actions are eventually-soon and can be delayed or dropped. Use multiple quiet no-op-safe attempts, offset from the top of the hour, and let the durable `period_id` claim decide whether work remains.

Recommended initial schedule:

```yaml
# UTC. Across EDT/EST these land Sunday roughly 17:43–20:43 Toronto.
- cron: "43 22 * * 0"
- cron: "43 23 * * 0"
- cron: "43 0 * * 1"

# One Monday early-evening fallback for the same Sunday period.
- cron: "43 22 * * 1"
```

The first successful Sunday attempt claims the period. Later attempts load state, see the same `period_id`, and stop **before provider requests**. If Sunday is completely missed, Monday targets the previous Sunday's cutoff and may publish that same period once.

After the Monday grace attempt, do not send a stale midweek roundup automatically. The next Sunday is a new fixed seven-day period.

A manual dispatch can offer a dry-run and an explicit period report, but should not silently bypass period idempotency.

## 7. Deterministic selection

The target is a shortlist, not a ledger. Initial policy should return **0–6 items**, normally 3–6 when enough qualifying work exists, with no minimum fill requirement.

### 7.1 Eligibility

An item qualifies only when all are true:

1. At selection time, at least one attributed `voice_id` resolves to an enabled **Core Voice** under the separate V2 authority.
2. Authorship was established by the existing evidence model; no mention/name inference is added.
3. The article has a valid `published_at` inside the fixed weekly period and not before the state's trusted `collecting_since` boundary.
4. It has a non-empty headline and publisher URL.
5. It is the primary representation of its duplicate/syndication group.
6. It is writing-bearing material under the configured source contract.

For #6, do not invent a title-keyword classifier. The current Voice model does not carry a universal media/content type. V1 should rely on Core source definitions that are genuinely article/essay surfaces and exclude a non-written item only when a provider supplies reliable structured type metadata. If mixed-media sources become a real problem, add an explicit normalized content-kind field later.

### 7.2 Ranking and breadth

Use only observable deterministic facts:

```text
item priority within a Voice:
    1. never appeared in a morning edition this period
    2. newest publication timestamp
    3. normalized headline
    4. canonical key

Voice order:
    rank of that Voice's best remaining item
    then stable voice_id
```

Selection is two breadth-first rounds:

1. Take at most one best item from each Voice, until the global cap of 6.
2. If capacity remains, take at most one second item from each Voice in the same deterministic order.
3. Stop. **Never exceed two items from one Voice.** Do not fill slot 6 with a prolific writer merely because it exists.
4. Once the set is chosen, display it newest-first with canonical key as the final tie-break.

This gives distinct-Voice breadth before depth, favors genuinely missed material within each writer's queue, keeps freshness important, and prevents a daily columnist from crowding out a sparse writer.

### 7.3 Sparse weeks

Do not manufacture a six-item roundup.

- 0 qualifying items: no ntfy notification; mark the period `empty` only when source/state evidence is trustworthy.
- 1–2 qualifying items: a 1–2 item roundup is acceptable. “3–6” is a target when enough exists, not a quota.
- 3–6: show all selected.
- >6: the deterministic policy above chooses six.

No popularity, views, clicks, engagement, sentiment, model score or editorial “importance” number is introduced.

## 8. The weekly static artifact

Render one current page at a stable path such as:

```text
docs/voices/index.html
```

Its product contract is deliberately smaller than Opinion:

```text
VOICES THIS WEEK
A few pieces worth catching up on.

Jonathan Haidt · After Babel · Sep 12
Headline
Open original

Conrad Black · National Post · Sep 11
Headline
Open original
```

Requirements:

- at most six items;
- headline, Core Voice name, publication and date;
- direct publisher link;
- no unread state;
- no badges;
- no archive/week picker;
- no pagination;
- no “load more”;
- no recommendations;
- no persistent history;
- no article body or protected-content scraping;
- no model-generated summary required.

The same path is overwritten each week. If a trustworthy period has zero items, update it to a dated empty state rather than leaving a stale previous roundup masquerading as current.

Do not add a new permanent navigation surface in the first implementation unless the separate product-authority stream explicitly asks for one. The page exists primarily as the durable destination for the one weekly interruption.

## 9. ntfy user experience

Send **one notification per non-empty weekly period**.

Recommended payload:

```json
{
  "title": "Voices this week",
  "message": "5 pieces from Jonathan Haidt, Conrad Black, George Monbiot +2.",
  "priority": 3,
  "tags": ["memo"],
  "click": "<PAGES_URL>/voices/"
}
```

For one or two Voices, name them naturally. For more, name at most three and use `+N`. Do not list all six headlines in the notification.

The notification should **not**:

- summarize every selected article;
- deep-link only to the first selected article;
- contain urgency language;
- carry an unread count;
- send one action per article.

The interruption says “there is a finite catch-up ready.” The Hermes page contains the shortlist; publisher pages contain the writing.

## 10. Idempotency and publish ordering

Reuse #12's conservative reliability budget at the **roundup level**.

Required ordering:

```text
load trusted state
-> collect/reconcile
-> compute deterministic period + selection
-> render current roundup
-> durably commit period claim + roundup page
-> only after that push succeeds, send ntfy
-> record delivery outcome best-effort
```

The state claim and generated page should land in the same compare-and-swap git transaction for the weekly publish. A notification must never point to a page that failed to publish.

Semantics remain **at-most-once, not exactly-once**:

- crash before durable claim: later attempt may retry normally;
- lost push race: reload, recompute, retry; send nothing until persistence wins;
- crash after page/claim push but before ntfy: roundup remains available, `pending` is terminal for that period, no duplicate push;
- ntfy request fails/returns ambiguously: mark `failed`, do not auto-retry because delivery may have occurred;
- outcome-status write fails after ntfy: claim remains `pending`; still no repeat.

For a once-weekly interruption, a rare lost push is less damaging than two identical Sunday notifications.

## 11. Failure semantics

### Daily collector

- **One source fails:** merge successful sources and log degradation.
- **All planned sources fail:** write no false observations; exit degraded for operator visibility.
- **State push loses a race:** reload and re-merge the same observations, bounded retry.
- **Morning edition cannot be read:** collect normally; do not set the optional surfaced timestamp.
- **No new observations:** no commit.

### Weekly publisher

- **Final cheap reconciliation partly fails:** select from trusted accumulated state plus successful observations.
- **All final sources fail but trusted accumulated candidates exist:** the week's prior evidence is sufficient; publish the deterministic shortlist and log the failed preflight.
- **No candidates and all final sources failed:** do not claim the period `empty`; let the next scheduled attempt try again.
- **No candidates and collection/source evidence is trustworthy:** claim `empty`, update the dated empty page, send nothing.
- **Git publish cannot win after bounded retries:** send nothing and fail visibly.
- **Run starts outside the Sunday/Monday delivery grace:** do not send a stale automatic interruption.

## 12. Cold start, corrupt state and migration

### 12.1 Use a new active roundup state path

Recommended migration path:

```text
data/voice_watch_state.json      # old release-alert claim log; becomes inert
data/voice_roundup_state.json    # new single active roundup accumulator
```

This is safer than an in-place schema change. An old hourly runner that began before the implementation merge understands only V1 watcher state; if both generations wrote the same path it could interpret the new version as corrupt and rewrite it. A new path makes any last in-flight V1 write harmless.

This is **not two long-lived state stores**. The old file becomes read-only/inert as soon as its schedule is removed and can be deleted after one deployment cycle. The active product has one small accumulator.

### 12.2 Never seed weekly candidates from old alert state

The old claim log lacks headline, outbound URL and publication metadata and mixes product-delivery statuses with observation history. More importantly, “alerted before migration” is not evidence that an item belongs in the first weekly catch-up.

Do not reconstruct a weekly backlog from it.

The first successful new collector sets `collecting_since` and only material at/after the trusted boundary can enter a future selection.

### 12.3 Cold/corrupt state is a silent baseline period

Preserve #12's fail-safe principle, widened to the weekly product:

- missing or corrupt roundup state is **not** equivalent to “the reader has never seen anything”;
- establish a fresh `collecting_since` baseline;
- collect observations but suppress automatic notification for the incomplete current weekly period;
- resume notifications at the first full trusted period after recovery.

A damaged state file costs one weekly roundup; it never creates a seven-day burst or resurrects old work.

Partial state parsing may retain valid entries for dedupe, but any recovery flag still suppresses the current period's notification.

## 13. Request and LLM cost

### Provider requests

The current watcher allows frequent sources to run outside 23:00–06:00 — roughly **18 passes/day, 126 passes/week** for those source classes if every cron lands.

The proposed notification product uses:

- 7 daily collection passes/week;
- at most 1 useful Sunday preflight pass (later attempts exit before network once the period is claimed);
- scarce providers only when the existing reconciliation marker says they are due.

That reduces frequent-source notification polling from roughly 126 passes/week to about **8**, around a 94% reduction. Cost still scales with distinct Core sources/batched provider requests, not Core Voice count.

Perigon need not increase: the daily collector can remain the once-daily reconciliation. The Sunday evening preflight occurs only several hours later and therefore stays in frequent/cheap mode.

The morning build's existing Voice discovery remains separate and unchanged.

### Gemini

Initial incremental Gemini usage: **zero calls, zero tokens**.

Deterministic selection chooses keys. The static page can be useful with headline, Voice, publication and date alone.

An optional future editorial-writing pass is justified only if real shadow output shows that metadata is consistently insufficient. A concrete trigger would be a multi-week audit showing a substantial fraction of selected items have both:

- an opaque/non-descriptive headline; and
- no usable public source description distinct from the headline.

If, for example, more than ~30% of selected items across at least six weekly shadow roundups meet that objective condition, a later issue may test **one batch Gemini call per roundup** to write short blurbs. That call must occur *after* deterministic selection, receive only the 3–6 fixed selected records, have no authority to add/drop/reorder items, and fall back cleanly to metadata when unavailable.

Never design one model call per Voice or article.

## 14. Exact implementation surface likely required

The implementation issue should be able to stay focused to these areas.

### Reuse substantially unchanged

- `src/voices/model.py`
- `src/voices/resolve.py`
- `src/voices/dedupe.py`
- `src/voices/discover.py`
- generic adapters and HTTP budgets
- registry loading/validation, plus the Core classification supplied separately

### Add/refactor

- `src/voices/roundup_state.py` — bounded accumulator, observation merge, recovery, period claim; reuse/generalize the proven git-store plumbing from `src/voices/state.py`.
- `src/voices/roundup.py` — Core filtering, daily collection, edition-exposure matching, fixed Toronto periods, deterministic weekly selection.
- `src/voice_roundup.py` — operator entrypoint: collect, weekly publish, dry-run, state report, smoke.
- `src/voices/notify.py` — retain generic JSON notifier; replace per-article composition with one roundup payload.
- `src/config.py` — roundup state path, collection lookback, cap/per-Voice cap, daily/period timing constants; retire release-time alert tuning after migration.
- `.github/workflows/voice-watch.yml` — replace or rename as a roundup workflow with daily silent collection + weekly attempts. Remove hourly schedule.
- a minimal roundup template/renderer and generated `docs/voices/index.html`.
- README / `VOICES.md` operator and product notes after implementation is proven.

### Explicitly not required

- changes to `src/curate.py`;
- Gemini prompt changes;
- a new database/backend;
- a new preference service;
- in-app unread state;
- a Voice history API;
- protected-body fetching;
- per-person adapter code.

The morning `src.build` path should remain untouched in the initial implementation. The daily collector reads the already-published edition artifact to record the optional morning-surface signal.

## 15. Test and acceptance plan

All core tests remain fixture/network-free. The later implementation issue should add at least the following.

### State

- round-trip and deterministic serialization;
- observation upsert unions all identity/syndication keys;
- secondary key matches an existing item;
- metadata enrichment is order-independent;
- `first_morning_surfaced_at` is sticky;
- article body/description is never stored;
- title/publication/URL bounds are enforced;
- 14-day pruning;
- 500-entry cap;
- one `last_roundup` record only;
- malformed and partially malformed state recovery.

### Core boundary

- Core item is collected and eligible;
- Selective item is not retained for notification pressure;
- Discovery item is not retained;
- legacy `notify: true` does not override a non-Core tier;
- a shared source can return several writers while only Core-attributed work enters roundup state.

### Daily collection

- 48-hour overlap does not duplicate entries;
- no ntfy client is required or called;
- no Gemini key/call is required;
- partial source failure still persists successful observations;
- all-source failure creates no false items;
- current `docs/index.html` match marks surfaced;
- stale/missing/malformed edition leaves surfaced unknown without failing collection;
- a no-change day creates no state commit.

### Selection

- zero candidates;
- sparse one/two-item week without force-fill;
- 3–6 qualifying items;
- >6 candidates capped at six;
- breadth across distinct Voices before depth;
- absolute maximum two per Voice;
- never-surfaced item preferred within a Voice over a surfaced item;
- freshness ordering within the same surface tier;
- stable tie-breaks;
- multi-author article with one or more Core Voices;
- exact duplicate across adapters;
- cross-run syndication/reprint consumes one slot;
- invalid/undated/out-of-period items excluded;
- non-writing item excluded only from reliable structured type/source evidence, never title guessing.

### Period and scheduling

- Sunday 17:00 cutoff is constructed in `America/Toronto` correctly in EDT and EST;
- DST-transition periods use local calendar boundaries correctly;
- the three Sunday UTC schedules map to early-evening Toronto in both offsets;
- Monday fallback targets the same prior-Sunday `period_id`;
- repeated Sunday/Monday attempts stop before provider requests after a claim;
- missing one entire week does not make the next period 14 days long;
- automatic delivery never occurs in quiet hours or after the Monday grace window.

### Weekly idempotency

- first eligible period publishes one page and one ntfy message;
- rerun sends zero additional messages;
- two overlapping runs racing the same period produce one durable claim/notification between them;
- lost git push sends nothing;
- crash after claim/page push does not re-notify;
- ntfy failure is terminal for that period;
- outcome-state write failure cannot reopen the period;
- no candidates + healthy evidence records `empty` once and never notifies;
- no candidates + blind final fetch remains retryable.

### Roundup artifact / Android-oriented UX

Inspect the exact generated page at the same representative phone sizes used by #11/#13. Assert:

- 0–6 items only;
- no horizontal overflow;
- direct publisher links remain correct;
- Voice/publication/date are legible but subordinate to headlines;
- 44px link targets where applicable;
- no unread/badge/history/load-more UI;
- no generated summary is required;
- notification click target resolves to the current roundup page;
- ntfy copy remains compact at Android notification widths and normal priority.

### Workflow contract

Update `tests/test_workflows.py` to assert the new product rather than preserving obsolete hourly assumptions:

- no hourly Voice schedule;
- daily collection exists and has no `NTFY_TOPIC`/Gemini dependency;
- weekly delivery attempts are off the top of the hour;
- weekly job has `NTFY_TOPIC` but no Gemini key;
- Core roundup state commits do not unnecessarily burn CI;
- the morning edition workflow/notification remains independent and unchanged;
- safe git compare-and-swap/retry semantics cover the state/page writer.

## 16. Implementation issue recommendation

Create one focused implementation issue after the V2 product-authority/Core-roster schema lands:

> **Voices V2 — replace release-time alerts with weekly Core Voices roundup**
>
> Replace the hourly per-article Voice watcher with a Core-only daily silent collector and a single finite Sunday catch-up. Reuse canonical identity, source adapters, bounded repo state, git CAS and ntfy. Accumulate only minimum public article metadata for 14 days; mark actual morning-edition exposure; select at most six deterministically with distinct-Voice breadth and max two per Voice; publish one overwrite-only `/voices/` roundup page; send one at-most-once ntfy notification per non-empty period. No Gemini calls, backend, unread state, history, Selective/Discovery notification pressure, protected-body scraping or per-article routine alerts. Migrate via a new roundup state path so old watcher state cannot generate a backlog.

A **strong regular implementation agent** is sufficient. The hardest correctness primitives already exist and are tested; the work is primarily a careful product-shaped refactor of those primitives, not a new source/adapter architecture.

## 17. Final decision

Proceed with the daily-silent-collector + weekly-single-publish architecture.

It is smaller operationally than the current release watcher, substantially cheaper on frequent source polling, requires no extra LLM work, preserves at-most-once interruption semantics, gives “already in the morning paper” a deterministic role without inventing engagement data, and produces a useful 3–6-item catch-up without turning Hermes into a Voice feed.
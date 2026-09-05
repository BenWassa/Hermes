# Hermes Voices

Status: **design authority for issue #9; not yet implemented**  
Baseline when written: `08e52581e5444a6cb51aca8cb70fa3bd3706df98` (`2026-09-05` edition)

This document defines how Hermes should follow named writers across publications and surface their new work inside Opinion without turning The Daily into a feed, adding a general backend, or weakening source/provenance discipline.

It complements `PRODUCT.md`, `PRD_daily_newspaper.md`, and `BUILD_INSTRUCTIONS.md`. If implementation detail conflicts with the product principles in `PRODUCT.md`, the product principles win unless this document explicitly narrows them.

## 1. Product decision

Hermes should support **Voices**.

A Voice is a person whose new writing the reader deliberately wants to see. It is independent of publication. Jonathan Haidt may publish at After Babel, The Atlantic, The New York Times, The Free Press, or elsewhere; Hermes should still understand those pieces as work from the same followed person when it can establish authorship reliably.

The Opinion desk becomes two related but distinct editorial surfaces:

1. **Following** — new qualifying work from explicitly followed Voices.
2. **Today's Opinion** — Hermes' ordinary curated Opinion selection.

Following is a deterministic reader preference. It is not merely another Gemini ranking signal.

The objective is not to create a personalized content stream. The Daily remains a finite morning paper. Following exists to make the Opinion desk better at a specific job: do not miss new work from thinkers the reader has deliberately chosen.

## 2. Why this fits Hermes

`PRODUCT.md` defines one reader, a five-to-ten-minute morning session, a static finished edition, and no growth or engagement loop. Voices should reinforce those properties.

The feature should therefore:

- improve the quality of a finite morning read;
- remain compact and editorially legible;
- use the existing static-build architecture where practical;
- avoid accounts, follower graphs, recommendation loops, unread-count pressure, or infinite history;
- preserve quiet broadsheet presentation;
- use the existing ntfy channel for optional release-time alerts rather than adding a second notification system.

A good implementation should feel like a newspaper subscriber asking the editor, "Make sure I see the new column when one of these people writes," not like opening a social feed.

## 3. Current-state gap

The production v2 pipeline already has most of the necessary plumbing, but authorship is not first-class.

Current behavior:

- `src/fetch.py` pulls Guardian, NYT, Perigon, and Toronto RSS.
- Guardian requests `show-fields=thumbnail,trailText,byline`.
- `src/normalize.py` drops that Guardian byline.
- NYT normalization also omits the API byline.
- Perigon normalization omits `authorsByline` and canonical journalist identity.
- `src/curate.py` sends normalized story records to Gemini for dedupe, sectioning, ranking, capping, and summarization.
- Opinion is an ordinary capped section (`cap = 4`).
- `template/index.template.html` renders only the final edition and currently has no author concept.
- GitHub Actions produces the morning edition on static GitHub Pages.
- ntfy already delivers the morning push.

The central correction is therefore not "add more Opinion queries." It is to preserve and resolve authorship before editorial curation, then give followed Voices a deterministic path through the edition.

## 4. Core invariants

### 4.1 Voice is not publication

The canonical object is a person.

A Voice may have zero, one, or many discovery sources, and those sources may change over time without changing the Voice ID.

### 4.2 Stable source identity beats name matching

When a provider exposes a stable contributor/journalist ID, Hermes should store and match that ID.

Name aliases are useful for feeds and weaker sources, but a bare string such as `John Smith` must not be treated as authoritative when a stronger identity is available.

### 4.3 Authorship must be established, not inferred from mentions

A search result containing a person's name is not evidence that the person wrote the piece.

Generic search, if ever used, is discovery only. A candidate must pass a separate authorship check using byline metadata, structured page metadata, a known author archive, or another source-specific signal.

LLM output alone is never sufficient to establish authorship.

### 4.4 Followed content cannot disappear inside model ranking

If a new article is reliably attributed to an enabled Voice and falls within the edition window, it must reach the Following candidate set independently of Gemini's Opinion cap.

Gemini may summarize or editorially process the item, but it must not have authority to decide that the user's explicit follow preference did not matter today.

### 4.5 One article should appear once

The same article may be found through RSS, a first-party API, Perigon, and the ordinary Opinion fetch. Hermes must collapse those observations into one canonical article.

If the ordinary editor also selects the followed article for Today's Opinion, the final rendered Opinion page should not show two cards for the same piece.

### 4.6 Partial source failure is normal

Voice discovery must follow the existing Hermes source philosophy: a dead feed or unavailable API logs clearly and contributes no items; it must not kill the edition.

### 4.7 No paywall circumvention

Hermes may discover and link to paywalled pieces using legitimate public metadata. It must not bypass access controls or scrape/reproduce subscription-only body text.

## 5. Canonical data model

The exact Python representation may evolve, but the semantic schema should look like this.

### 5.1 Voice registry

```json
{
  "id": "jonathan-haidt",
  "name": "Jonathan Haidt",
  "enabled": true,
  "notify": true,
  "aliases": ["Jon Haidt"],
  "sources": [
    {
      "type": "rss",
      "url": "https://www.afterbabel.com/feed",
      "author_names": ["Jon Haidt", "Jonathan Haidt"]
    },
    {
      "type": "perigon_journalist",
      "journalist_id": "provider-stable-id"
    }
  ]
}
```

Recommended source-of-truth file: `data/voices.json` or an equivalently simple reviewed config file.

Validation must reject at least:

- duplicate Voice IDs;
- empty display names;
- duplicate source definitions that would cause redundant polling;
- source adapters missing required identity fields;
- an enabled Voice with no usable source unless explicitly allowed as dormant.

### 5.2 Normalized story

Extend the existing normalized story schema compatibly:

```json
{
  "title": "...",
  "description": "...",
  "source": "The Atlantic",
  "section_hint": "opinion",
  "pub_date": "2026-09-05T12:34:56Z",
  "image": null,
  "link": "https://...",

  "source_article_id": "optional-provider-id",
  "canonical_url": "https://...",
  "byline": "Jonathan Haidt",
  "authors": [
    {
      "name": "Jonathan Haidt",
      "source_author_id": "optional-provider-id"
    }
  ],
  "voice_ids": ["jonathan-haidt"],
  "discovered_via": ["rss:after-babel"]
}
```

The old keys remain valid for existing curation code during migration.

### 5.3 Canonical article identity

Prefer, in order:

1. provider-native stable article ID where that provider can be trusted to identify the canonical item;
2. publisher canonical URL;
3. normalized URL after conservative removal of known tracking parameters;
4. bounded fingerprint fallback from normalized source + title + publication date when no stable identifier exists.

Do not aggressively rewrite URLs in ways that collapse genuinely different articles.

Syndicated/reprinted copies are a separate concept from exact duplicates. Hermes may choose one canonical presentation while retaining provenance that a story was observed elsewhere.

## 6. Source adapter architecture

Do not write one fetch function per person.

Define a generic adapter contract whose job is to return candidate articles with enough source-native evidence to normalize and resolve authorship.

Conceptually:

```python
class VoiceSourceAdapter:
    def fetch(self, source_spec, since, until) -> list[VoiceCandidate]: ...
```

A candidate should carry:

- title;
- URL;
- source/publication;
- publication timestamp if available;
- raw byline / structured authors;
- provider article ID;
- provider author/contributor IDs;
- description/image only when legitimately available;
- adapter provenance.

### 6.1 Tier A — RSS / Atom

Preferred for direct newsletters and personal publications.

Advantages:

- cheap;
- structured;
- no proprietary API quota;
- publication timestamps are usually explicit;
- often contains author metadata;
- easy to fixture/test.

Substack documents a standard publication feed at `https://<publication>/feed`.

Important: a publication feed can contain several writers. A feed URL does not itself prove that every entry belongs to the followed Voice. Match entry-level authorship when the feed is multi-author.

### 6.2 Tier B — first-party structured APIs

#### Guardian

Guardian Open Platform supports content filtering by `tag` and can return `show-tags=contributor`. The existing Hermes fetch already requests the human-readable byline.

Use canonical contributor tag identity when available, with byline retained for display.

Official reference:

- https://open-platform.theguardian.com/documentation/search
- https://open-platform.theguardian.com/documentation/tag

#### New York Times

Hermes currently underuses its NYT connection. Voice work may use the appropriate NYT public endpoint for recent Opinion/newswire/article-search discovery, but implementation must verify current API contracts and quotas rather than assume historic behavior.

At minimum, retain NYT byline data in normalization even for non-Voice stories.

Official API specs:

- https://github.com/nytimes/public_api_specs

### 6.3 Tier C — aggregator canonical journalist identity

Perigon is valuable for writers who publish across multiple outlets because its data model includes journalist identity and article author/byline fields.

Where available, resolve a known Voice to a Perigon journalist ID once and query by that stable ID rather than repeatedly searching by name.

Perigon should be a **coverage expander and reconciliation source**, not the default high-frequency poller on the current free plan.

As of 2026-09-05, public pricing lists the personal/free tier at 150 API requests per month. Limits are external configuration and may change; implementation should query/document current plan behavior and degrade gracefully.

References:

- https://perigon.io/products/apis
- https://perigon.io/products/pricing/apis

### 6.4 Tier D — bounded author/archive pages

Some writers have stable publication author pages even when no practical API/feed exists.

A generic author-page adapter may be justified when the page has durable machine-readable structure such as:

- JSON-LD `Article` / `Person` metadata;
- semantic `<article>` entries with author/date links;
- a stable public author archive with canonical article links.

This adapter must be site-pattern-based, not person-specific. A `new-york-sun-author-page` adapter is acceptable if several authors can use it; `conrad-black-page-parser` is not.

The parser should fail closed when the expected structure changes rather than silently inventing attribution.

### 6.5 Tier E — generic web search fallback

This is optional and last-resort.

If added, use a supported search API or similarly legitimate search surface. Do not scrape Google/Bing result HTML.

Search results produce candidates only. Hermes must verify authorship from the destination or structured source before surfacing the article as followed content.

A query such as `"Jonathan Haidt" article` is insufficient evidence by itself.

## 7. Initial acceptance Voices

The first implementation should prove generic coverage against different publishing patterns.

### Jonathan Haidt

Useful because his publishing footprint spans his own/known surfaces and third-party outlets.

Current first-party references include:

- After Babel: https://www.afterbabel.com/
- Essays index: https://www.jonathanhaidt.com/essays

After Babel is multi-author, so entry-level author matching matters.

### Jordan Peterson

Useful as a direct newsletter/site publishing case. The adapter should be generic RSS/site logic, not a Peterson-specific function.

### Conrad Black

Useful as a third-party publication-author-page/paywall case.

A current public author archive exists at The New York Sun:

- https://www.nysun.com/author/conrad-black-2

The system should be able to discover metadata and canonical links without needing article body access.

### Additional mandatory fixtures

Also include:

- one Guardian contributor resolved through canonical contributor metadata;
- one NYT Opinion writer;
- one article with two or more authors, exactly one of whom is followed;
- one deliberately common/ambiguous name to demonstrate that naïve name matching is rejected;
- one duplicate article observed from two adapters;
- one reprint/syndication case.

The acceptance names must never appear in fetch control flow except as data in the Voice registry/fixtures.

## 8. Edition window and finite-paper behavior

### 8.1 Morning window

The build should discover material newer than a durable logical cutoff, not merely "calendar today".

Recommended contract:

- include qualifying Voice pieces published after the previous successful edition cutoff;
- include a bounded lookback overlap (for example several hours) to tolerate delayed indexing;
- dedupe against prior seen/canonical IDs so overlap does not repeat old items;
- reject obviously stale historical feed entries;
- handle missing/invalid timestamps conservatively and log the decision.

Exact hours should be implementation constants with tests, not buried in prompt text.

### 8.2 Following cap

The Daily must remain finite even if several Voices publish on one day.

Recommended initial policy:

- render up to **6** new followed articles in the morning Following block;
- sort newest first, with deterministic tie-breaking;
- if more than 6 qualify, choose at most 2 per Voice before filling remaining slots by recency so one prolific writer cannot dominate the block;
- retain all qualifying items in build diagnostics if useful, but do not expose an infinite overflow feed.

If later evidence shows 6 is too much for the morning read, lower it. Do not increase it automatically based on activity.

### 8.3 Presentation

Opinion should show, only when non-empty:

```text
OPINION

FOLLOWING
Jonathan Haidt · After Babel
Headline...

Conrad Black · The New York Sun
Headline...

TODAY'S OPINION
(existing editorial cards...)
```

This is a conceptual hierarchy, not a pixel specification.

Requirements:

- no red notification badge;
- no unread count;
- no avatar carousel;
- no horizontal social-media scroller;
- no `For You` language;
- no endless history;
- author and publication visible but subordinate to headline;
- card expansion, Read full story, and Ask AI continue to work;
- 44px minimum interactive targets;
- reduced-motion behavior unchanged.

## 9. Curation integration

Do not simply append Voice candidates to the raw pool and tell Gemini to "prefer them."

Recommended flow:

```text
ordinary fetch
    -> normalize

voice discovery
    -> normalize
    -> resolve voice IDs
    -> canonicalize/dedupe

merge observations
    -> ordinary curation pool
    -> deterministic followed candidate set

Gemini editorial curation
    -> normal sections including Today's Opinion

post-pass
    -> attach Following set
    -> dedupe followed item from duplicate Opinion presentation
    -> render
```

A followed item may still be included in the Gemini prompt so that it receives the same style of summary and can be selected elsewhere when editorially appropriate. The deterministic Following set is maintained separately.

If model summarization of every followed item would materially inflate cost/token usage, the implementation may use a smaller dedicated summarization pass or source description, but the resulting UX must remain coherent. That decision should be measured rather than guessed.

## 10. V1 preference state

For issue #9, **the repository-backed Voice registry is authoritative**.

Do not add an in-app Follow/Unfollow toggle that writes only localStorage. The static page cannot communicate that preference to the scheduled GitHub Actions pipeline, so such a control would be semantically false: the user could appear to follow a writer while the backend never starts fetching them.

For this one-reader product, a reviewed edit to `data/voices.json` is an acceptable V1 management mechanism.

### Deferred in-app management

A future issue may add `Manage Voices` from the Opinion page, but it requires real writable remote state. At that point evaluate a tiny one-user store such as Firestore or another deliberately minimal endpoint.

That future feature must answer:

- how the static client authenticates writes;
- how scheduled Actions read preferences;
- how secrets remain off the client;
- offline behavior;
- preference migration/versioning;
- whether ntfy alert preferences use the same source of truth.

Do not prebuild this backend in #9.

## 11. Release-time watcher

Morning inclusion and release-time alerting are separate jobs.

A lightweight watcher should run independently of the full edition build:

```text
load Voice registry
load durable seen state
fetch recent candidates through quota-appropriate adapters
resolve + canonicalize + dedupe
filter already-seen
publish restrained ntfy alert for each new qualifying item
persist newly-seen identities
```

### 11.1 Delivery semantics

GitHub scheduled Actions are not a realtime event bus. Treat the watcher as **eventually-soon**.

Initial cadence should be conservative, likely hourly, unless provider quotas and observed Action reliability support something better.

Do not promise a fixed latency in product copy.

### 11.2 Notification style

Example:

```text
Jonathan Haidt — After Babel
Treasure Your Attention
```

No `BREAKING`, urgency copy, emoji alarm, or unread-count mechanics.

The notification should deep-link to the canonical article when practical. If later a Hermes Following landing target becomes useful, that can be reconsidered, but do not require a full edition rebuild to send an alert.

### 11.3 Durable idempotency

At-most-once alerting under retries/re-runs is mandatory.

A repo-backed state file is acceptable in this architecture, for example:

```json
{
  "version": 1,
  "seen": {
    "canonical-key": {
      "voice_id": "jonathan-haidt",
      "first_seen": "2026-09-05T18:00:00Z"
    }
  }
}
```

If repo state is used:

- prune old entries on a fixed retention window;
- store no article body/content;
- commit only on change;
- use a bot commit message distinct from morning edition commits;
- coordinate the watcher and morning build with a shared GitHub Actions concurrency group;
- before push, synchronize safely with current main so simultaneous jobs do not lose either the new edition or watcher state;
- retry paths must check state again before notifying when possible.

If a simpler durable mechanism is found during implementation, it may replace repo state, but adding a general application backend solely for watcher idempotency is not preferred.

## 12. Request and quota strategy

The dangerous implementation is `number of voices × polls per day × provider requests`.

Avoid that.

### RSS

Fetch dedicated feeds directly. Cache conditional headers (`ETag`, `Last-Modified`) only if doing so remains simple; correctness matters more than shaving tiny bandwidth.

### Guardian

Batch recent content/contributor queries where the API supports it and filter locally. Current developer access publicly documents up to 500 calls/day and 1 call/second for non-commercial use, but implementation should treat provider policy as external and current.

### NYT

Prefer a recent stream/section endpoint and local author matching when that captures the followed writers reliably. Use per-author search only when necessary and bounded.

### Perigon

Current personal/free allowance is 150 requests/month, so a 24×7 polling loop is inappropriate.

Use Perigon for one or more of:

- daily reconciliation;
- resolving a canonical journalist identity;
- filling coverage gaps for Voices without good first-party feeds;
- lower-frequency discovery.

The implementation should expose/log provider request counts sufficiently to detect accidental quota explosions.

## 13. Security, licensing, and content handling

- Keep API keys in GitHub secrets/environment variables as today.
- Never emit provider keys into generated HTML.
- Do not put full licensed/paywalled article bodies in `docs/index.html`, state files, fixtures, or logs.
- Fixtures should contain synthetic/minimal representative metadata where possible.
- Preserve canonical outbound publisher links.
- Follow provider attribution/licensing requirements.
- Treat public author/archive pages as discovery surfaces, not an invitation to mirror publication content.

## 14. Testing strategy

The current v2 production pipeline lacks an active first-class test suite. #9 should establish one focused on the new contracts rather than create a giant testing rewrite.

Recommended structure:

```text
tests/
  fixtures/
    guardian/
    nyt/
    rss/
    perigon/
    author_pages/
  test_voice_registry.py
  test_voice_resolution.py
  test_voice_adapters.py
  test_voice_dedupe.py
  test_following_integration.py
  test_voice_watch.py
```

All core tests must run without live network access.

### Mandatory deterministic cases

- valid and invalid registry entries;
- canonical provider author-ID match;
- exact alias match;
- alias normalization for punctuation/case/spacing;
- no substring/common-name overmatch;
- multi-author story where followed author is first/middle/last;
- feed with mixed authors;
- source missing author metadata;
- Guardian contributor identity;
- NYT byline retention;
- Perigon journalist identity when used;
- exact duplicate across adapters;
- tracking-parameter URL duplicate;
- reprint/syndication distinction;
- stale content;
- invalid/future date;
- adapter network failure;
- no followed items;
- one followed item;
- more than Following cap;
- duplicate between Following and Today's Opinion;
- watcher first discovery sends once;
- watcher retry sends zero additional alerts;
- state pruning;
- malformed state fails safely.

### Live smoke checks

Live-provider checks are useful before merge but cannot be the only proof and should not make routine deterministic tests flaky.

Verify the configured acceptance Voices and at least one real current article per adapter family where possible.

## 15. Build and workflow integration

Likely code areas:

- `src/fetch.py` — preserve current source behavior; perhaps expose reusable source methods.
- `src/normalize.py` — add author/provenance fields.
- `src/voices.py` — registry loading, adapter orchestration, identity resolution, canonicalization/dedupe.
- `src/voice_watch.py` — watcher entrypoint and state handling.
- `src/build.py` — integrate deterministic Following candidates with ordinary edition build.
- `src/curate.py` — maintain editorial curation while allowing followed-item summarization/data to survive.
- `src/config.py` — caps/timing constants only where appropriate; do not bury the Voice registry here if a data file is cleaner.
- `template/index.template.html` — compact Following presentation and author/source metadata.
- `.github/workflows/build.yml` — shared concurrency/safe-push adjustments if required.
- `.github/workflows/voice-watch.yml` — separate watcher.
- `requirements.txt` — only if a justified parser/utility dependency is needed.
- `README.md` — operator setup and how to add/remove a Voice.

Do not modify generated `docs/index.html` by hand. Render it through the normal production path.

## 16. Implementation sequence and agent allocation

### Slice A — canonical identity and discovery foundation

**Use Opus or Sol Ultra.**

This is the most reasoning-sensitive slice because subtle mistakes create false attribution or missed work.

Deliver:

- registry/schema and validation;
- normalized author model;
- adapter abstraction;
- RSS adapter;
- Guardian contributor path;
- one general cross-publication path (Perigon or justified structured author-page adapter);
- canonical URL/article identity;
- cross-adapter dedupe;
- focused test harness and fixtures.

Do not implement the watcher and major UI in the same PR unless there is a compelling dependency.

### Slice B — morning edition integration and Opinion UX

**Strong regular agent is sufficient after Slice A merges.**

Deliver:

- deterministic Following set in edition output;
- cap/overflow policy;
- duplicate suppression against Today's Opinion;
- author/publication presentation;
- preserved card expansion, Ask AI, links, keyboard and reduced motion;
- exact mobile inspection.

### Slice C — watcher, idempotency, workflow races

**Use Opus or Sol Ultra.**

Operational correctness matters more than code volume.

Deliver:

- `voice_watch` command;
- durable bounded seen state;
- at-most-once ntfy behavior;
- source-budget-aware polling;
- shared workflow concurrency and safe push semantics;
- retry/failure tests.

### Slice D — source hardening and operator documentation

**Regular agent.**

Deliver:

- bounded live audits;
- README instructions;
- example config entries;
- provider-capability notes;
- final fixture cleanup;
- generated production inspection.

Do not parallelize Slice B/C against unmerged schema changes from Slice A. Slice B and C may proceed in parallel only after the identity/data contract is stable and their touched files do not materially overlap.

## 17. Decisions deliberately deferred

### In-app Voice management

Deferred. Requires writable remote state and should be its own issue.

### Generic web-wide crawling

Deferred. First prove RSS, current APIs, aggregator identity, and bounded author pages. Add web search only for a demonstrated coverage gap.

### AI recommendations of new Voices

Not desired. The feature is explicit following, not recommendation discovery.

### Archive/history UI

Not desired in #9. The morning paper shows current work. A writer archive is a different product behavior.

### Full-text ingestion for followed essays

Not required. Metadata + legitimate source description + canonical link is enough to establish the feature. Use article text only where provider terms and existing Hermes behavior already justify it.

## 18. Definition of done

Issue #9 is complete only when:

1. Voice identity is publication-independent and backed by a validated registry.
2. Existing Guardian/NYT/Perigon normalization no longer discards useful authorship metadata.
3. At least three generic adapter patterns cover the initial real-world acceptance set without person-specific fetch code.
4. Ambiguous/common-name false attribution has explicit regression coverage.
5. Cross-adapter article duplicates collapse deterministically.
6. New followed pieces survive the ordinary Opinion cap and appear in a distinct finite Following treatment.
7. Today's Opinion still exists as editorial discovery.
8. The same article does not render twice merely because it is both followed and editorially selected.
9. Release-time watcher alerts are idempotent and source failures are local.
10. Request usage is bounded and operationally understandable.
11. Paywalls are respected and canonical outbound links are preserved.
12. Focused automated tests run for the production v2 feature contracts.
13. Generated exact production output is inspected on representative phone portrait/landscape sizes.
14. README/config documentation explains how to add, disable, and troubleshoot a Voice.
15. No multi-user backend, engagement feed, or fake local-only Follow semantics have leaked into V1.

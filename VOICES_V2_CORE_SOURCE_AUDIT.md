# Hermes Voices V2 — Core Source Audit

Status: **Wave 1B source-readiness audit, 2026-09-09**.

This document is research/audit authority only. It does **not** change `data/voices.json`, current morning `Following`, the release-time watcher, schedules, notifications, or any other production Voice behaviour.

`VOICES_V2.md` remains authoritative for the locked intellectual roster and tier semantics. This audit answers only the separate technical question: **what compliant production source can Hermes use for each of the 15 Core Voices with the adapters and authorship-evidence model that already exist?**

## Classification

- **READY** — an enabled, production-reachable source path is already present in the current V1 production registry and needs no source change to remain technically usable.
- **READY WITH CONFIG** — a generic existing adapter path has been live-proved from GitHub Actions; later V2 source configuration is needed, but no adapter code is required.
- **ADAPTER WORK** — a compliant source exists, but current generic adapters cannot consume it safely.
- **UNRESOLVED** — no compliant, production-reachable source has yet been proved.

A technical classification never changes Core membership.

## Audit method and evidence

The Wave 1B branch was continued rather than restarted. At the start of the finishing pass:

- current `main` was `9223237f827d4267f3c74b82757b2f3ea516b192`;
- `voices-v2-wave1b-core-source-audit` was at `d8597256293b3e2b484d2c88cdb2bd794033e65f`;
- the branch contained four temporary probe commits and was four commits behind then-current `main`;
- the earlier probe history contained useful live evidence but no durable audit artifact.

Useful earlier Actions evidence was preserved:

- run `34130004201` — initial source probe, success;
- run `34130644014` — extended candidate probe, success;
- run `34130875257` — final-candidate probe, success; this is the retained basis for the proven Ezra Klein, David Brooks and Jonathan Haidt paths;
- run `34131401109` — **not source evidence**. It failed before its intended check because the temporary workflow contained an invalid Python import while testing a User-Agent hypothesis.

Only bounded follow-up probes were added where the earlier evidence left a material source-choice or runner-reachability question:

- run `34375871256` — Adam Tooze / Foreign Policy RSS, Tyler Cowen / Marginal Revolution RSS, Dan Wang / personal RSS, and Fareed Zakaria / Washington Post author page all resolved attributable articles through the current adapters on GitHub-hosted Actions. The same four also worked when an explicit Hermes User-Agent was forced.
- run `34376070133` — Andrew Coyne, both Paul Wells candidates, both Francis Fukuyama candidates, both Helen Thompson author pages, Steven Pinker's first-party publications page, both Arthur C. Brooks feeds, and both Zeynep Tufekci feeds all resolved attributable articles through current adapters on GitHub-hosted Actions.
- run `34376191426` — Adam Tooze's preferred direct Chartbook/Substack RSS failed through Hermes on GitHub-hosted Actions. This is retained as a genuine publisher/source constraint; no evasion was attempted.

All probes were read-only. They fetched discovery metadata/feed/index surfaces only and did not scrape paywalled article bodies.

## Final 15-Voice readiness matrix

| Core Voice | Best production source | Adapter + reliable authorship evidence | GitHub Actions reachability / freshness / request cost | Fallback | Classification |
|---|---|---|---|---|---|
| **Conrad Black** | National Newswatch contributor index: `https://www.nationalnewswatch.com/author/conrad-black` | Existing generic `author_page`; exact `/author/conrad-black` contributor path yields `provider_id` evidence. | Already production-proved from Actions in #17 / PR #19; one author-page GET; National Newswatch retains linked external writing for a rolling window. | No equivalent dedicated fallback is currently safe. New York Sun returned HTTP 429 from GitHub runners; Perigon did not provide a stable Conrad journalist identity. | **READY** |
| **Andrew Coyne** | National Newswatch contributor index: `https://www.nationalnewswatch.com/author/andrew-coyne` | Existing generic `author_page`; exact `/author/andrew-coyne` path, external links allowed, `provider_id` required. | Actions-proved in run `34376070133`; one GET. The index was current through 2026-09-09 during the finishing audit. | Zero-incremental-cost attribution from an already-fetched morning pool item remains possible; no second dedicated source is required for readiness. | **READY WITH CONFIG** |
| **Paul Wells** | First-party newsletter RSS: `https://paulwells.substack.com/feed` | Existing `rss`; person-scoped first-party feed, so `scope` evidence is sufficient. | Actions-proved in run `34376070133`; one GET; active in September 2026. This direct feed is fresher than the aggregator fallback. | National Newswatch `/author/paul-wells`, also Actions-proved, using exact `provider_id` evidence. Its external archive is useful but can lag the newsletter. | **READY WITH CONFIG** |
| **Ezra Klein** | NYT byline RSS: `https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/by/ezra-klein/rss.xml` | Existing `rss`; feed-entry byline evidence. | Proven in the retained final-candidate Actions evidence; one GET. | Existing NYT morning-pool attribution costs zero additional source requests when an item is already in the ordinary edition fetch. | **READY WITH CONFIG** |
| **David Brooks** | Atlantic author RSS: `https://www.theatlantic.com/feed/author/david-brooks/` | Existing `rss`; feed-entry byline evidence. | Proven in the retained final-candidate Actions evidence; one GET. | Current V1 zero-request morning-pool/byline handling can still catch already-fetched NYT Opinion material; it is not equivalent to a dedicated cross-publication source. | **READY WITH CONFIG** |
| **Francis Fukuyama** | Person-scoped Persuasion column RSS: `https://www.persuasion.community/s/francis-fukuyama/feed` | Existing `rss`; first-party person-scoped feed, `scope` evidence. | Actions-proved in run `34376070133`; one GET; current Persuasion writing was published as recently as 2026-09-08 during the audit. | Persuasion main feed `https://www.persuasion.community/feed` with `byline` evidence; also Actions-proved. | **READY WITH CONFIG** |
| **Fareed Zakaria** | Washington Post author page: `https://www.washingtonpost.com/people/fareed-zakaria/` | Existing generic `author_page`; person-scoped archive, `scope` evidence; no article-body scraping. | Actions-proved in run `34375871256`; one GET. The page carried weekly Opinion columns through August 2026 during the audit. | No second dedicated source is promoted by this audit. Already-fetched ordinary-pool items can still be attributed at zero incremental request cost. | **READY WITH CONFIG** |
| **Adam Tooze** | Foreign Policy author RSS: `https://foreignpolicy.com/author/adam-tooze/feed/` | Existing `rss`; feed-entry byline evidence, including coauthored pieces. | Actions-proved in run `34375871256`; one GET; Foreign Policy author archive was current through late August 2026. | **Chartbook is not an operational Actions fallback:** `https://adamtooze.substack.com/feed` failed the dedicated run `34376191426` even though the public newsletter was extremely current. A broader provider fallback should use the existing evidence model only if a stable journalist identity is later proved. | **READY WITH CONFIG** |
| **Helen Thompson** | New Statesman author page: `https://www.newstatesman.com/author/helen-thompson` | Existing generic `author_page`; person-scoped archive, `scope` evidence. | Actions-proved in run `34376070133`; one GET. | UnHerd author page `https://unherd.com/author/helen-thompson/`, also Actions-proved; its visible archive was lower-frequency, with a 2026-03-02 item during the audit. | **READY WITH CONFIG** |
| **Jonathan Haidt** | After Babel RSS: `https://www.afterbabel.com/feed` | Existing `rss`; multi-author feed resolved by entry `byline` evidence, including the `Jon Haidt` alias already represented in the V1 model. | Already production-proved from GitHub Actions in the V1 hardening work and retained final-candidate evidence; one GET. | Existing Perigon infrastructure can be considered later for cross-publication coverage only with stable identity evidence and within the request budget; it is not needed for readiness. | **READY** |
| **Steven Pinker** | First-party publications bibliography: `https://stevenpinker.com/publications` | Existing generic `author_page`; person-scoped bibliography with `scope` evidence and external links allowed. This is safe because the page is explicitly Pinker's publications list, not a generic news/mention page. | Actions-proved in run `34376070133`; one GET. The first-party site listed 2026 authored publications including a 2026-09-03 Boston Globe piece during the audit. | No second source is required. Do **not** scope-attribute the site's generic News page: it also contains coverage *about* Pinker and therefore is not equivalent authorship evidence. | **READY WITH CONFIG** |
| **Arthur C. Brooks** | Person-scoped Free Press column RSS: `https://www.thefp.com/s/the-pursuit-of-happiness-with-arthur/feed` | Existing `rss`; person-scoped column feed, `scope` evidence. | Actions-proved in run `34376070133`; one GET; The Free Press column was current through 2026-09-07 during the audit. | Main Free Press feed `https://www.thefp.com/feed` with `byline` evidence; also Actions-proved, but the person feed is cleaner and less likely to lose an item to feed depth. | **READY WITH CONFIG** |
| **Tyler Cowen** | Marginal Revolution author RSS: `https://marginalrevolution.com/marginalrevolution/author/tyler-cowen/feed` | Existing `rss`; entry `byline` evidence. | Actions-proved in run `34375871256`; one GET; exceptionally fresh/high-frequency, with multiple posts on 2026-09-08/09 during the audit. | Same-site author archive is a natural operational fallback if the feed regresses; no separate provider is required for readiness. | **READY WITH CONFIG** |
| **Zeynep Tufekci** | NYT byline RSS: `https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/by/zeynep-tufekci/rss.xml` | Existing `rss`; feed-entry `byline` evidence. | Actions-proved in run `34376070133`; one GET. | `https://www.theinsight.org/feed` is also Actions-proved through the existing RSS adapter, but the public archive is materially stale and should be a fallback rather than the primary source. | **READY WITH CONFIG** |
| **Dan Wang** | First-party RSS: `https://danwang.co/feed/` | Existing `rss`; entry `byline` evidence. | Actions-proved in run `34375871256`; one GET. Publication cadence is deliberately episodic rather than frequent; the first-party site carried the 2025 annual letter on 2026-01-01 during the audit. | First-party homepage `https://danwang.co/` can be consumed by the existing generic `author_page` pattern with person `scope` if the feed regresses. | **READY WITH CONFIG** |

## Result

At this audit boundary:

- **2 / 15 are READY** on an already-shipped production source path: Conrad Black and Jonathan Haidt.
- **13 / 15 are READY WITH CONFIG** using generic adapters that have been live-proved on GitHub-hosted Actions.
- **0 / 15 require new adapter code** for the selected primary path.
- **0 / 15 are technically UNRESOLVED** at the level required to source at least one compliant stream of writing.

That does **not** mean every Voice has exhaustive cross-publication coverage. The audit deliberately separates a production-safe primary source from the larger question of collecting every venue in which a Core Voice may publish.

## Genuine unresolved limitations

### Adam Tooze / Chartbook completeness

Chartbook is the most frequent first-party stream for Adam Tooze and was publicly current throughout the audit, but its direct RSS failed through Hermes on a GitHub-hosted runner in run `34376191426`. Foreign Policy RSS is therefore the best **production-reachable** source now, not a claim that Foreign Policy is his complete output.

Do not evade the Chartbook restriction, spoof access, scrape article bodies, or add a Tooze-specific workaround. If future product requirements demand broader Tooze coverage, use a generic provider/identity route only after stable authorship identity has been proved.

### Blocked publisher surfaces remain blocked

The prior Conrad Black investigation established that New York Sun author/feed surfaces returned HTTP 429 from GitHub-hosted runners. That remains a blocked source, not an invitation to retry more aggressively.

Historical V1 evidence also showed a Jordan Peterson Substack feed returning HTTP 403 from a GitHub runner. Jordan Peterson is Selective, not part of this 15-Voice matrix, but the evidence is useful operationally: publisher/feed reachability must be tested per actual source. The successful Paul Wells Substack probe and failed Adam Tooze Chartbook probe demonstrate that there is no safe blanket assumption that all Substack feeds either work or fail.

## Adapter work and configuration work

No new adapter is justified by this audit. The existing generic stack covers all selected primary paths:

- `rss` for person feeds, author feeds and byline-filtered publication feeds;
- `author_page` for structured person-scoped archives and exact-provider-id indexes;
- existing zero-request morning-pool attribution where ordinary Hermes fetching already found the article;
- existing Perigon support only when stable provider identity and budget constraints justify it.

The later V2 implementation should therefore treat the remaining 13 Voices as **configuration/migration work**, not as 13 bespoke integrations.

One non-blocking code observation came out of the abandoned User-Agent probe: `VoiceHttp` uses `Session.headers.setdefault("User-Agent", USER_AGENT)`, while `requests.Session()` already carries a default User-Agent. The bounded comparison run showed that all four sources under question worked both with current behaviour and with an explicitly forced Hermes User-Agent. Therefore no HTTP change is required to land this audit, and the unfinished hypothesis must not be smuggled into source work.

## Operational guardrails for the implementation wave

1. Keep product membership from `VOICES_V2.md` independent of source state.
2. Add sources through registry/configuration, not person-named code paths.
3. Prefer the person-scoped feed/index when it gives stronger authorship evidence and lower request noise.
4. Use `provider_id` where a stable source-native author identifier exists; otherwise use `byline` or defensible person-page `scope` exactly as the current resolver model requires.
5. Deduplicate shared publication feeds/requests rather than creating linear per-Voice provider work.
6. Do not add provider calls merely to make the source matrix look redundant.
7. A blocked or stale fallback must degrade locally and must never demote a Core Voice.
8. Re-probe a source only when its operational behaviour materially changes; this audit is not a permanent network test suite.

## Cleanup requirement

The `.github/workflows/core-source-audit-probe.yml` workflow used for Wave 1B is temporary evidence-gathering infrastructure. It must not remain on the merge-ready branch. The durable artifact is this document plus the immutable GitHub Actions run history referenced above.

# Sports V2 — Production Source Audit

**Status:** accepted source authority for issues #34–#35  
**Date:** 2026-09-11  
**Parent:** #33  
**Product authority:** `SPORTS_V2.md`

This document records what was actually proved from the network environment that runs Hermes. It distinguishes technical reachability from provider-policy or trademark considerations. A URL working in a browser is not enough.

## Decision summary

| Need | Source | Classification | V2 role |
|---|---|---|---|
| Maple Leafs schedule/results | NHL `api-web.nhle.com` club schedule | **READY** | #35 primary |
| Maple Leafs record/standing | NHL `api-web.nhle.com` standings | **READY** | #35 primary |
| Raptors schedule/results | ESPN public site JSON team schedule | **READY WITH FALLBACK** | #35 primary |
| Raptors record/standing | ESPN public site JSON team detail | **READY WITH FALLBACK** | #35 primary |
| Raptors same-day result context | ESPN public site JSON scoreboard | **READY WITH FALLBACK** | #35 secondary input |
| NBA official CDN | `cdn.nba.com` JSON | **REJECTED** | Do not use from GitHub Actions |
| Blue Jays schedule/results | MLB Stats API | **READY WITH POLICY CAUTION** | #35 primary |
| Blue Jays record/standing | MLB Stats API | **READY WITH POLICY CAUTION** | #35 primary |
| CBC sport RSS | CBC NHL/NBA/MLB/Soccer/Olympics/NFL feeds | **REJECTED FOR GITHUB ACTIONS** | Do not make production dependency |
| Champions League / World Cup | football-data.org | **READY WITH CONFIG** | #37 candidate authority |
| Olympics | event-window sources | **UNRESOLVED BY DESIGN** | #37 owns activation/source choice |
| Leafs/Jays official logo assets | NHL/MLB-hosted SVGs | **TECHNICALLY READY / PRODUCT REJECTED** | Do not ship without permission |
| Raptors official logo | NBA-owned team mark | **PRODUCT REJECTED** | Do not ship without permission |

`READY WITH FALLBACK` means the source is usable but not a formal stable public API contract. Provider failure must yield a quiet unavailable team state rather than fail the Daily. No hidden alternate source is assumed.

## Live GitHub Actions evidence

### Baseline probe — run 34632724665

The first deliberate probe ran from `ubuntu-24.04` in GitHub Actions, the same network class used by the morning build.

Passed:

- NHL season schedule: HTTP 200, 88 games returned for Toronto.
- NHL current standings: HTTP 200, 32 rows, Toronto present.
- MLB Toronto schedule window: HTTP 200, 33 games returned.
- MLB American League standings: HTTP 200, 15 teams, Toronto present.
- NHL-hosted Leafs SVG: HTTP 200.
- MLB-hosted Blue Jays SVG: HTTP 200.

Failed:

- NBA CDN season schedule: HTTP 403.
- NBA CDN current scoreboard: HTTP 403.
- CBC NHL/NBA/MLB/Soccer/Olympics/NFL RSS: every feed timed out at 20 seconds from GitHub Actions.

These failures are product evidence, not transient errors to hide with retries. NBA CDN and CBC are therefore not baseline production dependencies.

### Raptors fallback proof — runs 34633098467 and 34633235274

ESPN public site JSON was then probed independently from GitHub Actions.

Passed:

- `site.api.espn.com/.../basketball/nba/teams/tor/schedule`: HTTP 200; Toronto Raptors identified; events returned.
- `site.api.espn.com/.../basketball/nba/teams/tor`: HTTP 200; record object present; standing summary present (`3rd in Atlantic Division` at probe time).
- `site.api.espn.com/.../basketball/nba/scoreboard`: HTTP 200; event list returned.

This is enough for #35 to derive the same provider-independent snapshot fields as Leafs/Jays without using `stats.nba.com`, NBA CDN, or a computed fake standing.

ESPN's site JSON interfaces are not a formally supported developer API. The adapter must therefore be small, schema-checked, independently failure-isolated, and easy to replace. No scraping of rendered ESPN HTML is allowed.

## Provider contracts for #35

### NHL — Maple Leafs

Primary endpoints:

- `https://api-web.nhle.com/v1/club-schedule-season/TOR/{season}`
- `https://api-web.nhle.com/v1/standings/now`

Required normalized facts:

- stable game id;
- UTC start time;
- game type/state;
- home/away identity and score;
- W/L/OTL record;
- division/conference standing context;
- next scheduled game.

Use no NHL images/content beyond the factual fields necessary to construct the Hermes snapshot.

### ESPN public site JSON — Raptors

Primary endpoints:

- `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/tor/schedule`
- `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/tor`

Optional same-day helper:

- `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard`

Required normalized facts:

- event id and UTC date;
- status/finality;
- competitors, home/away, scores;
- team record summary;
- standing summary;
- next scheduled game.

Do not depend on ESPN artwork, news prose, betting data, player data, or deep game feeds for #35.

Fallback: one Raptors-source failure returns a Raptors `unavailable` snapshot while Leafs/Jays survive. A bounded cached fallback may be added only if its freshness is explicit; #35 need not invent one.

### MLB Stats API — Blue Jays

Primary endpoints:

- `/api/v1/schedule?sportId=1&teamId=141&...`
- `/api/v1/standings?leagueId=103&season={year}&standingsTypes=regularSeason&...`

Required normalized facts:

- `gamePk`;
- UTC game date;
- abstract/detailed game status;
- teams/scores;
- W/L record;
- division/wild-card standing context where present;
- next scheduled game.

MLB's general Terms of Use include restrictions on automated scripts interacting with MLB Digital Properties. The endpoints are technically reachable and widely exposed as JSON, but Hermes should keep requests minimal, factual and personal-use oriented, never mirror provider content, and retain the source behind a replaceable adapter. If policy interpretation changes, the adapter can be replaced without changing the Sports domain model.

## Major-event source

`football-data.org` remains the preferred #37 starting point because its current free coverage includes the UEFA Champions League and FIFA World Cup, including fixtures and tables. Its free plan is key-authenticated and rate-limited (currently documented at 10 requests/minute for authenticated free clients), so it was not represented as an unauthenticated GitHub Actions proof in #34.

#37 must add the key/config and perform its own bounded production-network probe before shipping event mode.

## News-source finding

The targeted CBC sport feeds are useful conceptually but are unsuitable for Hermes's current GitHub Actions deployment: six independent feed URLs all timed out in the production-network probe. #36 should therefore not build its headline system around CBC.

#36 must choose sources that are both targeted enough for deterministic filtering and actually reachable from Actions. Existing Guardian access can remain a candidate, but broad Guardian `sport` ingestion into the normal Gemini pool remains contrary to Sports V2.

## Team marks / logo decision

Technical reachability is not permission to reproduce a mark.

### NHL / Maple Leafs

The NHL-hosted Toronto SVG resolved from Actions, but NHL's current copyright/legal pages state that NHL and team logos/marks are property of the league/clubs and may not be reproduced without prior written consent. Baseline decision: **do not embed, download, recolour, trace, or commit the Leafs mark.**

### MLB / Blue Jays

The MLB-hosted Blue Jays SVG also resolved from Actions. MLB's legal notices state that club names, logos, uniform designs and colour combinations may be used only with permission. Baseline decision: **do not embed, download, recolour, trace, or commit the Blue Jays mark.**

### NBA / Raptors

NBA's current Terms of Use expressly treat team logos as protected intellectual property and restrict logo use without written permission. Baseline decision: **do not ship the Raptors mark.**

### Visual fallback

#38 should begin with typography, abbreviation/wordmark-like plain text written by Hermes (`LEAFS`, `RAPTORS`, `BLUE JAYS`) and the existing Press Navy/Masthead Red design tokens. This preserves the intended restrained identity without reproducing protected logos. Logo support remains an optional later enhancement if an explicit permitted source/licence is obtained.

## Cost / request implications

The #35 baseline requires no new paid API and no AI call:

- Leafs: 2 bounded HTTP requests.
- Raptors: 2 bounded HTTP requests; scoreboard is optional and should only be requested if it materially closes a schedule freshness gap.
- Blue Jays: 2 bounded HTTP requests.
- Gemini: 0 sports records, 0 sports calls.

Adapters should share an HTTP session where appropriate, use explicit timeouts, and never retry indefinitely.

## Operator probe

`scripts/probe_sports_sources.py` is retained as a deliberate manual/operator audit tool. It is not run by deterministic CI and must not become a scheduled poller. Individual source names can be supplied so one blocked provider cannot hide evidence from the others.

The temporary branch-only probe workflow used for this audit must be removed before #34 merges.

## #34 conclusion

The source foundation is sufficient for #35:

- Leafs: NHL-hosted JSON.
- Raptors: ESPN public site JSON, failure-isolated because it is undocumented.
- Blue Jays: MLB Stats API, with documented provider-policy caution.
- no team logos in the baseline;
- no CBC production dependency;
- no NBA CDN dependency;
- no Gemini dependency.

This audit intentionally does not implement rendering, major-event mode, or headline filtering.
# Sports V2 — Toronto-first deterministic sports desk

**Status:** Product/engineering authority for planned Sports V2 work  
**Parent issue:** #33  
**Implementation issues:** #34–#39  
**Last updated:** September 11, 2026

## 1. Purpose

Sports V2 replaces the current generic article-first Sports section with a purpose-built morning sports desk for one Toronto reader.

The section should answer five questions quickly:

1. What happened to the Maple Leafs, Raptors and Blue Jays?
2. How are those teams doing?
3. What is next for them?
4. Did anything genuinely important happen around them that a score/standing cannot explain?
5. Is there a major global sporting event or result worth knowing this morning?

The product is not a live-score app, general sports portal, fantasy product or engagement feed. It remains a finite part of The Daily.

## 2. Locked reader priorities

Priority is explicit and deterministic:

1. **Toronto Maple Leafs** — highest priority.
2. **Toronto Raptors**.
3. **Toronto Blue Jays**.
4. **Major global events** — especially FIFA World Cup and Olympics.
5. **UEFA Champions League**.
6. **Other genuinely major soccer news / major European cups**.
7. **NFL** — major developments, playoffs and Super Bowl; not routine league detail.
8. **Rugby** — major tournaments/finals/deciders only.
9. **Cricket** — off by default.

Toronto FC and the Toronto Argonauts are not Core V2 teams. They can be reconsidered later through an explicit product change rather than drifting into the section through a broad feed.

## 3. Permanent Toronto team presence

The three favourite teams remain visible in Sports in every edition, including offseason periods.

### In season

Each team should show the smallest useful structured state supported by authoritative data:

- last completed result;
- current record;
- compact standing context appropriate to the sport;
- next scheduled game with opponent and Toronto-local date/time;
- concise postseason state when materially useful.

Examples of standing context differ by sport. NHL may use division/conference rank, NBA conference rank, and MLB division/wild-card context. The normalized model should preserve enough structured data to render the right phrase rather than forcing every league into one identical statistic.

### Offseason / inactive

The team does not disappear. It collapses to a quiet line such as:

`MAPLE LEAFS · OFFSEASON · Training camp / next game date when known`

Do not fill space with stale final-season statistics merely to make an inactive row look busy.

A qualifying major offseason update may appear beneath the team.

## 4. Sports is primarily state, not articles

Routine sports information should come from structured data. Scores, schedules, standings, records and competition tables do not need model synthesis.

Sports articles are secondary. Their job is to explain a material change that structured state cannot communicate well.

For each favourite team:

- **maximum one major headline per edition**;
- zero headlines is a valid and expected result;
- a routine game recap is suppressed when the score/result is already represented in the team row;
- offseason teams may still receive one headline for a genuinely important development.

The section must never manufacture filler merely to satisfy an article count.

## 5. Gemini budget contract

The core Sports path is designed to use **zero Gemini tokens**.

Gemini must never decide whether there is sports news worth showing. That decision happens before any model boundary.

### Required flow

```text
structured sports APIs
  -> provider adapters
  -> normalized deterministic sports state
  -> Toronto team snapshots / major-event state

sports news feeds
  -> deterministic entity matching
  -> deterministic significance classification
  -> deterministic dedupe/ranking
  -> 0..N already-qualified headline winners

normal editorial sources
  -> existing Gemini curation for non-Sports sections

sports state + qualified sports headlines
  -> final edition assembly
```

### Hard rules

- no sports-only Gemini call;
- no per-team model call;
- no per-article model call;
- no model classification of a broad sports pool;
- no model call to determine `nothing important today`;
- an empty qualified Sports-news set adds zero Sports material to the model input;
- source headline + public source description/excerpt is the default headline rendering path.

If later real-world evidence shows that a selected major story materially benefits from synthesized prose, the only permitted extension is to attach the **already-selected winner** to the existing once-daily curation request under a prose-only contract. The model may write prose but may not drop, promote, substitute, merge or discover Sports candidates.

Initial production should prefer the fully zero-model Sports path.

## 6. Deterministic major-headline qualification

Sports news discovery must be narrow before classification. Do not ingest an unrestricted general Sport feed and then attempt to clean it up downstream.

### Favourite-team eligibility

The deterministic classifier should support a conservative significance taxonomy including:

- major trade or signing;
- material contract extension;
- significant injury, surgery or long absence;
- coach/GM/front-office hire or firing;
- playoff qualification, elimination or championship;
- material suspension/discipline;
- retirement;
- major award, record or milestone;
- high-impact draft/roster event;
- major ownership/institutional/league development;
- major controversy only where public source metadata clearly supports it.

Explicit low-value/suppressed families include:

- routine game recap already captured structurally;
- previews;
- practice reports and line combinations;
- ordinary quotes/interviews;
- trade speculation or `could sign` stories without an actual event;
- minor roster churn;
- generic `injury update` wording that does not establish material severity;
- prospect/minor-league churn unless product authority later expands scope.

False negatives are preferable to routine noise.

### Ranking

Eligible candidates should be ranked deterministically using inspectable factors such as:

- significance tier;
- trusted-source priority;
- recency;
- direct team/entity match;
- corroboration from more than one trusted source where available;
- linkage to a structured league event where available.

Take at most one winner per favourite team.

Reuse existing URL canonicalization where appropriate. Obvious syndicated/duplicate coverage should collapse before final selection.

## 7. Major Events

Sports V2 has an explicit Major Events layer rather than an open-ended `other sports` feed.

### FIFA World Cup

Very high priority during the tournament. During an active World Cup window:

- Canada receives strong promotion when playing or materially advancing/eliminating;
- show important previous-day results;
- show next meaningful fixtures;
- make group/knockout state understandable;
- Sports may temporarily expand beyond its ordinary compact footprint within a hard event cap.

### Olympics

Very high priority during Games windows. Prioritize:

- meaningful Canadian medal/results;
- major global finals and records;
- medal-table context when useful;
- upcoming Canadian events selectively.

Do not carry a heavy Olympics-specific provider year-round solely for a two-week event. The implementation should activate event-specific inputs during the Games window.

### UEFA Champions League

Ongoing high priority. Structured competition data should cover recent results, upcoming fixtures and useful table/knockout context.

Hermes is a morning paper, not a live-score product. A free source with modest live delay is acceptable if completed results are settled by the 05:00–06:00 Toronto build window.

### Other soccer, NFL and rugby

- other European cups / major soccer: selective finals, knockout rounds and genuinely large developments;
- NFL: playoffs, Super Bowl and exceptional league developments;
- rugby: World Cup, major finals/deciders and exceptional international developments;
- routine coverage remains absent.

Cricket remains excluded unless this document is explicitly changed.

## 8. Event registry

Major-event coverage should be configuration-driven. A configured event may declare:

- stable provider/competition identifier;
- reader priority tier;
- activation window or provider-derived active state;
- result/fixture/table requirements;
- Canada-promotion rule;
- maximum display footprint;
- whether targeted article discovery is enabled;
- fallback behaviour.

This prevents temporary tournaments from becoming permanent polling and UI complexity.

## 9. Source direction

These are current candidates, not production proof. Issue #34 must validate them from normal production networking and update the source matrix with actual request/failure evidence.

| Need | Candidate | Current assessment |
|---|---|---|
| Maple Leafs schedule/results/standings | NHL-hosted `api-web.nhle.com` / NHL stats surfaces | Strong candidate; public web interfaces are used by NHL properties but require explicit stability audit |
| Maple Leafs mark | NHL-hosted `assets.nhle.com` SVG/logo assets | Technically promising; usage/redistribution policy must be checked |
| Raptors scores/schedule/standings | NBA-hosted scoreboard/CDN/stats surfaces | Strong data availability, but public interface stability is less formally documented; fallback required |
| Blue Jays schedule/results/standings | MLB Stats API (`statsapi.mlb.com`) | Strong candidate |
| Champions League / World Cup | football-data.org | Strong candidate; free tier currently includes Champions League and World Cup, fixtures and league tables with delayed scores |
| Sports news | Targeted CBC NHL/NBA/MLB/Soccer/Olympics/NFL RSS | Strong low-cost candidate for deterministic prefiltering |
| Global soccer analysis/news | Narrow Guardian retrieval where useful | Existing integration can be reused, but broad generic Sport ingestion should be retired |
| Olympics | Event-window source strategy | Must be audited; avoid a permanent broad dependency without need |

Research observed on September 11, 2026:

- football-data.org lists UEFA Champions League and FIFA World Cup in its free coverage; its free plan provides delayed scores, fixtures and league tables at 10 calls/minute;
- CBC publishes separate RSS feeds for NHL, NBA, MLB, soccer, Olympics and NFL;
- NHL-hosted web assets expose team logos and the NHL web API exposes team/game data through endpoints used by NHL web properties;
- MLB Stats API exposes schedule/team/stat endpoints appropriate to Blue Jays state.

Those observations justify the audit direction only. They are not a substitute for #34 production verification.

## 10. Failure and freshness contract

Sports is non-critical to Daily publication reliability.

- failure of one provider must not fail the Daily;
- failure of one team source must not suppress successful teams;
- do not silently show stale scores as current;
- if cached fallback data is used, it must have a bounded freshness ceiling and explicit `as of` semantics;
- otherwise show a quiet unavailable state for the affected team/event;
- every external request uses an explicit timeout;
- retries, if any, are bounded and evidence-based;
- the existing Daily idempotency/no-op gate remains ahead of Sports fetching, so a recovery run for an already-published edition does not spend source or model budget.

## 11. Dedicated edition schema

Scores and standings should not masquerade as ordinary story cards.

The exact Python representation may evolve during implementation, but the rendered edition should have a dedicated Sports payload conceptually similar to:

```json
{
  "sports": {
    "teams": [
      {
        "key": "maple-leafs",
        "name": "Toronto Maple Leafs",
        "league": "NHL",
        "phase": "regular",
        "last_result": {},
        "record": {},
        "standing": {},
        "next_game": {},
        "headline": null,
        "source": {},
        "fetched_at": "..."
      }
    ],
    "major_events": [],
    "other_headlines": []
  }
}
```

This is illustrative, not a frozen field-level API. The durable requirements are:

- provider-independent normalized state;
- team order is explicit, never model-ranked;
- source/freshness metadata remains inspectable;
- team/game identifiers are stable;
- Sports membership is independent of Gemini output;
- serialization into `data/latest.json` contains no secret credentials.

## 12. Renderer and visual direction

Sports should be recognizably purpose-built while remaining within Hermes's broadsheet identity.

### Composition

Inside the existing Sports tab:

1. **Toronto** — permanent favourite-team rows in Leafs -> Raptors -> Blue Jays order.
2. **Major Events** — present only when meaningful.
3. **Major Headlines** — optional already-qualified stories.

Do not use a dashboard card grid, horizontal score carousel, fantasy-style stat surface or sportsbook conventions.

### Favourite-team rows

A row should be understandable without tapping. The renderer may use denser tabular alignment than an ordinary article card, but the visual language remains ruled newspaper furniture.

The row should support:

- mark + team name;
- concise previous result;
- compact record/standing phrase;
- next opponent/time;
- dramatically reduced offseason form;
- an optional major headline beneath the team.

## 13. Team marks and theming

Small team marks are encouraged if #34 proves a clean source/usage contract.

They are editorial identifiers, not decorative hero art.

### Two-ink compatibility

`DESIGN.md` has a strict two-ink rule. Sports does not replace it.

Team marks should be normalized visually into the existing Hermes palette:

- **Press Navy**;
- **Masthead Red**;
- paper/neutral inks.

The Toronto teams fit this unusually well: Leafs naturally bias navy, Raptors can use restrained red/navy, and Blue Jays can use the existing red/navy pair.

Do not create full-colour team-background cards or introduce arbitrary league colours into the interface.

### Asset policy

Before committing any logo asset:

- establish the official/league-hosted source;
- determine whether remote use or local redistribution is appropriate;
- document trademark/licensing constraints known from the source;
- prefer stable league-hosted assets when repo redistribution is unclear;
- provide a text/monogram fallback;
- never scrape or vendor an arbitrary third-party logo pack.

Marks are redundant to visible team names and should be treated appropriately for accessibility.

## 14. Cost telemetry

The build should make Sports cost visible without adding an analytics service.

Log at minimum:

- structured requests per Sports provider;
- raw targeted news items fetched;
- items rejected before significance qualification;
- qualified candidates;
- final headline winners;
- Sports records attached to Gemini input;
- approximate Sports model-input characters/tokens if optional model prose is ever enabled.

Initial production acceptance target: **zero Sports records attached to Gemini input**.

## 15. Verification strategy

### Unit/fixture coverage

Cover at least:

- Leafs/Raptors/Jays result normalization;
- record and standing formatting;
- next-game selection;
- preseason/regular/postseason/offseason state;
- no-game days;
- postponed/cancelled games and baseball doubleheaders;
- Toronto timezone/date boundaries;
- source partial/malformed/failure responses;
- no stale-data misrepresentation;
- positive and negative major-headline examples;
- routine recap suppression;
- `trade talk`, `could sign`, routine `injury update` and similar false-positive cases;
- max one major headline per favourite team;
- duplicate/corroborated source handling;
- no cricket leakage;
- event-window activation/deactivation;
- Canada World Cup/Olympics promotion;
- zero Sports model payload on a quiet day;
- serialization/rendering round-trip.

### Live verification

Before production closeout:

- probe real sources from GitHub Actions or equivalent production networking;
- run a representative end-to-end morning build;
- inspect the actual phone-width composition in light and dark/lamplight modes;
- verify partial source failure does not block publication;
- inspect build logs for request and model-cost counters.

## 16. Delivery plan

### #34 — Source audit

Prove the data/news/logo inputs and their fallbacks before architecture hardens around assumptions.

### #35 — Deterministic Toronto state

Build provider adapters and normalized snapshots for Leafs, Raptors and Blue Jays. Zero Gemini.

### #36 — Deterministic major-headline selection

Targeted news discovery, significance taxonomy, dedupe/ranking, one-winner-per-team rule and hard model-budget isolation.

### #37 — Major events / Champions League

Competition registry, Champions League, World Cup and event-window logic for Olympics/NFL/rugby/other major soccer.

### #38 — Broadsheet rendering and team marks

Implement the special-purpose Sports composition and restrained logo treatment once source/asset contracts are known.

### #39 — Integration and production closeout

Remove Sports from ordinary Gemini editorial authority, retire broad generic Sport ingestion, merge the deterministic payload into the edition, add cost/reliability telemetry and complete live/mobile acceptance.

## 17. Non-goals

Sports V2 does **not** include:

- live minute-by-minute scores;
- push notifications for games;
- player-level fantasy statistics;
- betting odds;
- injury dashboards;
- full league scoreboards;
- personalized algorithmic sports recommendations;
- unread counts or sports alerts;
- comprehensive coverage of every league;
- AI-generated sports commentary;
- model-driven interest discovery.

## 18. Success criteria

Sports V2 is successful when a morning reader can open Sports and, in seconds, understand the three Toronto teams and any genuinely important global sporting context without wading through generic articles.

A normal morning should be cheap: structured data plus deterministic code, with **zero incremental Gemini use**. A quiet day is allowed to be quiet. A major World Cup, Olympics or Champions League day can become richer because the event deserves space, not because a generic feed happened to be busy.

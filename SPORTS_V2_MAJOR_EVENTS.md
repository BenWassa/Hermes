# Sports V2 — Major Events Contract

**Status:** issue #37 implementation authority  
**Date:** 2026-09-11  
**Parent:** #33  
**Related:** `SPORTS_V2.md`, `SPORTS_V2_SOURCE_AUDIT.md`

This note records the production source and activation decisions for the Major Events layer. It replaces the earlier assumption that football-data.org would necessarily be the baseline provider.

## Production source decision

A branch-only GitHub Actions probe was run from the same network class as the morning build.

### football-data.org

The repository currently has neither `FOOTBALL_DATA_API_KEY` nor `FOOTBALL_DATA_TOKEN` configured in Actions. football-data.org remains a technically suitable optional adapter candidate — its documented free tier covers Champions League and World Cup fixtures/tables with authenticated, rate-limited access — but #37 does **not** introduce an undeclared production secret requirement.

Classification: **READY WITH CONFIG / OPTIONAL ALTERNATIVE**.

### ESPN public site JSON

The following zero-key surfaces returned HTTP 200 from GitHub Actions:

- `site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard`
- `site.api.espn.com/apis/v2/sports/soccer/uefa.champions/standings`
- `site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`
- `site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings`

The live Champions League probe returned six completed matches from 2026-09-10 and a 36-club League Phase table. Match payloads exposed stable event ids, UTC dates, completion state, home/away competitors and scores; stage was available as `season.slug`. Standings exposed named stats including `gamesPlayed`, `points` and `pointDifferential`.

The World Cup scoreboard accepted bounded date queries and the standings surface returned grouped tables. The adapter therefore uses ESPN site JSON as the zero-key baseline while keeping all parsing provider-local and failure-isolated.

Classification: **READY WITH FALLBACK**. This is an undocumented public site JSON contract, not a formally supported developer API. A provider-shape or network failure must degrade only the affected competition.

## Request budget

Each active ESPN-backed competition uses at most:

1. one bounded scoreboard request covering yesterday through the next seven Toronto-calendar days;
2. one standings request when the event contract calls for standings.

No active competition means no request. No generic soccer scoreboard is fetched.

## Explicit event registry

Only registry entries can enter the Major Events desk.

| Event | Activation | Mode | Structured provider | Article exceptions |
|---|---|---|---|---|
| FIFA World Cup 2030 | 8 Jun–21 Jul 2030 | Event mode | ESPN `fifa.world` | targeted World Cup / Canada only |
| Los Angeles 2028 Olympics | 14–30 Jul 2028 | Event mode | event-window seam | Canada medals/results, finals, records |
| UEFA Champions League | active competition months, excluding Jul–Aug | High | ESPN `uefa.champions` | structured state is primary |
| Rugby World Cup 2027 | 1 Oct–13 Nov 2027 | Selective | headline-only | knockout/final exceptions |
| NFL postseason | Jan–Feb | Selective | headline-only | conference championships / Super Bowl / advancement |

Cricket has no registry entry and no discovery path.

## World Cup

FIFA's current 2030 plan includes three South American centenary matches on 8–9 June, followed by the main opening ceremony/opening matches on 13–14 June and the final on 21 July. Event mode therefore begins on **8 June 2030**, not 13 June.

During World Cup mode:

- Canada-involved matches are promoted within the fixed item cap;
- recent completed results and next fixtures are both preserved where possible;
- the Canada group table is preferred when available;
- ordinary Sports does not become a full tournament dashboard.

## Olympics

The IOC's published LA28 dates are **14–30 July 2028**. Hermes activates Olympics only inside that event window.

The baseline deliberately does not add a permanent Olympics provider years in advance. The domain accepts event-window factual highlights and deterministically prioritizes:

1. Canada medals/results;
2. world/Olympic records;
3. major finals;
4. other explicitly supplied highlights only within the hard cap.

If the Games window arrives without a production source configured, the Olympics snapshot reports `event_source_unavailable`; the Daily still publishes.

## NFL and rugby

These remain headline/event exceptions rather than persistent score products.

- NFL activates only in January–February and requires postseason/Super Bowl significance language.
- Men's Rugby World Cup 2027 activates from **1 October through 13 November 2027** and requires knockout/final significance.
- Neither source creates an always-on standings or score panel.

## Targeted article discovery

Event article discovery is driven only by active registry entries with `article_discovery=true`. Guardian queries are event-specific and bounded. No broad `sport` pool is used as fallback.

The deterministic trigger layer rejects generic previews, pool-table updates and routine coverage when the event contract requires a major exception. Selected event articles remain source headline + public description; #37 adds no Gemini calls or Sports payload to Gemini.

## Failure and size contract

- One competition failure cannot suppress another.
- Standings failure cannot erase valid match state.
- Ordinary Major Events has a six-item global structured cap.
- World Cup/Olympics event mode may expand to twelve structured items total.
- Each registry entry has its own tighter cap.
- Headline-only events never become persistent scoreboards.
- Off-window dates perform zero structured-event requests.

The branch-only probe workflow is evidence only and must be removed before merge.
# Issue 71: Gate incident-level crime on broader civic significance

GitHub issue: [#71](https://github.com/BenWassa/Hermes/issues/71)

Principle: report crime for its civic significance, not because the event is
dramatic. Hermes is a compact morning newspaper, not a breaking-crime feed.

## Trace (why an isolated incident could lead Local Crime)

- Intake: `CBC Toronto` and `Toronto Star GTA` RSS feeds are tagged
  `section_hint: toronto`. Nothing in `fetch.py` or `normalize.py` knows about
  crime.
- Bounded input: `_trim_input` dedupes exact URLs and round-robins by
  `section_hint`. Newest-first feeds mean a fresh local killing is among the
  first Toronto candidates, with no significance test of any kind.
- Model: the system prompt says only "rank by importance". `sensitivity` is
  used for image suppression, not selection. So drama, which the model reads
  from the description, was the only available proxy for importance, and
  victim biography made it more vivid.
- Rendering: the finished card inherits whatever the model chose; no
  deterministic check follows the call.

## Implementation (`src/crime.py`, wired in `src/curate.py`)

No new Gemini call, no new source, no schema change to the edition.

1. Classify (heuristic over public title and description): an *incident* is a
   Toronto-local or Canada-national item naming a specific violent act. It has
   a *significance reason* if the text states a continuing threat, multiple
   victims, a pattern, aggregate trend evidence, policing / court / policy
   consequence, real disruption, a broader public issue (for example intimate
   partner violence, murder-suicide) or a wider investigation. Statements such
   as "no ongoing threat" are removed first. Human-interest terms are not in any
   list, so they cannot move a story either way.
2. Before the model: incidents with no reason are capped at
   `CRIME_INCIDENT_INPUT_CAP` and moved behind ordinary candidates; they cannot
   become Canada-national or major-event recall. The input bound never grows.
3. At the model boundary: incident records alone gain a transient
   `crime_significance` note, and the system prompt gains a short contract
   (reason-first headlines, human-interest details are not hooks, prefer
   aggregate evidence over accumulated anecdotes, important crime stays in).
4. After the model: an incident without a reason cannot stay on Front Page or
   lead a section. Nothing is added, so caps and edition size are unchanged.

## Non-goals and known limits

- Not a crime-statistics module; trend evidence is preferred by prompt and by
  never gating stories that carry it.
- Classification is lexical and conservative by design. Two unsupported
  incidents may still reach the model so a missed signal can be recovered.
- Duplicate reports of one event are classified individually; if the model
  picks the weaker variant of a significant event, the guard applies to it.

## Acceptance evidence

`tests/test_crime_significance.py` covers isolated incidents, active threat,
patterns, mass casualty, disruption, court / policing consequence, trend
statistics, corruption, human-interest invariance, relationship relevance,
out-of-scope stories, the bounded input, dedupe, idempotency, and a single
model call. Move this spec to `docs/closed/` after merge and a production
edition review.

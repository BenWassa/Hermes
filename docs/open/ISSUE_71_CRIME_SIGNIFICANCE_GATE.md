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
2. Before the model: incidents with no reason are withheld from the model input
   (`CRIME_INCIDENT_INPUT_CAP = 0`, owner decision), so they cannot become
   Canada-national or major-event recall. The input bound never grows. Trade-off:
   a real signal the keyword matching misses means that story is not published;
   review real candidate pools and extend the signal lists accordingly.
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

## Closeout verification (2026-10-28)

Pilot verification of PR #85 against the acceptance criteria, on `main` at
`00708af`. Offline suite passes (browser tests excluded locally);
`tests/test_crime_significance.py`: 45 passed. A second reviewer (Codex,
read-only) checked the same mapping; each defect below was reproduced or read
in the code before being recorded.

| Criterion | Status | Evidence |
| --- | --- | --- |
| Isolated incidents lose prominent placement | Met for incidents the matcher recognises; see gap 1 | `crime.py` cap 0 + `enforce_placement`; tests lines 57-99, 308-341, 368-394 |
| Reason accompanies individual coverage | Met at model input (`crime_significance` marker) | `curate.py:215`; test 194-204 |
| Active threats / consequential crime eligible | Met, see gap 2 | tests 126-204, 453-491 |
| Human-interest detail not a hidden signal | Met for tested details; see gap 3 | tests 209-253 |
| No implicit trend-by-anecdote | Prompt rule plus statistics test; see gap 4 | `crime.py:169-173`; tests 171-180 |
| Deterministic first | Met | `crime.py` |
| No extra Gemini call | Met | single-call test 308-338 |
| Size/dedupe/idempotency intact | Met | tests 288-305, 381-394 |
| Regression tests | Met | 45 tests |

### Known gaps (not fixed here; need an editorial decision)

1. **False negative.** `"Man shot in Etobicoke"` with description
   `"Police are investigating."` is not classified as an incident, so an
   isolated shooting passes the gate. Incident detection requires the noun
   `shooting` or specific verb forms.
2. **False positive for significance.** `"Three people stabbed to death in
   Toronto"` is an incident with no reason and is withheld, although an
   explicit multiple-victim count is a stated reason.
3. **Keyword collisions.** `fraud`, `hate crime` and `trend` qualify a story
   without civic substance: "victim was a fraud investigator" (policing/courts),
   "police do not suspect a hate crime" (broader public issue), and a bare
   "trend" (statistics). Negation removal covers threat and randomness only.
4. **Trend evidence is not required**; bare `trend`, `surge`, `spike`,
   `uptick` count as a statistics reason.
5. **Placement backstop is dormant under cap 0.** `enforce_placement` receives
   the post-trim stories, so with every unsupported incident withheld its flagged
   set is empty. Separately, `_normalize_edition` re-marks `lead=True` on a
   section's first story when none is lead, which would undo a lead demotion
   for a section holding only a demoted incident. Defence in depth only: the
   model can only return links it was given.
6. **Stale code docstrings** in `curate.py` (lines ~20-24, ~348-350) still say
   unsupported incidents are "capped"/demoted rather than withheld.

### Remaining before closure

- Owner decision on gaps 1-4 (matcher tuning is an editorial judgment).
- Production edition review required by this spec's own closeout rule. The
  issue stays open and this spec stays in `docs/open/` until then.

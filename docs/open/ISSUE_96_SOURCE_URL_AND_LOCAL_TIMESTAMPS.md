---
status: open
issue: 96
lane: editorial-metadata
owner: unassigned
updated: 2026-10-26
---

# Daily: derive canonical article links and Toronto times from trusted source metadata (HQA-005/006)

**Tracking:** https://github.com/BenWassa/Hermes/issues/96
**Current state:** Implementation merged: PR #102 (1d2ac8b7); seven-edition validation and unmatched-link policy pending.

The GitHub issue is the discussion/approval surface; this is its single retained execution spec under [issue tracking conventions](../ISSUE_TRACKING.md). The requirements below originate from the owner-reviewed issue. Keep only this file updated for durable scope changes; do not create a parallel plan.

---

## Status and evidence
**Scoped only — implementation requires owner approval.** P1/P2 source-integrity follow-up to Sentinel weekly Candidate 2, HQA-005 (canonical links mismatched **2/3** audited dates) and HQA-006 (one verified timezone error, **1/3**). The weekly report covers only three of seven days; these are *observed occurrences*, not systemwide rates. [Weekly synthesis](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/weekly/2026-W43.md), [findings](https://github.com/BenWassa/Hermes/blob/sentinel/reviews/docs/sentinel/FINDINGS.md).
- [2026-10-24 edition](https://github.com/BenWassa/Hermes/blob/9f6b45c0aac31ce4460d1789cbfed09274c80770/docs/index.html): Guardian slug has `:` where captured canonical source uses `-`; [source](https://www.theguardian.com/world/2026/oct/24/ukraine-war-briefing-russian-diesel-tankers-headed-for-north-america-says-moscow-as-us-tries-to-revive-peace-talks).
- [2026-10-25 edition](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/docs/index.html): `neighborhood` vs canonical `neighbourhood`; [source](https://www.theguardian.com/world/2026/oct/24/israel-soldiers-raze-west-bank-neighbourhood-hebron-families-from-homes).
- 2026-10-25 lead reports 08:00Z as 8:00 AM Toronto, whereas 08:00Z is 04:00 EDT; [same-commit evidence](https://github.com/BenWassa/Hermes/blob/1b5faea1c510c378ed654ebcbfdc88b8bc513d19/data/edition_evidence/2026/10/2026-10-25.json).
These establish **identity and display mismatch**, *not* proof that URLs return HTTP 404 or that one specific model stage caused either error.

## Outcome
Never let free-form generated values silently replace deterministic source article identities or timezone-aware source timestamps. All displayed article links and publication times should come from trusted normalized metadata whenever identity can be established. Keep legitimate late additions safely handled without inventing matches.

## Proposed bounded implementation
1. **Map authority once:** trace `src/normalize.py` canonical IDs/URLs and source `pub_date` → `src/curate.py` model input/output and `_normalize_edition` → final JSON/renderer; identify which stage rewrites links or time strings. Do not assume all output links are guaranteed to match a source.
2. **Identity map:** build per-edition deterministic, bounded source-ID/canonical URL mapping for the **actual 60 candidates sent to the model**, accounting for harmless tracking/query differences and exact article deduplication. For a returned, matched card, replace altered model URL with the recorded canonical/public source URL. Do not choose an arbitrary nearest title match.
3. **Unknown links:** define explicit policy for unmatched links, e.g. retain only if independently validated against a documented allowed class of sources, or suppress unsupported link/card while preserving a publishable edition; record reason without inventing provenance. Protect separately selected Following and Sports from ordinary-candidate rewrites.
4. **Time authority:** parse normalized source timestamps with offset-aware conversion using `zoneinfo.ZoneInfo("America/Toronto")`; render using documented local clock/date conventions. Never trust a model-generated free-form publication time when a reliable original timestamp exists. Missing/unparseable times should show a neutral Unknown/omitted value, not current build time.
5. **Measure:** add bounded outcome counters (`matched canonical`, `normalized redirect/tracking`, `unmatched/withheld`, `timestamp parsed/missing`), without expanding public metadata payload or storing secrets. Keep proven #74 evidence semantics.
6. **Validation:** evaluate at least seven consecutive subsequent editions for canonical drift and local-time accuracy. A URL HTTP reachability check is optional and must not be described as completed without actual fetch/redirect evidence.

## Acceptance
- [ ] Both Guardian URL variants in the historical examples resolve to the **exact captured canonical article ID**, not a spelling correction guessed by the model; mismatches demonstrably disappear after a deterministic mapping.
- [ ] Tests cover duplicate syndicated articles, identical titles with different sources, HTTP redirects, tracking params, changed publisher slugs, out-of-input/unmatched hallucinated URLs, missing canonical ID and Following-owned links.
- [ ] 08:00:58Z on 2026-10-25 displays 04:00 EDT with the correct day; UTC midnight, Toronto previous day, DST spring/fall transitions and invalid/missing offsets tested.
- [ ] Existing curation output format, section order/caps, one-model-call path, privacy limits, bounded evidence, publication gate and fail-open treatment preserved.
- [ ] No web request per article added on normal rendering path, and no new paid provider or second AI call.
- [ ] Full deterministic and rendered browser tests green, before/after examples and limitations in focused PR.

## Ownership / branch / non-goals
Suggested branch `fix/editorial-source-metadata-integrity`; proposed owner: final-edition **source identity and timestamp policy**, distinct from factual correctness ([#95](https://github.com/BenWassa/Hermes/issues/95)), Canada intake ([#94](https://github.com/BenWassa/Hermes/issues/94)), Toronto section guarantees ([#83](https://github.com/BenWassa/Hermes/issues/83)), and provenance writer ([merged #80](https://github.com/BenWassa/Hermes/pull/80)). Coordinate edits in `src/curate.py` with #94 and #95, ideally sequentially. No new section, model migration, or redesign. **Approval pending; no code branch opened yet.**

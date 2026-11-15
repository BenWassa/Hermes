---
status: open
issue: 111
lane: editorial-source-fidelity
updated: 2026-11-10
---

# #111 — Prevent unrelated incident blending (HQA-010)

**Issue:** https://github.com/BenWassa/Hermes/issues/111

## Verified example and causal limits

The Nov 2 Toronto lead (pinned f16f9bc3306533e738ab5e581bca48c3a6ca30df) combined a fatal vehicle collision near Guelph with a separate SIU fare-evasion arrest investigation under a single crash link. That day's `edition_evidence` identifies two separate pre-cutoff candidate URLs: the crash article was `final_selected`, the SIU article was `model_input`. This shows an unsupported **published mixed card**, not which internal model step produced it. Existing source metadata repair in `src/editorial_integrity.py` restores link and time but cannot enforce prose fidelity.

## Focused incremental safeguard

- After canonical link restoration, resolve each ordinary card against its *exact matched source* in the actual post-trim input. Never treat other publisher text as evidence that the linked source supports a claim.
- In a high-confidence **disjoint incident-pair case** only, compare source title+public description with the generated card and with other distinct candidate titles+descriptions. Detect a road collision linked to separate police arrest/use-of-force story or the inverse, where the matched source lacks the second incident marker.
- On such a signal, conservatively replace model prose with that linked source's existing public title/description and drop speculative analysis; leave link/time/section/lead unchanged. Do not join two sources under one link or fabricate a combined article. Log bounded counts, not private content.
- Abstain on unmatched links, insufficient metadata, same-incident corroboration, shared source evidence, or absence of a distinct alternative candidate.
- This is not a universal semantic fact checker. More incident categories require verified fixtures and false-positive review before adding patterns; no extra model call or provider fetch.

## Test and release gates

- [x] Deterministic Nov 2 crash/SIU fixture including original two input identities and contaminated headline/summary.
- [x] Negative controls: related same-event reporting; source explicitly covering both events; correct single-event prose; no second candidate; unmatched identity; unrelated topics.
- [x] Direct guard test and curation-pipeline hook test.
- [ ] PR CI green, review diff.
- [ ] Seven later actual published editions manually adjudicated with source provenance; no precision/recall rates without denominator.
- [ ] Owner merge approval and production verification.

Out of scope: political roles (#95), source link/time (#96), crime significance (#71/#109), any provider or scheduling change. Retain HQA-010 Open until production validated, and keep this spec in docs/open/ until merged and closed.
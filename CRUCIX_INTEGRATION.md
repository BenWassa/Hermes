# Hermes × Crucix Integration Plan (v2)

**Status:** Active Draft (Execution-Ready)  
**Date:** 2026-04-10  
**Branch:** `feature/crucix-integration-v2`

---

## 1. Objective

Build a deterministic daily intelligence pipeline:

```
[Crucix OSINT] -> [Normalizer + Filter] -> [Hermes Input Bundle] -> [LLM Briefing + Amplifier] -> [Hermes UI]
```

The LLM must interpret only provided signals. No external retrieval in generation steps.

---

## 2. Non-Negotiable Contracts

### 2.1 Canonical Storage Root

Use one root only:

```
hermes-data/
  raw/
  processed/
  bundles/
  briefings/
  amplifiers/
  logs/
```

`hermes-data/` is local data, excluded from git.

### 2.2 Canonical Domain Enum

To remove cross-doc drift, this is the single enum used everywhere:

- `GEOPOLITICS`
- `MACRO`
- `ENERGY`
- `DEFENSE`
- `TECH`
- `FINANCE`
- `CLIMATE`
- `POLICY`

If this changes, update schema, normalizer, prompts, and tests in one commit.

### 2.3 Signal Schema (v1)

```json
{
  "$schema": "hermes-signal-v1",
  "date": "YYYY-MM-DD",
  "source_count": 0,
  "signal_count": 0,
  "signals": [
    {
      "id": "sig_YYYYMMDD_001",
      "source": "Reuters",
      "domain": "ENERGY",
      "region": "MIDDLE EAST",
      "headline": "Oil rises on Red Sea disruption",
      "summary": "1-3 sentence factual compression",
      "timestamp": "2026-04-10T05:10:00Z",
      "confidence": "HIGH",
      "tags": ["oil", "shipping"],
      "source_url": "https://..."
    }
  ]
}
```

### 2.4 Bundle Schema (v1)

```json
{
  "$schema": "hermes-bundle-v1",
  "date": "YYYY-MM-DD",
  "signals": [],
  "signal_count": 0,
  "previous_briefing": {
    "date": "YYYY-MM-DD",
    "executive_summary": "string",
    "watchlist": ["string"]
  },
  "active_threads": [
    {
      "id": "thread_001",
      "label": "Red Sea Shipping",
      "open_since": "YYYY-MM-DD",
      "last_update": "YYYY-MM-DD"
    }
  ]
}
```

---

## 3. Architecture Boundaries

- **Crucix layer:** fetch only.
- **Normalizer/filter layer:** parse, dedup, classify, rank.
- **LLM layer:** interpret and synthesize; no fetching or enrichment.
- **UI layer:** render JSON only.

No responsibility leakage across layers.

---

## 4. Execution Phases (with Gates)

### Phase 0: Contract Lock (0.5 day)

Deliverables:

1. `docs/SIGNAL_SCHEMA.md`
2. `docs/BUNDLE_SCHEMA.md`
3. Prompt enum alignment in:
   - `docs/DAILY_BRIEFING_PROMPT.md`
   - `docs/INTELLIGENCE_AMPLIFIER_PROMPT.md`

Gate to pass:

- One canonical domain enum present in all docs.
- Prompt JSON examples have no duplicated top-level keys.

### Phase 1: Proof of Value (1 day)

Deliverables:

1. Manual Crucix run for one date/query.
2. Store raw payload in `hermes-data/raw/`.
3. Produce a hand-crafted `signals.json` sample.
4. Run briefing generation with structured signals.

Gate to pass:

- Structured-input output quality is materially better than free-text baseline.
- Every major claim can be traced to at least one `signal.id`.

### Phase 2: Deterministic MVP Pipeline (2-3 days)

Deliverables:

1. `scripts/crucix-runner.js`
2. `scripts/normalizer.js`
3. `scripts/bundle-assembler.js`
4. `scripts/pipeline.js` (rules-only filtering)
5. npm scripts:
   - `hermes:fetch`
   - `hermes:normalize`
   - `hermes:bundle`
   - `hermes:daily`

Gate to pass:

- Pipeline runs end-to-end for a fixed date.
- Re-running with same inputs is stable within accepted variance.
- Errors are surfaced with non-zero exit code and readable logs.

### Phase 3: Quality Hardening (2-4 days)

Deliverables:

1. Dedup pass (exact hash + fuzzy similarity threshold).
2. 48-hour freshness filter.
3. Confidence threshold gate.
4. Output validator requiring signal attribution in major developments.

Gate to pass:

- Noise reduced without deleting key events.
- Validation catches hallucinated claims.

### Phase 4: Automation (0.5-1 day)

Deliverables:

1. Cron at 05:30 local time.
2. Runtime and success/failure logging.
3. Optional retention policy (e.g., 90-day raw retention, longer processed retention).

Gate to pass:

- Three unattended successful runs.

---

## 5. Implementation Blueprint

### 5.1 `scripts/crucix-runner.js`

Responsibilities:

- Accept `--date` (default local today).
- Build query string with date.
- Execute Crucix command.
- Write raw payload to `hermes-data/raw/{DATE}_raw.json`.
- Emit timing + source count logs.

### 5.2 `scripts/normalizer.js`

Responsibilities:

- Parse heterogeneous raw format.
- Map to `hermes-signal-v1`.
- Normalize timestamps, casing, domains, region labels.
- Apply rule-based filters and dedup.
- Write `hermes-data/processed/{DATE}_signals.json`.

### 5.3 `scripts/bundle-assembler.js`

Responsibilities:

- Load same-day processed signals.
- Load latest prior briefing (if any).
- Load active threads from prior outputs.
- Build and write `hermes-data/bundles/{DATE}_bundle.json`.

### 5.4 `scripts/pipeline.js`

Responsibilities:

- Orchestrate full flow with step-level retry policy.
- Stop on first critical failure.
- Produce run log in `hermes-data/logs/{DATE}_run.log`.

Sequence:

```js
await runCrucix(date);
await normalize(date);
await assembleBundle(date);
await generateBriefing(date);   // existing generation workflow
await generateAmplifier(date);  // existing generation workflow
await persistOutputs(date);
```

---

## 6. Prompt Contract Updates

Daily briefing prompt must include hard constraint:

- Use only bundle signals.
- Each `major_developments[]` item must include `signal_ids` referencing bundle IDs.
- If insufficient evidence, reduce certainty instead of inventing.

Amplifier prompt must include:

- `story_id` references must match briefing IDs.
- No restating facts not present in briefing input.

---

## 7. Risks and Mitigations

- **Schema drift:** Maintain schema docs + version tag in outputs.
- **Noisy ingestion:** Rules-based filter before any optional LLM quality pass.
- **Prompt drift:** Add output validation checks post-generation.
- **Operational brittleness:** Step-wise logs + deterministic rerun by date.
- **Data growth:** Retention policy and optional compression for old raw dumps.

---

## 8. Acceptance Criteria

System is considered integrated when all are true:

1. `npm run hermes:daily -- --date YYYY-MM-DD` runs end-to-end.
2. All artifacts are written under `hermes-data/` with expected names.
3. Briefing and amplifier are generated from bundle input only.
4. Claims are traceable to `signal_ids`.
5. Reprocessing past dates is possible without manual edits.

---

## 9. Immediate Next Actions

1. Lock contract docs (`SIGNAL_SCHEMA.md`, `BUNDLE_SCHEMA.md`).
2. Fix prompt JSON duplication and enum drift.
3. Implement `crucix-runner.js` + `normalizer.js` first.
4. Run one real dated sample (`2026-04-10`) and inspect outputs.
5. Add `bundle-assembler.js`, then wire `pipeline.js`.

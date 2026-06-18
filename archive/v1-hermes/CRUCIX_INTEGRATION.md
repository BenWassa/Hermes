# Hermes × Crucix Integration Plan

**Status:** Draft
**Date:** 2026-03-23
**Branch:** `claude/hermes-integration-plan-NMmoD`

---

## 1. Strategic Vision

### Current State

Hermes is a mobile-first intelligence dashboard that ingests daily briefings via manual JSON paste. The production flow is:

```
User writes prompt → LLM generates JSON → User pastes into app → Dashboard renders
```

The system is prompt-driven and human-gated at every step. Each briefing is a one-shot generation with no persistent signal memory or structured input layer.

### Target State

Hermes becomes a **pipeline-driven intelligence system** with deterministic data ingestion, structured normalization, and a controlled LLM reasoning layer.

```
[Crucix OSINT] → [Normalization Layer] → [Hermes Input Bundle] → [LLM Engine] → [Dashboard]
```

The fundamental shift:

| Before | After |
|--------|-------|
| Generate insight on demand | Continuously produce structured intelligence artifacts |
| Prompt-driven, ad hoc | Pipeline-driven, reproducible |
| LLM sources its own context | LLM interprets only provided signals |
| No historical signal record | Owned daily signal dataset |

---

## 2. System Architecture

### Layer Overview

```
┌─────────────────────────────────────────────────┐
│  Layer 4 — Presentation                         │
│  Mobile HUD dashboard (existing Hermes UI)      │
│  JSON-driven, no logic                          │
└─────────────────┬───────────────────────────────┘
                  │ briefing JSON + amplifier JSON
┌─────────────────▼───────────────────────────────┐
│  Layer 3 — Intelligence Engine                  │
│  LLM briefing prompt → Daily Briefing JSON      │
│  LLM amplifier prompt → Intelligence Amplifier  │
│  Uses ONLY provided input bundle                │
└─────────────────┬───────────────────────────────┘
                  │ typed signal bundle
┌─────────────────▼───────────────────────────────┐
│  Layer 2 — Normalization (NEW)                  │
│  Raw OSINT → cleaned signals → typed events     │
│  Deduplication, domain classification, ranking  │
└─────────────────┬───────────────────────────────┘
                  │ raw OSINT dump
┌─────────────────▼───────────────────────────────┐
│  Layer 1 — Ingestion (Crucix)                   │
│  CLI-triggered OSINT aggregation                │
│  ~27 sources, heterogeneous output              │
└─────────────────────────────────────────────────┘
```

### Separation of Concerns

| Layer | Responsibility | Does NOT do |
|-------|---------------|-------------|
| Crucix | Fetch raw data from sources | Interpret, filter, or rank |
| Normalizer | Clean, deduplicate, classify | Fetch or reason |
| Hermes Engine | Interpret + synthesize signals | Fetch or clean data |
| Dashboard UI | Render JSON | Any data processing |

These layers must remain isolated. Do not mix responsibilities.

---

## 3. End-to-End Data Flow

### Daily Pipeline

```
[1] Trigger (cron at 05:30 or npm run hermes:daily)
        ↓
[2] Crucix CLI executes OSINT query
        ↓
[3] Raw output → /hermes/raw/YYYY-MM-DD_raw.json
        ↓
[4] Normalizer script processes raw data
        ↓
[5] Signals written → /hermes/processed/YYYY-MM-DD_signals.json
        ↓
[6] Input bundle assembled (signals + previous briefing + active threads)
        ↓
[7] LLM → Daily Briefing JSON (existing prompt, updated)
        ↓
[8] LLM → Intelligence Amplifier JSON (existing prompt, updated)
        ↓
[9] Outputs stored → /hermes/briefings/ and /hermes/amplifiers/
        ↓
[10] Dashboard reads from store / user imports JSON
```

---

## 4. File Storage Structure

```
/hermes-data/              ← root data store (outside src/, not committed)
  raw/
    2026-03-23_raw.json    ← Crucix dump, unmodified
  processed/
    2026-03-23_signals.json  ← normalized signal array
  bundles/
    2026-03-23_bundle.json   ← full LLM input bundle
  briefings/
    2026-03-23.json          ← final Daily Briefing JSON
  amplifiers/
    2026-03-23_amp.json      ← final Amplifier JSON
```

The `hermes-data/` directory should be added to `.gitignore`. It is your owned intelligence archive, not application code.

---

## 5. Technical Implementation

### Step 1 — Crucix Command Layer

Wrap Crucix execution in a reproducible runner:

```bash
crucix "global macro geopolitics energy markets {DATE}" --json > hermes-data/raw/{DATE}_raw.json
```

If Crucix does not support `--json` output natively, pipe its output through a parser that extracts structured content from text. The runner should:

- Accept a date argument (defaults to today)
- Write raw output to the correct path
- Log source count and execution time

**File to create:** `scripts/crucix-runner.sh` or `scripts/crucix-runner.js`

---

### Step 2 — Normalization Layer

**Goal:** Transform heterogeneous OSINT output into a typed signal array.

**Output schema:**

```json
{
  "date": "2026-03-23",
  "source_count": 14,
  "signals": [
    {
      "id": "sig_001",
      "source": "Reuters",
      "domain": "ENERGY",
      "region": "MENA",
      "headline": "Oil rises on Red Sea shipping disruption",
      "summary": "Houthi attacks on tankers force rerouting...",
      "timestamp": "2026-03-23T05:10:00Z",
      "confidence": "HIGH",
      "tags": ["oil", "shipping", "conflict"]
    }
  ]
}
```

**Domain taxonomy:**

- `ENERGY` — oil, gas, power grids, transition
- `MACRO` — rates, inflation, GDP, central banks
- `GEOPOLITICS` — conflict, diplomacy, sanctions
- `TECHNOLOGY` — AI, semiconductors, cyber
- `MARKETS` — equities, FX, commodities
- `POLICY` — legislation, regulation, elections

**Implementation:** Node.js script (consistent with existing Hermes toolchain).

**File to create:** `scripts/normalizer.js`

---

### Step 3 — Signal Filtering Layer

Raw OSINT is noisy. Apply two passes:

**Pass 1 — Rules-based:**

```javascript
// Remove duplicates by headline similarity (Levenshtein or hash)
// Filter events older than 48 hours
// Remove signals below confidence threshold
// Apply domain classification via keyword map
```

**Pass 2 — Optional LLM pass (quality gate):**

```
System: You are a signal filter for an intelligence pipeline.
Input: Array of raw signals
Task: Return only decision-relevant signals. Remove duplicates, noise, and irrelevant items.
Compress each signal into its atomic event.
Output: Filtered signal array in the same schema.
```

This pass is optional for MVP but critical for quality at scale.

---

### Step 4 — Hermes Input Bundle

Replace the current "paste raw text into prompt" approach with a structured input bundle:

```json
{
  "date": "2026-03-23",
  "signals": [...],
  "signal_count": 14,
  "previous_briefing": {
    "date": "2026-03-22",
    "headline": "...",
    "watchlist": [...]
  },
  "active_threads": [
    {
      "id": "thread_001",
      "label": "Red Sea Shipping Disruption",
      "open_since": "2026-03-18",
      "last_update": "2026-03-22"
    }
  ]
}
```

This becomes the **single source of truth input** for the LLM.

**File to create:** `scripts/bundle-assembler.js`

---

### Step 5 — Prompt Refactor

Update both `docs/DAILY_BRIEFING_PROMPT.md` and `docs/INTELLIGENCE_AMPLIFIER_PROMPT.md`.

**Old instruction (implicit):**
> Use web search and general knowledge to produce today's briefing.

**New instruction:**
> Use ONLY the signals provided in the input bundle. Do not supplement with external knowledge. Every claim in the output must trace to a provided signal. If a signal is absent, do not invent it.

This creates:

- **Determinism** — same input produces consistent output
- **Reproducibility** — briefings can be regenerated from stored bundles
- **Auditability** — every insight has a traceable source signal

---

### Step 6 — Pipeline Runner

Single command to execute the full pipeline:

```bash
npm run hermes:daily
# or
node scripts/pipeline.js --date 2026-03-23
```

Pipeline sequence:

```javascript
async function runPipeline(date) {
  await runCrucix(date);         // Step 1: fetch raw data
  await normalize(date);          // Step 2: clean + classify
  await filter(date);             // Step 3: deduplicate + rank
  await assembleBundle(date);     // Step 4: build input bundle
  await generateBriefing(date);   // Step 5: LLM → briefing JSON
  await generateAmplifier(date);  // Step 6: LLM → amplifier JSON
  await store(date);              // Step 7: write outputs
}
```

**File to create:** `scripts/pipeline.js`

---

## 6. MVP Build Plan

### Phase 1 — Proof of Flow (1–2 days)

Validate the hypothesis before building automation.

1. Run Crucix manually for one query
2. Save raw output
3. Manually convert to signal schema
4. Feed structured signals into existing Hermes prompt
5. Compare briefing quality vs. current unstructured input

**Decision gate:** Does structured multi-source ingestion materially improve briefing quality? If yes, proceed to Phase 2.

---

### Phase 2 — Basic Pipeline (3–5 days)

1. Write `scripts/normalizer.js` with domain classification
2. Write `scripts/bundle-assembler.js`
3. Create `hermes-data/` directory structure
4. Update prompts to accept structured input bundle
5. Run end-to-end manually: Crucix → normalize → bundle → LLM → JSON

---

### Phase 3 — Filtering + Quality (5–7 days)

1. Implement deduplication (headline hash + similarity threshold)
2. Add signal confidence scoring
3. Implement domain classifier with keyword map
4. Add optional LLM filter pass
5. Test signal quality with multiple Crucix runs

---

### Phase 4 — Full Automation

1. Write `scripts/pipeline.js` orchestrator
2. Add `npm run hermes:daily` to `package.json`
3. Configure cron job (05:30 local time)
4. Add pipeline logging + error handling
5. Test full unattended run

---

## 7. Design Decisions

### A — Determinism vs. Flexibility

The LLM becomes an **interpretation layer only**, not a retrieval layer. Crucix owns all data fetching. This eliminates hallucinated signals and day-to-day output drift.

### B — Local-First

The entire pipeline runs locally except the OSINT sources themselves. No vendor dependencies for pipeline execution. The intelligence archive is yours.

### C — Schema Stability

Lock the signal schema early. Changes to `signals[]` shape require updates to the normalizer, bundle assembler, and LLM prompts simultaneously. Version the schema explicitly if it changes.

### D — Incremental Adoption

The existing Hermes UI requires no changes for MVP. The frontend already consumes briefing JSON. The pipeline improves what feeds into JSON generation — the UI stays stable.

---

## 8. What This Unlocks

### Historical Intelligence Dataset

Every day produces a structured signal archive. After 30 days you have a dataset for:
- Trend analysis across domains
- Frequency mapping of recurring themes
- Comparative analysis: "What changed between March and April?"

### Backtesting and Auditability

Stored bundles allow you to replay any past briefing:

```bash
node scripts/pipeline.js --date 2026-03-10 --reprocess
```

This is critical for consulting-grade credibility. You can show the exact inputs that produced a given analysis.

### Multi-Agent Expansion (Future)

The signal bundle becomes a shared input for multiple specialized agents without changing ingestion:

```
signals.json → Analyst Agent   → sector analysis
             → Risk Agent      → threat assessment
             → Scenario Agent  → forward projections
```

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Crucix output is too noisy | Filtering layer (Phase 3) handles deduplication and ranking |
| Source inconsistency across days | Normalization schema enforces consistent shape regardless of source format |
| LLM ignores the input constraint | Prompt engineering + output validation; add assertion that every major development references a signal ID |
| Schema drift as requirements evolve | Version the schema; maintain a `SIGNAL_SCHEMA.md` document |
| Pipeline latency (Crucix + LLM calls) | Accept 5–10 minute pipeline runtime; this runs at 05:30, not on demand |
| `hermes-data/` grows large | Implement a rolling 90-day retention policy in the pipeline script |

---

## 10. Immediate Next Steps

In order:

1. **Run Crucix manually** for one real query (`global macro geopolitics energy markets 2026-03-23`)
2. **Save the raw output** to `hermes-data/raw/2026-03-23_raw.json`
3. **Manually convert** a subset of the output to the signal schema above
4. **Update the existing Hermes prompt** to accept signal array input instead of free text
5. **Compare output quality** — length, specificity, traceability of claims

This is a one-hour test that validates the entire architectural premise before writing any pipeline code.

---

## Appendix A — Signal Schema Reference

```json
{
  "$schema": "hermes-signal-v1",
  "date": "YYYY-MM-DD",
  "source_count": 0,
  "signals": [
    {
      "id": "sig_NNN",
      "source": "string — publication or outlet name",
      "domain": "ENERGY | MACRO | GEOPOLITICS | TECHNOLOGY | MARKETS | POLICY",
      "region": "string — optional geographic anchor",
      "headline": "string — ≤120 chars, factual",
      "summary": "string — 1–3 sentences, key facts only",
      "timestamp": "ISO 8601",
      "confidence": "HIGH | MEDIUM | LOW",
      "tags": ["string"]
    }
  ]
}
```

## Appendix B — Input Bundle Schema Reference

```json
{
  "$schema": "hermes-bundle-v1",
  "date": "YYYY-MM-DD",
  "signals": [...],
  "signal_count": 0,
  "previous_briefing": {
    "date": "YYYY-MM-DD",
    "executive_summary": "string",
    "watchlist": ["string"]
  },
  "active_threads": [
    {
      "id": "thread_NNN",
      "label": "string",
      "open_since": "YYYY-MM-DD",
      "last_update": "YYYY-MM-DD"
    }
  ]
}
```

## Appendix C — npm Scripts

Add to `package.json`:

```json
{
  "scripts": {
    "hermes:daily": "node scripts/pipeline.js",
    "hermes:fetch": "node scripts/crucix-runner.js",
    "hermes:normalize": "node scripts/normalizer.js",
    "hermes:bundle": "node scripts/bundle-assembler.js"
  }
}
```

---

*This document lives at the root of the Hermes repository. Update it as the implementation evolves.*

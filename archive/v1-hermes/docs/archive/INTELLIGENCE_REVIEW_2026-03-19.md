# Hermes Intelligence Review

Date: March 19, 2026

## Purpose

Document the current quality assessment of Hermes as an intelligence product, using the real multi-day export in `tests/hermes-export-2026-03-20T01-44-49Z.json`, and define the next upgrade path.

This review focuses on Hermes as it exists today:

- daily JSON generated externally by a scheduled ChatGPT task
- manual paste/import into the app
- local archive and local review inside the mobile UI

## Current Workflow

Hermes is currently operating as a two-part human workflow, even though the app schema still treats it like a single artifact.

### Step 1: Daily record generation

ChatGPT produces a daily JSON briefing from a scheduled task.

The output is intended to represent the day:

- pulse headlines
- major developments
- risk matrix
- context
- sources

### Step 2: Cross-day synthesis

The user later asks ChatGPT to review multiple days and generate a richer synthesis across the archive.

That synthesis may include:

- thread continuity
- recurring arcs
- redundancy detection
- trend or phase shifts
- better interpretation over time

## Main Finding

Hermes is currently a polished single-day JSON dashboard, not yet a true multi-day intelligence system.

The primary weakness is not visual presentation. The primary weakness is that continuity, memory, and cross-day identity are not first-class runtime concepts in the app.

## What Is Working

### Strong daily structure

The current briefing shape is already useful for scan, understand, and think speeds:

- `today_in_60_seconds`
- `major_developments`
- `risk_matrix`
- `analyst_consensus`
- `strategic_context`

### Good narrative quality in the export

The real export demonstrates:

- coherent day-to-day escalation
- meaningful strategic framing
- useful risk and macro context

This confirms the upstream prompting is already capable of producing strong daily material.

### Good UI for same-day consumption

The app works well as:

- a local daily intelligence console
- a mobile viewer for structured briefing objects
- a personal archive of daily outputs

## Core Problems

### 1. Story identity is not enforced

The same underlying system-level story is repeatedly renamed across days.

Examples from the export include:

- `hormuz-shipping-disruption`
- `story-energy-hormuz`
- `story-hormuz-shipping`
- `story-hormuz-selective-flow`
- `story-hormuz-disruption`
- `story-hormuz-coalition`

Consequence:

- threads cannot be tracked reliably
- archive review becomes fuzzy
- search cannot cluster recurring narratives
- synthesis has to repair identity after the fact

### 2. The app does not use cross-day identity at runtime

The live UI still behaves primarily as a same-day renderer.

Examples:

- importer validates only minimal fields
- pulse-to-modal matching relies on `id` or `domain`, not persistent `story_id`
- archive and search are date-oriented, not thread-oriented

Consequence:

- a story can be documented but still not be operationally traceable inside Hermes

### 3. Memory objects are optional and currently unstable

`active_threads` and `thematic_arcs` appear only once in the reviewed export.

Consequence:

- Hermes has no dependable medium-term memory layer
- users cannot review a story lifecycle inside the app
- synthesis objects are not yet treated as durable product data

### 4. Daily briefing and cross-day synthesis are being conflated

The current schema direction assumes one JSON payload can serve both jobs.

That is too much for one object.

Daily briefing should answer:

- what happened today
- what changed today
- why today matters

Cross-day synthesis should answer:

- what persisted
- what accelerated
- what changed phase
- what stories belong together

Consequence:

- the app has weak boundaries
- prompt design becomes muddled
- memory fields appear inconsistently

### 5. Risk is shown as a snapshot, not an evolving forecast

The current risk model is useful for daily prioritization, but it does not show:

- delta in probability
- delta in impact
- trend direction
- acceleration or stabilization

Consequence:

- users cannot distinguish “still high” from “getting worse”

### 6. There is no verification layer around schema quality

There is currently no active automated test harness for:

- importer validation
- schema normalization
- identity continuity checks
- rendering of richer multi-day objects

Consequence:

- the app cannot safely evolve into a more structured intelligence system without regressions

## Product Direction

Hermes should explicitly adopt a two-artifact model.

### Artifact A: Daily briefing

This is the scheduled-task output.

Its purpose is to create a high-quality daily record with stable structure.

It should prioritize:

- consistency
- stable IDs
- compact daily interpretation
- evidence and sourcing

### Artifact B: Synthesis overlay

This is the later cross-day analysis output.

Its purpose is to analyze a date range and enrich the archive with memory and pattern recognition.

It should prioritize:

- thread repair
- arc detection
- phase shifts
- deltas
- compression
- system-level interpretation

### Important rule

The synthesis overlay should not blindly overwrite the daily record.

Hermes should store both:

- daily records as source-of-day truth
- synthesis overlays as date-range analytical layers

## Upgrade Plan

### Phase 1: Stabilize the daily record

Goal:

Make the scheduled-task output consistent enough that Hermes stops accumulating ambiguous history.

Work:

- tighten the daily schema
- make `story_id` mandatory on all developments
- add an explicit `driver` field to each major development or the daily root
- make `what_changed` a required section
- require `change_type`, `story_stage`, and `previous_brief_refs`
- define stricter prompt rules for canonical IDs

Outcome:

Daily imports become durable building blocks instead of loosely related one-day snapshots.

### Phase 2: Add synthesis as a separate import type

Goal:

Stop forcing multi-day intelligence into the daily payload.

Work:

- define a dedicated synthesis schema
- support import of synthesis objects alongside daily briefings
- attach synthesis objects to a date range
- render `active_threads`, `thematic_arcs`, and related cross-day objects in a dedicated UI layer

Candidate synthesis fields:

- `active_threads`
- `thematic_arcs`
- `story_clusters`
- `delta_risks`
- `phase_shifts`
- `dominant_system`
- `coverage_bias`
- `meta_findings`

Outcome:

Hermes gains a true memory layer without corrupting the daily record.

### Phase 3: Make thread identity operational in the UI

Goal:

Use continuity objects at runtime instead of only documenting them in the schema.

Work:

- make pulse/development matching prefer persistent identity
- add story-thread views
- make archive reviewable by thread as well as by date
- improve search to operate on stories, tags, and arcs instead of raw string blobs

Outcome:

Hermes becomes usable for drift review, recurring-theme analysis, and multi-day tracking.

### Phase 4: Add quality controls

Goal:

Reduce schema drift and regression risk as the product becomes more structured.

Work:

- add import validation beyond minimal JSON shape
- add continuity checks for repeated story IDs
- add tests for importer behavior and rendering of core intelligence objects
- define a small set of golden fixture exports for review

Outcome:

Schema upgrades become safer and easier to maintain.

## Immediate Next Steps

The highest-leverage next work is:

1. redesign the schemas into `daily briefing` and `synthesis overlay`
2. revise the prompts so each prompt has one job
3. update Hermes import/rendering so both artifacts can coexist cleanly

## Prompting Implications

### Daily scheduled prompt

The daily prompt should optimize for:

- factual structure
- stable canonical story IDs
- concise daily interpretation
- explicit daily change markers

It should not try to fully solve long-horizon synthesis.

### Synthesis prompt

The synthesis prompt should optimize for:

- identity repair
- thread continuity
- narrative compression
- phase-change detection
- risk deltas
- system dominance and coverage balance

It should not rewrite the daily archive as if it were the only source of truth.

## Definition of Success

Hermes should move from:

"high-quality structured daily briefings"

to:

"a system that preserves daily records and layers cross-day intelligence on top of them."

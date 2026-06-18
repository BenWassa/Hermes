# Hermes Intelligence Layer UI Strategy

Date: March 20, 2026

## Purpose

Document a strategy for making the Hermes intelligence layer feel organized by story rather than like a flood of disconnected data.

This memo assumes:

- the current daily briefing JSON should remain the input contract for now
- improvements should come primarily from UI-side processing and presentation
- the main design problem is continuity, not lack of signal

## Main Assessment

The current Hermes experience is strong for initial scan but weak for retained understanding.

The first dashboard load works because it answers a simple question:

- what matters today

After that, the interface shifts into a data-object reading mode:

- pulse tiles
- timeline
- risk matrix
- macro indicators
- consensus
- strategic context
- amplifier sections

Each of those components may be individually good, but together they ask the user to rebuild the story architecture mentally.

That is the source of the "information bombardment" concern.

The problem is not that Hermes has too much information.

The problem is that Hermes currently organizes the information by source object and analysis type instead of by remembered narrative unit.

## What The Current App Is Doing

### Daily briefing view is object-first

The main briefing display renders in this sequence:

1. top status strip
2. `today_in_60_seconds`
3. signal architecture widgets
4. consensus
5. strategic context
6. watchlist

That is a clean visual order, but not a strong memory order.

It mixes:

- entry points
- evidence
- interpretation
- forward watchpoints

without keeping them attached to one story container.

### The amplifier is analysis-first

The amplifier modal is currently grouped by analysis categories:

- decision layer
- delta lens
- scenarios
- driver decomposition
- second-order effects
- transmission map
- system map

That structure is logical from an analyst-output standpoint, but it is not how a user remembers evolving situations.

The user is more likely to remember:

- the Hormuz story
- the ECB repricing story
- the sovereign compute story

than:

- one `driver_decomposition` item
- one `transmission_map` edge
- one `second_order` note

### Story runtime exists, but arrives too late

Hermes already has:

- `story_id` on developments
- archive thread grouping
- story view across days
- synthesis thread cards

So the product already contains the right narrative primitive.

The issue is that the primitive is not the organizing center of the main daily intelligence experience.

## What The Current JSON Already Supports

The existing daily schema is already enough to build a story-led intelligence layer without changing input.

Useful fields already present:

- `today_in_60_seconds` gives story priority and scan order
- `major_developments[].story_id` gives story identity
- `major_developments[].headline` gives user-facing story naming
- `major_developments[].driver` gives causal framing
- `major_developments[].change_type` gives delta framing
- `major_developments[].story_stage` gives lifecycle framing
- `major_developments[].why_it_matters_now` gives current relevance
- `major_developments[].next_watchpoints` gives forward continuity
- `what_changed` gives day-over-day movement
- amplifier `driver_decomposition[].story_id` already links analytical content back to stories

This means the near-term problem is primarily a processing problem:

- regroup
- compress
- order
- cross-link

not a schema problem.

## Design Principle

The intelligence layer should answer:

1. what is the story
2. what changed in that story today
3. why is it moving
4. what does it affect
5. what do I watch next

Everything else should support those five questions.

The user should not need to traverse multiple independent sections to reconstruct one narrative.

## Recommended Organizing Model

Use a three-level hierarchy.

### Level 1: Dashboard for orientation

Keep the current dashboard role.

Its job is only to orient:

- top 3 to 5 stories
- overall system condition
- one-line daily shift

This is the "open the app and understand the day in 10 seconds" layer.

### Level 2: Story stack for understanding

After the opening dashboard, the primary scroll should become a story stack.

Each story card should be the main unit of comprehension.

Recommended card structure:

- story label and domain
- headline
- `change_type` plus `story_stage`
- one-sentence driver
- one-sentence why-it-matters-now
- 2 to 3 supporting facts
- 2 forward watchpoints
- optional "system effects" chips
- optional "full thread" action

This turns the interface into:

- story first
- evidence second
- supporting system context third

instead of forcing the user to jump between unrelated panels.

### Level 3: Supporting system layer

Timeline, risk, macro, transmission, and scenario views should become supporting material attached to the relevant story or reachable from it.

They should stop competing with stories as equal top-level blocks.

## Recommended UI Processing Layer

Add a derived view-model step between imported JSON and rendered UI.

The raw JSON can stay unchanged.

Example derived object per story:

```json
{
  "story_id": "story-energy-hormuz",
  "priority_rank": 1,
  "headline": "Oil Shock and War Risk",
  "domain": "ENERGY",
  "change_type": "ESCALATION",
  "story_stage": "PEAKING",
  "driver": "The disruption is now materially altering inflation expectations, shipping costs, and central-bank path assumptions.",
  "why_now": "The story has become a macro transmission channel rather than a regional disruption.",
  "supporting_facts": ["...", "..."],
  "watchpoints": ["...", "..."],
  "amplifier": {
    "decomposition": "...",
    "second_order": ["..."],
    "transmission": ["..."],
    "scenario_summary": "..."
  }
}
```

That processing layer should do five things.

### 1. Resolve story priority

Order stories using:

- `today_in_60_seconds` position first
- impact/system status second
- `change_type` third

This gives a stable "what should I read first" sequence.

### 2. Merge same-story material

For each `story_id`, combine:

- pulse tile
- development detail
- matching amplifier content
- matching risk or transmission references where possible

This creates one story packet instead of many scattered mentions.

### 3. Compress repeated meaning

The current data often says the same thing in multiple ways:

- pulse headline
- executive summary
- driver
- delta lens
- second-order effect

The UI layer should deliberately choose one lead sentence and demote the rest to supporting detail.

Rule of thumb:

- one primary sentence for "what changed"
- one primary sentence for "why it is moving"
- one primary sentence for "why it matters"

### 4. Attach system context to stories

Instead of a freestanding global section wherever possible:

- map timeline nodes to the dominant story when relevant
- map amplifier items by `story_id`
- map second-order and transmission items to a story by keyword/domain/story reference

If an item is truly system-wide, keep it in a separate "cross-story system shift" block.

### 5. Preserve memory anchors

Every story surface should repeat the same compact anchors:

- stable story name
- stage
- change state
- last-seen or ongoing signal

Repetition here is useful. It helps the user remember the narrative across days.

## How To Rework The Amplifier Without Changing JSON

The current amplifier should be reframed from a section list into two modes.

### Mode A: Story-linked amplifier

For each story, show only the amplifier content relevant to that story:

- driver decomposition
- second-order effects tied to that story
- transmission paths tied to that story
- scenario note if the scenario is materially about that story

This should be the default intelligence-layer reading mode.

### Mode B: System-wide overlay

Keep a separate "system view" for:

- cross-story delta lens
- portfolio-level scenario framing
- system map chains that span multiple stories

This protects the high-level analytical richness without dumping it on the user before narrative grounding exists.

## Proposed Information Architecture

Recommended order for the home intelligence flow:

1. Daily orientation strip
2. Apex story tiles
3. "What changed today" delta summary
4. Story stack
5. Cross-story system shifts
6. Deep analysis tools: timeline, risk map, macro, full amplifier system view

This makes the UI read like:

- orient me
- tell me the main stories
- tell me what changed
- show me why it matters
- then let me explore the machinery underneath

## Practical Implementation Approach

### Phase 1: Processing-only upgrade

No input schema change required.

Build a derived selector such as:

- `buildStoryPackets(briefing, amplifier)`

Responsibilities:

- use `today_in_60_seconds` as rank source
- join matching `major_developments` by `story_id` or pulse `id`
- attach amplifier `driver_decomposition` by `story_id`
- infer second-order/transmission matches where obvious
- produce one normalized story packet array

Primary product value:

- immediate reduction in cognitive overload
- better continuity inside a single day
- no import contract churn

### Phase 2: UI restructure

Use story packets to render:

- a compact apex summary
- a story stack replacing most free-floating blocks
- an optional expandable system section below

At this phase, timeline/risk/macro can still exist, but visually demoted beneath the story layer.

### Phase 3: Cross-day continuity enhancement

Once the story stack is working, improve memory with:

- latest prior appearance preview
- "changed since last briefing" sentence derived from `change_type` and `previous_brief_refs`
- direct thread continuation entry point

This can still reuse the existing schema.

## Decision Rules For What Stays Global

Not everything should be forced into story cards.

Keep a separate global block only when the item:

- spans multiple stories equally
- describes system condition rather than one narrative
- is primarily portfolio or allocation level

Examples:

- top-level system status
- a cross-market macro shock note
- a system-wide scenario range

Everything else should default toward story attachment.

## Risks And Tradeoffs

### Risk: over-clustering

If the UI forces every analytical object into a story, genuine system-level insights may disappear.

Mitigation:

- maintain a small explicit "cross-story system shifts" block

### Risk: weak joins

Some amplifier sections do not cleanly reference `story_id`.

Mitigation:

- only auto-attach high-confidence matches
- leave ambiguous items in the system-wide layer

### Risk: duplicate wording

If the UI shows pulse text, development summary, and amplifier phrasing together, clutter returns.

Mitigation:

- enforce one lead sentence per story role
- hide duplicate wording behind expansion

## Recommended Next Build Target

The best next move is not a schema redesign.

The best next move is a UI-processing layer that produces story packets and reorders the home intelligence experience around them.

That gives Hermes:

- stronger memory
- clearer narrative stitching
- less perceived bombardment
- better use of the JSON you already have

## Concrete Recommendation

Implement this sequence:

1. add a `buildStoryPackets(briefing, amplifier)` selector/util
2. create a story-stack component that renders the day from those packets
3. move timeline/risk/macro/amplifier-system sections below the story stack
4. keep the current archive/story-thread model as the cross-day deepening layer

This keeps the dashboard, preserves the JSON contract, and makes the intelligence layer feel like a narrative system instead of a pile of analytical fragments.

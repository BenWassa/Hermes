# Following: morning Opinion integration

Status: production implementation record for issue #11 (Slice B of `VOICES.md`) and issue #46 presentation convergence.

`VOICES.md`, issue #9 and issue #11 remain the product authority for Following semantics. Issue #46 and this note record the shipped Opinion presentation architecture.

## Authority boundary

Following entitlement is fixed before Gemini runs:

```text
ordinary fetch -> normalize
                    |
                    +-> Voice discover / attribute / canonicalize
                              -> finite select_following()
                              -> Following seeds

ordinary editorial pool
  - duplicate followed Opinion candidates
            |
            +-> one Gemini curation call
                  - ranks/cuts ordinary sections
                  - writes prose for fixed Following keys only
            |
            +-> defensive duplicate post-pass
            +-> render Opinion: Following + Today's Opinion
```

Gemini may write `summary`, optional `sub`, and `sensitivity` for a selected followed item. It cannot choose whether the item exists, change its author/publication, change its canonical destination, reorder the selected set, or consume one of the ordinary Opinion slots. If Gemini omits or malforms a Following result, Hermes retains the item and falls back to its legitimate public source description; if that is absent too, Hermes uses a plain non-substantive notice and the publisher link rather than inventing a summary.

## Finite selection

Following keeps the deterministic policy established by #10:

- maximum 6 followed pieces in one morning paper;
- maximum 2 selected pieces per Voice before leftover filling;
- breadth-first round-robin across Voices, then recency;
- final selected cards remain in deterministic recency order;
- syndication non-primaries remain excluded.

This preserves the anti-domination intent without introducing a second cap policy in the edition layer.

## Duplicate ownership

Hermes uses both an early and late guard:

1. Before curation, a canonical followed article is removed only from the **ordinary Opinion candidate pool**. This gives the editor room to choose a different useful Opinion piece instead of spending a slot on a duplicate that will later disappear.
2. After curation, the same canonical check runs again defensively in case a duplicate nevertheless returns.

Following wins the duplicate because it represents an explicit reader preference. Other desks are not stripped merely because a followed writer authored the same canonical URL; the suppression contract is specifically Following versus ordinary Opinion.

## One curation call, not two

Following shares the existing morning curation call.

When Following is non-empty, the user payload contains separate `stories` and `following` arrays. The system instruction limits editorial ranking/cutting to `stories` and requires one prose result for each fixed Following key. When Following is empty, Hermes keeps the raw-story-array request shape.

This avoids a second model request while making explicit-follow survival structural rather than prompt-dependent.

## Rendering

The Opinion tab preserves two semantic groups while using one article presentation system:

```text
Opinion tab
  -> Following
       -> cardHtml(...)
  -> Today's Opinion
       -> cardHtml(...)
```

`Following` appears first when qualifying work exists. `Today's Opinion` follows as the independent editorial group. With zero qualifying followed pieces the page uses the ordinary Opinion treatment and renders no Following heading.

Both groups are composed through the same `opinionGroupHtml` pattern and terminate at the same `cardHtml` story renderer. Following remains a top-level `edition.following` collection; it is not moved into `sections[].stories`, because deterministic reader-choice authority remains distinct from editorial Opinion.

### Shared card contract

Following cards adapt into the normal display fields consumed by the standard story renderer:

- `lead`
- `kicker`
- `headline`
- `sub`
- `summary`
- `analysis`
- `time`
- `tag`
- `sensitivity`
- `image`
- `link`

Following always uses the normal **non-lead** treatment. The followed writer occupies the standard kicker position. Publication and filing time are combined into the standard quiet `time` metadata position, with deterministic fallback to whichever value exists.

There is no Following-specific byline/meta row, card padding, headline treatment, expansion path, image behavior, Read full story action, Ask AI action, keyboard behavior, touch behavior, reduced-motion behavior, or dark-mode variant.

### Serialized field audit

The rendered Following card retains `author` and `publication` in addition to the display fields because `buildPrompt()` uses them to preserve provenance in Ask AI briefings.

The following card-level fields were removed because no runtime consumer remained:

- `paywalled`;
- `voice_ids`;
- `canonical_key`;
- `following: true`.

Those facts may still exist upstream in Voice/seed state where they serve identity, source, or access metadata. They are no longer copied into the presentation record without a consumer.

### Retired presentation paths

Issue #46 removed rather than preserved alongside the shared system:

- `.following-block .card` padding overrides;
- `.follow-meta` CSS and markup;
- the `st.following` conditional inside `cardHtml`;
- Following-only metadata fixture expectations;
- dead card-level presentation fields listed above.

`following-block` and `today-opinion` remain only as semantic group selectors for accessibility, layout geometry, and behavioral tests.

## Visual contract

Following and Today's Opinion share:

- story-rule treatment;
- headline typography;
- standfirst placement;
- quiet metadata treatment;
- expansion spacing and tint;
- image handling;
- Read full story placement;
- Ask AI behavior;
- keyboard/touch behavior;
- reduced-motion behavior;
- dark/lamplight behavior.

The group headings remain distinct because they communicate different editorial authority. Shared card styling does not erase that distinction.

## Verification contract

The deterministic suite covers:

- no followed material;
- one fixed followed item;
- several Voices and several items;
- the finite cap/prolific-Voice policy inherited from #10;
- co-authors;
- duplicate Following/editorial candidates and the defensive post-pass;
- missing image/description/model prose;
- missing author/publication/time display fallbacks;
- canonical outbound destinations;
- local Voice-source failure;
- removal of dead card-level fields.

The browser suite renders the real production template through `src.render.render()` and exercises the generated static artifact in Chromium at 390x844 portrait, 320x568 short portrait, and 844x390 landscape. It proves:

- Following and Today's Opinion share the same card markup structure;
- no `.follow-meta`, Following padding override, or `st.following` presentation branch remains;
- author renders through the normal kicker;
- publication/time render through the normal quiet metadata slot;
- Following remains non-lead while Today's Opinion retains its normal lead behavior;
- zero Following retains the ordinary Opinion state;
- Read full story, Ask AI provenance, touch, keyboard, 44px action targets, reduced motion and horizontal overflow remain intact.

CI preserves rendered HTML plus screenshots as short-lived inspection artifacts. Structural/computed-style assertions are the correctness oracle; screenshots are inspection aids rather than pixel locks.

## Scope boundary

This architecture does not create watcher state, notification cadence, release-time alerts, a writable preference backend, new Voice tier semantics, a new Gemini call, a new top-level Opinion schema, or a new global story-card design.

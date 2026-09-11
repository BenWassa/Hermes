# Following: morning Opinion integration

Status: implementation record for issue #11 (Slice B of `VOICES.md`), with presentation convergence authority added by issue #46.

`VOICES.md`, issue #9 and issue #11 remain the product authority for Following semantics. Issue #46 and this note govern the Opinion presentation convergence described below. This note records the concrete implementation choices where the shipped architecture is narrower or more specific than the design examples.

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

Gemini may write `summary`, optional `sub`, and `sensitivity` for a selected followed item. It cannot choose whether the item exists, change its author/publication, change its canonical destination, reorder the selected set, or consume one of the ordinary Opinion slots. If Gemini omits or malforms a Following result, Hermes retains the item and falls back to its legitimate public source description; if that is absent too, Hermes uses a plain non-substantive notice and the canonical publisher link rather than inventing a summary.

## Finite selection

Slice B keeps the policy #10 already made deterministic:

- maximum 6 followed pieces in one morning paper;
- maximum 2 selected pieces per Voice before leftover filling;
- breadth-first round-robin across Voices, then recency;
- final selected cards remain in deterministic recency order;
- syndication non-primaries remain excluded.

This preserves the anti-domination intent without introducing a second cap policy in the edition layer.

## Duplicate ownership

The design proposed a post-curation duplicate pass. Slice B uses both an early and late guard:

1. Before curation, a canonical followed article is removed only from the **ordinary Opinion candidate pool**. This gives the editor room to choose a different useful Opinion piece instead of spending a slot on a duplicate that will later disappear.
2. After curation, the same canonical check runs again defensively in case a duplicate nevertheless returns.

Following wins the duplicate because it represents an explicit reader preference. Other desks are not stripped merely because a followed writer authored the same canonical URL; the suppression contract is specifically Following versus ordinary Opinion.

## One curation call, not two

`VOICES.md` allowed followed pieces either to share the normal curation call or to use a smaller dedicated summarization pass. Slice B keeps the existing one-call morning architecture.

When Following is non-empty, the user payload becomes an object containing separate `stories` and `following` arrays. The system instruction explicitly limits editorial ranking/cutting to `stories` and requires one prose result for each fixed Following key. When Following is empty, Hermes keeps the previous raw-story-array request shape.

This avoids a second model request while making explicit-follow survival structural rather than prompt-dependent.

## Rendering

The production template changes only inside Opinion when followed material exists:

- `Following` appears first;
- author, publication and filing time remain visible;
- `Today's Opinion` follows as a separate editorial group;
- both use the existing card expansion, `Read full story`, Ask AI, keyboard and touch machinery;
- no avatar, badge, unread count, horizontal feed, history, recommendation language, or browser-only Follow control is added;
- paywalled work uses the same canonical outbound publisher link and no access-control workaround.

With zero qualifying followed pieces the page uses the previous ordinary Opinion treatment and renders no Following heading.

### Issue #46 presentation convergence

The two Opinion groups are semantically different but must not maintain separate article-component families.

The locked target is:

```text
Opinion tab
  -> Following group
       -> ordinary supporting-story card renderer
  -> Today's Opinion group
       -> ordinary story card renderer
```

`Following` remains a deterministic reader-choice collection. `Today's Opinion` remains a Gemini-curated editorial collection. Their collection boundaries remain separate, while their article presentation converges on the same story-card primitive.

#### Shared card contract

Following cards must use the existing display fields already consumed by the normal story renderer:

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

Following uses the normal **non-lead** story treatment. The first followed item must not be promoted to a lead merely to imitate Today's Opinion because that would imply editorial ranking that does not exist.

The followed writer should be carried through the standard kicker position. Publication and filing time should be carried through the normal quiet metadata/time position with deterministic fallbacks when either is missing. The card should not gain a Following-only byline row.

Authoritative fields such as `author`, `publication`, `paywalled`, `voice_ids`, and `canonical_key` may remain on the serialized Following record only where a real non-rendering consumer needs them. The issue implementation must audit their usages and remove presentation-only or dead fields instead of preserving them by habit. The `following: true` marker should be removed if that audit shows no remaining consumer.

#### Schema boundary

Do not move Following into `sections[].stories` merely to make rendering convenient. The top-level `edition.following` boundary is intentional because it preserves reader-choice authority separately from ordinary editorial Opinion and is already inspected by Voice/roundup code.

No broad Gemini/output-schema migration is required for issue #46. Do not add author/provenance fields to every ordinary curation record or enlarge the daily model prompt simply to achieve visual parity.

If implementation needs a small render-time adapter, it belongs at the existing Opinion/render boundary and must adapt into the normal story-card contract. Do not introduce a second long-lived `FollowingCard` schema or a new top-level Opinion payload.

#### Renderer consolidation

Following and Today's Opinion should be composed through one small Opinion-group pattern and one `cardHtml`-equivalent story renderer. Exact helper names are not product authority; the constraints are:

- one card renderer;
- one group-heading composition pattern;
- separate semantic collections;
- separate empty-state rules where necessary.

The implementation should delete, not leave dormant:

- `.following-block .card` visual padding overrides;
- `.follow-meta` CSS and markup;
- any Following-only article rendering branch replaced by the shared card renderer;
- stale test assertions that exist only to protect the retired custom treatment;
- redundant fixture/presentation fields that have no remaining consumer.

Structural classes/selectors may remain only where they still serve accessibility, group identity, layout, or stable behavioral testing.

#### Visual contract

Following and Today's Opinion should therefore share:

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
- missing image/description and missing model prose;
- canonical paywalled destinations;
- local Voice-source failure.

The browser suite renders the real production template through `src.render.render()` and exercises the generated static artifact in Chromium at 390x844 portrait, 320x568 short portrait, and 844x390 landscape. It checks real tab/card/touch/keyboard/Ask-AI/link behavior, 44px action targets, reduced motion and horizontal overflow. CI preserves the rendered HTML plus screenshots as a short-lived inspection artifact.

For issue #46, verification must additionally prove:

- Following and Today's Opinion cards share the same story-card renderer/classes/structure;
- no `.follow-meta` element remains;
- no Following-specific card-padding override remains;
- author is visible through the normal kicker position;
- publication/time render through the normal quiet metadata position with missing-field fallbacks;
- Following records remain non-lead;
- Today's Opinion lead behavior is unchanged;
- zero Following retains the ordinary Opinion state;
- deterministic membership/order, duplicate suppression, canonical links and sensitivity behavior are unchanged;
- browser interaction/accessibility acceptance remains green at all existing mobile/landscape viewports;
- light and dark/lamplight composition remain coherent.

Prefer structural and computed-style assertions over pixel-perfect screenshot comparison. Screenshots remain useful inspection artifacts, not the primary correctness oracle.

## Scope boundary

Issue #12 remains outside this document's original Slice B scope. Issue #46 likewise does not create watcher state, notification cadence, release-time alerts, workflow concurrency for watcher publishing, a writable preference backend, new Voice tier semantics, a new Gemini call, or a new global story-card design.
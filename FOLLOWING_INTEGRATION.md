# Following: morning Opinion integration

Status: implementation record for issue #11 (Slice B of `VOICES.md`).

`VOICES.md`, issue #9 and issue #11 remain the product authority. This note records the concrete Slice B choices where the implementation is narrower or more specific than the design examples.

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
- author, publication and filing time are one quiet metadata line under the headline;
- `Today's Opinion` follows as a separate editorial group;
- both use the existing card expansion, `Read full story`, Ask AI, keyboard and touch machinery;
- no avatar, badge, unread count, horizontal feed, history, recommendation language, or browser-only Follow control is added;
- paywalled work uses the same canonical outbound publisher link and no access-control workaround.

With zero qualifying followed pieces the page uses the previous ordinary Opinion treatment and renders no Following heading.

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

## Scope boundary

Issue #12 is untouched. Slice B does not create watcher state, notification cadence, release-time alerts, workflow concurrency for watcher publishing, or a writable preference backend.

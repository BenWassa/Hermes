# Product

## Register

product

> Product with editorial soul: design serves the fast morning read, but the
> broadsheet identity (masthead, serifs, kickers) is non-negotiable character.

## Users

One reader: Ben, in Toronto. Opens The Daily on a phone around 7:00 AM from a
push notification, often before getting out of bed or over coffee. The edition
should already be there: the primary build target is the **05:00
America/Toronto hour**, with bounded recovery if GitHub scheduling is delayed
or dropped, and normal publication by **06:00 local time**. The session is short
and finite: skim the front page, dip into two or three sections, expand a
handful of stories, done in five to ten minutes. Reads like a business
professional: wants the world, the markets, and the city, synthesized, not
aggregated. There is no second user, no growth funnel, no engagement metric.
The only KPI is "was this morning's read worth it."

## Product Purpose

An autonomous overnight pipeline that assembles a personalized Toronto morning
newspaper: wire APIs and local RSS in, one curated edition out, rendered as a
single static page and pushed once per day. It exists to replace doomscrolling
three news apps with one finite, finished paper. Success looks like: the
edition is fresh and waiting every morning, the lead stories carry real
synthesis (the "why it matters", not just the what), and the whole read fits
comfortably in a phone-sized morning window.

The morning operating contract is deliberately local-time based. The Daily
starts around 05:00 `America/Toronto`; a small minute offset is acceptable to
avoid GitHub Actions congestion. Recovery attempts may follow, but once the
Toronto-calendar edition exists they must become no-ops before expensive source
or Gemini work. Issue #25 owns implementation and production reliability for
this contract.

## Opinion and Voices

Opinion has two legitimate jobs: editorial discovery and deliberate following.
Hermes may guarantee new work from explicitly chosen **Voices** across
publications, while still curating a separate ordinary Opinion selection. A
Voice is a person, not a publisher and not an algorithmic interest profile.
Following must remain finite and quiet: no `For You` feed, unread-count
treadmill, social graph, recommendation loop, or infinite archive.

Voices has three reader surfaces, but only one proactive Voice interruption:

1. **Morning Following** — qualifying Voice work inside the finite Daily.
2. **Recent Core writing** — a bounded, quiet in-app shelf. Core articles are
   collected and deduplicated silently and remain available for optional
   browsing. The user may check it or ignore it; nothing there creates an
   unread obligation or notification.
3. **Weekly Core digest** — Hermes screens the week's Core writing for actual
   attention-worthiness, keeps the shortlist deliberately small, produces one
   compact weekly summary, and may send **one** restrained weekly ntfy
   notification linking to it.

Publication by a Core Voice is collection eligibility, not evidence that a
piece deserves interruption or inclusion in the weekly digest. Weekly screening
should prefer substantive/new explanatory value, material relevance to Hermes's
editorial interests, novelty versus the other candidates, and useful breadth.
Routine churn, minor reactions and redundant pieces should remain browseable
without occupying the digest.

There are **no routine per-article Voice notifications** and no per-article
Gemini calls merely because a Core Voice published. The weekly digest is the
sole proactive Voice notification product. Prefer one bounded weekly
screening/synthesis model call; if it fails, degrade to a conservative small
deterministic selection. Paywalls and publisher access controls are never
bypassed.

Morning Daily notification remains a separate Daily product and is unaffected.
See `VOICES.md` for the proven identity/source architecture and `VOICES_V2.md`
for current tier and weekly-notification semantics. Issue #29 owns the
weekly-only notification and relevance-screening correction; it supersedes only
the release-alert policy introduced by #26/PR #28.

## Brand Personality

Classic broadsheet, refined. Three words: **authoritative, calm, finished**.
The interface should feel like a well-set print paper that happens to be on a
phone: confident serif headlines, restrained navy-and-red accents on warm
paper tones, a masthead with presence. Evolution of print DNA, not
reinvention. The emotional goal is the settled feeling of reading a finished
morning paper, the opposite of a feed's open-ended pull.

## Anti-references

- **News-app engagement slop**: infinite scroll, red badges, BREAKING banners,
  clickbait cards, algorithmic "for you" energy. The Daily is finite by
  design; nothing may imply there is always more.
- **Generic SaaS/AI aesthetic**: rounded card grids, gradient accents,
  glassmorphism, dashboard vibes. Nothing that says "template".
- **Cluttered legacy news sites**: ad-slot density, competing headlines,
  tiny cramped text, CNN/local-TV visual noise.

## Design Principles

1. **The finite paper.** Every screen communicates "this is today's edition,
   complete". Clear beginnings and ends; no bottomless anything.
2. **Hierarchy is the product.** The editor already ranked the news; the
   design's job is to make that ranking legible in one glance. Leads must
   look like leads.
3. **Print DNA, phone ergonomics.** Broadsheet typography and structure, but
   every touch target, safe area, and scroll behavior is honest to a
   one-handed phone read in bed.
4. **Quiet chrome, loud content.** Navigation, weather, and controls recede;
   headlines and summaries carry the visual weight.
5. **One reader, no compromise.** No feature exists for a hypothetical
   audience. Anything that doesn't improve Ben's five-minute morning read is
   noise.

## Accessibility & Inclusion

- Reading context is dim-light mornings; type sizes and contrast must hold up
  at arm's length in bed, not just at desk distance.
- Touch targets sized for a sleepy thumb (44px minimum).
- Respect reduced-motion preferences; motion is subtle regardless.
- No WCAG certification target, but body text contrast should meet AA as a
  matter of craft.

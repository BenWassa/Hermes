---
name: The Daily
description: A personalized Toronto morning newspaper, typeset for one reader's phone.
colors:
  press-navy: "#1a2744"
  masthead-red: "#8b1a1a"
  newsprint-cream: "#efece6"
  paper-warm: "#faf8f3"
  ink: "#17130d"
  ink-sub: "#453f38"
  ink-muted: "#635d54"
  meta-gray: "#6c665c"
  rule-gray: "#dcd6cc"
  rule-warm: "#e3ded4"
  tint-open: "#f2ede4"
  tint-analysis: "#ece6da"
  strip-ink: "#f7f4ee"
typography:
  display:
    fontFamily: "Georgia, serif"
    fontSize: "2.375rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Georgia, serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.25
  title:
    fontFamily: "Georgia, serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.25
  toggle:
    fontFamily: "Georgia, serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1
  body:
    fontFamily: "Georgia, serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.7
  sub:
    fontFamily: "Georgia, serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.4
  caption:
    fontFamily: "Georgia, serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "Arial, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    letterSpacing: "0.12em"
  label-sm:
    fontFamily: "Arial, sans-serif"
    fontSize: "0.625rem"
    fontWeight: 700
    letterSpacing: "0.12em"
  meta:
    fontFamily: "Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    letterSpacing: "0.04em"
  chip:
    fontFamily: "Arial, sans-serif"
    fontSize: "0.5625rem"
    fontWeight: 700
    letterSpacing: "0.08em"
rounded:
  chip: "2px"
  img: "3px"
spacing:
  hair: "6px"
  compact: "10px"
  card: "14px"
  gutter: "20px"
components:
  tab:
    textColor: "{colors.ink-muted}"
    typography: "{typography.label}"
    padding: "12px 18px"
  tab-active:
    textColor: "{colors.press-navy}"
    typography: "{typography.label}"
    padding: "12px 18px"
  story-card:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink}"
    padding: "14px 0"
  story-card-lead:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink}"
    padding: "20px 0 16px"
  tag-chip:
    backgroundColor: "{colors.masthead-red}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.chip}"
    padding: "1px 6px"
  readmore-link:
    textColor: "{colors.press-navy}"
    typography: "{typography.label}"
---

# Design System: The Daily

## 1. Overview

**Creative North Star: "The Morning Broadsheet"**

A finished print paper folded onto a phone. Every element answers to one
question: would this belong on a well-set front page? The system is built
from print furniture, not app chrome: a masthead with presence, hairline
rules between stories, uppercase sans kickers against serif headlines, a
single navy that does the work of a whole palette. The page is finite, and
the design says so; it has a top, sections, and an end.

The system explicitly rejects news-app engagement slop (infinite scroll, red
badges, BREAKING banners), the generic SaaS/AI aesthetic (rounded card grids,
gradients, glassmorphism), and cluttered legacy news sites (ad-slot density,
competing headlines). It is authoritative, calm, finished.

**Key Characteristics:**
- Paper metaphor carried by warm neutrals: Newsprint Cream ground, Paper White page
- One structural color (Press Navy) plus one editorial accent (Masthead Red)
- Serif-first typography; sans-serif appears only in small uppercase labels
- Ruled, not boxed: hierarchy through hairline borders and weight, never containers
- Flat as newsprint; no shadows anywhere

## 2. Colors

Two inks on warm paper: navy for structure, red for editorial heat, and a
ladder of grays doing the quiet work.

### Primary
- **Press Navy** (#1a2744): The paper's structural ink. Masthead rule, weather strip ground, active tab, lead-story rules, read-more links. Where Press Navy appears, the page is asserting order.

### Secondary
- **Masthead Red** (#8b1a1a): Editorial heat, spent sparingly. Kicker labels and flag chips (DEVELOPING, WAR) only. Its scarcity is what makes a flagged story feel flagged.

### Neutral
- **Newsprint Cream** (#efece6): The desk the paper sits on; page background beyond the column.
- **Paper Warm** (#faf8f3): The sheet itself; the reading column. A tinted white, never pure #fff, so a full-brightness phone in a dark bedroom reads as paper, not glare.
- **Ink** (#17130d): Headlines and primary text; a warm near-black, not #000.
- **Ink Sub** (#453f38): Subheads, standfirsts, and expanded body text.
- **Ink Muted** (#635d54): Inactive tabs.
- **Meta Gray** (#6c665c): Timestamps, dateline, taglines, footer. Meets AA at small sizes on Paper Warm; never lighter.
- **Rule Gray** (#dcd6cc): Hairline rules between story cards.
- **Rule Warm** (#e3ded4): Hairline rules inside an opened story.
- **Tint Open** (#f2ede4): Ground of an expanded story card.
- **Tint Analysis** (#ece6da): Ground of the "Why it matters" editor's note and the stale-edition ribbon.
- **Strip Ink** (#f7f4ee): Warm white text on the Press Navy weather strip.

### Named Rules
**The Two-Ink Rule.** Press Navy and Masthead Red are the only chromatic
colors on the page. Navy structures, red flags. A third color is a defect.

**The Scarce Red Rule.** Masthead Red carries heat, so it must stay rare.
Red is allowed on kicker labels and on *hot* flag chips only
(DEVELOPING, BREAKING, LIVE, WAR, ALERT, URGENT). Procedural flags (FINAL,
EDITORIAL) take a Press Navy chip instead, so a red chip still signals urgency.
Never red on backgrounds larger than a chip, never body text, never links.

**The Lamplight Rule.** The system ships a dark edition via
`prefers-color-scheme: dark`: deep navy-black paper (#151a22), cream ink
(#e9e3d5), desaturated red (#d1726b). The broadsheet furniture (masthead,
rules, kickers, tints) is preserved; only the ink and paper invert. Darkness
is a lighting change, not a redesign.

## 3. Typography

**Display Font:** Georgia (serif)
**Body Font:** Georgia (serif)
**Label Font:** Arial (sans-serif)

**Character:** A single workhorse serif set with print conviction, sparked by
tiny industrial sans labels. The contrast is between roles, not families:
big bold serif headlines against small tracked-out uppercase sans kickers.

Sizes are in rem so iOS text-size preferences scale the whole paper (root is
100%, so 1rem = 16px by default).

### Hierarchy
- **Display** (700, 2.375rem, lh 1, -0.01em): The masthead title only.
- **Headline** (700, 1.375rem, lh 1.25): Lead story headlines.
- **Title** (700, 1.0625rem, lh 1.25): Standard story headlines.
- **Body** (400, 0.9375rem, lh 1.7): Story summaries inside expanded cards.
- **Sub / Caption** (400 italic, 0.875-0.8125rem, lh 1.4): Standfirsts and weather detail.
- **Label** (700, 0.625-0.6875rem, 0.12em tracking, UPPERCASE, Arial): Kickers, tabs, timestamps, dateline, footer.

### Named Rules
**The Two-Family Rule.** Georgia for everything readers read; Arial only for
uppercase furniture under ~0.75rem. A sans-serif headline or serif label is
a typesetting error. (Tabs are Arial label type, not Georgia.)

## 4. Elevation

Flat as newsprint. The system uses no shadows anywhere; depth is conveyed by
ink weight and background tint alone. An opened story is "lifted" by tinting
its ground (Tint Open) and ruling it off, exactly as a print pull-quote sits
in a tinted box. Layering exists only in the sticky tab bar, which overlaps
content by position, not by shadow.

### Named Rules
**The No-Shadow Rule.** `box-shadow` is prohibited. If an element needs
separation, rule it off with a hairline or tint its ground.

## 5. Components

Set in ink: components read as print furniture, ruled off rather than boxed
in. Square corners throughout (2-3px radii exist only to keep chips and
images from looking sharp-cornered at small sizes).

### Story Card
- **Corner Style:** none; cards are ruled, not boxed
- **Background:** Paper White; Tint Open (#f8f7f4) when expanded
- **Separation:** 1px Rule Gray top border; lead stories get a 3px Press Navy top rule
- **Internal Padding:** 14px vertical (20px top for leads), no horizontal (column gutter handles it)
- **Behavior:** whole card toggles expansion; +/− glyph at top right signals state

### Kicker + Flag Chip
- **Kicker:** Label type in Masthead Red, above the headline
- **Hot chip:** Masthead Red ground, Strip Ink text, ~9px, 2px radius; DEVELOPING/BREAKING/LIVE/WAR/ALERT/URGENT only
- **Cool chip:** Press Navy ground, same shape; all procedural flags (FINAL, EDITORIAL). Per the Scarce Red Rule, red chips are earned, not default.

### Tabs (Section Nav)
- **Style:** Label type (Arial, ~11px, 0.12em, uppercase), horizontally scrollable strip, sticky at viewport top; min 44px touch height
- **Default:** Ink Muted text, transparent underline
- **Active:** Press Navy text, 3px Press Navy underline; auto-scrolls into view on select
- **Bottom rule:** 2px Press Navy across the strip

### Weather Strip
- **Style:** Press Navy ground, white text, single-line summary
- **Behavior:** tap toggles a 7-day row, ruled with translucent white hairlines

### Read More Link
- **Style:** Label type in Press Navy, no underline at rest, underline on hover

### Masthead (Signature Component)
- Dateline (Gray Meta, uppercase, tracked) over "THE DAILY" in Display over
  tagline (Gray Meta label). Ruled off below with 4px Press Navy. This is
  the identity moment; nothing else on the page competes with it.

## 6. Do's and Don'ts

### Do:
- **Do** separate content with hairline rules (1px Rule Gray) and weight, in the print manner.
- **Do** keep Press Navy structural and Masthead Red editorial, per the Two-Ink Rule.
- **Do** keep the page finite: a masthead at the top, a footer colophon at the end.
- **Do** size touch targets for a sleepy thumb: 44px minimum for tabs, cards, and toggles.
- **Do** hold body text at 0.9375rem/1.7 or better, in rem so iOS text-size preferences carry; the reading distance is arm's length in bed.
- **Do** pad every screen edge with `env(safe-area-inset-*)`; the paper launches installed from a 7AM push, under the notch and home indicator.
- **Do** preserve the reader's place: never rebuild the whole page on a tap, and keep scroll and open state across interactions.

### Don't:
- **Don't** introduce news-app engagement slop: infinite scroll, red badges, BREAKING banners, clickbait cards, or any "for you" energy (PRODUCT.md anti-reference, verbatim).
- **Don't** use pure #fff or #000; tint every neutral toward the paper, light edition and lamplight edition alike.
- **Don't** use the generic SaaS/AI aesthetic: rounded card grids, gradient accents, glassmorphism, dashboard vibes (PRODUCT.md anti-reference, verbatim).
- **Don't** recreate cluttered legacy news sites: ad-slot density, competing headlines, tiny cramped text (PRODUCT.md anti-reference, verbatim).
- **Don't** use box-shadows, gradients, or borders thicker than hairlines except the masthead (4px), lead (3px), and active-tab (3px) navy rules.
- **Don't** use `border-left` or `border-right` stripes as colored accents on callouts or cards; rule across the top or tint the ground instead.
- **Don't** add a third chromatic color. Two inks, warm grays, nothing else.

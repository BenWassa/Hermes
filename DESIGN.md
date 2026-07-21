---
name: The Daily
description: A personalized Toronto morning newspaper, typeset for one reader's phone.
colors:
  press-navy: "#1a2744"
  masthead-red: "#8b1a1a"
  newsprint-cream: "#efece6"
  paper-white: "#ffffff"
  ink: "#111111"
  ink-sub: "#444444"
  ink-muted: "#666666"
  gray-meta: "#999999"
  rule-gray: "#dddddd"
  rule-warm: "#e0ddd8"
  tint-open: "#f8f7f4"
  tint-analysis: "#f1efe9"
typography:
  display:
    fontFamily: "Georgia, serif"
    fontSize: "38px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Georgia, serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.25
  title:
    fontFamily: "Georgia, serif"
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Georgia, serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Arial, sans-serif"
    fontSize: "10px"
    fontWeight: 700
    letterSpacing: "0.12em"
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
- **Paper White** (#ffffff): The sheet itself; the reading column.
- **Ink** (#111111): Headlines and primary text.
- **Ink Sub** (#444444): Subheads and standfirsts.
- **Ink Muted** (#666666): Inactive tabs.
- **Gray Meta** (#999999): Timestamps, dateline, taglines.
- **Rule Gray** (#dddddd): Hairline rules between story cards.
- **Rule Warm** (#e0ddd8): Hairline rules inside an opened story.
- **Tint Open** (#f8f7f4): Ground of an expanded story card.
- **Tint Analysis** (#f1efe9): Ground of the "Why it matters" editor's note.

### Named Rules
**The Two-Ink Rule.** Press Navy and Masthead Red are the only chromatic
colors on the page. Navy structures, red flags. A third color is a defect.

**The Scarce Red Rule.** Masthead Red may only appear in kickers and flag
chips. Never backgrounds larger than a chip, never body text, never links.

## 3. Typography

**Display Font:** Georgia (serif)
**Body Font:** Georgia (serif)
**Label Font:** Arial (sans-serif)

**Character:** A single workhorse serif set with print conviction, sparked by
tiny industrial sans labels. The contrast is between roles, not families:
big bold serif headlines against small tracked-out uppercase sans kickers.

### Hierarchy
- **Display** (700, 38px, lh 1, -0.01em): The masthead title only.
- **Headline** (700, 22px, lh 1.25): Lead story headlines.
- **Title** (700, 17px, lh 1.25): Standard story headlines.
- **Body** (400, 15px, lh 1.7): Story summaries and analysis inside expanded cards.
- **Sub** (400 italic, 14px, lh 1.4): Standfirsts under headlines.
- **Label** (700, 10-11px, 0.12em tracking, UPPERCASE, Arial): Kickers, tabs, timestamps, read-more, footer.

### Named Rules
**The Two-Family Rule.** Georgia for everything readers read; Arial only for
uppercase furniture 11px and under. A sans-serif headline or serif label is
a typesetting error.

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
- **Chip:** Masthead Red ground, Paper White text, 9px, 2px radius, 1px 6px padding; sits inline before the kicker text

### Tabs (Section Nav)
- **Style:** Label type, horizontally scrollable strip, sticky at viewport top
- **Default:** Ink Muted text, transparent underline
- **Active:** Press Navy text, 3px Press Navy underline, weight 700
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
- **Do** hold body text at 15px/1.7 or better; the reading distance is arm's length in bed.

### Don't:
- **Don't** introduce news-app engagement slop: infinite scroll, red badges, BREAKING banners, clickbait cards, or any "for you" energy (PRODUCT.md anti-reference, verbatim).
- **Don't** use the generic SaaS/AI aesthetic: rounded card grids, gradient accents, glassmorphism, dashboard vibes (PRODUCT.md anti-reference, verbatim).
- **Don't** recreate cluttered legacy news sites: ad-slot density, competing headlines, tiny cramped text (PRODUCT.md anti-reference, verbatim).
- **Don't** use box-shadows, gradients, or borders thicker than hairlines except the masthead (4px), lead (3px), and active-tab (3px) navy rules.
- **Don't** use `border-left` or `border-right` stripes as colored accents on callouts or cards; rule across the top or tint the ground instead.
- **Don't** add a third chromatic color. Two inks, warm grays, nothing else.

# The Daily — App Style Guide

This document describes the visual identity of The Daily so that app icons, splash screens, and any future UI work stays consistent with the existing design.

---

## Concept

The Daily is a personal morning newspaper. The visual language is deliberately **print-editorial**: broadsheet newspaper aesthetic translated to mobile, not a news-app aesthetic. Think broadsheet folded to pocket size — restrained, typographic, high contrast. No illustrations. No gradients. No rounded bubbles. The UI should feel like something that could have been set in hot metal type and then adapted to a screen.

---

## Colour Palette

| Role | Hex | Usage |
|---|---|---|
| Navy (primary) | `#1a2744` | Masthead title, section borders, tab active state, weather strip, footer |
| Crimson (accent) | `#8b1a1a` | Kicker labels, tag badges (DEVELOPING / WAR / LIVE / EDITORIAL) |
| Ink | `#111111` | Body text, headlines |
| Warm white | `#ffffff` | Card backgrounds, masthead |
| Newsprint | `#efece6` | Page background (shows between cards on narrow screens) |
| Warm off-white | `#f8f7f4` | Open/expanded card background |
| Rule grey | `#dddddd` | Story dividers |
| Caption grey | `#444444` | Subheadlines (italic) |
| Muted grey | `#999999` | Date, time stamps, footer text |

---

## Typography

| Element | Font | Size | Style |
|---|---|---|---|
| Masthead title "THE DAILY" | Georgia, serif | 38px | 700 weight, tight tracking |
| Section tabs | Georgia, serif | 13px | UPPERCASE, 0.04em letter-spacing |
| Lead headline | Georgia, serif | 22px | 700 weight |
| Story headline | Georgia, serif | 17px | 700 weight |
| Subheadline / deck | Georgia, serif | 14px | Italic, `#444` |
| Expanded body copy | Georgia, serif | 15px | 1.7 line-height |
| Kicker / tag / timestamp | Arial / sans-serif | 10–11px | UPPERCASE, tracked |
| Tagline | Arial / sans-serif | 10px | UPPERCASE, 0.18em letter-spacing, `#999` |

---

## Layout

- **Max-width:** 680px, centred on a newsprint `#efece6` background
- **Masthead:** Full-width white block, 4px navy bottom border
- **Weather strip:** Full-bleed navy band, collapses/expands with a chevron tap
- **Tab nav:** Sticky at the top when scrolling, 2px navy bottom border, Georgia uppercase
- **Stories list:** 20px horizontal padding; each story separated by a 1px rule (lead story: 3px navy rule)
- **Cards expand inline** — tap headline to open summary + image + read-more link in place

---

## Icon Design Direction

The icon should look like the app itself — editorial, typographic, print-inspired. Target aesthetic: a **miniature newspaper front page** or **masthead crop**.

**Primary concept:** A square or slightly rounded-square canvas with a white background, a visible newspaper-rule border (thin navy rectangle), and "THE DAILY" set in Georgia bold at the top. Below the masthead rule, a few thin horizontal bars suggest headline text. Optionally a navy bottom footer rule.

**Alternative concept:** The Caduceus of Hermes (the app's namesake) rendered as a clean, single-colour stamp — navy on white, or white on navy — in a style that looks like a newspaper printer's mark or masthead seal.

**Do not use:**
- Gradients or drop shadows
- Rounded icons (the icon should feel rectilinear / broadsheet)
- Colour photography or illustrations
- Sans-serif typography in the main icon text

**Sizes needed:**
- `icons/icon-192.svg` — 192×192 (home screen, Android)
- `icons/icon-512.svg` — 512×512 (splash, PWA store)
- `icons/icon-180.png` — 180×180 (iOS apple-touch-icon, PNG)
- `icons/icon-32.png` — 32×32 (favicon)

---

## Tone

Calm. Serious. Uncluttered. The design respects the reader's attention — no badges, no red notification dots, no engagement-bait colour. The crimson accent (`#8b1a1a`) is used sparingly and only for genuinely urgent editorial signals (war, breaking news, developing).

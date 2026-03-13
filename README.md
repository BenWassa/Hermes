# Hermes

GlobalBrief is a mobile-first intelligence dashboard for daily AI-generated geopolitical and macroeconomic briefings.

## Structure

- `src/` - application source code
- `docs/` - project documentation
- `archive/` - previous project snapshots

## Current Scope

- Mobile HUD interface for daily briefings
- JSON paste import flow
- Archive and search views
- Progressive disclosure briefing layout
- Visual streams for timeline, risk matrix, and macro indicators

## Versioning

- Semantic Versioning with `v` git tags is used for releases.
- Changelog is maintained in `CHANGELOG.md`.
- Versioning and release policy lives in `docs/VERSIONING.md`.

## Briefing Format

- Daily JSON import format is documented in `docs/DAILY_BRIEFING_FORMAT.md`.
- Product and UX vision is documented in `docs/VISION.md`.

## Firebase Setup

1. Copy `.env.example` to `.env`.
2. Set `VITE_FIREBASE_API_KEY` manually.
3. Install dependencies with `npm install`.
4. Run `npm run dev`.

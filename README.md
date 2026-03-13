# Hermes

Hermes is a mobile-first intelligence dashboard for daily AI-generated geopolitical and macroeconomic briefings.

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
2. Fill in the Firebase web app values in `.env`.
3. In Firebase Console, enable `Authentication` -> `Sign-in method` -> `Google`.
4. In Firebase Authentication settings, make sure your local dev host and Firebase Hosting domain are listed under authorized domains.
5. This app uses Firebase Auth client-side only. If the auth session disappears, the UI returns to the onboarding sign-in view automatically.

## Firebase Hosting

Static Firebase Hosting is enough for the current app. The repo already ships with SPA hosting config in [firebase.json](./firebase.json) and a default Firebase project in [.firebaserc](./.firebaserc).

Deploy flow:

1. Install the Firebase CLI if needed: `npm install -g firebase-tools`
2. Log in: `firebase login`
3. Build and deploy hosting: `npm run deploy:hosting`

Because the app is a Vite SPA, Hosting only needs to serve `dist/` and rewrite routes to `index.html`.

## Development

- Dev server on your local network: `npm run dev`
- Install dependencies with `npm install`.
- Run `npm run dev`.

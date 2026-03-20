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

The default Firebase web app config for Hermes is checked into the client bundle, so local dev and GitHub Actions deploys do not require extra env setup for the current project.

1. Optional: copy `.env.example` to `.env` only if you want to override the default Firebase project locally.
2. In Firebase Console, enable `Authentication` -> `Sign-in method` -> `Google`.
3. In Firebase Authentication settings, make sure your local dev host and Firebase Hosting domain are listed under authorized domains.
4. Enable `Firestore Database` in the same Firebase project.
5. This app uses Firebase Auth for identity and Firestore for shared content plus access control.
6. Access is managed by Firestore documents in `access/{uid}` rather than a hardcoded UID allowlist. Seed each approved user with `active: true` and `role: 'admin'` or `role: 'reader'`.

## Firebase Hosting

Static Firebase Hosting is enough for the current app. The repo already ships with SPA hosting config in [firebase.json](./firebase.json) and a default Firebase project in [.firebaserc](./.firebaserc).

Deploy flow:

1. Install the Firebase CLI if needed: `npm install -g firebase-tools`
2. Log in: `firebase login`
3. Build and deploy hosting: `npm run deploy:hosting`

Because the app is a Vite SPA, Hosting only needs to serve `dist/` and rewrite routes to `index.html`.

## Shared Data Model

- `briefings/{id}` stores shared daily briefing documents keyed by `YYYY-MM-DD`
- `syntheses/{id}` stores shared synthesis overlay documents
- `access/{uid}` stores allowlist and role data for each approved Firebase Auth user

Firestore rules live in [firestore.rules](./firestore.rules). Only approved active users can read shared content, and only admins can write it.

## Development

- Dev server on your local network: `npm run dev`
- Install dependencies with `npm install`.
- Run `npm run dev`.

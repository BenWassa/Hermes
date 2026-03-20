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
3. For frontend-only changes, build and deploy hosting: `npm run deploy:hosting`
4. For Firestore rules and indexes only, deploy Firestore config: `npm run deploy:firestore`
5. For app releases that change both frontend code and Firestore access, deploy both together: `npm run deploy:app`

Because the app is a Vite SPA, Hosting only needs to serve `dist/` and rewrite routes to `index.html`.

## Shared Data Model

- `briefings/{id}` stores shared daily briefing documents keyed by `YYYY-MM-DD`
- `syntheses/{id}` stores shared synthesis overlay documents
- `amplifiers/{id}` stores shared intelligence amplifier documents keyed by briefing ID
- `access/{uid}` stores allowlist and role data for each approved Firebase Auth user

Firestore rules live in [firestore.rules](./firestore.rules). Only approved active users can read shared content, and only admins can write it.
If a newly added collection ships in the frontend before Firestore rules are deployed, signed-in users will see `permission-denied` from that collection until `npm run deploy:firestore` or `npm run deploy:app` is run.

## Development

- Dev server on your local network: `npm run dev`
- Install dependencies with `npm install`.
- Run `npm run dev`.

# Testing on Mobile Devices

Because Hermes uses Firebase Authentication, you cannot test on a mobile device on your local network (e.g., `192.168.x.x`) by default, because Firebase only authorizes `localhost` out of the box.

To test on your mobile device over Wi-Fi without Firebase Auth blocking you:

1. **Find your Mac's Local IP Address:** Run `ipconfig getifaddr en0` in your Mac's terminal (e.g., `192.168.1.164`).
2. **Whitelist the IP in Firebase:** 
   - Go to the [Firebase Console](https://console.firebase.google.com/) for this project.
   - Navigate to **Authentication** > **Settings** > **Authorized domains**.
   - Click **Add domain**, paste your IP address (e.g., `192.168.1.164`), and save.
3. **Start the Dev Server:** Ensure you run `npm run dev` (which includes the `--host` flag to broadcast it locally).
4. **Access on Mobile:** Navigate to `http://YOUR_LOCAL_IP:5173` on your mobile device connected to the same Wi-Fi.

> **Note:** Your local IP address may change sporadically depending on your router's DHCP lease. If access breaks in the future, re-check your IP address and update the authorized domains list in Firebase.

## Setup

1. Copy `.env.template` to `.env` and fill in Firebase config

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [Unreleased]

## [1.1.0] - 2026-03-19

### Added
- Shared Firestore-backed `briefings` and `syntheses` collections so approved users see the same Hermes content across devices.
- Firestore-backed `access/{uid}` authorization model with admin and reader roles.
- Firestore security rules and checked-in Firestore project config files.

### Changed
- Import flow now writes shared data to Firestore instead of browser-local storage.
- Export flow now includes both daily briefings and synthesis overlays in one archive.
- UI controls now reflect role-based access, hiding shared write actions from readers.

## [1.0.5] - 2026-03-13

### Changed
- Patch version bump for the current Firebase Hosting deployment line.

## [1.0.4] - 2026-03-13

### Changed
- Switched Hermes to a checked-in default Firebase web config so GitHub Actions and local builds no longer depend on repo secrets for the current project.
- Simplified Firebase Hosting and release workflows by removing the temporary `VITE_FIREBASE_*` secret injection path.

## [1.0.3] - 2026-03-13

### Changed
- Added a third header pill for an analyst-facing `Driver` signal, with a layout tuned to fit mobile widths more reliably.
- Firebase Hosting GitHub Actions builds now require and inject the full `VITE_FIREBASE_*` web config at build time.

### Fixed
- Removed the fake Firebase API key fallback so broken auth config cannot silently ship in production bundles.

## [1.0.0] - 2026-03-13

### Added
- Firebase Google authentication gate with onboarding sign-in flow and automatic fallback when no valid session exists.
- Static Firebase Hosting deployment script and setup guidance for shipping the Vite SPA.
- System status HUD badge in the briefing header for global condition and volatility posture.
- Higher-density pulse tiles with richer schema support for `domain`, `summary`, `status`, `target`, and `metric`.
- Signal Architecture visual layer with timeline, threat map, and macro indicator streams.
- Real-time import validation and richer schema guidance in the add-briefing view.

### Changed
- Default dev server now binds with `--host` so the app is reachable on the local network.
- Header layout, pulse hierarchy, and risk matrix presentation were redesigned for denser mobile scanning.
- Sample briefing data and JSON format documentation were upgraded to match the live UI schema.
- 60-Second Pulse interactions now route directly into Tactical Breakdown filtering and scroll targeting.

### Fixed
- Mobile pulse affordance visibility and lower-card spacing issues in the pulse grid.
- Live JSON validation now uses the same sanitization path as import submission.

## [0.1.0] - 2026-03-13

### Added
- Initial GlobalBrief mobile prototype (React + Vite + Tailwind).
- Modular app structure (`components`, `views`, `hooks`, `data`, `utils`).
- Product vision document for the commission scope.

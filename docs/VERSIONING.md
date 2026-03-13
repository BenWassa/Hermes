# Versioning Policy

This repository uses Semantic Versioning with `v` tags.

## Rules

- `MAJOR` (`v2.0.0`): breaking changes.
- `MINOR` (`v1.3.0`): backward-compatible features.
- `PATCH` (`v1.2.4`): backward-compatible fixes.
- Pre-releases use `-rc.N` (example: `v1.4.0-rc.0`).

## Source of Truth

- `package.json` `version` is the app version.
- Git tags (`vX.Y.Z`) are release markers.
- `CHANGELOG.md` tracks release notes.

## Commit Style (Recommended)

Use Conventional Commits to make history and release notes predictable.

- `feat: add archive filters`
- `fix: prevent invalid JSON import crash`
- `docs: update vision and IA`
- `chore: update build config`

Breaking changes should include `!` or a `BREAKING CHANGE:` footer.

## Release Workflow

1. Ensure `main` is clean and up to date.
2. Pick bump type:
   - `npm run release:patch`
   - `npm run release:minor`
   - `npm run release:major`
   - `npm run release:rc`
3. Update `CHANGELOG.md`:
   - move items from `Unreleased` to the new version section
   - add release date
4. Push commit + tags:
   - `git push origin main --follow-tags`
5. GitHub Action builds on tag push and publishes a GitHub Release with generated notes.

## Best-Practice Guardrails

- Release only from `main`.
- Never mutate old tags.
- Keep each release focused; avoid bundling unrelated changes.
- Require successful CI before pushing release tags.
- Document user-facing impact in changelog entries.

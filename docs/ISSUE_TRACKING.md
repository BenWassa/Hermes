# Issue tracking convention

Hermes uses GitHub issues as the execution unit and repository issue specs for substantial active work.

## Active work

- Keep detailed issue specs in `docs/open/` while the issue is active.
- Name specs `ISSUE_<number>_<SHORT_DESCRIPTION>.md`.
- Link the GitHub issue to the spec and the spec back to the GitHub issue.
- Keep one authoritative spec per issue. Update the existing spec rather than creating parallel planning documents.
- Scope implementation, acceptance criteria, tests, non-goals, dependencies, and relevant production evidence in the spec when they materially matter.
- Small issues that do not need a durable execution spec may remain GitHub-only; do not create documentation solely for ceremony.

## Completion

An issue spec moves from `docs/open/` to `docs/closed/` only after the work is complete on merged `main` and any required production verification is finished.

During the same closeout pass:

- reconcile the spec to the shipped result if implementation materially changed the plan;
- move the file rather than copying it, so no stale active duplicate remains;
- close the GitHub issue;
- remove or reconcile superseded temporary planning documents;
- update any durable product/build documentation made inaccurate by the change.

`docs/closed/` is an archive of completed issue specs, not a second source of active requirements.

## Repository hygiene

- Do not create overlapping specs for the same work.
- Do not leave completed issue specs in `docs/open/`.
- Do not move an issue spec to `docs/closed/` merely because a PR exists; merge and required verification come first.
- Prefer updating existing durable architecture/product documentation over adding another document when the information belongs there.
- Generated GitHub Pages assets under `docs/` remain separate from issue lifecycle documentation.

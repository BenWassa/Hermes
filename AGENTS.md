# AGENTS.md

Entry point for any agent working in this repo. Built from the repo's own docs. Items marked TODO were not confirmed and need Ben.

## What this is

- **The Daily:** an autonomous overnight pipeline that builds one personalized Toronto morning newspaper, publishes it to GitHub Pages and sends one ntfy push.
- Python pipeline in `src/` (orchestrator: `src/build.py`), rendered static output in `docs/`, tests in `tests/`.
- Product authority: [PRODUCT.md](PRODUCT.md) and [PRD_daily_newspaper.md](PRD_daily_newspaper.md). Production contract: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md). Overview: [README.md](README.md).
- Studio index entry: https://github.com/BenWassa/studio/blob/main/projects/INDEX.md

## Read first

1. [PRODUCT.md](PRODUCT.md) for the one reader, the 05:00 to 06:00 Toronto contract and design stance
2. [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for the current production contract
3. [EDITORIAL_PROVENANCE.md](EDITORIAL_PROVENANCE.md) before touching anything editorial
4. [docs/ISSUE_TRACKING.md](docs/ISSUE_TRACKING.md) for how work is tracked
5. [DESIGN.md](DESIGN.md) for the visual system

## Where work is tracked

- **GitHub Issues are the execution unit.** Substantial active work gets a spec in `docs/open/` named `ISSUE_<number>_<SHORT_DESCRIPTION>.md`.
- Move the spec to `docs/closed/` only after the work is on merged `main` and any production verification is done. Move it, do not copy it.
- Small issues may stay GitHub-only. Do not create docs for ceremony.

## Commands

```bash
pip install -r requirements-dev.txt
python -m playwright install --with-deps chromium   # for the rendered-browser tests
python -m src.voices.audit                          # validate the voice registry (offline)
python -m pytest                                    # deterministic and rendered-browser suite
```

- Offline quality gates use no API keys or quota. See the release skill for the full list: [.claude/skills/release/SKILL.md](.claude/skills/release/SKILL.md).
- CI (`.github/workflows/ci.yml`) runs the voice audit and pytest and keeps rendered inspection artifacts.

## Hard rules

- **Do not spend API quota casually.** Gemini, Guardian, NYT, Perigon, GNews and NewsData calls cost money or limits. Prefer offline tests and `--dry-run`.
- **Never print, commit or log secrets.** Names only: `GEMINI_API_KEY`, `GUARDIAN_API_KEY`, `NYT_API_KEY`, `PERIGON_API_KEY`, `GNEWS_API_KEY`, `NEWSDATA_API_KEY`, `NTFY_TOPIC`. Local values go in `.env` (git-ignored). `.env.example` is the template.
- **Do not hand-edit generated output.** `docs/index.html` and the edition evidence file are written and pushed by `build.yml`. The voice state files (`data/voice_roundup_state.json`, `data/voice_watch_state.json`) are maintained by the bot (recent `chore(voices): ...` commits by `github-actions[bot]`). Edit them only when an issue says to.
- **Do not tag or version-bump.** There is no versioned package. Old `v1.x` tags belong to the archived v1 dashboard. See the release skill.
- **Editorial integrity is non-negotiable.** Do not weaken provenance, fact guard or integrity checks in `src/editorial_*.py` to make a test pass.
- Sports stays deterministic and outside the Gemini story pool. Canada-national intake is an internal lane, not a rendered section.
- The scheduled build must be a no-op once the Toronto-calendar edition exists, before any expensive provider or model work.

## Protected paths (do not change without Ben's explicit approval)

```
.github/workflows/**        schedules, secrets wiring and bot push permissions
.env*  (except .env.example)
docs/index.html and other generated output
data/voices.json  and the *_state.json files
src/editorial_*.py  EDITORIAL_PROVENANCE.md
requirements*.txt   (dependency changes)
archive/**          historical, read-only
```

## Notes for agents

- `main` receives frequent bot commits (the daily build and voice workflows push to it). Run `git pull --rebase` before starting and before pushing.
- GitHub scheduled events have been delivered hours late. Do not assume a schedule fired. Verify from the Actions run list.

## Git

- Prefer Conventional Commits (`type(scope): subject`). History already conforms: 40 of the last 40 commits (all bot-authored). Human commits should match.
- One logical change per commit. Squash merge. Add the Co-Authored-By trailer for agent work.
- No em dashes in anything written for Ben.

## Studio rules

Global policy (authority order, permission tiers, quality evidence) lives in the studio repo: https://github.com/BenWassa/studio. This file may be stricter, never looser.

## TODO for Ben

- Confirm the protected path list, especially whether `requirements*.txt` should be protected.
- Confirm whether agents may run live provider calls (`--live`) in cloud sessions, and under what budget.
- Confirm whether any human-authored work should go through a PR or directly to `main`.

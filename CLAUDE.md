# Hermes — agent guidance

The Daily: an overnight pipeline that builds a Toronto morning newspaper (`src/build.py`) and publishes it to GitHub Pages. Read `README.md` for the pipeline and `PRODUCT.md` for product authority; Voices authority is `VOICES_V2.md`.

## Before working
- GitHub is authoritative. Check the live issue and open PRs first; follow `docs/ISSUE_TRACKING.md` (one spec per issue in `docs/open/`, move to `docs/closed/` only after merge and any required production verification).
- Work on a branch and open a PR. Do not merge, close issues, tag, or push to `main`; the daily build cron commits to `main`, so `git pull --rebase` before branching.
- `docs/` is both documentation and the published site. Never overwrite `docs/index.html` (running `python -m src.render` does; restore it with `git checkout -- docs/index.html`).

## Checks (offline, no API keys or quota)
```bash
source .venv/bin/activate
python -m pytest -q          # CI also runs the two browser tests (Chromium)
python -m py_compile src/*.py
```
Tests use recorded fixtures; never call live news providers or Gemini from tests.

## Rules that matter
- No extra Gemini call for editorial rules: prefer deterministic guards (`src/crime.py`, `src/toronto.py`, `src/genre.py`) over prompt-only fixes.
- The release skill (`.claude/skills/release`) applies: this repo has no version bump or tags.

# /release — The Daily

This repo has **no versioned package**: no `package.json`, `pyproject.toml`,
`Cargo.toml`, or `go.mod`. It is a daily-build pipeline (`src/build.py`) whose
own cron (`.github/workflows/build.yml`) already publishes a new "release"
(an edition) every morning, commits `docs/index.html`, and pushes.

**Do not tag or version-bump this repo.** The `v1.2.x`-style tags in `git tag`
belong to the archived Firebase/React "Hermes v1" dashboard
(`archive/v1-hermes/`, tagged `v1-final`) — they predate the v2 rewrite and
have nothing to do with this pipeline. Continuing that numbering, or starting
a new semver line, would imply a kind of release this project doesn't have.

"Release" here means: verify the pipeline is sound and pushed, confirm
GitHub Pages will serve it. Nothing to bump, nothing to tag.

## Recipe

### 1. Pre-flight
```bash
git status --short          # clean except expected in-progress work
git pull --rebase            # if origin has moved (the build cron pushes daily)
```

### 2. Quality gates (all offline, no API keys/quota spent)

```bash
source .venv/bin/activate
python -m py_compile src/*.py                 # syntax across every module
python -m src.images                           # offline self-test (pure function)
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/build.yml', '.github/workflows/notify.yml']]"
```

`src/render.py`'s own self-test writes `docs/index.html` from the bundled
fixture — useful to prove the template still renders, but it **overwrites
the live published edition** on disk. If you run it, restore immediately:

```bash
python -m src.render          # writes docs/index.html from data/fixtures/edition_sample.json
git checkout -- docs/index.html   # restore the real, already-deployed edition
```

**Do not run `src/curate.py` or `src/fetch.py` as a release gate.** Their
`__main__` blocks hit live wire APIs (Guardian/NYT/Perigon) and the Gemini
API — real quota, not a repeatable check. The pipeline's true integration
test is `python -m src.build`, which already runs daily in CI and is what
actually publishes an edition (see step 4).

A gate failure (syntax error, invalid YAML, images self-test assertion) is a
real defect — fix it, don't skip past it.

### 3. Version bump
None. There is nothing to bump.

### 4. Build
Only run `python -m src.build` if you are deliberately publishing a fresh
edition right now (spends `GEMINI_API_KEY` + wire API quota, overwrites
`docs/index.html` with live content). This is not a required release step —
the scheduled cron in `build.yml` already does this daily. Only do it
on-demand if code changes (curate prompt, template) need to be reflected on
the live site sooner than the next scheduled run.

If you do run it, verify before committing:
```bash
python -m src.build
git diff --stat docs/index.html      # sanity-check the diff size looks right
```

### 5. Commit
Stage only what actually changed — review `git status` first, never blind
`git add -A` (this repo commits `docs/index.html` as build output, which is
expected, but flag anything else that looks like stray in-progress work).

Match the existing convention: this repo uses Conventional Commits
(`feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`,
`chore(edition): publish YYYY-MM-DD edition` for automated builds). No
`release:` prefix — that convention belongs to the old v1 app.

### 6. Tag
None.

### 7. Push
```bash
git push origin main
```
If `git push` is rejected non-fast-forward (the build cron runs multiple
times a day and may have pushed an edition mid-work), rebase and resolve —
conflicts are almost always confined to `docs/index.html`; keep whichever
side has the edition you intend to ship live, then continue:
```bash
git fetch origin
git rebase origin/main
# resolve docs/index.html conflict: git checkout --ours/--theirs -- docs/index.html
git add docs/index.html
git rebase --continue
git push origin main
```

## Deploy

**CI-triggered, not manual.** GitHub Pages serves `docs/` on every push to
`main` — there is nothing to run by hand. After pushing, confirm the live
site picked it up (Pages deploys take roughly a minute):
```bash
curl -fsS "https://BenWassa.github.io/Hermes/?cb=$RANDOM" | grep -o "content=\"[^\"]*\"" | head -1   # check the build-timestamp meta tag, or grep for today's date string
```

`notify.yml` fires an ntfy.sh push automatically after a successful build
that actually published (see its freshness gate) — no manual notify step
either.

## Report template

When this recipe finishes, report:
- which gates ran and passed (list them; note any skipped and why)
- whether a fresh edition was built and published, or the existing deployed
  edition was left as-is
- confirmation the live site reflects `origin/main`'s HEAD

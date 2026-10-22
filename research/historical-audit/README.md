# Historical edition backfill — reproducibility and ownership

Scope: [Hermes #75](https://github.com/BenWassa/Hermes/issues/75). As-of snapshot: **2026-10-22**, main at `550a9f821292e6ed32a2272b2ed95ad52eed1a9e`.

- [HISTORY_INDEX.md](HISTORY_INDEX.md): exactly 30 latest **distinct recoverable Toronto edition dates** in the fixed historical snapshot, full commit SHAs, Git blob identities, build times and file links.
- [BASELINE_2026-10-22.md](BASELINE_2026-10-22.md): evidence-graded observations, verified structural/classification issues, source-level factual probes, limitations and handoff.
- No copied edition HTML, licensed article bodies, hidden model reasoning, API tokens or retrospective candidate-pool inventions.

## Branch ownership contract with #76

Issue #75 uses **`research/historical-audit`**, writing only under **`research/historical-audit/`**, proposed into `main` as read-only research. Issue [#76](https://github.com/BenWassa/Hermes/issues/76) exclusively owns the prospective **`sentinel/reviews`** branch and **`docs/sentinel/`** paths, including its authoritative **`docs/sentinel/HISTORY_INDEX.md`**. This audit makes **no write to** that branch or path.

After this research PR is merged, the Sentinel owner may **reference or explicitly import** the pinned history index, adding its own weekly/daily context and HQA IDs. Do not give the research-local `HA-##` IDs authority as Sentinel `HQA-###` identifiers. Avoid rewriting the source index in place based on later daily runs; the as-of snapshot is fixed.

## Reconstruct without network APIs or production writes

Use a local Git clone with the full history and Python 3.11+:

```bash
git fetch origin main
git cat-file -e 550a9f821292e6ed32a2272b2ed95ad52eed1a9e^{commit}
git log --format='%H%x09%cI%x09%s' \
  550a9f821292e6ed32a2272b2ed95ad52eed1a9e -- docs/index.html
# For one exact edition:
git show 550a9f821292e6ed32a2272b2ed95ad52eed1a9e:docs/index.html
git rev-parse 550a9f821292e6ed32a2272b2ed95ad52eed1a9e:docs/index.html
```

The following **read-only** Python snippet derives the sample records directly from those Git objects. It does not serialize the edition HTML, news bodies, or model prompts, and can be rerun with no credentials. Its headings can be compared with `HISTORY_INDEX.md` (the documented 30-row window is frozen as of October 22).

```python
import json
import re
import subprocess
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

REF = "550a9f821292e6ed32a2272b2ed95ad52eed1a9e"
PATH = "docs/index.html"
TORONTO = ZoneInfo("America/Toronto")
TITLE = re.compile(r"^chore\(edition\): publish (\d{4}-\d{2}-\d{2}) edition$")
EMBEDDED = re.compile(
    r'<script id="edition" type="application/json">([\s\S]*?)</script>'
)
BUILD = re.compile(r'<meta name="build" content="([^"]+)"')

def git(*args):
    return subprocess.check_output(["git", *args], text=True)

# Path restriction includes non-publication changes, so explicitly inspect
# commit subjects. If earlier history includes repairs/republications,
# record every alternate and choose the latest same-date publication snapshot.
raw = git("log", "--format=%H%x09%cI%x09%s", REF, "--", PATH)
records = []
seen = set()
for line in raw.splitlines():
    sha, committed_at, subject = line.split("\t", 2)
    match = TITLE.fullmatch(subject)
    if not match:
        continue
    edition_date = match.group(1)
    if edition_date in seen:
        print("DUPLICATE_PUBLICATION_DATE", edition_date, sha)
        continue
    seen.add(edition_date)
    html = git("show", f"{sha}:{PATH}")
    embedded_match = EMBEDDED.search(html)
    build_match = BUILD.search(html)
    if not embedded_match or not build_match:
        raise ValueError(f"missing edition data or build timestamp: {sha}")

    edition = json.loads(embedded_match.group(1))
    displayed = datetime.strptime(edition["date"], "%A, %B %d, %Y").date()
    build = datetime.fromisoformat(build_match.group(1).replace("Z", "+00:00"))
    commit = datetime.fromisoformat(committed_at)
    local_build = build.astimezone(TORONTO)
    local_commit = commit.astimezone(TORONTO)
    story_count = sum(len(s.get("stories", [])) for s in edition["sections"])
    toronto = next((s for s in edition["sections"] if s["id"] == "toronto"), None)
    toronto_count = len(toronto["stories"]) if toronto is not None else 0
    blob = git("rev-parse", f"{sha}:{PATH}").strip()
    flags = []
    if displayed.isoformat() != edition_date:
        flags.append("DISPLAY_DATE_MISMATCH")
    if local_build.date().isoformat() != edition_date:
        flags.append("BUILD_DATE_MISMATCH")
    if local_commit.date().isoformat() != edition_date:
        flags.append("COMMIT_DATE_MISMATCH")
    if toronto is None:
        flags.append("TORONTO_SECTION_ABSENT")
    records.append((edition_date, sha, blob, local_build, story_count,
                    toronto_count, ",".join(flags) or "-"))
    if len(records) == 30:
        break

for date_value, sha, blob, dt, count, local_count, flags in records:
    print(date_value, dt.isoformat(), count, local_count, sha, blob, flags,
          sep="\t")
if len(records) != 30:
    print("ONLY", len(records), "recoverable editions")
if records:
    cursor = date.fromisoformat(records[0][0])
    oldest = date.fromisoformat(records[-1][0])
    indexed = {date.fromisoformat(item[0]) for item in records}
    while cursor >= oldest:
        if cursor not in indexed:
            print("MISSING_DATE_IN_PUBLICATION_HISTORY", cursor.isoformat())
        cursor -= timedelta(days=1)
```

### Validation rules

1. Confirm **30** distinct dates, commits and blobs, descending by edition date; compare each `git rev-parse SHA:docs/index.html` with the index's Git blob hash. A Git blob SHA is not a SHA-256 checksum.
2. Compare the commit subject date, embedded human-readable edition date, `build` timestamp converted to Toronto, and committer time converted to Toronto. In this window, all 30 **dates** match; a one-second build/commit delta is normal.
3. Check missing dates **within the observed sample window** only. A date with no matching canonical commit is an **unlocated publication**, not proof a scheduled job failed or the site was unavailable.
4. Check exact repeated links independently of title wording. Reuse may represent updates; do not score repeats as defects without checking whether material content changed.
5. For external fact checks, document source publication time **relative to the edition build time**. Later corroboration can validate a historical claim but not establish contemporaneous discoverability or prove an omission.

The Git commit is immutable once created, but long-term remote accessibility still depends on the repository retaining reachable Git objects (history rewrite/garbage collection can remove them). No paywalled full text is mirrored.

### Research boundaries

The embedded JSON reconstructs **what was published**, not the fetch/normalize candidate pool, editorial rejections, precise model prompts, token usage, model reasoning, provider failures, Actions run conclusions or Pages propagation. A future #74 provenance record can close some of these gaps **prospectively**, not retroactively. The live weekly #76 review should consume this snapshot as calibration evidence and independently re-check allegations before raising severity.

# Hermes Sentinel — audit ledger

**Authority:** [issue #76](https://github.com/BenWassa/Hermes/issues/76). **Writing branch:** [sentinel/reviews](https://github.com/BenWassa/Hermes/tree/sentinel/reviews). **Production:** main (read-only to Sentinel). **Timezone:** America/Toronto.

Sentinel is the Git-backed, independently reviewed evidence and decisions ledger for the scheduled ChatGPT daily and weekly Hermes audits. It is not production code, a live newspaper archive, or a substitute for primary source reporting. Auditor findings are judgments; they do not authorize implementation.

## Paths and independent owners

| Path | Owner | Purpose |
| --- | --- | --- |
| docs/sentinel/daily/YYYY-MM-DD.md | Daily schedule only | One report per **Toronto edition date**, never per UTC run |
| docs/sentinel/weekly/YYYY-Www.md | Weekly schedule only | One report per Toronto ISO Monday–Sunday week |
| docs/sentinel/FINDINGS.md | Weekly schedule only | Stable HQA IDs, observations, status and action history |
| docs/sentinel/templates/DAILY.md; templates/WEEKLY.md | Infrastructure (#76) | Report formats, not audits |
| docs/sentinel/examples/* | Infrastructure (#76) | **Smoke tests only**; exclude from statistics |
| docs/sentinel/HISTORY_INDEX.md and retrospective research | [Historical audit #75](https://github.com/BenWassa/Hermes/issues/75) | Reserved for the history owner; #76 does not populate it |

Daily must not edit FINDINGS or weekly. Weekly must not rewrite daily evidence. Neither schedule owns history, templates, README or examples. #75 must coordinate any additions to this branch and avoid overwriting prospective files; its independent research branch remains isolated until deliberate integration.

## Daily audit rubric

Review the *actual edition for the America/Toronto date*, its available embedded JSON, and the corresponding full-SHA Git commit. The mutable homepage cannot prove historical publication. Record the publication time (Toronto time and original timezone), observed check time, edition SHA, cutoff assumptions, and build/deployment evidence when inspectable. If absent, distinguish an actual verified non-publication from a transient fetch failure. Never use yesterday's edition as today's.

Grade these dimensions **Pass / Concern / Not evaluated**, with brief anchored evidence: factual accuracy and source fidelity; significant omissions; editorial ranking and classification; analytical depth; source diversity; Toronto/Canada relevance; duplication/staleness; UX/presentation; publication timing/reliability. Consider opinion/reporting separation, Voices/Following and Sports when applicable. Pass requires an actual check; unreviewed sections are not passes. Disclose the assessed denominator and any inaccessible content.

Every material observation includes:
1. Original short claim or missing event, visible location and **commit-pinned edition URL** with complete SHA; an operational claim needs timestamped workflow/deployment evidence instead.
2. Independent reputable or primary **source URL**, publisher, publication/event timestamp, and checked-at time. Explain whether it was knowable *by the edition publication cutoff*. Do not treat hindsight or a later correction as an original defect.
3. Dimension, severity (**Critical, Major, Minor, Opportunity**), confidence (**High, Medium, Low**), evidence state, reader impact, contradictory evidence/limitations and current matching GitHub issue/PR if found.
4. Root-cause claim only when supported by runtime or code evidence. Otherwise mark **cause hypothesis**. Never infer the candidate pool, provider behavior, or editorial model reasoning from the output.

**Evidence state:** Verified defect = direct edition claim plus decisive contemporaneous check; Supported concern = credible incomplete check; Hypothesis = unverified causal or counterfactual claim; Editorial preference = reasoned subjective call; Not assessable = inadequate evidence. Separate these in counts. **Severity:** Critical = dangerously/materially incorrect high-impact information or systemic failure to publish; Major = serious omission, accuracy, ranking or reliability defect; Minor = localized problem; Opportunity = unproven improvement. Severity is distinct from confidence.

A significant omission requires a contemporaneous event with verifiable significance and the reason it deserved inclusion relative to the published edition; without the original candidate pool, do not claim the model rejected it. An isolated incident is not a recurrent pattern; a repeated output symptom is not a confirmed root cause. Respect paywalls; store no licensed full article bodies, secrets or private internal model reasoning.

## Identity and finding register

Daily uses report-local **D-01, D-02...** for individual observations. Daily can attach an existing HQA ID only after reading FINDINGS; it cannot allocate one. Weekly owns persistent **HQA-001, HQA-002...** IDs for one stable, falsifiable issue across dates. Allocate next integer after the maximum existing entry **after a fresh fetch**. Match new incidents to existing trigger/impact/mechanism before allocating. Link dated D-IDs in the register. Retain IDs permanently; merge duplicates by marking one Superseded by HQA-### rather than renumbering or deleting. One report re-reviewed twice still counts as one edition.

**Finding lifecycle:** Open → Monitoring → Resolved / Rejected / Superseded, with dated transitions. **Action lifecycle** is independent: Not proposed → Proposed → Owner approved / Deferred / Declined → Implemented → Verified / Reopened. An implementation is not verified until measured on later editions.

## Weekly assessment and owner decisions

Only count available daily reports in the ISO week and explicitly state N/7 and missing dates. Compare before/after with like denominators; do not invent a trend from absent data. Check current main, relevant existing issues/PRs and any #75 baseline when actually available. Preserve linkable distinct dated examples. Present **at most three** improvement proposals, each with impact, frequency, uncertainty, likely cause vs proven cause, existing issue/PR matching, alternative approaches, bounded acceptance tests, risks, owner decision (default Pending), and post-merge verification plan. Do not create/close issues, open PRs, merge or edit production automatically.

After **2–4 weeks of actual scheduled reports**, calibrate the auditor against at least five independently adjudicated examples covering true defects, true negatives, uncertain omissions, cutoff issues and subjective choices. Record disagreements, false positives, missed errors where discoverable, paywall/access limitations and changes to judgment criteria. Do not report recall without a known denominator.

## Conflict-safe GitHub connector protocol — mandatory on each scheduled run

1. Read main **only** for immutable edition evidence. Read target branch sentinel/reviews and the exact report path. Determine file key in America/Toronto. **Never omit the branch argument on writes**, and never force-push, merge or edit main.
2. First run: create just the correctly keyed report if absent. Rerun: reread the existing file, reuse its report-local IDs, merge genuinely new evidence/revisions and explain changed conclusions in its revision log. No-op if substantively unchanged. Never make duplicates such as suffix -2.
3. Updates must use the blob SHA from the **latest fetch** in GitHub Contents API; that SHA is a compare-and-swap precondition. For 409/422 conflicts, refetch and reconcile semantically before retrying **at most twice**. Never overwrite a newer assessment blindly. Do not run two writes to the same file in parallel.
4. For weekly: refetch FINDINGS, match existing HQA IDs and allocate any new ID, write register using its blob SHA, then write/update that week's report **sequentially**. On a conflict repeat HQA allocation against the new register. If only one succeeds, report partial persistence and reconcile on next run.
5. **PERSISTED** requires GitHub to return a commit SHA **and** a subsequent fresh read of the branch/path confirming date/report key and expected content. Return verified commit and file URL. Existing unchanged content may be PERSISTED after fresh read, linked to the file and latest commit if known; do not invent a new write.
6. Permission/approval, tool, evidence or conflict failure: deliver full audit text labelled **NOT PERSISTED**, the attempted path, reason and recovery step. Never silently fall back to default main. A returned success without readback is **NOT VERIFIED** and must not be represented as persisted.

GitHub Contents commits are per-file, not transactional across files; partial weekly commits must be flagged. Auditor cannot infer branch write authorization for future schedule contexts merely from this setup's account permissions. Neither branch nor data structure is a GitHub Actions scheduled runner.

## Initial validation

The examples folder contains a **manual connector write/readback smoke test**, not daily or weekly schedule execution or evidence of editorial quality. The already enabled daily (~10:00 Toronto) and weekly (Sunday afternoon) ChatGPT schedules must each independently persist and verify their first live report, or return explicit NOT PERSISTED. Do not represent them as tested before their scheduled runs occur.

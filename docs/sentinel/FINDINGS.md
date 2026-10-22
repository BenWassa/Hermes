# Hermes Sentinel — canonical findings register

**Branch:** sentinel/reviews. **Owner:** weekly ChatGPT reviewer only. **Source of IDs:** this file, not daily reports. This register starts empty; test/synthetic examples do not allocate HQA IDs.

## ID allocation and conflict guard

On each weekly run, fetch this file and its current GitHub blob SHA. Match new daily observations against all existing IDs by trigger, falsifiable symptom and impact. Reuse an existing ID when warranted. Only then allocate the lowest sequential new identifier greater than the maximum existing HQA integer (starting at HQA-001). Submit an update using that fetched blob SHA; on 409/422 refetch, reconcile new entries and retry up to twice, then report NOT PERSISTED. Never recycle or renumber IDs; retire duplicates as Superseded by HQA-###, with dated rationale. Report-local D-## identifiers remain anchored to their original dated report.

**Finding states:** Open / Monitoring / Resolved / Rejected / Superseded. **Intervention states:** Not proposed / Proposed / Owner approved / Deferred / Declined / Implemented / Verified / Reopened. Differentiate root-cause evidence from hypotheses, edition recurrence from repeated references, and implementation from proof of editorial improvement. Register changes must link directly to dated reports and independent checks. Preserve prior transitions.

## Finding summary

| ID | Stable falsifiable description | Dimension | Evidence state | Severity / confidence | Distinct editions observed | Finding status | Intervention status | Existing issue/PR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

*No findings registered yet. Do not count infrastructure smoke tests as findings.*

## Detailed records

For every registered HQA ID, add a section with this exact heading form:

### HQA-001 — concise falsifiable title

- **Identity / what distinguishes this from other findings:**
- **Dimension, evidence state, severity, confidence:**
- **Dated occurrences:** YYYY-MM-DD D-01 link; independent contemporaneous evidence URL and cutoff status for each.
- **Distinct editions / denominator:** n / actual reviewed days (list unknowns).
- **Cause:** confirmed code/run link, or unproven hypothesis.
- **Existing work:** GitHub issue(s)/PR(s), if any; what remains uncovered.
- **Finding state / transitions:** dated rationale, prior state retained.
- **Intervention state / owner decision:** dated approved/declined/deferred only when actual owner decision exists.
- **Implementation:** PR/commit/date or None.
- **Before/after validation:** post-change edition SHA, dates, observed outcomes, denominators, contrary evidence and conclusion.
- **Supersedes / superseded by:** only if applicable.

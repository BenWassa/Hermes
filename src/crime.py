"""Incident-level crime significance gate (issue #71).

Report crime for its civic significance, not because the event is dramatic.

This module is deliberately small and deterministic, like ``canada.py``. It adds
no Gemini call. It does three things around the existing single curation call:

1. Before the model boundary, a local crime *incident* (a shooting, stabbing,
   homicide, assault and similar) whose public title/description establishes no
   substantive reason to be in a compact morning paper is withheld from the
   model input. Incidents that do carry a reason are
   untouched.
2. The model sees one transient ``crime_significance`` field on incident
   records only, plus a short editorial contract, so a surviving incident is
   written up for the reason it matters rather than its most vivid detail.
3. After the model returns, an unsupported incident cannot hold Front Page or
   lead a section, whatever the model decided.

Significance is judged only from substantive reasons: a continuing threat,
multiple victims, a pattern, aggregate trend evidence, policing / court /
policy consequence, real disruption, a broader public issue, or a wider
investigation. Severity, gruesomeness, and human-interest detail (relationship,
age, parenthood, occupation, biography) are never signals, so adding or
removing them cannot change a story's standing. A relationship matters only
when the text also states the substantive interpretation it changes, for
example intimate partner violence or a murder-suicide investigation.

Matching is a conservative heuristic over public title and description, not a
verdict on any one story: no victim category, neighbourhood or count is a
rule. Unsupported incidents are withheld from the model (cap 0), so a signal the
keyword matching misses means that story does not reach the edition; extend the
signal lists when a review of real candidate pools finds such a miss.
"""

from __future__ import annotations

import re

# Unsupported incidents that may reach the model. Owner decision: none. An
# incident with no established civic significance is withheld from the model
# input entirely; the post-model placement guard remains as defence in depth.
CRIME_INCIDENT_INPUT_CAP = 0

# Intake scope: Toronto-local and Canada-national reporting. World wire items
# (wars, attacks abroad, political violence) are never gated here, and neither
# are Opinion, Sports or the deterministic Following block.
_LOCAL_HINTS = frozenset({"toronto"})
_CANADA_LANE = "canada-national"

_SPACE_RE = re.compile(r"\s+")

# What makes a record an incident-level crime item. Only specific acts of
# violence; a bare "killed" or "died" also covers crashes, fires and war.
_INCIDENT_RE = re.compile(
    r"\b(?:homicides?|murder(?:ed|s)?|manslaughter|shootings?|gunfire|gunman|"
    r"(?:fatally|critically|seriously) (?:shot|stabbed)|"
    r"shot (?:dead|and killed|to death|multiple times|outside|in the)|stabb(?:ed|ing|ings)|"
    r"slain|found dead|suspicious death|death investigation|"
    r"(?:sexual )?assault(?:ed)?|carjacking|armed robbery|home invasion|"
    r"kidnapp(?:ed|ing)|abduct(?:ed|ion))\b"
)

# A statement that there is no continuing threat (or that an attack was not
# random) is the opposite of a signal, so it is removed before matching.
_NEGATED_RE = re.compile(
    r"\b(?:no|not|without)\s+(?:an?\s+)?"
    r"(?:(?:ongoing|continuing|further|known|immediate|apparent|current|active|"
    r"broader|wider|general|public safety|public)\s+){0,3}"
    r"(?:threat|danger|risk|concern)s?\b"
    r"(?:\s+to\s+(?:the\s+)?(?:general\s+)?public(?:\s+safety)?)?"
    r"|\b(?:not|isn'?t|wasn'?t)\s+(?:an?\s+)?random(?:ly)?\b"
)

# Substantive reasons, in the order they are reported. Nothing here is a
# human-interest term.
_REASONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("active public threat", re.compile(
        r"\b(?:at large|armed and dangerous|considered dangerous|outstanding suspects?|"
        r"public safety (?:alert|threat|concern|risk)|threat to (?:the )?public|"
        r"police (?:warn|are warning|urge|are urging|ask the public)|"
        r"residents? (?:are |were )?(?:urged|asked|told)|shelter in place|"
        r"hold and secure|lockdown|locked down|hostages?|barricaded|"
        r"random(?:ly)?)\b")),
    ("multiple victims or mass casualty", re.compile(
        r"\b(?:mass (?:shooting|stabbing|casualty|casualties|killing)|mass-casualty|"
        r"multiple (?:victims|people|fatalities|shootings|stabbings|casualties)|"
        r"several (?:people|victims) (?:shot|stabbed|killed|injured|wounded)|"
        r"terror(?:ism|ist)?|explosion|bombing|bomb threat)\b")),
    ("recurring pattern", re.compile(
        r"\b(?:serial|string of|series of|spate of|wave of|rash of|latest in a|"
        r"latest of|linked (?:to|incidents)|connected (?:to|incidents)|pattern|"
        r"repeat offenders?|second (?:shooting|homicide|stabbing|killing) in)\b")),
    ("crime trend or statistics", re.compile(
        r"(?:\bper ?cent\b|\bpercent\b|%|\byear[- ]over[- ]year\b|"
        r"\bcompared (?:with|to) last year\b|\bso far this year\b|\byear[- ]to[- ]date\b|"
        r"\bstatistics\b|\bcrime (?:data|rate|rates|statistics)\b|\bpolice data\b|"
        r"\btrends?\b|\bsurge\b|\bspike\b|\buptick\b|"
        r"\b(?:increase|decrease|rise|drop|decline) in\b|\bviolence on transit\b|"
        r"\btransit violence\b)")),
    ("policing, courts or policy", re.compile(
        r"\b(?:polic(?:y|ies|ing)|legislation|bail reform|police services board|"
        r"oversight|special investigations unit|siu|officer-involved|police-involved|"
        r"misconduct|corruption|bribery|fraud|embezzlement|money laundering|"
        r"racketeering|wrongful conviction|public inquiry|inquest|class action|"
        r"lawsuit|sentenced|convicted|verdict|acquitted|supreme court|court of appeal|"
        r"(?:court|judge'?s|judicial) ruling|judge ruled|ruled (?:unconstitutional|inadmissible)|"
        r"constitutional|charter (?:rights|challenge)|line of duty)\b")),
    ("civic disruption", re.compile(
        r"\b(?:service (?:suspended|disrupted|halted)|suspended service|"
        r"shut down|evacuat(?:ed|ion)|road closures?|(?:road|highway|station) closed|"
        r"closed (?:the )?(?:road|highway|station)|(?:transit|service|major) delays)\b")),
    ("broader public issue", re.compile(
        r"\b(?:intimate[- ]partner violence|domestic violence|gender-based violence|"
        r"femicide|murder[- ]suicide|hate crime|hate-motivated|gun violence|gun crime|"
        r"firearms? trafficking|illegal firearms|human trafficking)\b")),
    ("wider investigation", re.compile(
        r"\b(?:organized crime|criminal (?:network|organization)|task force|"
        r"multi-agency|joint investigation|cross-border|trafficking ring|extortion)\b")),
)

_EDITORIAL_INSTRUCTION = """

CRIME AND INCIDENT SIGNIFICANCE
The Daily is a compact morning newspaper, not a breaking-crime feed. Report
crime for its civic significance, not because the underlying event is dramatic.

- Severity, gruesomeness, novelty and emotional detail are never sufficient
  reasons to include an individual crime incident. An incident needs at least one
  substantive reason: a continuing threat to the public, multiple victims,
  a recurring pattern, relevance to citywide or neighbourhood safety conditions,
  policing / court / institutional / policy consequence, real disruption to
  transit, schools, hospitals or civic services, or a significant investigative
  development that illuminates a broader public issue.
- Some input records carry a `crime_significance` field set by Hermes. When it
  begins "isolated incident", the source text establishes no such reason: omit
  the record unless the text itself clearly supplies one Hermes missed, and if you
  keep it, make it a supporting story, never a lead and never Front Page. When it
  lists reasons, headline and summarize the story around the first listed reason.
  Apply the same standard to any crime incident that has no such field.
- Relationship, age, parenthood, occupation, biography, relatives' tributes and
  similar human-interest details must not raise a story's priority or serve as a
  headline hook. Use them only when they change the substantive interpretation
  of the case, such as intimate partner violence or a murder-suicide
  investigation, and then state that interpretation, not the vivid detail.
- For the question "is Toronto getting safer or more dangerous?" prefer aggregate
  evidence (counts, rates, year-over-year and multi-year comparisons, police
  statistical releases, serious explanatory reporting). Do not let a run of
  individual incidents stand in for trend evidence, and do not infer a trend
  from the incidents in this batch.
- Important crime coverage stays in scope: active public threats, major attacks,
  serial or patterned offending, corruption or misconduct investigations,
  important court rulings, policing-policy changes, statistically meaningful
  changes, and stories with major institutional or citywide consequences.
"""


def editorial_instruction() -> str:
    """Single-call editorial contract appended to the curation system prompt."""
    return _EDITORIAL_INSTRUCTION


def _text(story: dict) -> str:
    text = " ".join(str(story.get(key, "") or "") for key in ("title", "description"))
    return _SPACE_RE.sub(" ", text.casefold()).strip()


def in_scope(story: dict) -> bool:
    """Whether the gate applies: Toronto-local or Canada-national news intake."""
    return story.get("section_hint") in _LOCAL_HINTS or story.get("coverage_lane") == _CANADA_LANE


def is_incident(story: dict) -> bool:
    """Whether an in-scope story is an individual violent-crime incident."""
    return in_scope(story) and bool(_INCIDENT_RE.search(_text(story)))


def significance_reasons(story: dict) -> tuple[str, ...]:
    """Substantive reasons an incident belongs in the paper, in report order."""
    text = _NEGATED_RE.sub(" ", _text(story))
    return tuple(reason for reason, pattern in _REASONS if pattern.search(text))


def is_unsupported_incident(story: dict) -> bool:
    """An incident whose public text establishes no civic significance."""
    return is_incident(story) and not significance_reasons(story)


def model_marker(story: dict) -> str:
    """Transient model-only note for incident records; empty for everything else."""
    if not is_incident(story):
        return ""
    reasons = significance_reasons(story)
    if reasons:
        return "civic significance: " + "; ".join(reasons)
    return "isolated incident: no civic significance established in source text"


def bound_unsupported_incidents(
    stories: list[dict], cap: int = CRIME_INCIDENT_INPUT_CAP
) -> tuple[list[dict], int]:
    """Cap unsupported incidents and move the survivors to the back.

    Returns the reordered list and how many incidents were withheld. Relative
    order is otherwise preserved, so the section-balanced selection that
    follows fills its slots with ordinary candidates first.
    """
    ordinary: list[dict] = []
    unsupported: list[dict] = []
    for story in stories:
        (unsupported if is_unsupported_incident(story) else ordinary).append(story)
    kept = unsupported[: max(0, cap)]
    return ordinary + kept, len(unsupported) - len(kept)


def enforce_placement(sections: list[dict], input_stories: list[dict]) -> int:
    """Keep unsupported incidents off Front Page and out of lead position.

    Mutates the model's raw sections in place and returns how many stories were
    affected. Stories are matched to input records by link, so a record the
    model rewrote beyond recognition is simply left alone. Nothing is added, so
    section caps and edition size cannot grow.
    """
    flagged_links = {
        str(story.get("link") or "")
        for story in input_stories
        if story.get("link") and is_unsupported_incident(story)
    }
    if not flagged_links:
        return 0

    affected = 0
    for section in sections:
        stories = section.get("stories") or []
        flagged = [story for story in stories if str(story.get("link") or "") in flagged_links]
        if not flagged:
            continue
        flagged_ids = {id(story) for story in flagged}
        rest = [story for story in stories if id(story) not in flagged_ids]
        if section.get("id") == "front":
            section["stories"] = rest
        else:
            for story in flagged:
                story["lead"] = False
            section["stories"] = rest + flagged
        affected += len(flagged)
    return affected

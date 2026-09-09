"""Operational tuning for the Voices V2 weekly roundup."""

STATE_PATH = "data/voice_roundup_state.json"
PAGE_PATH = "docs/voices/index.html"

LOOKBACK_HOURS = 48
RETENTION_DAYS = 14
MAX_ENTRIES = 500
CAP = 6
MAX_PER_VOICE = 2

RECONCILE_HOURS = 24
PUSH_ATTEMPTS = 5

# Fixed product period: Sunday 17:00 America/Toronto. Monday recovery stops
# after 21:00 local; no automatic stale midweek delivery.
CUTOFF_HOUR = 17
MONDAY_GRACE_HOUR = 21

CADENCE = {
    "rss": "frequent",
    "guardian": "frequent",
    "author_page": "frequent",
    "perigon": "reconcile",
}

# Daily rather than hourly, so these remain generous safety ceilings while
# still preventing a registry mistake from becoming an unbounded source run.
REQUEST_BUDGET = {
    "rss": 24,
    "guardian": 3,
    "author_page": 14,
    "perigon": 1,
}

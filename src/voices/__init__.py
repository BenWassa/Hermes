"""Followed Voices: identity, discovery, and article canonicalization.

A Voice is a *person*, not a publication. This package is the foundation that
lets Hermes represent a writer once, find their new work across whichever
surfaces they publish on, establish that they actually wrote it, and recognise
the same piece when it arrives twice.

Reading order:

* ``registry``  - the reviewed ``data/voices.json`` schema and its validation
* ``names``     - person-name normalization and byline parsing
* ``urls``      - canonical URLs and article identity keys
* ``adapters``  - generic source adapters (RSS, Guardian, Perigon, author page)
* ``resolve``   - evidence-based attribution
* ``dedupe``    - merging observations into canonical articles
* ``window``    - what counts as new this morning
* ``following`` - the deterministic, finite Following selection
* ``discover``  - orchestration, request budgets, and diagnostics
* ``state``     - the watcher's durable, bounded seen state
* ``notify``    - restrained release-time alerts over the existing ntfy topic
* ``watch``     - the release-time watcher's claim-then-alert run

The Opinion treatment in #11 consumes ``discover`` and ``following``; the
release-time watcher entrypoint is ``src.voice_watch``. Nothing else should
need to know how attribution works.
"""

from .discover import DiscoveryResult, discover, observations_from_pool, resolve_observations
from .following import select_following, suppress_duplicates
from .model import Attribution, Author, Observation, VoiceArticle
from .notify import Alert, NotifyError, Notifier, NtfyNotifier, build_alert
from .registry import Registry, RegistryError, Voice, VoiceSource, load_registry, validate
from .state import FileStateStore, GitStateStore, SeenEntry, StateStore, WatchState, load_state
from .watch import WatchOutcome, run_watch
from .window import EditionWindow, WindowVerdict

__all__ = [
    "Alert",
    "Attribution",
    "Author",
    "DiscoveryResult",
    "EditionWindow",
    "FileStateStore",
    "GitStateStore",
    "NotifyError",
    "Notifier",
    "NtfyNotifier",
    "Observation",
    "Registry",
    "RegistryError",
    "SeenEntry",
    "StateStore",
    "Voice",
    "VoiceArticle",
    "VoiceSource",
    "WatchOutcome",
    "WatchState",
    "WindowVerdict",
    "build_alert",
    "discover",
    "load_registry",
    "load_state",
    "observations_from_pool",
    "resolve_observations",
    "run_watch",
    "select_following",
    "suppress_duplicates",
    "validate",
]

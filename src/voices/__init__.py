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

Downstream slices (the Opinion treatment in #11, the release-time watcher in
#12) consume ``discover`` and ``following``; nothing else should need to know
how attribution works.
"""

from .discover import DiscoveryResult, discover, observations_from_pool, resolve_observations
from .following import select_following, suppress_duplicates
from .model import Attribution, Author, Observation, VoiceArticle
from .registry import Registry, RegistryError, Voice, VoiceSource, load_registry, validate
from .window import EditionWindow, WindowVerdict

__all__ = [
    "Attribution",
    "Author",
    "DiscoveryResult",
    "EditionWindow",
    "Observation",
    "Registry",
    "RegistryError",
    "Voice",
    "VoiceArticle",
    "VoiceSource",
    "WindowVerdict",
    "discover",
    "load_registry",
    "observations_from_pool",
    "resolve_observations",
    "select_following",
    "suppress_duplicates",
    "validate",
]

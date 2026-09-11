"""Small inspectable Sports model-budget counters.

Sports V2 starts with an intentionally empty model payload. These counters make
that contract measurable before #39 wires them into morning-build logging.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence


def headline_budget_metrics(
    *,
    raw_candidates: Sequence,
    qualified_candidates: Sequence,
    winners: Mapping,
    model_payload: Sequence[dict],
) -> dict[str, int]:
    serialized = json.dumps(list(model_payload), ensure_ascii=False, separators=(",", ":"))
    model_chars = 0 if not model_payload else len(serialized)
    return {
        "raw_candidates": len(raw_candidates),
        "qualified_candidates": len(qualified_candidates),
        "winners": len(winners),
        "model_records": len(model_payload),
        "model_chars": model_chars,
        "approx_model_tokens": (model_chars + 3) // 4,
    }

"""Bounded repair for the exact fixed-topic legacy SELECTED retry failure.

This module owns no model call and changes no quality threshold. It may replace
only micro_narrative.hook, only after the existing validator reports the exact
Hook/Core Question repetition error, and only from one repo-owned exact fixed
 topic seed's existing specific_observation. The unchanged validator is then run
again and remains authoritative.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Sequence

from quality.fixed_topic_seed_grounding import exact_fixed_topic_seed_record


_REPEAT_MARKERS = ("micro_narrative hook", "Core Question")
_QUESTION_PREFIXES = (
    "왜 ", "왜?", "어떻게 ", "무엇", "어떤 ", "언제 ", "어디",
    "how ", "why ", "what ", "when ", "where ",
)


def _declarative(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or text.endswith("?"):
        return False
    lowered = text.lower()
    return not lowered.startswith(_QUESTION_PREFIXES)


def validate_legacy_selected_with_exact_hook_repair(
    data: Dict[str, Any],
    *,
    validate_output_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    scope: Any,
    fixed_topic: Any,
    trusted_records: Sequence[Dict[str, Any]],
) -> tuple[Dict[str, Any], bool]:
    """Run validator, then repair only the exact repeated-hook failure.

    Returns ``(validated, repaired)``. Any non-matching condition re-raises the
    original validator error unchanged.
    """

    try:
        return validate_output_fn(data), False
    except (TypeError, ValueError) as original_exc:
        error_text = str(original_exc)
        if not all(marker in error_text for marker in _REPEAT_MARKERS):
            raise
        if str(scope or "").strip().lower() != "aviation":
            raise
        if not isinstance(data, dict):
            raise
        if str(data.get("status") or "").strip().upper() != "SELECTED":
            raise

        winner = data.get("winner")
        if not isinstance(winner, dict):
            raise
        record = exact_fixed_topic_seed_record(
            winner,
            fixed_topic,
            trusted_records=trusted_records,
        )
        if record is None:
            raise
        seed = record.get("seed_candidate")
        observation = seed.get("specific_observation") if isinstance(seed, dict) else None
        if not _declarative(observation):
            raise

        repaired = deepcopy(data)
        repaired_winner = deepcopy(winner)
        repaired_micro = deepcopy(repaired_winner.get("micro_narrative") or {})
        repaired_micro["hook"] = str(observation).strip()
        repaired_winner["micro_narrative"] = repaired_micro
        repaired["winner"] = repaired_winner

        # The original validator remains final authority after the bounded edit.
        return validate_output_fn(repaired), True

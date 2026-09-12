"""Deterministic host-side Candidate Pool Handoff.

The Candidate Explorer remains the supplier. This module owns no model, Vision,
image-generation, or network call. It receives a bounded pool from the existing
Explorer response, validates candidates independently, supplies trusted canonical
identity evidence, and converts surviving supply back into the legacy SELECTED
shape consumed by the unchanged downstream Candidate Gate.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple

from quality.canonical_subject_grounding import (
    evaluate_candidate_subject_grounding,
    normalize_candidate_subject_metadata,
)
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)


# Reuses the existing Candidate Explorer shortlist ceiling ("최대 3개").
CANDIDATE_POOL_MAX = 3

# Run 34704697595 showed that the model can still paraphrase Core Question in
# micro_narrative.hook despite the prompt contract. Only already-supplied
# specificity fields may repair that malformed first beat. No fact is invented.
_HOOK_REPAIR_FIELDS = (
    "specific_observation",
    "counterintuitive_result",
    "constraint",
    "tradeoff",
    "concrete_condition",
)
_HOOK_REPEAT_ERROR_MARKERS = (
    "micro_narrative hook",
    "Core Question",
)
_QUESTION_PREFIXES = (
    "왜 ",
    "왜?",
    "어떻게 ",
    "무엇",
    "어떤 ",
    "언제 ",
    "어디",
    "how ",
    "why ",
    "what ",
    "when ",
    "where ",
)


def candidate_pool_handoff_enabled(scope: Any) -> bool:
    return str(scope or "").strip().lower() == "aviation"


def _failure(reason: str, diagnostics: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "status": "REGENERATE",
        "reason": (
            "모든 후보가 구조·사실성 Hard Gate를 통과하지 못했습니다. "
            f"ALL_CANDIDATES_HARD_FAILED: {reason}"
        ),
        "_candidate_pool_handoff": {
            "status": "ALL_CANDIDATES_HARD_FAILED",
            "diagnostics": list(diagnostics),
        },
    }


def _copy_model_identity_metadata(raw: Dict[str, Any], validated: Dict[str, Any]) -> None:
    """Preserve identity hints without trusting model-authored provenance.

    The canonical gate itself decides whether explicit identity evidence is valid,
    while the trusted supplier may replace it with independently owned evidence.
    """

    metadata = normalize_candidate_subject_metadata(raw)
    for key, value in metadata.items():
        if value not in ("", [], 0.0):
            validated[key] = deepcopy(value)


def _looks_like_declarative_supplied_beat(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or text.endswith("?"):
        return False
    lowered = text.lower()
    return not any(lowered.startswith(prefix) for prefix in _QUESTION_PREFIXES)


def _validate_with_bounded_hook_repair(
    raw: Dict[str, Any],
    *,
    prefix: str,
    validate_candidate_fn: Callable[..., Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    """Validate once, then repair only the exact repeated-Hook failure.

    The replacement must come from one of the Candidate's own specificity fields
    and must itself pass the unchanged candidate validator. Any other schema
    failure remains fail-closed. Returns (validated, source_field), where an empty
    source_field means no repair was needed.
    """

    try:
        return validate_candidate_fn(raw, prefix=prefix), ""
    except (TypeError, ValueError) as original_exc:
        error_text = str(original_exc)
        if not all(marker in error_text for marker in _HOOK_REPEAT_ERROR_MARKERS):
            raise

        micro = raw.get("micro_narrative")
        if not isinstance(micro, dict):
            raise

        for field in _HOOK_REPAIR_FIELDS:
            supplied = raw.get(field)
            if not _looks_like_declarative_supplied_beat(supplied):
                continue
            repaired = deepcopy(raw)
            repaired_micro = deepcopy(micro)
            repaired_micro["hook"] = str(supplied).strip()
            repaired["micro_narrative"] = repaired_micro
            try:
                validated = validate_candidate_fn(repaired, prefix=prefix)
            except (TypeError, ValueError):
                continue
            return validated, field

        raise original_exc


def handoff_candidate_pool(
    data: Dict[str, Any],
    *,
    scope: Any,
    validate_candidate_fn: Callable[..., Dict[str, Any]],
    hard_validate_fn: Callable[[Dict[str, Any]], Tuple[bool, str]],
    trusted_records: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate a host-visible Explorer pool candidate-by-candidate.

    Individual failures do not erase surviving supply. All-candidate hard failure
    remains fail-closed and deliberately emits the existing #283 semantic recovery
    marker so the established 1/1 supply recovery contract can still run.

    Run 34703818223 exposed malformed oversize pools; those are bounded to the
    existing first-three ceiling. Run 34704697595 then showed repeated Hook/Core
    Question phrasing can survive prompt guidance. The host may repair only that
    exact malformed beat from already-supplied specificity evidence, after which
    the unchanged validator and grounding authorities run again.
    """

    if not candidate_pool_handoff_enabled(scope):
        raise ValueError("Candidate Pool Handoff is aviation-only")
    if not isinstance(data, dict):
        raise ValueError("Candidate pool response must be an object")
    if str(data.get("status") or "").strip().upper() != "CANDIDATE_POOL":
        raise ValueError("Candidate pool status must be CANDIDATE_POOL")

    raw_pool = data.get("candidates")
    if not isinstance(raw_pool, list):
        raise ValueError("Candidate pool candidates must be a list")
    if not raw_pool:
        return _failure(
            f"pool size must be 1..{CANDIDATE_POOL_MAX}; got 0",
            [],
        )

    supplied_count = len(raw_pool)
    pool_normalization = None
    if supplied_count > CANDIDATE_POOL_MAX:
        raw_pool = raw_pool[:CANDIDATE_POOL_MAX]
        pool_normalization = {
            "status": "TRUNCATED_TO_HOST_MAX",
            "supplied": supplied_count,
            "validated": len(raw_pool),
            "limit": CANDIDATE_POOL_MAX,
        }

    survivors: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    combined_trusted_records = tuple(trusted_records or ()) + tuple(
        CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    )

    for index, raw in enumerate(raw_pool, start=1):
        topic = str(raw.get("topic") or "").strip() if isinstance(raw, dict) else ""
        diag: Dict[str, Any] = {"index": index, "topic": topic}

        if not isinstance(raw, dict):
            diag.update(status="REJECT", reason="candidate is not an object")
            diagnostics.append(diag)
            continue

        try:
            validated, hook_repair_field = _validate_with_bounded_hook_repair(
                raw,
                prefix=f"Candidate pool[{index}]",
                validate_candidate_fn=validate_candidate_fn,
            )
        except (TypeError, ValueError) as exc:
            diag.update(status="REJECT", reason=f"schema: {exc}")
            diagnostics.append(diag)
            continue

        if hook_repair_field:
            diag["normalization"] = {
                "status": "REPAIRED_REPEATED_HOOK_FROM_SUPPLIED_EVIDENCE",
                "source_field": hook_repair_field,
            }

        _copy_model_identity_metadata(raw, validated)

        hard_ok, hard_reason = hard_validate_fn(validated)
        if not hard_ok:
            diag.update(status="REJECT", reason=f"host hard validation: {hard_reason}")
            diagnostics.append(diag)
            continue

        grounded = supply_trusted_subject_grounding(
            validated,
            trusted_records=combined_trusted_records,
        )
        grounding = evaluate_candidate_subject_grounding(grounded)
        if grounding.get("status") != "PASS":
            diag.update(
                status="REJECT",
                reason=f"canonical grounding: {grounding.get('reason', '')}",
            )
            diagnostics.append(diag)
            continue

        grounded["_subject_grounding"] = deepcopy(grounding.get("subject_grounding") or {})
        diag.update(status="SURVIVE", reason="host deterministic validation PASS")
        diagnostics.append(diag)
        survivors.append(grounded)

    if not survivors:
        result = _failure("no host-validated survivors", diagnostics)
        if pool_normalization is not None:
            result["_candidate_pool_handoff"]["supplied"] = supplied_count
            result["_candidate_pool_handoff"]["validated"] = len(raw_pool)
            result["_candidate_pool_handoff"]["normalization"] = pool_normalization
        return result

    # Preserve supplier order. Editorial ranking remains downstream Candidate Gate
    # authority; this layer does not invent a new score or quality threshold.
    trace: Dict[str, Any] = {
        "status": "SURVIVORS",
        "supplied": supplied_count,
        "validated": len(raw_pool),
        "survived": len(survivors),
        "diagnostics": diagnostics,
    }
    if pool_normalization is not None:
        trace["normalization"] = pool_normalization

    result: Dict[str, Any] = {
        "status": "SELECTED",
        "winner": survivors[0],
        "runner_up": None,
        "_candidate_pool_handoff": trace,
    }
    return result

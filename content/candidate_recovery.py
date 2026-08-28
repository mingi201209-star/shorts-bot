# content/candidate_recovery.py

from __future__ import annotations

from copy import deepcopy


_PLACEHOLDER_MARKERS = (
    "재탐색이 필요한 구체적인 이유",
    "구체적인 후보가 부족하여 재탐색이 필요함",
    "탐색한 후보가 충분히 구체적이지 않거나 흥미로운 연결이 부족함",
    "placeholder",
    "todo",
    "tbd",
)

# Candidate Gate is primarily an editorial gate, but fail closed if its reason
# explicitly reports a grounding / fabrication / validation problem.
_HARD_REJECT_REASON_MARKERS = (
    "fact-risky",
    "fact risky",
    "fabricat",
    "unsupported",
    "unverified",
    "hallucinat",
    "도시전설",
    "출처 불명",
    "검증 불가능",
    "미확인",
    "근거 없",
    "근거가 없",
    "사실 오류",
    "사실과 다",
    "불명확한 인과",
    "스키마",
    "필드 누락",
    "비어 있습니다",
)

# "Predictable" feedback is editorial, not a FACT/safety failure. It is kept
# recoverable so automatic production can use the strongest grounded candidate
# instead of spending the entire Candidate budget on repeated exploration.
_PREDICTABLE_EDITORIAL_MARKERS = (
    "예상 가능",
    "예측 가능",
    "too predictable",
    "predictable conclusion",
)

# Strong explicit low-novelty judgements remain terminal. This preserves the
# channel's non-obviousness floor while separating it from a softer prediction
# that the viewer may guess the answer.
_NOVELTY_REJECT_REASON_MARKERS = (
    "뻔",
    "의외성이 부족",
    "의외성 부족",
    "새로움이 부족",
    "새로움 부족",
    "참신성이 부족",
    "참신성 부족",
    "novelty 부족",
    "low novelty",
)

_REQUIRED_FIELDS = (
    "topic",
    "angle",
    "core_question",
)

_REQUIRED_MICRO_FIELDS = (
    "hook",
    "core_question",
    "reveal",
    "payoff",
)


def _text(value):
    return str(value or "").strip()


def _flatten_candidate_text(candidate):
    chunks = []
    for field in _REQUIRED_FIELDS:
        chunks.append(_text(candidate.get(field)))

    micro = candidate.get("micro_narrative")
    if isinstance(micro, dict):
        for field in _REQUIRED_MICRO_FIELDS:
            chunks.append(_text(micro.get(field)))

    return "\n".join(chunk for chunk in chunks if chunk).lower()


def _has_required_shape(candidate):
    if not isinstance(candidate, dict):
        return False

    for field in _REQUIRED_FIELDS:
        if not _text(candidate.get(field)):
            return False

    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        return False

    for field in _REQUIRED_MICRO_FIELDS:
        if not _text(micro.get(field)):
            return False

    return True


def _has_placeholder(candidate):
    text = _flatten_candidate_text(candidate)
    return any(marker.lower() in text for marker in _PLACEHOLDER_MARKERS)


def _reason_is_hard_reject(reason):
    lowered = _text(reason).lower()
    return any(marker in lowered for marker in _HARD_REJECT_REASON_MARKERS)


def _reason_is_predictable_editorial(reason):
    lowered = _text(reason).lower()
    return any(marker in lowered for marker in _PREDICTABLE_EDITORIAL_MARKERS)


def _reason_is_novelty_reject(reason):
    lowered = _text(reason).lower()
    return any(marker in lowered for marker in _NOVELTY_REJECT_REASON_MARKERS)


def recovery_eligibility(candidate, gate_result):
    """Return a fail-closed recovery decision for a gate-rejected Winner.

    Only Candidates that already reached Explorer SELECTED are passed here by
    production. This helper never upgrades Explorer-level hard-gate failures.
    """
    if not _has_required_shape(candidate):
        return False, "invalid_candidate_shape"

    if _has_placeholder(candidate):
        return False, "placeholder_candidate"

    if not isinstance(gate_result, dict):
        return False, "invalid_gate_result"

    status = _text(gate_result.get("status")).upper()
    reason = _text(gate_result.get("reason"))

    if status != "REGENERATE":
        return False, "gate_status_not_rejected"

    if not reason:
        return False, "missing_gate_reason"

    if _reason_is_hard_reject(reason):
        return False, "hard_grounding_reject"

    if _reason_is_novelty_reject(reason):
        return False, "hard_novelty_reject"

    if _reason_is_predictable_editorial(reason):
        return True, "predictable_editorial_reject"

    return True, "soft_editorial_reject"


def _list_count(value):
    if isinstance(value, (list, tuple)):
        return len([item for item in value if _text(item)])
    if isinstance(value, dict):
        return len([value for value in value.values() if _text(value)])
    return 1 if _text(value) else 0


def recovery_strength(candidate):
    """Deterministic ranking; no extra model calls are introduced."""
    micro = candidate.get("micro_narrative") or {}
    reveal = _text(micro.get("reveal"))
    payoff = _text(micro.get("payoff"))

    evidence = (
        3 * _list_count(candidate.get("visual_proof"))
        + 2 * _list_count(candidate.get("fact_check_focus"))
        + 2 * _list_count(candidate.get("mechanism"))
    )

    specificity = min(len(reveal), 120) + min(len(payoff), 120)
    return evidence * 1000 + specificity


def make_recovery_record(candidate, gate_result, *, attempt):
    eligible, eligibility_reason = recovery_eligibility(candidate, gate_result)
    if not eligible:
        return None

    return {
        "candidate": deepcopy(candidate),
        "gate_reason": _text(gate_result.get("reason")),
        "eligibility_reason": eligibility_reason,
        "attempt": int(attempt),
        "strength": recovery_strength(candidate),
    }


def select_best_recovery(records):
    valid = [record for record in (records or []) if isinstance(record, dict)]
    if not valid:
        return None

    # Strongest deterministic evidence/specificity signal first. Earlier
    # attempts win exact ties so repeated retries cannot reshuffle recovery.
    return max(
        valid,
        key=lambda record: (
            int(record.get("strength", 0)),
            -int(record.get("attempt", 9999)),
        ),
    )

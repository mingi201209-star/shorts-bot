from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "# CANDIDATE_POOL_HANDOFF_V1"


PATCH = r'''

# CANDIDATE_POOL_HANDOFF_V1
# Run 33887547463 + Run 33893139846: both measured ZERO_SUPPLY=6/7,
# EXPLORER_SELECTED=1/7. The Explorer remains the supplier, while host-owned
# deterministic validation/grounding becomes authoritative before Candidate Gate.
# No new LLM/Vision/image-generation call is introduced here.
from quality.candidate_pool_handoff import handoff_candidate_pool
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)

_candidate_pool_previous_validate_explorer_output = validate_explorer_output


def _candidate_pool_host_hard_validate(candidate):
    # Reuse existing aviation deterministic helpers, but intentionally do not use
    # generic-question/generic-reveal/predictable-payoff editorial checks here.
    # Those remain the independent Candidate Gate's authority.
    if not aviation_scope_compatible(candidate):
        return False, "candidate drifted outside aviation scope"

    details = _aviation_detail_values(candidate)
    if not details:
        return False, (
            "no concrete observation/constraint/result/trade-off/condition"
        )

    if not _aviation_detail_is_referenced(candidate, details):
        return False, "concrete detail is not carried by topic/question/reveal"

    visual_proof = str(candidate.get("visual_proof") or "").strip()
    fact_focus = str(candidate.get("fact_check_focus") or "").strip()
    if not visual_proof:
        return False, "visual_proof is empty"
    if not fact_focus:
        return False, "fact_check_focus is empty"

    return True, "aviation host hard validation PASS"


def validate_explorer_output(data):
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    status = str((data or {}).get("status") or "").strip().upper() if isinstance(data, dict) else ""

    if not aviation_scope or status != "CANDIDATE_POOL":
        return _candidate_pool_previous_validate_explorer_output(data)

    result = handoff_candidate_pool(
        data,
        scope="aviation",
        validate_candidate_fn=validate_candidate,
        hard_validate_fn=_candidate_pool_host_hard_validate,
        trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )

    trace = result.get("_candidate_pool_handoff") or {}
    print(
        "[CANDIDATE_POOL_HANDOFF] "
        f"status={trace.get('status')} "
        f"supplied={trace.get('supplied', len((data or {}).get('candidates') or []))} "
        f"survived={trace.get('survived', 0)}"
    )
    for item in trace.get("diagnostics") or []:
        print(
            "[CANDIDATE_POOL_ITEM] "
            f"index={item.get('index')} status={item.get('status')} "
            f"topic={item.get('topic', '')} reason={item.get('reason', '')}"
        )
    return result


CANDIDATE_EXPLORER_PROMPT += r"""

============================================================
15. AVIATION CANDIDATE POOL HANDOFF V1 — HOST AUTHORITY
============================================================

SHORTS_CANDIDATE_SCOPE=aviation의 automatic exploration에서는 이 블록이
앞선 shortlist/final-selection 지시보다 우선한다.

책임 경계:
- LLM = bounded candidate supplier
- HOST = deterministic schema / aviation specificity / canonical grounding authority
- Candidate Gate = independent editorial authority

기존 한 번의 Candidate Explorer 호출 안에서만 작업한다. 새 호출을 요구하지 마라.
#283의 observable seed contract를 그대로 사용해 broad direction 안에서 서로 다른
구체 관찰 seed를 만들고, 검토 가능한 Candidate를 host에 넘겨라.

SUPPLY-TIME에 Candidate 하나를 숨기거나 제거해도 되는 명백한 실패:
- Candidate object/schema 자체가 malformed
- required field 자체가 없음
- 명백한 fabrication 또는 실제로 성립 불가능한 claim
- 명백한 non-aviation/off-scope candidate

HOST가 판정할 항목이므로 LLM 내부에서 pool 전체를 0으로 만들지 말 것:
- canonical subject identity / grounding sufficiency
- aviation specificity의 deterministic 충족 여부
- visual_proof / structural grounding sufficiency
- factual/grounding validation

EDITORIAL 항목은 Candidate Gate 권한이므로 공급 단계에서 숨기지 말 것:
- broadness / genericness
- predictable payoff
- weak novelty
- 약한 editorial framing

즉 factual하고 구조적으로 작성 가능한 Candidate가 editorially 약해 보여도
host 검토를 받을 수 있도록 pool에 남겨라. Candidate Gate가 최종 reject할 수 있다.

[POOL SIZE]
기존 shortlist ceiling을 그대로 재사용한다. candidates는 1~3개만 반환한다.
숫자를 채우기 위해 fabrication/placeholder를 넣지 마라.

[AVIATION OUTPUT — PRIMARY]
검토 가능한 Candidate가 하나라도 있으면 반드시:
{
  "status": "CANDIDATE_POOL",
  "candidates": [
    {
      "topic": "...",
      "angle": "...",
      "core_question": "...",
      "micro_narrative": {
        "hook": "...",
        "core_question": "...",
        "reveal": "...",
        "payoff": "..."
      },
      "fact_check_focus": "...",
      "visual_proof": "...",
      "selection_reason": "...",
      "specific_observation": "...",
      "constraint": "...",
      "counterintuitive_result": "...",
      "tradeoff": "...",
      "concrete_condition": "...",
      "subject_kind": "physical_entity | non_physical_concept",
      "canonical_subject": "... | UNKNOWN | NOT_APPLICABLE",
      "subject_identity_confidence": 0.0,
      "grounding_evidence": []
    }
  ]
}

기존 Candidate schema와 aviation specificity fields를 그대로 사용한다.
적용되지 않는 optional specificity field는 빈 문자열이어도 되지만 최소 하나는
구체적으로 채워야 한다. source/citation/technical identity를 지어내지 마라.

REGENERATE는 malformed/fabricated/off-scope 후보를 제외한 뒤에도 host에 넘길
검토 가능한 Candidate가 정말 0개일 때만 사용한다. #282 supply/editorial 분리와
#283 observable-seed/recovery contract는 유지한다.
"""
'''


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ Candidate Pool Handoff V1 already applied")
        return
    required = (
        "AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V2",
        "AVIATION_OBSERVABLE_SEED_SUPPLY_V1",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(
            "Candidate Pool Handoff requires existing aviation contracts: "
            + ", ".join(missing)
        )
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ Candidate Pool Handoff V1 installed; host validation authority active")


main()

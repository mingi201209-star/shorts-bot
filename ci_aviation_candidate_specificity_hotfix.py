from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    text = append_once(
        text,
        "AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V1",
        r'''
# AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V1
# Strengthen aviation candidate generation before Candidate Gate. Candidate Gate
# itself is intentionally untouched.
_AVIATION_SPECIFICITY_FIELDS = (
    "specific_observation",
    "constraint",
    "counterintuitive_result",
    "tradeoff",
    "concrete_condition",
)
_AVIATION_DOMAIN_TERMS = {
    "비행기", "항공", "여객기", "기내", "객실", "조종석", "활주로", "공항",
    "엔진", "흡입구", "흡기", "날개", "윙렛", "착륙장치", "랜딩기어", "좌석",
    "aircraft", "airplane", "aviation", "airliner", "cabin", "cockpit", "runway",
    "engine", "wing", "winglet", "landing gear",
}
_AVIATION_GENERIC_REVEAL_TERMS = (
    "안전을 높", "안전성을 높", "안전을 위해", "효율을 높", "효율을 위해",
    "편의성을 높", "편의를 위해", "공기 흐름을 개선", "승객 경험을 개선",
    "승객 경험을 높", "소음을 줄", "성능을 높", "도움이 된다", "도움을 준다",
)
_AVIATION_GENERIC_QUESTION_FRAGMENTS = (
    "왜 특정하게 설계", "왜 이런 구조", "왜 이렇게 생", "왜 이런 배열",
    "왜 특정 배열", "왜 특정 위치", "왜 특정한 형태", "왜 존재할까",
)
_AVIATION_STOP_TOKENS = {
    "비행기", "항공", "여객기", "왜", "이유", "설계", "구조", "특정", "장치",
    "시스템", "기능", "있다", "하는", "위해", "때문", "일반", "실제",
}


def _aviation_norm(value):
    return re.sub(r"[^0-9a-zA-Z가-힣]+", " ", str(value or "").lower()).strip()


def _aviation_detail_values(candidate):
    return [
        str(candidate.get(field) or "").strip()
        for field in _AVIATION_SPECIFICITY_FIELDS
        if str(candidate.get(field) or "").strip()
    ]


def _aviation_detail_tokens(value):
    return {
        token for token in _aviation_norm(value).split()
        if len(token) >= 2 and token not in _AVIATION_STOP_TOKENS
    }


def aviation_scope_compatible(candidate):
    combined = " ".join(
        [
            str(candidate.get("topic") or ""),
            str(candidate.get("angle") or ""),
            str(candidate.get("core_question") or ""),
            str((candidate.get("micro_narrative") or {}).get("reveal") or ""),
        ]
    ).lower()
    return any(term in combined for term in _AVIATION_DOMAIN_TERMS)


def _aviation_detail_is_referenced(candidate, details):
    micro = candidate.get("micro_narrative") or {}
    combined = _aviation_norm(
        " ".join(
            [
                str(candidate.get("topic") or ""),
                str(candidate.get("core_question") or ""),
                str(micro.get("reveal") or ""),
            ]
        )
    )
    combined_tokens = set(combined.split())
    for detail in details:
        normalized = _aviation_norm(detail)
        if normalized and normalized in combined:
            return True
        detail_tokens = _aviation_detail_tokens(detail)
        if detail_tokens and combined_tokens & detail_tokens:
            return True
    return False


def _aviation_generic_reveal(candidate, details):
    reveal = _aviation_norm((candidate.get("micro_narrative") or {}).get("reveal"))
    if not reveal:
        return True
    if not any(term in reveal for term in _AVIATION_GENERIC_REVEAL_TERMS):
        return False
    # A generic benefit word may appear inside a concrete mechanism. Only reject it
    # when no structured concrete detail is actually referenced by the reveal.
    reveal_tokens = set(reveal.split())
    for detail in details:
        if reveal_tokens & _aviation_detail_tokens(detail):
            return False
    return True


def aviation_candidate_quality_check(candidate):
    if not isinstance(candidate, dict):
        return False, "aviation candidate is not an object"
    if not aviation_scope_compatible(candidate):
        return False, "aviation candidate drifted outside aviation scope"

    details = _aviation_detail_values(candidate)
    if not details:
        return False, "generic aviation topic: no concrete observation/constraint/result/trade-off/condition"

    core = _aviation_norm(candidate.get("core_question"))
    if (
        any(fragment in core for fragment in _AVIATION_GENERIC_QUESTION_FRAGMENTS)
        and not _aviation_detail_is_referenced(candidate, details)
    ):
        return False, "generic why-design question without a concrete element"

    if not _aviation_detail_is_referenced(candidate, details):
        return False, "topic/core question/reveal does not directly carry the concrete element"

    if _aviation_generic_reveal(candidate, details):
        return False, "generic benefit reveal without a concrete mechanism/constraint/trade-off"

    return True, "aviation candidate has concrete Shorts-level specificity"


_aviation_specificity_previous_validate_candidate = validate_candidate


def validate_candidate(candidate, *, prefix, runner_up=False):
    result = _aviation_specificity_previous_validate_candidate(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )
    # Optional structured specificity fields. They are not required for non-aviation
    # candidates, and empty/inapplicable fields are intentionally omitted.
    for field in _AVIATION_SPECIFICITY_FIELDS:
        value = candidate.get(field) if isinstance(candidate, dict) else None
        if isinstance(value, str) and value.strip():
            result[field] = value.strip()
    return result


_aviation_specificity_previous_validate_output = validate_explorer_output


def validate_explorer_output(data):
    result = _aviation_specificity_previous_validate_output(data)
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return result
    if result.get("status") != "SELECTED":
        return result

    winner = result.get("winner") or {}
    winner_ok, winner_reason = aviation_candidate_quality_check(winner)
    if winner_ok:
        return result

    runner = result.get("runner_up")
    if runner:
        runner_ok, _ = aviation_candidate_quality_check(runner)
        if runner_ok:
            promoted = dict(runner)
            promoted.pop("backup_independence", None)
            return {
                "status": "SELECTED",
                "winner": promoted,
                "runner_up": None,
            }

    return {
        "status": "REGENERATE",
        "reason": f"Aviation Explorer quality check: {winner_reason}",
    }


_aviation_specificity_previous_build_context = build_execution_context


def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
):
    context = _aviation_specificity_previous_build_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
    )
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return context

    rejected = [str(item).strip() for item in (rejected_topics or []) if str(item).strip()]
    rejected_feedback = "\n".join(f"- {item}" for item in rejected) or "- 없음"

    return context + f"""

============================================================
[AVIATION SHORTS SPECIFICITY CONTRACT]
============================================================

이번 aviation 탐색에서는 generic why-design topic을 최종 Candidate로 제출하지 마라.
"왜 X가 이런 모양/배열/위치인가?"라고만 묻고 Reveal이 안전·효율·편의·공기 흐름·승객 경험 같은 일반 목적어로 끝나면 Explorer 단계에서 버려라.

각 Candidate는 실제 사실 근거가 있는 경우 아래 필드 중 적용 가능한 것만 추가하라. 모든 필드를 억지로 채우지 마라.
- specific_observation: 눈에 보이는 특정 부품/구조의 이상하거나 구체적인 디테일
- constraint: 설계를 제한하는 압력·무게·공간·속도·온도·소음·안전 등의 구체 제약
- counterintuitive_result: 일반인의 직관과 반대되는 구체 결과
- tradeoff: 안전/성능 등을 위해 일부러 감수한 구체 단점 또는 손해
- concrete_condition: 숫자·거리·시간·압력·속도·온도·비상/극한 조건 등 구체 상황

최종 topic, core_question, micro_narrative.reveal에는 위 필드 중 최소 하나의 구체 요소가 직접 드러나야 한다.
필드만 채우고 실제 질문/Reveal에는 반영하지 않는 것은 실패다.

강한 후보의 중심은 다음 중 최소 하나여야 한다.
- 특정 부품/구조의 눈에 띄는 디테일
- 숫자/거리/시간/압력/속도/온도 같은 구체 조건
- 강한 설계 제약
- 안전 때문에 감수하는 trade-off
- 직관과 반대되는 결과
- 비정상/극한 상황에서 드러나는 기능
- 같은 항공기 내부 다른 구조와 비교했을 때 생기는 차이

[DOWNSTREAM REJECTION FEEDBACK]
아래 후보는 이번 실행에서 이미 downstream Candidate Gate 또는 앞선 탐색에서 폐기되었다.
{rejected_feedback}

위 명사를 단순히 다른 부품명으로 바꾼 같은 semantic pattern을 다시 만들지 마라.
특히 "왜 [부품]이 특정 모양/배치/위치인가? → 안전/효율/편의 때문에" 패턴이 폐기됐다면 다음 attempt에서는 반드시 다른 구체 관찰, 제약, trade-off, 조건 또는 counterintuitive result를 중심으로 탐색하라.
retry 횟수나 API budget을 늘리지 말고 현재 attempt 안에서 약한 seed를 스스로 버려라.

[AVIATION OUTPUT EXTENSION]
기존 JSON contract를 그대로 유지하면서 winner/runner_up 객체에는 적용 가능한 경우에만 다음 선택 필드를 추가할 수 있다:
"specific_observation", "constraint", "counterintuitive_result", "tradeoff", "concrete_condition".
"""


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION OUTPUT NOTE]
SHORTS_CANDIDATE_SCOPE=aviation 실행에서는 execution context의 AVIATION SHORTS SPECIFICITY CONTRACT를 최우선으로 지켜라.
선택 필드에 근거 없는 내용을 만들어 넣지 마라.
"""
''',
    )
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation candidate specificity + rejected-pattern feedback hotfix applied")


if __name__ == "__main__":
    main()

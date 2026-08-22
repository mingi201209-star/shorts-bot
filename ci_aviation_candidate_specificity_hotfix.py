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
        "AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V2",
        r'''
# AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V1
# AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V2
# Candidate Gate is unchanged. This layer makes the Explorer produce candidates
# at the level the Gate already expects, including fixed-topic retries.
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
    "연료 효율", "비행 효율", "비행 안정", "비행 성능", "이점",
)
_AVIATION_GENERIC_QUESTION_FRAGMENTS = (
    "왜 특정하게 설계", "왜 이런 구조", "왜 이렇게 생", "왜 이런 배열",
    "왜 특정 배열", "왜 특정 위치", "왜 특정한 형태", "왜 존재할까",
    "어떤 영향을", "어떤 이점", "왜 효율", "성능에", "효율에",
)
_AVIATION_STOP_TOKENS = {
    "비행기", "항공", "여객기", "왜", "이유", "설계", "구조", "특정", "장치",
    "시스템", "기능", "있다", "하는", "위해", "때문", "일반", "실제",
    "효율", "성능", "안전", "이점", "영향", "도움",
}
_AVIATION_MECHANISM_HINTS = (
    "와류", "유도항력", "압력차", "압력 차", "양력", "항력", "난류", "소용돌이",
    "vortex", "induced drag", "pressure", "lift", "drag", "turbulence",
)


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
        token
        for token in _aviation_norm(value).split()
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
            return {"status": "SELECTED", "winner": promoted, "runner_up": None}
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
    fixed_topic=None,
    fixed_topic_gate_feedback="",
):
    context = _aviation_specificity_previous_build_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic=fixed_topic,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
    )
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return context

    rejected = [str(item).strip() for item in (rejected_topics or []) if str(item).strip()]
    rejected_feedback = "\n".join(f"- {item}" for item in rejected) or "- 없음"
    fixed = str(fixed_topic or "").strip()
    gate_feedback = str(fixed_topic_gate_feedback or "").strip()
    fixed_contract = ""
    if fixed:
        fixed_contract = f"""
[FIXED AVIATION TOPIC — CONCRETE MECHANISM CONTRACT]
고정 주제: {fixed}

고정 주제의 명사는 유지하되 질문을 '효율/성능/안전에 어떤 영향?' 같은 추상적 benefit 질문으로 바꾸지 마라.
반드시 다음 구조로 좁혀라:
1) 사람이 화면에서 바로 확인할 수 있는 구체 관찰 하나
2) 그 관찰을 만든 물리적/기계적 원인 또는 설계 제약 하나
3) 그 원인이 만드는 직접 결과 하나

core_question은 1)의 관찰을 직접 물어야 하고, micro_narrative.reveal은 2)와 3)을 명시해야 한다.
'효율이 좋아진다', '안정성이 높아진다', '성능에 도움이 된다'만으로 Reveal을 끝내면 실패다.

예시 형식(문구 복사 금지):
- 관찰: 날개 끝이 위로 꺾여 있다
- 질문: 왜 날개 끝을 위로 꺾어 놓았을까?
- 메커니즘: 날개 위아래 압력 차가 끝단에서 강한 소용돌이를 만들고, 끝단 형상이 그 흐름을 약화시킨다
- 직접 결과: 유도항력이 줄어든다

윙렛/날개끝 주제라면 사실 근거가 있을 때 '날개 끝 와류', '압력 차', '유도항력'처럼 실제 메커니즘 단위를 우선 검토하라. 근거 없는 수치나 효과 크기는 만들지 마라.
이전 Gate 피드백: {gate_feedback or '없음'}
"""

    return context + f"""

============================================================
[AVIATION SHORTS SPECIFICITY CONTRACT]
============================================================
{fixed_contract}
이번 aviation 탐색에서는 generic why-design topic을 최종 Candidate로 제출하지 마라.
각 Candidate는 사실 근거가 있는 경우 specific_observation / constraint / counterintuitive_result / tradeoff / concrete_condition 중 적용 가능한 필드를 사용하라.
최종 topic, core_question, micro_narrative.reveal에는 최소 하나의 구체 요소가 직접 드러나야 한다.

[DOWNSTREAM REJECTION FEEDBACK]
{rejected_feedback}

같은 명사만 바꾸거나 '왜 X인가? → 안전/효율/편의' 패턴을 반복하지 마라. retry/API budget은 늘리지 않는다.

[AVIATION OUTPUT EXTENSION]
기존 JSON contract를 유지하고 적용 가능한 경우에만 선택 specificity 필드를 추가하라.
"""


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION OUTPUT NOTE]
SHORTS_CANDIDATE_SCOPE=aviation에서는 execution context의 specificity contract를 최우선으로 지켜라.
특히 fixed_topic이 있으면 추상적 benefit 질문이 아니라 관찰 → 메커니즘 → 직접 결과 구조로 좁혀라.
근거 없는 내용을 만들지 마라.
"""
''',
    )
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation candidate specificity V2 + fixed-topic mechanism contract applied")


if __name__ == "__main__":
    main()

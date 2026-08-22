from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    marker = "AVIATION_SPECIFICITY_PROJECTION_V2"
    if marker in text:
        print("✅ Aviation specificity projection already applied")
        return

    text += r'''

# AVIATION_SPECIFICITY_PROJECTION_V2
# Reuses the existing single bounded aviation repair slot to project an already
# grounded specificity detail into the user-visible Candidate fields consumed by
# Candidate Gate. No gate threshold, retry limit, cost ceiling, or Sora setting
# is changed.

def _aviation_projection_failure_reason(candidate):
    if not isinstance(candidate, dict):
        return "candidate is not an object"
    ok, reason = aviation_candidate_quality_check(candidate)
    return "" if ok else str(reason or "")


def _aviation_specificity_repair_needed(data):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return False
    if not isinstance(data, dict):
        return False
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return False

    winner = data.get("winner")
    if _aviation_specificity_output_missing(winner):
        return True

    reason = _aviation_projection_failure_reason(winner)
    return (
        "does not directly carry the concrete element" in reason
        or "generic why-design question without a concrete element" in reason
        or "generic benefit reveal without a concrete mechanism/constraint/trade-off" in reason
    )


def _aviation_original_text_blob(candidate):
    return _aviation_norm(json.dumps(candidate or {}, ensure_ascii=False, sort_keys=True))


def _aviation_repaired_specificity_is_grounded(original, repaired):
    if not isinstance(original, dict) or not isinstance(repaired, dict):
        return False
    original_blob = _aviation_original_text_blob(original)
    for field in _AVIATION_SPECIFICITY_FIELDS:
        old_value = str(original.get(field) or "").strip()
        new_value = str(repaired.get(field) or "").strip()
        if old_value:
            if new_value != old_value:
                return False
            continue
        if not new_value:
            continue
        normalized = _aviation_norm(new_value)
        if not normalized or normalized not in original_blob:
            return False
    return bool(_aviation_detail_values(repaired))


def _aviation_projection_preserves_identity(original, repaired):
    protected = (
        "angle",
        "fact_check_focus",
        "visual_proof",
        "selection_reason",
    )
    return all(repaired.get(field) == original.get(field) for field in protected)


def _repair_aviation_specificity_output_if_needed(data, *, model=MODEL):
    if not _aviation_specificity_repair_needed(data):
        return data

    call_number = authorize_call(model)
    print(
        "🩹 Aviation specificity projection repair API call authorized: "
        f"#{call_number}"
    )

    original_json = json.dumps(data, ensure_ascii=False, indent=2)
    repair_prompt = f"""
[AVIATION SPECIFICITY PROJECTION REPAIR — ONE BOUNDED PASS]

아래 Candidate Explorer JSON은 aviation SELECTED 후보지만, 구체 요소가 구조화 필드에만 있거나
구체 필드가 빠져 있어 Candidate Gate가 읽는 topic/core_question/micro_narrative.reveal에
실제 구체성이 충분히 드러나지 않는다.

이 호출은 새 Candidate를 만드는 호출이 아니다. 원본에 이미 적힌 사실과 의미만 사용해
구체 요소를 보이는 문장으로 투영하는 단 한 번의 bounded repair다.

절대 규칙:
1. 새 사실, 새 숫자, 새 부품, 새 인과관계, 새 설계 의도, 새 역사적 원인을 추가하지 마라.
2. angle, fact_check_focus, visual_proof, selection_reason은 byte-for-byte 같은 JSON 값으로 유지하라.
3. runner_up이 null이면 그대로 null이다.
4. 기존 specificity 필드 값은 한 글자도 바꾸지 마라.
5. specificity 필드가 모두 비어 있다면 원본 topic/core_question/micro_narrative 안에 이미 문구로 존재하는
   구체 요소 하나만 그대로 복사해 다음 중 맞는 필드 하나에 넣을 수 있다:
   specific_observation, constraint, counterintuitive_result, tradeoff, concrete_condition.
6. topic, core_question, micro_narrative의 hook/core_question/reveal/payoff는 의미를 바꾸지 않는 최소 재표현만 허용한다.
   목적은 기존 구체 요소를 문장 안에 직접 보이게 하는 것이다.
7. 특히 topic + core_question + reveal 중 최소 하나가 구조화 specificity 값의 핵심 표현을 직접 포함해야 하고,
   reveal은 안전/효율/편의 같은 일반 목적어로 끝나지 말고 원본에 이미 있는 메커니즘/제약/trade-off를 명시해야 한다.
8. 원본에 안전하게 투영할 concrete element가 없다면 발명하지 말고
   {{"status":"REGENERATE","reason":"aviation specificity projection could not recover grounded detail"}}
   만 반환하라.
9. JSON 객체 하나만 반환하라. 설명/Markdown 금지.

원본 JSON:
{original_json}
"""

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You perform one conservative JSON projection repair. "
                    "Use only facts and concrete wording already present in the input. "
                    "Never invent a detail to make the candidate pass."
                ),
            },
            {"role": "user", "content": repair_prompt},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    usage = record_usage(model, response)
    print(f"💰 Aviation specificity projection repair call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        return {
            "status": "REGENERATE",
            "reason": "aviation specificity projection repair returned empty output",
        }

    repaired = extract_json(content)
    if str(repaired.get("status") or "").strip().upper() != "SELECTED":
        return repaired

    original_winner = data.get("winner") or {}
    repaired_winner = repaired.get("winner") or {}

    if not _aviation_projection_preserves_identity(original_winner, repaired_winner):
        return {
            "status": "REGENERATE",
            "reason": "aviation specificity projection changed protected identity fields",
        }

    if not _aviation_repaired_specificity_is_grounded(original_winner, repaired_winner):
        return {
            "status": "REGENERATE",
            "reason": "aviation specificity projection introduced ungrounded specificity",
        }

    ok, reason = aviation_candidate_quality_check(repaired_winner)
    if not ok:
        return {
            "status": "REGENERATE",
            "reason": f"aviation specificity projection still weak: {reason}",
        }

    return repaired


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION SPECIFICITY PROJECTION — GATE-VISIBLE CONTRACT]
aviation Candidate에서 concrete detail을 별도 필드에만 숨기지 마라.
Candidate Gate가 직접 읽는 topic, core_question, micro_narrative.reveal에도 같은 구체 요소를 명시하라.
예: '왜 특정 형태인가 → 안전을 위해'처럼 일반론으로 쓰지 말고,
이미 사실 근거가 있는 구체 관찰/제약/trade-off/조건이 질문과 Reveal 자체의 중심이 되게 하라.
새로운 사실을 만들어 구체적으로 보이게 하는 것은 금지한다.
"""
'''

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation gate-visible specificity projection hotfix applied")


if __name__ == "__main__":
    main()

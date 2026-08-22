from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    marker = "AVIATION_SPECIFICITY_OUTPUT_REPAIR_V1"
    if marker in text:
        print("✅ Aviation specificity output repair already applied")
        return

    insert_before_result = '''    result = (\n        validate_explorer_output(\n            parsed\n        )\n    )\n'''
    replacement = '''    parsed = _repair_aviation_specificity_output_if_needed(\n        parsed,\n        model=model,\n    )\n\n    result = (\n        validate_explorer_output(\n            parsed\n        )\n    )\n'''
    count = text.count(insert_before_result)
    if count != 1:
        raise RuntimeError(f"explorer validation insertion marker mismatch: {count}")
    text = text.replace(insert_before_result, replacement, 1)

    text += r'''

# AVIATION_SPECIFICITY_OUTPUT_REPAIR_V1
# Production-safe schema repair for aviation Candidate Explorer output.
# This does not weaken Candidate Gate or specificity quality checks. It only gives
# a SELECTED aviation output that omitted all structured specificity fields one
# bounded chance to copy an already-stated concrete element into the proper field.
# If the original candidate contains no safely reusable concrete element, repair
# must return REGENERATE rather than inventing a fact.

def _aviation_specificity_output_missing(candidate):
    if not isinstance(candidate, dict):
        return True
    return not any(
        isinstance(candidate.get(field), str) and candidate.get(field).strip()
        for field in _AVIATION_SPECIFICITY_FIELDS
    )


def _aviation_specificity_repair_needed(data):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return False
    if not isinstance(data, dict):
        return False
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return False
    return _aviation_specificity_output_missing(data.get("winner"))


def _repair_aviation_specificity_output_if_needed(data, *, model=MODEL):
    if not _aviation_specificity_repair_needed(data):
        return data

    call_number = authorize_call(model)
    print(
        "🩹 Aviation specificity schema repair API call authorized: "
        f"#{call_number}"
    )

    original_json = json.dumps(data, ensure_ascii=False, indent=2)
    repair_prompt = f"""
[AVIATION CANDIDATE SCHEMA REPAIR — ONE BOUNDED PASS]

아래 Candidate Explorer JSON은 SELECTED이지만 winner가 aviation specificity 구조화 필드를 모두 누락했다.
이 호출은 새 Candidate 생성이나 내용 개선이 아니라 출력 스키마 복구만 수행한다.

절대 규칙:
1. topic, angle, core_question, micro_narrative, fact_check_focus, visual_proof, selection_reason의 의미를 바꾸지 마라.
2. 새 사실, 새 숫자, 새 인과관계, 새 설계 의도, 새 역사적 원인을 추가하지 마라.
3. 아래 기존 JSON에 이미 명시적으로 표현된 구체 요소만 그대로 요약/복사하여 적절한 필드에 넣어라.
4. winner에는 다음 중 사실상 맞는 필드를 최소 1개 포함해야 한다:
   specific_observation, constraint, counterintuitive_result, tradeoff, concrete_condition
5. 모든 필드를 억지로 채우지 마라. 근거가 있는 필드만 사용한다.
6. 기존 JSON에 안전하게 옮길 수 있는 구체 요소가 하나도 없다면 내용을 발명하지 말고
   {{"status":"REGENERATE","reason":"aviation specificity repair could not recover a grounded concrete field"}}
   만 반환하라.
7. runner_up이 null이면 그대로 null. runner_up이 있더라도 근거 없는 필드를 만들지 마라.
8. JSON 객체 하나만 반환하라. 설명/Markdown 금지.

원본 JSON:
{original_json}
"""

    response = (
        openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You repair a JSON schema without adding facts. "
                        "Preserve candidate meaning exactly; if a grounded field cannot be copied "
                        "from the original JSON, return REGENERATE."
                    ),
                },
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    )

    usage = record_usage(model, response)
    print(f"💰 Aviation specificity repair call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        return {
            "status": "REGENERATE",
            "reason": "aviation specificity repair returned empty output",
        }

    repaired = extract_json(content)
    if str(repaired.get("status") or "").strip().upper() == "SELECTED":
        original_winner = data.get("winner") or {}
        repaired_winner = repaired.get("winner") or {}
        protected_fields = (
            "topic",
            "angle",
            "core_question",
            "micro_narrative",
            "fact_check_focus",
            "visual_proof",
            "selection_reason",
        )
        for field in protected_fields:
            if repaired_winner.get(field) != original_winner.get(field):
                return {
                    "status": "REGENERATE",
                    "reason": f"aviation specificity repair changed protected field: {field}",
                }

    return repaired


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION OUTPUT CONTRACT OVERRIDE — SPECIFICITY REQUIRED]
SHORTS_CANDIDATE_SCOPE=aviation에서 status=SELECTED를 반환할 때 winner에는 아래 5개 중
실제 근거가 있는 필드를 최소 1개 반드시 포함하라:
specific_observation, constraint, counterintuitive_result, tradeoff, concrete_condition.
이전의 '선택 필드' 표현은 '모든 필드를 강제하지 않는다'는 뜻일 뿐이며,
winner가 5개를 전부 생략해도 된다는 뜻이 아니다.
근거 없는 값을 만들어 필드 수를 채우는 것은 금지한다.
안전하게 넣을 수 있는 구체 필드가 하나도 없다면 SELECTED가 아니라 REGENERATE를 반환하라.
"""
'''

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation specificity output contract + bounded repair hotfix applied")


if __name__ == "__main__":
    main()

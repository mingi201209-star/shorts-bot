from pathlib import Path

path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

marker = "SCRIPT_VALIDATION_RECOVERY_V1"
if marker not in text:
    needle = "        prompt = f\"\"\"\n"
    if needle not in text:
        raise RuntimeError("script prompt marker not found")

    text = text.replace(
        needle,
        "        recovery_guidance = _script_validation_recovery_guidance(last_error)\n\n" + needle,
        1,
    )

    prompt_anchor = "[CONTENT LOCK]\n"
    if prompt_anchor not in text:
        raise RuntimeError("content lock marker not found")
    text = text.replace(
        prompt_anchor,
        "[VALIDATION RECOVERY]\n{recovery_guidance}\n\n[CONTENT LOCK]\n",
        1,
    )

    text += r'''

# SCRIPT_VALIDATION_RECOVERY_V1
# Feed the previous hard-validation failure back into the next already-bounded
# Script Generator attempt. This does not add API calls or weaken validators.
def _script_validation_recovery_guidance(last_error):
    reason = str(last_error or "").strip()
    if not reason:
        return (
            "첫 시도다. Candidate의 검증된 사실 범위만 사용하고, "
            "FUNCTION을 DESIGN INTENT/HISTORICAL CAUSE로 바꾸지 마라."
        )

    guidance = [
        f"직전 대본은 다음 하드 검증에서 실패했다: {reason}",
        "이번 시도에서는 실패 원인만 교정하고 Candidate의 topic/angle/core_question/reveal/payoff는 유지한다.",
        "검증기를 우회하거나 기준을 낮추지 말고, 문제가 된 주장/반복/구조를 제거하거나 사실 안전한 표현으로 다시 쓴다.",
    ]

    lowered = reason.lower()
    if "unsupported design intent" in lowered or "historical cause" in lowered:
        guidance.extend([
            "Candidate 근거에 설계 목적/역사적 원인이 명시되지 않았다면 '위해 설계됐다', '때문에 만들었다', '발명됐다', '개발됐다' 같은 목적·기원 단정을 쓰지 마라.",
            "대신 현재 관찰 가능한 FUNCTION과 MECHANISM을 직접 설명한다: '이 구조는 X를 한다', 'X가 Y를 통해 Z로 이어진다'.",
            "problem/constraint 단계가 근거에 없으면 억지로 채우지 말고 생략한다. DESIGN CAUSALITY는 근거 없는 causal stage를 요구하지 않는다.",
        ])
    if "paraphrase" in lowered or "causal step" in lowered or "progression" in lowered:
        guidance.extend([
            "같은 mechanism/result를 어휘만 바꿔 반복하지 마라.",
            "Candidate에 specificity/specific_observation/constraint/counterintuitive_result/tradeoff/concrete_condition이 있으면 그 검증된 값을 서로 다른 causal unit으로 직접 사용한다.",
            "설계형 최소 장면 수를 맞출 때 같은 결과를 반복하지 말고 HOOK/OBSERVATION → QUESTION/PROBLEM → CONSTRAINT/CONDITION → DESIGN/STRUCTURE → MECHANISM STEP → CONSEQUENCE → RESULT → PAYOFF처럼 각 장면의 역할을 분리한다. 단, Candidate에 없는 사실은 만들지 않는다.",
        ])
    if "장면 수 부족" in reason or "scene" in lowered and "부족" in reason:
        guidance.extend([
            "설계형 주제의 최소 장면 수를 먼저 확보하되 filler를 추가하지 마라.",
            "Candidate의 서로 다른 검증된 observation/constraint/condition/tradeoff/mechanism/result를 각각 한 장면의 새 정보 단위로 배치한다.",
        ])
    if "generic outro" in lowered or "filler" in lowered or "repetition" in lowered:
        guidance.append("일반론적 마무리와 길이 채우기 문장을 삭제하고 Core Question의 직접 답으로 끝낸다.")

    return "\n".join(f"- {item}" for item in guidance)
'''

# SCRIPT_VALIDATION_RECOVERY_V2_GROUNDED_SPECIFICITY
# Candidate Explorer may carry aviation-specific grounded fields that the base
# validator historically dropped. Preserve them for the already-bounded script
# attempts so causal progression can use verified units instead of inventing
# filler. This changes neither validators nor retry/API/cost limits.
if "SCRIPT_VALIDATION_RECOVERY_V2_GROUNDED_SPECIFICITY" not in text:
    text += r'''

# SCRIPT_VALIDATION_RECOVERY_V2_GROUNDED_SPECIFICITY
_script_recovery_original_validate_candidate = validate_candidate
_SCRIPT_RECOVERY_SPECIFICITY_KEYS = (
    "specific_observation",
    "constraint",
    "counterintuitive_result",
    "tradeoff",
    "concrete_condition",
)


def validate_candidate(candidate):
    cleaned = _script_recovery_original_validate_candidate(candidate)
    if not isinstance(candidate, dict):
        return cleaned

    specificity = candidate.get("specificity")
    if isinstance(specificity, dict):
        kept = {
            key: str(value).strip()
            for key, value in specificity.items()
            if key in _SCRIPT_RECOVERY_SPECIFICITY_KEYS and str(value).strip()
        }
        if kept:
            cleaned["specificity"] = kept

    for key in _SCRIPT_RECOVERY_SPECIFICITY_KEYS:
        value = str(candidate.get(key, "")).strip()
        if value:
            cleaned[key] = value

    return cleaned
'''

path.write_text(text, encoding="utf-8")
print("✅ Bounded script validation recovery guidance + grounded specificity preservation applied")

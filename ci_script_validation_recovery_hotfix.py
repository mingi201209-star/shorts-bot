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
            "새 component/condition/consequence가 Candidate 근거에 없다면 장면을 늘리지 말고 압축한다.",
        ])
    if "generic outro" in lowered or "filler" in lowered or "repetition" in lowered:
        guidance.append("일반론적 마무리와 길이 채우기 문장을 삭제하고 Core Question의 직접 답으로 끝낸다.")

    return "\n".join(f"- {item}" for item in guidance)
'''

path.write_text(text, encoding="utf-8")
print("✅ Bounded script validation recovery guidance applied")

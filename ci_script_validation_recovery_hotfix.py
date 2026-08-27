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
    if "narrative reveal contract" in lowered or "opening question" in lowered:
        guidance.extend([
            "마지막 두 Scene은 Candidate의 locked reveal → locked payoff 순서로 질문을 명시적으로 회수한다.",
            "결말을 새로운 일반론이나 분위기 문장으로 바꾸지 말고, 처음 질문의 직접 답을 끝부분에 남긴다.",
        ])

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

# SCRIPT_OPENING_LOCK_V1 + SCRIPT_CLOSING_LOCK_V1
# Candidate/Hook selection already approved the first two and final two narrative
# beats. Preserve generated visual metadata, but deterministically restore those
# narration beats before every existing validator runs.
if "SCRIPT_OPENING_LOCK_V1" not in text:
    validation_anchor = '''            valid, reason = validate_script(
                generated
            )
'''
    locked_validation = '''            generated = _script_opening_lock_apply(
                generated,
                candidate,
            )
            generated = _script_closing_lock_apply(
                generated,
                candidate,
            )

            valid, reason = validate_script(
                generated
            )
'''
    if text.count(validation_anchor) != 1:
        raise RuntimeError(
            f"script opening/closing lock validation marker mismatch: {text.count(validation_anchor)}"
        )
    text = text.replace(validation_anchor, locked_validation, 1)

    prompt_marker = '''[MICRO NARRATIVE]
HOOK: {micro['hook']}
QUESTION: {micro['core_question']}
REVEAL: {micro['reveal']}
PAYOFF: {micro['payoff']}
'''
    prompt_replacement = '''[MICRO NARRATIVE]
HOOK: {micro['hook']}
QUESTION: {micro['core_question']}
REVEAL: {micro['reveal']}
PAYOFF: {micro['payoff']}

[LOCKED OPENING — DO NOT REWRITE]
Scene 1 narration text is already approved and will be restored deterministically to:
{micro['hook']}
Scene 2 narration text is already approved and will be restored deterministically to:
{micro['core_question']}
Generate useful visual_goal/keyword fields for those scenes, but spend your writing effort on Scene 3 onward.
Do not duplicate Scene 1/2 wording later in the script.

[LOCKED CLOSING — DO NOT REWRITE]
The final two narration beats are already approved and will be restored deterministically to:
REVEAL: {micro['reveal']}
PAYOFF: {micro['payoff']}
Generate useful visual_goal/keyword fields for those final scenes. Build the middle scenes so they lead causally into this reveal/payoff without duplicating it early.
'''
    if text.count(prompt_marker) != 1:
        raise RuntimeError("script opening/closing lock prompt marker mismatch")
    text = text.replace(prompt_marker, prompt_replacement, 1)

    text += r'''

# SCRIPT_OPENING_LOCK_V1
_SAFE_FORMAL_ENDING_REPAIRS = (
    (re.compile(r"있는데요([.!?…]*)$"), r"있습니다\1"),
    (re.compile(r"없는데요([.!?…]*)$"), r"없습니다\1"),
    (re.compile(r"되는데요([.!?…]*)$"), r"됩니다\1"),
    (re.compile(r"생기는데요([.!?…]*)$"), r"생깁니다\1"),
    (re.compile(r"하는데요([.!?…]*)$"), r"합니다\1"),
    (re.compile(r"인데요([.!?…]*)$"), r"입니다\1"),
    (re.compile(r"있죠([.!?…]*)$"), r"있습니다\1"),
    (re.compile(r"없죠([.!?…]*)$"), r"없습니다\1"),
    (re.compile(r"되죠([.!?…]*)$"), r"됩니다\1"),
    (re.compile(r"생기죠([.!?…]*)$"), r"생깁니다\1"),
    (re.compile(r"보이죠([.!?…]*)$"), r"보입니다\1"),
    (re.compile(r"때문이죠([.!?…]*)$"), r"때문입니다\1"),
    (re.compile(r"보세요([.!?…]*)$"), r"볼 수 있습니다\1"),
    # SCRIPT_FINAL_FORMAL_ENDING_PARITY_V1
    # Mirror the already-approved Script V2 deterministic formalization at the
    # production generator's last boundary before strict speech-style validation.
    # Declarative-only patterns deliberately exclude '?' so question contracts
    # remain owned by the existing question path.
    (re.compile(r"않는다([.!…]*)$"), r"않습니다\1"),
    (re.compile(r"줄어든다([.!…]*)$"), r"줄어듭니다\1"),
    (re.compile(r"늘어난다([.!…]*)$"), r"늘어납니다\1"),
    (re.compile(r"약해진다([.!…]*)$"), r"약해집니다\1"),
    (re.compile(r"강해진다([.!…]*)$"), r"강해집니다\1"),
    (re.compile(r"달라진다([.!…]*)$"), r"달라집니다\1"),
    (re.compile(r"좋아진다([.!…]*)$"), r"좋아집니다\1"),
    (re.compile(r"이루어진다([.!…]*)$"), r"이루어집니다\1"),
    (re.compile(r"알려진다([.!…]*)$"), r"알려집니다\1"),
    (re.compile(r"도와준다([.!…]*)$"), r"도와줍니다\1"),
    (re.compile(r"워진다([.!…]*)$"), r"워집니다\1"),
    (re.compile(r"되었다([.!…]*)$"), r"되었습니다\1"),
    (re.compile(r"한다([.!…]*)$"), r"합니다\1"),
)


def _script_safe_formal_ending_repair(text):
    value = str(text or "").strip()
    for pattern, replacement in _SAFE_FORMAL_ENDING_REPAIRS:
        repaired = pattern.sub(replacement, value)
        if repaired != value:
            before_ending = value.rstrip(".!…").split()[-1] if value else ""
            after_ending = repaired.rstrip(".!…").split()[-1] if repaired else ""
            print(
                "[ScriptFinalNormalize] changed=true "
                f"before_ending={before_ending!r} after_ending={after_ending!r}"
            )
            return repaired
    return value


def _script_opening_lock_apply(payload, candidate):
    if not isinstance(payload, dict) or not isinstance(candidate, dict):
        return payload

    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        return payload

    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    locked_hook = str(micro.get("hook", "")).strip()
    locked_question = str(micro.get("core_question", "")).strip()

    if len(scenes) >= 1 and isinstance(scenes[0], dict) and locked_hook:
        scenes[0]["text"] = locked_hook
    if len(scenes) >= 2 and isinstance(scenes[1], dict) and locked_question:
        scenes[1]["text"] = locked_question

    for scene in scenes[2:]:
        if isinstance(scene, dict):
            scene["text"] = _script_safe_formal_ending_repair(scene.get("text", ""))

    return payload


# SCRIPT_CLOSING_LOCK_V1
def _script_closing_lock_apply(payload, candidate):
    if not isinstance(payload, dict) or not isinstance(candidate, dict):
        return payload

    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 4:
        return payload

    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        return payload

    locked_reveal = str(micro.get("reveal", "")).strip()
    locked_payoff = str(micro.get("payoff", "")).strip()

    if isinstance(scenes[-2], dict) and locked_reveal:
        scenes[-2]["text"] = _script_safe_formal_ending_repair(locked_reveal)
    if isinstance(scenes[-1], dict) and locked_payoff:
        scenes[-1]["text"] = _script_safe_formal_ending_repair(locked_payoff)

    return payload
'''

path.write_text(text, encoding="utf-8")
print("✅ Bounded script validation recovery + approved opening/closing lock applied")

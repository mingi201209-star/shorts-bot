from pathlib import Path


# Script-only production parity layer. Runs after #30 and does not touch video/provider code.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

# Replace the conflicting duration-fill instructions with a candidate-aware helper.
# Non-design topics retain the legacy target range; design topics use only the max cap.
old_intro = (
    "새 소재를 탐색하지 말고 확정 Winner를 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초,\n"
    "{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n"
)
new_intro = (
    "{_script_parity_duration_opening(candidate)}\n"
    "{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n"
)
if old_intro not in text:
    raise RuntimeError("script duration opening marker not found")
text = text.replace(old_intro, new_intro, 1)

old_length = (
    "[LENGTH]\n"
    "전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다.\n"
    "너무 짧은 문장을 억지로 Scene 수만 맞추려고 잘게 쪼개지 마라.\n"
)
new_length = (
    "[LENGTH]\n"
    "{_script_parity_length_instruction(candidate)}\n"
    "너무 짧은 문장을 억지로 Scene 수만 맞추려고 잘게 쪼개지 마라.\n"
)
if old_length not in text:
    raise RuntimeError("script length marker not found")
text = text.replace(old_length, new_length, 1)

if "SCRIPT_PRODUCTION_CONTEXT_PARITY_V1" not in text:
    text += r'''

# SCRIPT_PRODUCTION_CONTEXT_PARITY_V1
_SCRIPT_PARITY_ACTIVE_CONTEXT = None


def _script_parity_context(candidate):
    if not isinstance(candidate, dict):
        return {}
    return {
        "topic": str(candidate.get("topic", "")),
        "angle": str(candidate.get("angle", "")),
        "core_question": str(candidate.get("core_question", "")),
        "fact_check_focus": list(candidate.get("fact_check_focus", []) or []),
        "micro_narrative": dict(candidate.get("micro_narrative", {}) or {}),
    }


def _script_parity_is_design_candidate(candidate):
    try:
        return bool(design_causality_applicable(_script_parity_context(candidate)))
    except Exception:
        return False


def _script_parity_duration_opening(candidate):
    if _script_parity_is_design_candidate(candidate):
        return (
            f"새 소재를 탐색하지 말고 확정 Winner를 최대 {TARGET_MAX_SECONDS}초 안에서, "
            "검증된 causal information이 끝나는 즉시 자연스럽게 종료되는"
        )
    return (
        f"새 소재를 탐색하지 말고 확정 Winner를 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초,"
    )


def _script_parity_length_instruction(candidate):
    if _script_parity_is_design_candidate(candidate):
        return (
            f"설계형 주제는 {TARGET_MAX_SECONDS}초를 안전 상한으로만 사용한다. "
            "TARGET_MIN_SECONDS를 채우기 위해 mechanism/result를 반복하거나 filler를 추가하지 않는다. "
            "검증된 problem→constraint→design→mechanism→payoff 정보가 30~40초대에 끝나면 그대로 종료해도 된다."
        )
    return (
        f"전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다."
    )


# Mechanism-role semantics: distinguish a genuinely new causal step from paraphrase/detail.
_SCRIPT_PARITY_MECHANISM_ROLES = {
    "sense_analyze": (
        r"분석", r"감지", r"측정", r"탐지", r"모니터", r"주파수.{0,8}(읽|분석|감지)",
        r"방향.{0,8}(읽|분석|감지)",
    ),
    "counter_signal": (
        r"반대.{0,6}(신호|소리|파형)", r"상쇄.{0,6}(음|소리|신호|파형)",
        r"역위상", r"취소.{0,6}(신호|소리)", r"반대.{0,6}(생성|발생|만들)",
    ),
    "regulate_balance": (
        r"조절", r"균형", r"평형", r"압력.{0,8}(맞|조절|균형)", r"유량.{0,8}(조절|제어)",
    ),
    "transfer_distribute": (
        r"분산", r"전달", r"재분배", r"하중.{0,8}(분산|전달)", r"응력.{0,8}(분산|전달)",
    ),
    "absorb_damp": (
        r"흡수", r"감쇠", r"진동.{0,8}(줄|낮|감쇠)", r"소음.{0,8}(줄|낮|감쇠)",
    ),
    "flow_route": (
        r"흐르", r"유도", r"배출", r"통과", r"우회", r"공기.{0,8}(흐|배출|유도)",
    ),
}
_SCRIPT_PARITY_COMPONENT_MARKERS = (
    "센서", "마이크", "마이크로폰", "스피커", "제어기", "컨트롤러", "프로세서",
    "밸브", "구멍", "패널", "막", "필터", "덕트", "팬", "모터", "창문", "판", "층",
    "sensor", "microphone", "speaker", "controller", "processor", "valve", "filter", "duct",
)
_SCRIPT_PARITY_CONDITION_MARKERS = (
    "때", "경우", "조건", "고도", "속도", "온도", "압력", "하중", "진동", "상태", "주파수대",
)


def _script_parity_mechanism_roles(text):
    body = str(text or "")
    return {
        role
        for role, patterns in _SCRIPT_PARITY_MECHANISM_ROLES.items()
        if any(re.search(pattern, body) for pattern in patterns)
    }


def _script_parity_components(text):
    body = str(text or "").lower()
    return {marker for marker in _SCRIPT_PARITY_COMPONENT_MARKERS if marker.lower() in body}


def _script_parity_conditions(text):
    body = str(text or "")
    return {marker for marker in _SCRIPT_PARITY_CONDITION_MARKERS if marker in body}


def _script_parity_new_causal_step(current_text, prior_text):
    current_stages = _causal_stage_presence(current_text)
    prior_stages = _causal_stage_presence(prior_text)
    # A transition into a different non-mechanism causal role is real progression.
    current_non_mechanism = current_stages - {"mechanism", "result"}
    prior_non_mechanism = prior_stages - {"mechanism", "result"}
    if current_non_mechanism - prior_non_mechanism:
        return True
    # A newly introduced physical component or operating condition can make a
    # same-family mechanism a genuinely distinct step.
    if _script_parity_components(current_text) - _script_parity_components(prior_text):
        return True
    if _script_parity_conditions(current_text) - _script_parity_conditions(prior_text):
        return True
    return False


_script_parity_original_assessment = causal_information_progression_assessment


def causal_information_progression_assessment(scenes, context=None):
    base = _script_parity_original_assessment(scenes, context)
    if not base.get("applicable") or not base.get("pass"):
        return base

    scene_list = [scene for scene in (scenes or []) if isinstance(scene, dict)]
    seen_roles = {}
    repeated_mechanism_scenes = []
    mechanism_units = []

    for index, scene in enumerate(scene_list):
        body = str(scene.get("text", "")).strip()
        roles = _script_parity_mechanism_roles(body)
        unit_kind = "genuinely_new_causal_step"
        for role in sorted(roles):
            prior = seen_roles.get(role)
            if prior is not None:
                if _script_parity_new_causal_step(body, prior["text"]):
                    unit_kind = "genuinely_new_causal_step"
                else:
                    unit_kind = "paraphrase_or_elaboration_same_mechanism"
                    repeated_mechanism_scenes.append(index)
            seen_roles[role] = {"index": index, "text": body}
        mechanism_units.append({
            "index": index,
            "roles": sorted(roles),
            "unit_kind": unit_kind,
        })

    if repeated_mechanism_scenes:
        value = dict(base)
        value.update({
            "pass": False,
            "reason": "mechanism paraphrase/elaboration without a new causal step",
            "repeated_mechanism_scenes": sorted(set(repeated_mechanism_scenes)),
            "mechanism_units": mechanism_units,
        })
        return value

    value = dict(base)
    value["repeated_mechanism_scenes"] = []
    value["mechanism_units"] = mechanism_units
    return value


# The active context is set around the actual production generate_script() call.
# validate_script() therefore does not depend on whether the local response variable
# is named generated, result, payload, or anything else.
_script_parity_original_generate_script = generate_script


def generate_script(topic_info, candidate):
    global _SCRIPT_PARITY_ACTIVE_CONTEXT
    previous = _SCRIPT_PARITY_ACTIVE_CONTEXT
    _SCRIPT_PARITY_ACTIVE_CONTEXT = _script_parity_context(candidate)
    try:
        return _script_parity_original_generate_script(topic_info, candidate)
    finally:
        _SCRIPT_PARITY_ACTIVE_CONTEXT = previous


_script_parity_original_validate_script = validate_script


def validate_script(payload):
    if not isinstance(payload, dict):
        return _script_parity_original_validate_script(payload)

    active = dict(_SCRIPT_PARITY_ACTIVE_CONTEXT or {})
    design_expected = bool(active and design_causality_applicable(active))
    sentinel = object()
    previous_context = payload.get("_design_causality_context", sentinel)

    if active:
        payload["_design_causality_context"] = active

    try:
        valid, reason = _script_parity_original_validate_script(payload)
        if not valid:
            return valid, reason

        if design_expected:
            assessment = causal_information_progression_assessment(
                payload.get("scenes", []),
                active,
            )
            # Fail closed only for a production call that is known to be design-type.
            if not assessment.get("applicable"):
                return False, "Script Production Parity 실패: design context missing/fail-open"
            if not assessment.get("pass"):
                return False, f"Script Production Parity 실패: {assessment.get('reason')}"
        return valid, reason
    finally:
        if previous_context is sentinel:
            payload.pop("_design_causality_context", None)
        else:
            payload["_design_causality_context"] = previous_context
'''

path.write_text(text, encoding="utf-8")

# Strengthen the existing explanation/rewrite path without changing its bounded policy.
path = Path("quality/explanation_judge.py")
text = path.read_text(encoding="utf-8")
if "SCRIPT PRODUCTION PARITY — MECHANISM PROGRESSION" not in text:
    text += '''\n\n# SCRIPT PRODUCTION PARITY — MECHANISM PROGRESSION\n# The production hotfix extends the existing explanation judge guidance:\n'''
    text = text.replace(
        "- 길이가 짧다는 이유만으로 감점하지 말고, 실제 필요한 정보가 있으면 긴 대본도 허용한다. duration이 아니라 정보 밀도를 평가한다.\n",
        "- 길이가 짧다는 이유만으로 감점하지 말고, 실제 필요한 정보가 있으면 긴 대본도 허용한다. duration이 아니라 정보 밀도를 평가한다.\n"
        "- 같은 mechanism을 어휘만 바꿔 반복하거나 세부 표현만 덧붙였는데 새 causal consequence/condition/component가 없다면 독립 NEW INFORMATION으로 보지 않는다.\n"
        "- 실제로 새로운 component, operating condition, causal consequence가 추가되는 별도 mechanism step은 보존한다.\n",
        1,
    )
path.write_text(text, encoding="utf-8")

path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
if "[SCRIPT PRODUCTION PARITY 수정]" not in text:
    text = text.replace(
        "[INFORMATION DENSITY 수정]\n",
        "[SCRIPT PRODUCTION PARITY 수정]\n"
        "- 설계형 대본에서 같은 mechanism의 paraphrase/elaboration, 반복 result, generic outro, 최소 길이를 채우기 위한 filler를 압축/제거한다.\n"
        "- 새 component/condition/consequence가 있는 실제 별도 mechanism step은 삭제하지 않는다.\n"
        "- 기존 bounded rewrite 횟수를 늘리지 않는다.\n"
        "[INFORMATION DENSITY 수정]\n",
        1,
    )
path.write_text(text, encoding="utf-8")

print("✅ Script production context parity + semantic mechanism progression hotfix applied")

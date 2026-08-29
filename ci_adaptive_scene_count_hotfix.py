import re
from pathlib import Path


# Retention Story V2:
# Writer contract first: do not make the Writer fill a scene/duration quota after
# the information is complete. V1's deterministic filler compressor stays intact
# as a compatibility safety net; V2 does not add new post-processing deletion rules.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

old_scene_instruction = "{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n"
new_scene_instruction = "{_adaptive_scene_count_instruction(candidate)}\n"
if old_scene_instruction not in text and new_scene_instruction not in text:
    raise RuntimeError("adaptive scene-count prompt marker not found")
text = text.replace(old_scene_instruction, new_scene_instruction, 1)

# Script production parity already owns the intro duration sentence. Keep that
# composition boundary and override its helper below instead of rewriting prompt text.
if "{_script_parity_duration_opening(candidate)}" not in text:
    raise RuntimeError("script parity duration helper boundary not found")

length_pattern = r"\[LENGTH\]\n.*?\n\n\[OUTPUT\]"
length_replacement = "[LENGTH]\n{_adaptive_length_instruction(candidate)}\n\n[OUTPUT]"
text, length_count = re.subn(
    length_pattern,
    length_replacement,
    text,
    count=1,
    flags=re.DOTALL,
)
if length_count != 1 and "{_adaptive_length_instruction(candidate)}" not in text:
    raise RuntimeError("adaptive length prompt boundary not found")

if "ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V3" not in text:
    text += r'''

# ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V3
# V2 contract: 6~7 is a preference, not a validation floor. Keep a separate
# compatibility floor for V1 compression so V2 does not widen post-processing.
ADAPTIVE_DESIGN_VALIDATION_MIN_SCENES = 1
ADAPTIVE_DESIGN_MIN_SCENES = 6
ADAPTIVE_DESIGN_PREFERRED_MAX_SCENES = 7

_RETENTION_PROTECTED_ROLES = {
    "hook", "phenomenon", "question", "core_question", "evidence", "contrast",
    "payoff", "result", "reveal", "causal_clue", "mechanism", "mechanism_1",
}
_RETENTION_FILLER_PATTERNS = (
    r"(?:은|는|이|가).{0,18}중요합니다\.?$",
    r"(?:은|는|이|가).{0,18}핵심\s*역할을\s*합니다\.?$",
    r"(?:은|는|이|가).{0,18}성능을\s*(?:높|향상)\w*\.?$",
    r"(?:은|는|이|가).{0,18}도움이\s*됩니다\.?$",
)
_RETENTION_CONCRETE_PROGRESS_MARKERS = (
    "왜", "때문", "압력", "양력", "항력", "속도", "각도", "공기", "흐름", "증가",
    "감소", "낮", "높", "펼", "접", "분산", "전달", "조절", "변화", "반대로",
    "없으면", "없다면", "결과", "그래서", "따라서",
)


def _adaptive_scene_count_context(runtime, candidate=None):
    if isinstance(candidate, dict):
        try:
            return runtime._script_parity_context(candidate)
        except Exception:
            return dict(candidate)
    return dict(getattr(runtime, "_SCRIPT_PARITY_ACTIVE_CONTEXT", None) or {})


def _adaptive_scene_count_runtime_is_design(runtime, candidate=None):
    context = _adaptive_scene_count_context(runtime, candidate)
    if not context:
        return False
    try:
        return bool(runtime.design_causality_applicable(context))
    except Exception:
        return False


def _adaptive_scene_count_is_design(candidate=None):
    runtime = globals().get("_SCRIPT_PARITY_RUNTIME") or globals()
    if isinstance(runtime, dict):
        context = _script_parity_context(candidate) if isinstance(candidate, dict) else dict(
            _SCRIPT_PARITY_ACTIVE_CONTEXT or {}
        )
        return bool(context) and bool(design_causality_applicable(context))
    return _adaptive_scene_count_runtime_is_design(runtime, candidate)


def _adaptive_duration_instruction(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return (
            "필요한 만큼만 설명하되 보통 20~35초를 선호한다. 목표 시간을 채우려고 내용을 늘리지 말고 "
            "18~20초에 설명이 충분하면 그대로 끝내라"
        )
    return f"{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초"


def _adaptive_length_instruction(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return (
            "전체 길이는 정보량의 결과다. 목표 시간을 채우기 위해 문장이나 Scene을 추가하지 마라. "
            "설명이 끝났다면 즉시 종료하고, 하나의 자연스러운 인과를 Scene 수 때문에 잘게 쪼개지 마라."
        )
    return (
        f"전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다. "
        "너무 짧은 문장을 억지로 Scene 수만 맞추려고 잘게 쪼개지 마라."
    )


def _adaptive_scene_count_instruction(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return (
            f"Scene 수는 목표가 아니라 상한/가이드다. 일반적인 설명형 Shorts는 보통 "
            f"{ADAPTIVE_DESIGN_MIN_SCENES}~{ADAPTIVE_DESIGN_PREFERRED_MAX_SCENES} Scene을 선호하지만 hard minimum이 아니다. "
            "내용이 짧으면 5 Scene 이하도 허용하고, 필요한 설명이 끝나면 즉시 종료한다. "
            f"반대로 새 정보가 실제로 필요하면 8 Scene 이상도 {MAX_SCENES} Scene까지 허용한다. "
            "Scene 수를 채우기 위한 mechanism_n, 같은 결론의 재진술, 중간 요약 filler를 추가하지 마라. "
            "각 intermediate Scene은 이전 Scene까지 없던 새 사실/새 원인 또는 메커니즘/새 의문/반전 또는 대조/"
            "payoff 진전/의미 있는 visual 변화 중 최소 하나를 가져야 한다. 무엇이 새 정보인지 답할 수 없으면 그 Scene을 만들지 마라. "
            "'중요합니다', '핵심 역할을 합니다', '성능을 높입니다', '도움이 됩니다' 같은 표현도 새 정보 없이 앞 내용을 요약할 뿐이면 독립 Scene으로 만들지 마라. "
            "인접 Scene이 하나의 자연스러운 causal step이면 한 Scene에서 한 호흡으로 설명한다."
        )
    return f"{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라."


# Keep the existing production-parity prompt composition. Only change the design
# branch of the helper; non-design topics retain the original behavior.
_retention_v2_original_duration_opening = _script_parity_duration_opening

def _script_parity_duration_opening(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return f"새 소재를 탐색하지 말고 확정 Winner를 {_adaptive_duration_instruction(candidate)},"
    return _retention_v2_original_duration_opening(candidate)


def _retention_scene_role(scene):
    for key in ("role", "narrative_role", "story_role", "scene_role"):
        value = str(scene.get(key, "")).strip().lower()
        if value:
            return value
    return ""


def _retention_is_generic_filler(scene):
    body = str(scene.get("text", "")).strip()
    if not body:
        return False
    if not any(re.search(pattern, body) for pattern in _RETENTION_FILLER_PATTERNS):
        return False
    concrete_hits = sum(marker in body for marker in _RETENTION_CONCRETE_PROGRESS_MARKERS)
    return concrete_hits <= 1


def retention_story_compress_scenes(scenes):
    if not isinstance(scenes, list) or len(scenes) <= ADAPTIVE_DESIGN_MIN_SCENES:
        return scenes
    kept = []
    total = len(scenes)
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            kept.append(scene)
            continue
        role = _retention_scene_role(scene)
        protected = index < 2 or index == total - 1 or role in _RETENTION_PROTECTED_ROLES
        can_remove = len(kept) + (total - index - 1) >= ADAPTIVE_DESIGN_MIN_SCENES
        if not protected and can_remove and _retention_is_generic_filler(scene):
            print(f"🗜️ RETENTION STORY V1 filler removed: scene={index + 1} text={scene.get('text', '')}")
            continue
        kept.append(scene)
    return kept


def retention_story_compress_result(result, context=None):
    if not isinstance(result, dict):
        return result
    runtime = globals().get("_SCRIPT_PARITY_RUNTIME") or globals()
    is_design = (
        _adaptive_scene_count_runtime_is_design(runtime, context)
        if not isinstance(runtime, dict)
        else _adaptive_scene_count_is_design(context)
    )
    if not is_design:
        return result
    scenes = result.get("scenes")
    compressed = retention_story_compress_scenes(scenes)
    if compressed is scenes or len(compressed) == len(scenes or []):
        return result
    updated = dict(result)
    updated["scenes"] = compressed
    updated["_retention_story_v1"] = {
        "before_scenes": len(scenes),
        "after_scenes": len(compressed),
        "removed": len(scenes) - len(compressed),
    }
    return updated


def _install_adaptive_scene_validator(runtime):
    if runtime is None or not hasattr(runtime, "validate_scenes"):
        return False
    current = runtime.validate_scenes
    if getattr(current, "_adaptive_scene_count_v3", False):
        return True

    def adaptive_validate_scenes(scenes):
        if not isinstance(scenes, list):
            return False, "scenes가 배열이 아님"
        if _adaptive_scene_count_runtime_is_design(runtime):
            if len(scenes) < ADAPTIVE_DESIGN_VALIDATION_MIN_SCENES:
                return False, f"설계형 장면 수 부족: {len(scenes)}"
            if len(scenes) > runtime.MAX_SCENES:
                return False, f"장면 수 초과: {len(scenes)}"
            if len(scenes) < runtime.MIN_SCENES:
                padded = list(scenes)
                while len(padded) < runtime.MIN_SCENES:
                    padded.append(dict(scenes[-1]))
                return current(padded)
        return current(scenes)

    adaptive_validate_scenes._adaptive_scene_count_v3 = True
    adaptive_validate_scenes._adaptive_scene_count_original = current
    runtime.validate_scenes = adaptive_validate_scenes
    return True


def _install_retention_story_compressor(runtime):
    if runtime is None or not hasattr(runtime, "generate_script"):
        return False
    current = runtime.generate_script
    if getattr(current, "_retention_story_v1", False):
        return True

    def compressed_generate_script(topic_info, candidate, *args, **kwargs):
        result = current(topic_info, candidate, *args, **kwargs)
        return retention_story_compress_result(result, candidate)

    compressed_generate_script._retention_story_v1 = True
    compressed_generate_script._retention_story_original = current
    runtime.generate_script = compressed_generate_script
    return True


try:
    _adaptive_runtime = _SCRIPT_PARITY_RUNTIME
except NameError:
    try:
        _adaptive_runtime = _LEGACY
    except NameError:
        _adaptive_runtime = None

_install_adaptive_scene_validator(_adaptive_runtime)
_install_retention_story_compressor(_adaptive_runtime)

_adaptive_scene_count_original_validate_scenes = validate_scenes

def validate_scenes(scenes):
    if _adaptive_runtime is not None:
        return _adaptive_runtime.validate_scenes(scenes)
    if not isinstance(scenes, list):
        return False, "scenes가 배열이 아님"
    if _adaptive_scene_count_is_design():
        if len(scenes) < ADAPTIVE_DESIGN_VALIDATION_MIN_SCENES:
            return False, f"설계형 장면 수 부족: {len(scenes)}"
        if len(scenes) > MAX_SCENES:
            return False, f"장면 수 초과: {len(scenes)}"
        if len(scenes) < MIN_SCENES:
            padded = list(scenes)
            while len(padded) < MIN_SCENES:
                padded.append(dict(scenes[-1]))
            return _adaptive_scene_count_original_validate_scenes(padded)
    return _adaptive_scene_count_original_validate_scenes(scenes)

validate_scenes._adaptive_scene_count_v3 = True
'''

path.write_text(text, encoding="utf-8")
print("✅ Retention Story V2 Writer contract applied; V1 compressor unchanged")

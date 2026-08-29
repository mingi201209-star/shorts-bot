from pathlib import Path


# Retention Story V1:
# dense design explainers must not be padded to a fixed scene floor. Production
# run 33223881121 showed the failure mode directly: generic summary scenes such
# as "성능을 높입니다" / "역할은 매우 중요합니다" added no information and
# produced an abstract `important role` visual query. Keep this deterministic:
# no extra LLM call, no new factual claim, no visual-threshold change.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

old_scene_instruction = "{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n"
new_scene_instruction = "{_adaptive_scene_count_instruction(candidate)}\n"
if old_scene_instruction not in text and new_scene_instruction not in text:
    raise RuntimeError("adaptive scene-count prompt marker not found")
text = text.replace(old_scene_instruction, new_scene_instruction, 1)

old_duration_instruction = "새 소재를 탐색하지 말고 확정 Winner를 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초,\n"
new_duration_instruction = "새 소재를 탐색하지 말고 확정 Winner를 {_adaptive_duration_instruction(candidate)},\n"
if old_duration_instruction in text:
    text = text.replace(old_duration_instruction, new_duration_instruction, 1)

if "ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V3" not in text:
    text += r'''

# ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V3
ADAPTIVE_DESIGN_MIN_SCENES = 6
ADAPTIVE_DESIGN_PREFERRED_MAX_SCENES = 8

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
# Context nouns such as "이륙/착륙" do not by themselves make a summary novel.
# These markers represent an actual mechanism, measurable consequence, contrast,
# or state change inside the candidate sentence.
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
            "정보량이 충분하면 약 25~35초로 압축하되 숫자를 맞추기 위해 Scene을 "
            "추가하거나 삭제하지 마라"
        )
    return f"{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초"


def _adaptive_scene_count_instruction(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return (
            f"설계형 주제는 보통 {ADAPTIVE_DESIGN_MIN_SCENES}~{ADAPTIVE_DESIGN_PREFERRED_MAX_SCENES} Scene을 우선하되 "
            f"새 정보가 실제로 필요하면 {MAX_SCENES} Scene까지 허용한다. "
            "Scene 수를 맞추기 위해 같은 mechanism/result를 반복하거나 filler를 추가하지 마라. "
            "각 intermediate Scene은 새로운 사실/원인/원리/의문/반전/대조/payoff 진전/의미 있는 visual 변화 중 "
            "최소 하나가 있을 때만 유지한다. 인접 Scene이 하나의 causal step이면 자연스럽게 합쳐도 된다."
        )
    return f"{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라."


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
            if len(scenes) < ADAPTIVE_DESIGN_MIN_SCENES:
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
        if len(scenes) < ADAPTIVE_DESIGN_MIN_SCENES:
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
print("✅ Retention Story V1 adaptive scene-count + filler compression applied")

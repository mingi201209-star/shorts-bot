from pathlib import Path


# Production counterexample hotfix:
# #31 removed filler/repeated mechanism, but the legacy 12-scene hard floor could
# reject an otherwise dense design script. Keep the legacy contract for normal
# topics and relax only design-type candidates. The important production detail is
# that compatibility exports may validate through `_LEGACY`, so install the same
# validator on both the exported module and the actual legacy runtime.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

old_scene_instruction = "{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n"
new_scene_instruction = "{_adaptive_scene_count_instruction(candidate)}\n"
if old_scene_instruction not in text:
    raise RuntimeError("adaptive scene-count prompt marker not found")
text = text.replace(old_scene_instruction, new_scene_instruction, 1)

if "ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V2" not in text:
    text += r'''

# ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V2
ADAPTIVE_DESIGN_MIN_SCENES = 8


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


def _adaptive_scene_count_instruction(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return (
            f"설계형 주제는 {ADAPTIVE_DESIGN_MIN_SCENES}~{MAX_SCENES} Scene을 사용한다. "
            "12 Scene을 채우기 위해 같은 mechanism/result를 반복하거나 filler를 추가하지 말고, "
            "각 Scene이 독립적인 causal information 또는 필요한 visual beat를 가질 때만 Scene을 추가한다."
        )
    return f"{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라."


def _install_adaptive_scene_validator(runtime):
    if runtime is None or not hasattr(runtime, "validate_scenes"):
        return False
    current = runtime.validate_scenes
    if getattr(current, "_adaptive_scene_count_v2", False):
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
                # Preserve all legacy structural checks while bypassing only its
                # global count floor. The padded copy never escapes validation.
                padded = list(scenes)
                while len(padded) < runtime.MIN_SCENES:
                    padded.append(dict(scenes[-1]))
                return current(padded)
        return current(scenes)

    adaptive_validate_scenes._adaptive_scene_count_v2 = True
    adaptive_validate_scenes._adaptive_scene_count_original = current
    runtime.validate_scenes = adaptive_validate_scenes
    return True


# Install on the actual compatibility runtime first. This is where exported
# generate_script() delegates validation in production after #31.
try:
    _adaptive_runtime = _SCRIPT_PARITY_RUNTIME
except NameError:
    try:
        _adaptive_runtime = _LEGACY
    except NameError:
        _adaptive_runtime = None

_install_adaptive_scene_validator(_adaptive_runtime)

# Also wrap the exported module validator for direct callers/regressions.
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

validate_scenes._adaptive_scene_count_v2 = True
'''

path.write_text(text, encoding="utf-8")
print("✅ Adaptive design scene-count runtime hotfix applied")

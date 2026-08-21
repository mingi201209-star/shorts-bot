from pathlib import Path


# Production counterexample hotfix:
# #31 removed filler/repeated mechanism, but the legacy 12-scene hard floor could
# reject an otherwise dense design script. Keep the legacy contract for normal
# topics and relax only design-type candidates while the parity context is active.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

old_scene_instruction = "{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n"
new_scene_instruction = "{_adaptive_scene_count_instruction(candidate)}\n"
if old_scene_instruction not in text:
    raise RuntimeError("adaptive scene-count prompt marker not found")
text = text.replace(old_scene_instruction, new_scene_instruction, 1)

if "ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V1" not in text:
    text += r'''

# ADAPTIVE_SCENE_COUNT_FOR_DENSE_DESIGN_V1
# 8 is intentionally a narrow design-only floor. It covers the observed 8/10-scene
# production counterexamples without weakening the legacy 12~13 contract globally.
ADAPTIVE_DESIGN_MIN_SCENES = 8


def _adaptive_scene_count_is_design(candidate=None):
    context = _script_parity_context(candidate) if isinstance(candidate, dict) else dict(
        _SCRIPT_PARITY_ACTIVE_CONTEXT or {}
    )
    if not context:
        return False
    try:
        return bool(design_causality_applicable(context))
    except Exception:
        return False


def _adaptive_scene_count_instruction(candidate):
    if _adaptive_scene_count_is_design(candidate):
        return (
            f"설계형 주제는 {ADAPTIVE_DESIGN_MIN_SCENES}~{MAX_SCENES} Scene을 사용한다. "
            "12 Scene을 채우기 위해 같은 mechanism/result를 반복하거나 filler를 추가하지 말고, "
            "각 Scene이 독립적인 causal information 또는 필요한 visual beat를 가질 때만 Scene을 추가한다."
        )
    return f"{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라."


_adaptive_scene_count_original_validate_scenes = validate_scenes


def validate_scenes(scenes):
    if not isinstance(scenes, list):
        return False, "scenes가 배열이 아님"

    if _adaptive_scene_count_is_design():
        if len(scenes) < ADAPTIVE_DESIGN_MIN_SCENES:
            return False, f"설계형 장면 수 부족: {len(scenes)}"
        if len(scenes) > MAX_SCENES:
            return False, f"장면 수 초과: {len(scenes)}"

        # Reuse every legacy per-scene structural check by padding only for the
        # count check. Padding duplicates are never returned or rendered.
        if len(scenes) < MIN_SCENES:
            padded = list(scenes)
            while len(padded) < MIN_SCENES:
                padded.append(dict(scenes[-1]))
            return _adaptive_scene_count_original_validate_scenes(padded)

    return _adaptive_scene_count_original_validate_scenes(scenes)
'''

path.write_text(text, encoding="utf-8")
print("✅ Adaptive design scene-count hotfix applied")

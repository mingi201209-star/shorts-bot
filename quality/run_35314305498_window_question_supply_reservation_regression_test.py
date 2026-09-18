"""Regression for Development Engine Run 35314305498.

The run proved the Hook fix and reached Scene 5, then failed because the
neutral Scene-2 shape question consumed deterministic explanation transform
1/3. This test executes the production append in a controlled namespace and
proves that the grounded comparison now blocks both reuse paths while
continuing into fresh still generation. The still and explanation ceilings
remain unchanged.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "ci_grounded_deterministic_explanation_hotfix.py"
CANONICAL = "modern aircraft passenger window with rounded/oval corners"


def _scene(*, grounded=True):
    scene = {
        "scene_id": 2,
        "role": "question",
        "text": "그런데 왜 비행기 창문 모서리를 둥글게 디자인했을까요?",
        "visual_goal": "둥근 창문 모서리를 확대하고 물음표를 표시합니다.",
        "keyword": "aircraft window why rounded corners stage 2",
    }
    if grounded:
        scene["_canonical_visual_supply"] = {
            "canonical_subject": CANONICAL,
            "grounding_source": "faa_comet_lessons_v1",
        }
    return scene


def main():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    installer = runpy.run_path(str(INSTALLER), run_name="run_35314305498_installer")
    append = installer["_STILL_FALLBACK_APPEND"]

    namespace = {"_calls": []}
    exec(
        '''
def _scene_id(scene):
    return scene.get("scene_id", "unknown")

def _reuse_verified_question_subject(scene, *, output_path, duration, trigger_reason):
    return {"mode": "UNSAFE_QUESTION_REUSE"}

def _reuse_verified_still(scene, *, output_path, duration, trigger_reason):
    return {"mode": "UNSAFE_GENERIC_REUSE"}

def generate_still_motion_fallback(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    question_reuse = _reuse_verified_question_subject(
        scene, output_path=output_path, duration=duration, trigger_reason=trigger_reason
    )
    generic_reuse = _reuse_verified_still(
        scene, output_path=output_path, duration=duration, trigger_reason=trigger_reason
    )
    _calls.append({
        "scene": dict(scene),
        "question_reuse": question_reuse,
        "generic_reuse": generic_reuse,
    })
    return {"mode": "FRESH_VERIFIED_STILL"}
''',
        namespace,
    )
    exec(append, namespace)

    result = namespace["generate_still_motion_fallback"](
        _scene(), output_path="unused.mp4", duration=5.0,
        trigger_reason="no_semantically_safe_stock",
    )
    assert result == {"mode": "FRESH_VERIFIED_STILL"}, result
    assert len(namespace["_calls"]) == 1
    routed = namespace["_calls"][0]
    assert routed["question_reuse"] is None
    assert routed["generic_reuse"] is None
    assert routed["scene"]["_window_comparison_fresh_still_v2"] is True
    goal = routed["scene"]["visual_goal"]
    assert "각진 창문 모서리" in goal and "둥근 창문 모서리" in goal and "나란히" in goal
    assert "응력, 균열, 파열 또는 원인 설명은 표시하지 않습니다" in goal

    # An ungrounded look-alike keeps the original behavior and both established
    # reuse paths; the reservation is closed to the trusted aircraft-window case.
    result = namespace["generate_still_motion_fallback"](
        _scene(grounded=False), output_path="unused.mp4", duration=5.0,
        trigger_reason="no_semantically_safe_stock",
    )
    assert result == {"mode": "FRESH_VERIFIED_STILL"}
    ungrounded = namespace["_calls"][1]
    assert ungrounded["question_reuse"] == {"mode": "UNSAFE_QUESTION_REUSE"}
    assert ungrounded["generic_reuse"] == {"mode": "UNSAFE_GENERIC_REUSE"}
    assert "_window_comparison_fresh_still_v2" not in ungrounded["scene"]

    # Upgrade safety: an already-composed V1 runtime exposes the underlying
    # pre-skip generator in this global. V2 must call that base rather than
    # chaining into V1's unconditional comparison skip.
    migration_namespace = {"_calls": []}
    exec(namespace_source := '''
def _scene_id(scene):
    return scene.get("scene_id", "unknown")

def _reuse_verified_question_subject(scene, *, output_path, duration, trigger_reason):
    return {"mode": "UNSAFE_QUESTION_REUSE"}

def _reuse_verified_still(scene, *, output_path, duration, trigger_reason):
    return {"mode": "UNSAFE_GENERIC_REUSE"}

def _base_generate(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    _calls.append(dict(scene))
    return {"mode": "V1_UNDERLYING_BASE"}

_window_comparison_original_generate_still_motion_fallback = _base_generate

def generate_still_motion_fallback(scene, *, output_path, duration, trigger_reason="semantic_scarcity"):
    return None
''', migration_namespace)
    exec(append, migration_namespace)
    migrated = migration_namespace["generate_still_motion_fallback"](
        _scene(), output_path="unused.mp4", duration=5.0,
        trigger_reason="no_semantically_safe_stock",
    )
    assert migrated == {"mode": "V1_UNDERLYING_BASE"}
    assert migration_namespace["_calls"][0]["_window_comparison_fresh_still_v2"] is True

    installer_source = INSTALLER.read_text(encoding="utf-8")
    visual_source = (ROOT / "video" / "visual_explanation.py").read_text(encoding="utf-8")
    still_source = (ROOT / "video" / "still_image_fallback.py").read_text(encoding="utf-8")
    assert 'os.environ.get("MAX_EXPLANATION_TRANSFORMS_PER_VIDEO", "3")' in visual_source
    assert 'os.environ.get("STILL_IMAGE_MAX_PER_VIDEO", "2")' in still_source
    for forbidden in (
        "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO =",
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "V3_MAX_API_CALLS =",
        "V3_MAX_COST_USD =",
    ):
        assert forbidden not in installer_source, forbidden

    print("RUN 35314305498 WINDOW QUESTION SUPPLY RESERVATION: PASS")


if __name__ == "__main__":
    main()

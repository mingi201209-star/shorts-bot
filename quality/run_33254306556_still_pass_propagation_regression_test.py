"""Run 33254306556 Scene 2 still Vision PASS propagation regression.

The production counterexample was:
- strict Vision result.pass=True
- visible_components=engine+chevron+airflow
- no generation artifact / factual contradiction
- trusted canonical subject=jet engine nacelle/nozzle chevrons
- outer still state incorrectly became rejected_by_vision

This regression keeps Vision and concrete subject checks fail-closed while allowing
an already-verified jet-engine subassembly close-up to satisfy its trusted aircraft
parent-domain anchor without requiring a separate whole-aircraft component in-frame.
No network/model call is performed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_still_image_verifier_contract_hotfix as hotfix

# Exercise the same dedicated verifier installer production applies from
# ci_final_visual_semantic_qa_hotfix.py.
hotfix.main()

from video import hook_visual_dominance as dominance  # noqa: E402
from video import still_image_fallback as still  # noqa: E402


SCENE = {
    "scene_id": 2,
    "role": "question",
    "text": "그런데 비행기 엔진 뒤가 톱니처럼 생긴 이유는 무엇일까요?",
    "visual_goal": "비행기 엔진의 구조",
    "keyword": "aircraft engine chevron airflow detail stage 2",
    "_canonical_visual_supply": {
        "canonical_subject": "jet engine nacelle/nozzle chevrons",
        "identity_confidence": 0.98,
        "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
        "grounding_source": "trusted-fixture",
    },
}


def vision_result(*, passed, visible):
    return {
        "pass": bool(passed),
        "target_subject": "jet engine rear chevron",
        "subject_dominance": 9.0,
        "subject_visibility": 9.0,
        "action_match": 10.0,
        "competing_subject_risk": 1.0,
        "vertical_crop_subject_visible": True,
        "visible_components": list(visible),
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "reason": "The engine chevron is clearly visible, large, and dominant in the frame.",
    }


original_eval = dominance.evaluate_hook_subject_dominance
try:
    # A. Exact LIVE contradiction: strict Vision PASS + engine/chevron proof must
    # survive the still-specific parent-domain aggregation.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        passed=True,
        visible=["engine", "chevron", "airflow"],
    )
    verified, evidence = still._verify_motion_clip(
        SCENE,
        ROOT / "not-read-because-vision-is-mocked.mp4",
    )
    assert verified is True, evidence
    assert evidence.get("pass") is True
    assert evidence.get("parent_domain_satisfied") == ["aircraft"], evidence

    # B. Vision FAIL stays fail-closed even with the same visible components.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        passed=False,
        visible=["engine", "chevron", "airflow"],
    )
    verified, evidence = still._verify_motion_clip(
        SCENE,
        ROOT / "not-read-because-vision-is-mocked.mp4",
    )
    assert verified is False, evidence

    # C. A partial engine-only still still cannot escape the chevron hard proof.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        passed=True,
        visible=["engine", "airflow"],
    )
    verified, evidence = still._verify_motion_clip(
        SCENE,
        ROOT / "not-read-because-vision-is-mocked.mp4",
    )
    assert verified is False, evidence

    # D. The parent-domain exception is trusted-canonical only. Removing the
    # canonical profile restores the literal aircraft+engine+chevron requirement.
    untrusted_scene = dict(SCENE)
    untrusted_scene.pop("_canonical_visual_supply", None)
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        passed=True,
        visible=["engine", "chevron", "airflow"],
    )
    verified, evidence = still._verify_motion_clip(
        untrusted_scene,
        ROOT / "not-read-because-vision-is-mocked.mp4",
    )
    assert verified is False, evidence

    # E. Existing fully explicit 3/3 still remains accepted.
    dominance.evaluate_hook_subject_dominance = lambda candidate, scene: vision_result(
        passed=True,
        visible=["aircraft", "engine", "chevron", "airflow"],
    )
    verified, evidence = still._verify_motion_clip(
        SCENE,
        ROOT / "not-read-because-vision-is-mocked.mp4",
    )
    assert verified is True, evidence
finally:
    dominance.evaluate_hook_subject_dominance = original_eval

print("RUN 33254306556 STILL VISION PASS PROPAGATION REGRESSION: PASS")

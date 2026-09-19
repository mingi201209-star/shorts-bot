import os
import tempfile
from pathlib import Path

from quality_core_v2.actual_visual_qa import validate_actual_v2_visuals
from quality_core_v2.schemas import SceneV2, VisualPlanV2


def _scene():
    return SceneV2.from_dict({
        "scene_index": 1,
        "narration": "비행 중 날개가 위로 휩니다.",
        "causal_role": "phenomenon",
        "owned_claim_id": "wing_upward_bending",
        "new_information": "날개가 위로 휜다",
        "visual_requirement": "날개의 위쪽 탄성 휨이 실제로 보여야 함",
    })


def _plan():
    return VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "required_relation_or_mechanism": ["wing deformation under aerodynamic load"],
        "forbidden_visuals": ["generic cruising aircraft"],
        "search_queries": ["aircraft wing flex"],
    })


def main():
    scene = _scene()
    plan = _plan()
    item = {
        "text": scene.narration,
        "keyword": "aircraft wing flex",
        "visual_goal": "visible upward elastic bending",
    }

    with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        os.chdir(tmp)
        try:
            clip = Path("vertical_video_0.mp4")
            clip.write_bytes(b"fixture")

            def paths(_idx):
                return {"vertical_video": str(clip)}

            passed = validate_actual_v2_visuals(
                [scene],
                [plan],
                [item],
                get_scene_paths_fn=paths,
                inspect_fn=lambda *_args: {
                    "visible_components": ["aircraft", "wing"],
                    "observable_states": ["visible upward elastic bending"],
                    "visible_relations_or_mechanisms": [
                        "wing deformation under aerodynamic load"
                    ],
                    "forbidden_visuals_present": [],
                    "components_satisfied": True,
                    "observable_state_satisfied": True,
                    "relation_or_mechanism_satisfied": True,
                    "reason": "The wing is visibly bent upward under load.",
                },
            )
            assert passed["status"] == "PASS"

            try:
                validate_actual_v2_visuals(
                    [scene],
                    [plan],
                    [item],
                    get_scene_paths_fn=paths,
                    inspect_fn=lambda *_args: {
                        "visible_components": ["aircraft", "wing"],
                        "observable_states": ["static wing"],
                        "visible_relations_or_mechanisms": [],
                        "forbidden_visuals_present": [],
                        "components_satisfied": True,
                        "observable_state_satisfied": False,
                        "relation_or_mechanism_satisfied": False,
                        "reason": "Aircraft wing is visible but no bending is observable.",
                    },
                )
                raise AssertionError("static subject-only visual must fail closed")
            except RuntimeError as exc:
                assert "V2_ACTUAL_VISUAL_QA_FAILED" in str(exc)

            report = Path("v2_actual_visual_qa.json").read_text(encoding="utf-8")
            assert '"status": "FAIL"' in report
            assert "no bending is observable" in report
        finally:
            os.chdir(old)

    print("V2 ACTUAL RENDERED VISUAL QA REGRESSION: PASS")


if __name__ == "__main__":
    main()

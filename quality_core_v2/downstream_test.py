"""Offline integration test: CandidateV2 -> ScriptPlanV2 -> VisualPlanV2 ->
retrieval decision -> scene handoff -> render/export handoff.

Every network/LLM/provider/MP4 boundary is stubbed. This checks control
flow and schema compatibility end-to-end, not real output quality (that's
what the Golden E2E is for, and it runs at most once per the usage fuse).
"""

from quality_core_v2.candidate import evaluate_candidate_v2
from quality_core_v2.downstream import render_v2_pipeline, scene_v2_to_v1_item
from quality_core_v2.replay import _run_retrieval_adapter
from quality_core_v2.schemas import CandidateV2, SceneV2, VisualPlanV2
from quality_core_v2.script_plan import evaluate_script_plan_v2
from quality_core_v2.visual_plan import evaluate_visual_plan_v2


def test_full_control_flow_candidate_to_render_handoff():
    # 1. CandidateV2
    candidate = CandidateV2.from_dict({
        "topic": "aircraft wing flex", "concrete_subject": "aircraft main wing",
        "observable_phenomenon": "upward elastic bending", "core_question": "왜 휘는가",
        "mechanism": "탄성 변형", "reveal": "일부러 휘도록 설계됨",
        "canonical_subject": "aircraft main wing",
    })
    candidate_verdict = evaluate_candidate_v2(candidate)
    assert candidate_verdict.passed

    # 2. ScriptPlanV2
    scenes = [
        SceneV2.from_dict({
            "scene_index": 1, "narration": "날개 끝이 위로 휩니다", "causal_role": "phenomenon",
            "owned_claim_id": "phenomenon", "new_information": "날개가 휜다",
            "visual_requirement": "wingtip bending",
        }),
        SceneV2.from_dict({
            "scene_index": 2, "narration": "이것은 의도된 설계입니다", "causal_role": "payoff",
            "owned_claim_id": "payoff", "new_information": "의도된 설계다",
            "visual_requirement": "wide shot of flexing wing",
        }),
    ]
    script_verdict = evaluate_script_plan_v2(scenes)
    assert script_verdict.passed

    # 3. VisualPlanV2 per scene
    plans = [
        VisualPlanV2.from_dict({
            "scene_index": 1, "subject": "aircraft main wing",
            "required_visible_components": ["aircraft", "main wing"],
            "required_observable_state": ["visible upward elastic bending"],
            "search_queries": ["airplane wing flexing in flight"],
        }),
        VisualPlanV2.from_dict({
            "scene_index": 2, "subject": "aircraft main wing",
            "required_visible_components": ["aircraft", "main wing"],
            "required_observable_state": ["visible upward elastic bending"],
            "search_queries": ["airplane wing wide shot"],
        }),
    ]
    for plan in plans:
        assert evaluate_visual_plan_v2(plan).passed

    # 4. Retrieval decision (stubbed provider attempts, no network)
    retrieval_verdict = _run_retrieval_adapter({
        "attempts": [{"provider": "pexels", "status": "hit", "visual": {"source_type": "stock"}}]
    })
    assert retrieval_verdict.passed

    # 5. Scene handoff: SceneV2+VisualPlanV2 -> V1 create_scene's dict shape
    items = [scene_v2_to_v1_item(s, p) for s, p in zip(scenes, plans)]
    assert items[0] == {
        "text": "날개 끝이 위로 휩니다",
        "keyword": "airplane wing flexing in flight",
        "visual_goal": "visible upward elastic bending",
        "visual_type": "real_world_broll",
    }

    # 6. Render/export handoff: stub generate_scenes/render_final_video so
    # no real TTS/video/MP4 work happens, just verify the call shape.
    calls = {}

    def fake_generate_scenes(scene_items):
        calls["scene_items"] = scene_items
        return ["clip1", "clip2"]

    def fake_render_final_video(scene_clips):
        calls["scene_clips"] = scene_clips
        return "final_shorts.mp4"

    result = render_v2_pipeline(
        scenes, plans,
        generate_scenes_fn=fake_generate_scenes,
        render_final_video_fn=fake_render_final_video,
    )
    assert result == "final_shorts.mp4"
    assert calls["scene_items"] == items
    assert calls["scene_clips"] == ["clip1", "clip2"]

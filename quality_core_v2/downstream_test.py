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
            "search_queries": ["airplane wing flex bending wide shot"],
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
        "_v2_required_visible_components": ["aircraft", "main wing"],
        "_v2_required_observable_state": ["visible upward elastic bending"],
        "_v2_required_relation_or_mechanism": [],
        "_v2_forbidden_visuals": [],
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
        reset_final_visual_semantic_report_fn=lambda: None,
        validate_final_visual_semantic_qa_fn=lambda scenes_: None,
        validate_actual_v2_visuals_fn=lambda scenes_, plans_, items_: None,
    )
    assert result == "final_shorts.mp4"
    assert calls["scene_items"] == items
    assert calls["scene_clips"] == ["clip1", "clip2"]


def test_scene_v2_to_v1_item_skips_blank_first_search_query():
    # Golden E2E #2 regression (run 35430296847, scene 2): search_queries[0]
    # was blank even though the list was non-empty; picking index 0 blindly
    # produced an empty keyword and create_scene raised ValueError.
    scene = SceneV2.from_dict({
        "scene_index": 2, "narration": "n", "causal_role": "payoff",
        "owned_claim_id": "payoff", "new_information": "i", "visual_requirement": "v",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 2, "subject": "aircraft main wing",
        "required_visible_components": ["aircraft"],
        "required_observable_state": ["bending"],
        "search_queries": ["", "  ", "airplane wing wide shot"],
    })
    item = scene_v2_to_v1_item(scene, plan)
    assert item["keyword"] == "airplane wing wide shot"


def test_scene_v2_to_v1_item_falls_back_to_subject_when_all_queries_blank():
    scene = SceneV2.from_dict({
        "scene_index": 1, "narration": "n", "causal_role": "phenomenon",
        "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1, "subject": "aircraft main wing",
        "required_visible_components": ["aircraft"],
        "required_observable_state": ["bending"],
        "search_queries": ["", ""],
    })
    item = scene_v2_to_v1_item(scene, plan)
    assert item["keyword"] == "aircraft main wing"


def test_scene_v2_to_v1_item_rejects_when_no_keyword_available():
    scene = SceneV2.from_dict({
        "scene_index": 1, "narration": "n", "causal_role": "phenomenon",
        "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v",
    })
    # subject is required non-blank by VisualPlanV2's own gate, so this shape
    # (blank subject) only happens if a plan is used without that gate --
    # this test guards scene_v2_to_v1_item's OWN fail-closed behavior
    # independent of that gate having already run.
    plan = VisualPlanV2(
        scene_index=1, subject="", required_visible_components=["aircraft"],
        required_observable_state=["bending"], search_queries=["", ""],
    )
    try:
        scene_v2_to_v1_item(scene, plan)
        assert False, "should have raised ValueError"
    except ValueError as exc:
        assert "no usable keyword" in str(exc)


def test_render_v2_pipeline_calls_reset_generate_qa_render_in_order():
    scenes = [SceneV2.from_dict({
        "scene_index": 1, "narration": "n", "causal_role": "phenomenon",
        "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v",
    })]
    plans = [VisualPlanV2.from_dict({
        "scene_index": 1, "subject": "aircraft main wing",
        "required_visible_components": ["aircraft"],
        "required_observable_state": ["bending"],
        "search_queries": ["aircraft wing flex"],
    })]
    calls = []
    result = render_v2_pipeline(
        scenes, plans,
        reset_final_visual_semantic_report_fn=lambda: calls.append("reset"),
        generate_scenes_fn=lambda items: calls.append("generate") or ["clip"],
        validate_final_visual_semantic_qa_fn=lambda scenes_: calls.append("v1qa"),
        validate_actual_v2_visuals_fn=lambda scenes_, plans_, items_: calls.append("v2qa"),
        render_final_video_fn=lambda clips: calls.append("render") or "final.mp4",
    )
    assert calls == ["reset", "generate", "v1qa", "v2qa", "render"]
    assert result == "final.mp4"


def test_render_v2_pipeline_skips_render_when_qa_fails():
    scenes = [SceneV2.from_dict({
        "scene_index": 1, "narration": "n", "causal_role": "phenomenon",
        "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v",
    })]
    plans = [VisualPlanV2.from_dict({
        "scene_index": 1, "subject": "aircraft main wing",
        "required_visible_components": ["aircraft"],
        "required_observable_state": ["bending"],
        "search_queries": ["aircraft wing flex"],
    })]
    calls = []

    def failing_qa(scenes_):
        calls.append("qa")
        raise RuntimeError("FINAL_VISUAL_SEMANTIC_QA_FAILED missing=[] failed=[1]")

    try:
        render_v2_pipeline(
            scenes, plans,
            reset_final_visual_semantic_report_fn=lambda: calls.append("reset"),
            generate_scenes_fn=lambda items: calls.append("generate") or ["clip"],
            validate_final_visual_semantic_qa_fn=failing_qa,
            render_final_video_fn=lambda clips: calls.append("render") or "final.mp4",
        )
        assert False, "should have raised"
    except RuntimeError as exc:
        assert "FINAL_VISUAL_SEMANTIC_QA_FAILED" in str(exc)
    assert calls == ["reset", "generate", "qa"]  # render never called


def test_render_v2_pipeline_skips_render_when_actual_visual_qa_fails():
    scenes = [SceneV2.from_dict({
        "scene_index": 1, "narration": "n", "causal_role": "phenomenon",
        "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v",
    })]
    plans = [VisualPlanV2.from_dict({
        "scene_index": 1, "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "wing"],
        "required_observable_state": ["visible upward bending"],
        "search_queries": ["aircraft wing flex"],
    })]
    calls = []

    def failing_actual(scenes_, plans_, items_):
        calls.append("v2qa")
        raise RuntimeError("V2_ACTUAL_VISUAL_QA_FAILED scenes=[1]")

    try:
        render_v2_pipeline(
            scenes, plans,
            reset_final_visual_semantic_report_fn=lambda: calls.append("reset"),
            generate_scenes_fn=lambda items: calls.append("generate") or ["clip"],
            validate_final_visual_semantic_qa_fn=lambda scenes_: calls.append("v1qa"),
            validate_actual_v2_visuals_fn=failing_actual,
            render_final_video_fn=lambda clips: calls.append("render") or "final.mp4",
        )
        assert False, "should have raised"
    except RuntimeError as exc:
        assert "V2_ACTUAL_VISUAL_QA_FAILED" in str(exc)
    assert calls == ["reset", "generate", "v1qa", "v2qa"]

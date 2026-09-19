"""Offline regressions for Clean V2 exact-asset downstream handoff."""

from quality_core_v2.candidate import evaluate_candidate_v2
from quality_core_v2.downstream import render_v2_pipeline, scene_v2_to_v1_item
from quality_core_v2.schemas import CandidateV2, CandidateVisualV2, SceneV2, VisualPlanV2
from quality_core_v2.script_plan import evaluate_script_plan_v2
from quality_core_v2.visual_plan import evaluate_visual_plan_v2


def _scene(index, narration, role, claim, info, requirement):
    return SceneV2.from_dict({
        "scene_index": index,
        "narration": narration,
        "causal_role": role,
        "owned_claim_id": claim,
        "new_information": info,
        "visual_requirement": requirement,
    })


def _plan(index, query):
    return VisualPlanV2.from_dict({
        "scene_index": index,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "search_queries": [query],
    })


def _visual(index):
    return CandidateVisualV2.from_dict({
        "source_type": "stock",
        "description": "aircraft main wing visible upward elastic bending",
        "visible_components": ["aircraft", "main wing"],
        "observable_state": ["visible upward elastic bending"],
        "provider": "pexels",
        "source_id": f"asset-{index}",
        "media_url": f"https://cdn.example/asset-{index}.mp4",
        "thumbnail_url": f"https://cdn.example/asset-{index}.jpg",
        "search_query": "aircraft wing flex",
    })


def test_full_control_flow_candidate_to_exact_asset_render_handoff():
    candidate = CandidateV2.from_dict({
        "topic": "aircraft wing flex",
        "concrete_subject": "aircraft main wing",
        "observable_phenomenon": "upward elastic bending",
        "core_question": "왜 휘는가",
        "mechanism": "탄성 변형",
        "reveal": "일부러 휘도록 설계됨",
        "canonical_subject": "aircraft main wing",
    })
    assert evaluate_candidate_v2(candidate).passed

    scenes = [
        _scene(
            1,
            "aircraft wing flex visible",
            "phenomenon",
            "phenomenon",
            "wing flex is visible",
            "aircraft main wing visible upward elastic bending",
        ),
        _scene(
            2,
            "aircraft wing flex remains visible",
            "payoff",
            "payoff",
            "flex is intentional",
            "aircraft main wing visible upward elastic bending",
        ),
    ]
    assert evaluate_script_plan_v2(scenes).passed

    plans = [
        _plan(1, "aircraft wing flexing in flight"),
        _plan(2, "aircraft wing flex wide shot"),
    ]
    for plan in plans:
        assert evaluate_visual_plan_v2(plan).passed

    visuals = [_visual(1), _visual(2)]
    calls = {}

    def fake_generate(scenes_, plans_, visuals_):
        calls["asset_urls"] = [v.media_url for v in visuals_]
        return ["clip1", "clip2"]

    def fake_render(clips):
        calls["clips"] = clips
        return "final_shorts.mp4"

    result = render_v2_pipeline(
        scenes,
        plans,
        visuals,
        generate_selected_scenes_fn=fake_generate,
        render_final_video_fn=fake_render,
    )
    assert result == "final_shorts.mp4"
    assert calls["asset_urls"] == [
        "https://cdn.example/asset-1.mp4",
        "https://cdn.example/asset-2.mp4",
    ]
    assert calls["clips"] == ["clip1", "clip2"]


def test_scene_v2_to_v1_item_skips_blank_first_search_query():
    scene = _scene(2, "n", "payoff", "payoff", "i", "v")
    plan = VisualPlanV2.from_dict({
        "scene_index": 2,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft"],
        "required_observable_state": ["bending"],
        "search_queries": ["", "  ", "airplane wing wide shot"],
    })
    item = scene_v2_to_v1_item(scene, plan)
    assert item["keyword"] == "airplane wing wide shot"


def test_scene_v2_to_v1_item_falls_back_to_subject_when_all_queries_blank():
    scene = _scene(1, "n", "phenomenon", "a", "i", "v")
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft"],
        "required_observable_state": ["bending"],
        "search_queries": ["", ""],
    })
    item = scene_v2_to_v1_item(scene, plan)
    assert item["keyword"] == "aircraft main wing"


def test_scene_v2_to_v1_item_rejects_when_no_keyword_available():
    scene = _scene(1, "n", "phenomenon", "a", "i", "v")
    plan = VisualPlanV2(
        scene_index=1,
        subject="",
        required_visible_components=["aircraft"],
        required_observable_state=["bending"],
        search_queries=["", ""],
    )
    try:
        scene_v2_to_v1_item(scene, plan)
        assert False, "should have raised ValueError"
    except ValueError as exc:
        assert "no usable keyword" in str(exc)


def test_render_v2_pipeline_rejects_mismatched_asset_before_render():
    scene = _scene(
        1,
        "aircraft wing flex visible",
        "phenomenon",
        "a",
        "i",
        "aircraft main wing visible upward elastic bending",
    )
    plan = _plan(1, "aircraft wing flex")
    bad = CandidateVisualV2.from_dict({
        "source_type": "stock",
        "description": "static aircraft wing",
        "visible_components": ["aircraft", "main wing"],
        "observable_state": [],
        "provider": "pexels",
        "source_id": "bad",
        "media_url": "https://cdn.example/bad.mp4",
    })
    calls = []
    try:
        render_v2_pipeline(
            [scene],
            [plan],
            [bad],
            generate_selected_scenes_fn=lambda *_: calls.append("generate") or ["clip"],
            render_final_video_fn=lambda *_: calls.append("render") or "final.mp4",
        )
        assert False, "should have raised"
    except RuntimeError as exc:
        assert "selected visual rejected before render" in str(exc)
    assert calls == []


def test_render_v2_pipeline_rejects_asset_without_exact_media_url():
    scene = _scene(
        1,
        "aircraft wing flex visible",
        "phenomenon",
        "a",
        "i",
        "aircraft main wing visible upward elastic bending",
    )
    plan = _plan(1, "aircraft wing flex")
    visual = _visual(1)
    visual.media_url = ""
    try:
        render_v2_pipeline([scene], [plan], [visual])
        assert False, "should have raised"
    except RuntimeError as exc:
        assert "no exact media_url" in str(exc)

"""Offline tests for the pure halves of the adapters. No network, no keys."""

import json

from quality_core_v2.adapters.explorer_adapter import parse_explorer_response, propose_candidate_with_bounded_rewrite
from quality_core_v2.adapters.writer_adapter import parse_writer_response, parse_visual_plan_response
from quality_core_v2.adapters.retrieval_adapter import parse_visual_classification, provider_hit_to_description, select_visual_for_scene
from quality_core_v2.schemas import ShapeError


def test_parse_explorer_response_ok():
    raw = json.dumps({
        "topic": "aircraft wing flex", "concrete_subject": "aircraft main wing",
        "observable_phenomenon": "upward bending", "core_question": "왜 휘는가",
        "mechanism": "탄성 변형", "reveal": "일부러 휘도록 설계됨",
        "canonical_subject": "aircraft main wing",
    })
    c = parse_explorer_response(raw)
    assert c.concrete_subject == "aircraft main wing"


def test_parse_explorer_response_malformed_raises():
    try:
        parse_explorer_response("not json")
        assert False, "should have raised"
    except ShapeError:
        pass


def test_bounded_rewrite_stops_after_one_retry():
    calls = {"n": 0}

    def fake_call(topic, recent):
        calls["n"] += 1
        return json.dumps({
            "topic": topic, "concrete_subject": "x", "observable_phenomenon": "y",
            "core_question": "z", "mechanism": "m", "reveal": "효율을 향상시킵니다",
            "canonical_subject": "x",
        })

    candidate, verdict = propose_candidate_with_bounded_rewrite("dir", [], call_fn=fake_call)
    assert candidate is None
    assert not verdict.passed
    assert calls["n"] == 2  # 1 initial + MAX_CANDIDATE_REWRITES(1)


def test_parse_writer_response_ok():
    raw = json.dumps({"scenes": [
        {"scene_index": 1, "narration": "n", "causal_role": "phenomenon",
         "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v"},
    ]})
    scenes = parse_writer_response(raw)
    assert len(scenes) == 1 and scenes[0].scene_index == 1


def test_parse_visual_plan_response_defaults_scene_index():
    raw = json.dumps({"subject": "wing", "required_visible_components": ["wing"],
                       "required_observable_state": ["bending"]})
    plan = parse_visual_plan_response(raw, scene_index=3)
    assert plan.scene_index == 3


def test_parse_visual_classification_ok():
    raw = json.dumps({"visible_components": ["wing"], "observable_state": ["bending"]})
    v = parse_visual_classification(raw, source_type="stock", description="d")
    assert v.visible_components == ["wing"]


def test_provider_hit_to_description_pixabay_uses_tags():
    assert provider_hit_to_description({"tags": "wing, aircraft"}, "pixabay") == "wing, aircraft"


def test_provider_hit_to_description_pexels_uses_query():
    assert provider_hit_to_description({"query": "wing bending"}, "pexels") == "wing bending"


# ============================================================
# budget_guard contract regression (no real OpenAI call; a fake client
# with a fake response object exercises the exact call_* functions
# against the real quality.budget_guard module).
# ============================================================

class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5
    prompt_tokens_details = None


class _FakeMessage:
    content = "{}"


class _FakeChoice:
    message = _FakeMessage()


class _FakeResponse:
    usage = _FakeUsage()
    choices = [_FakeChoice()]


class _FakeCompletions:
    def create(self, **kwargs):
        return _FakeResponse()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeClient:
    chat = _FakeChat()


def _reset_budget():
    from quality.budget_guard import reset_budget
    reset_budget()


def test_call_explorer_matches_budget_guard_contract():
    from quality_core_v2.adapters.explorer_adapter import call_explorer
    _reset_budget()
    raw = call_explorer("dir", [], client=_FakeClient())
    assert raw == "{}"


def test_call_writer_matches_budget_guard_contract():
    from quality_core_v2.adapters.writer_adapter import call_writer
    from quality_core_v2.schemas import CandidateV2
    _reset_budget()
    candidate = CandidateV2.from_dict({
        "topic": "t", "concrete_subject": "s", "observable_phenomenon": "p",
        "core_question": "q", "mechanism": "m", "reveal": "r", "canonical_subject": "s",
    })
    raw = call_writer(candidate, client=_FakeClient())
    assert raw == "{}"


def test_call_visual_planner_matches_budget_guard_contract():
    from quality_core_v2.adapters.writer_adapter import call_visual_planner
    from quality_core_v2.schemas import SceneV2
    _reset_budget()
    scene = SceneV2.from_dict({
        "scene_index": 1, "narration": "n", "causal_role": "c",
        "owned_claim_id": "a", "new_information": "i", "visual_requirement": "v",
    })
    raw = call_visual_planner(scene, client=_FakeClient())
    assert raw == "{}"


def test_call_visual_classifier_matches_budget_guard_contract():
    from quality_core_v2.adapters.retrieval_adapter import call_visual_classifier
    from quality_core_v2.schemas import VisualPlanV2
    _reset_budget()
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward bending"],
    })
    raw = call_visual_classifier(
        "http://example.com/thumb.jpg",
        plan,
        client=_FakeClient(),
    )
    assert raw == "{}"


def test_select_visual_for_scene_preserves_exact_accepted_media_url():
    from quality_core_v2.schemas import SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "aircraft wing flex visible",
        "causal_role": "phenomenon",
        "owned_claim_id": "wing_flex",
        "new_information": "wing flex is visible",
        "visual_requirement": "aircraft wing flex visible",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward bending"],
        "search_queries": ["aircraft wing flex"],
    })

    hits = [
        {
            "id": "static",
            "url": "https://cdn.example/static.mp4",
            "thumbnail": "https://cdn.example/static.jpg",
            "query": "aircraft wing flex",
        },
        {
            "id": "flex",
            "url": "https://cdn.example/flex.mp4",
            "thumbnail": "https://cdn.example/flex.jpg",
            "query": "aircraft wing flex",
        },
    ]

    def fake_search(_query):
        return hits

    def fake_classify(thumbnail_url, plan_):
        if thumbnail_url.endswith("static.jpg"):
            return json.dumps({
                "description": "aircraft main wing static",
                "visible_components": ["aircraft", "main wing"],
                "observable_state": [],
            })
        return json.dumps({
            "description": "aircraft wing flex visible upward bending",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
        })

    def exact_video_classifier(scene_, plan_, identity_, path_):
        state = (
            []
            if identity_.source_id == "static"
            else list(plan_.required_observable_state)
        )
        return __import__(
            "quality_core_v2.schemas", fromlist=["CandidateVisualV2"]
        ).CandidateVisualV2.from_dict({
            "source_type": "stock",
            "description": (
                "aircraft main wing static"
                if not state
                else "aircraft wing flex visible upward bending"
            ),
            "visible_components": list(plan_.required_visible_components),
            "observable_state": state,
            "provider": identity_.provider,
            "source_id": identity_.source_id,
            "media_url": path_,
            "thumbnail_url": identity_.thumbnail_url,
            "search_query": identity_.search_query,
        })

    selected, verdict = select_visual_for_scene(
        scene,
        plan,
        provider_searches=[("pexels", fake_search)],
        classify_fn=fake_classify,
        max_classifications=2,
        download_stock_fn=lambda visual_, _scene: f"/tmp/{visual_.source_id}.mp4",
        classify_stock_video_fn=exact_video_classifier,
    )
    assert verdict.passed
    assert selected is not None
    assert selected.source_id == "flex"
    assert selected.media_url == "/tmp/flex.mp4"
    assert selected.thumbnail_url == "https://cdn.example/flex.jpg"


def test_generated_preference_uses_exact_generated_asset_without_stock_search():
    from quality_core_v2.adapters.retrieval_adapter import select_visual_for_scene
    from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 2,
        "narration": "aircraft wing flex visible",
        "causal_role": "mechanism_change",
        "owned_claim_id": "elastic_bending",
        "new_information": "elastic bending is visible",
        "visual_requirement": "aircraft main wing visible upward elastic bending",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 2,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "preferred_source_type": "generated",
        "search_queries": ["aircraft wing flex"],
    })
    stock_calls = []

    def forbidden_stock(query):
        stock_calls.append(query)
        return []

    def fake_generate(_scene, _plan):
        return {
            "path": "workspace/temp/generated-scene-2.mp4",
            "provider": "openai_image",
            "source_id": "generated-2",
        }

    def fake_classify_generated(scene_, plan_, identity_, path_):
        assert path_ == "workspace/temp/generated-scene-2.mp4"
        return CandidateVisualV2.from_dict({
            "source_type": "generated",
            "description": "aircraft wing flex visible",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
            "provider": identity_.provider,
            "source_id": identity_.source_id,
            "media_url": identity_.media_url,
            "search_query": identity_.search_query,
        })

    visual, verdict = select_visual_for_scene(
        scene,
        plan,
        provider_searches=[("pexels", forbidden_stock)],
        generate_fn=fake_generate,
        classify_generated_fn=fake_classify_generated,
    )
    assert verdict.passed
    assert visual is not None
    assert visual.media_url == "workspace/temp/generated-scene-2.mp4"
    assert stock_calls == []


def test_required_relation_must_be_visibly_proven():
    from quality_core_v2.visual_plan import match_visual_to_plan
    from quality_core_v2.schemas import CandidateVisualV2, VisualPlanV2

    plan = VisualPlanV2.from_dict({
        "scene_index": 4,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "required_relation_or_mechanism": ["bending under aerodynamic load"],
    })
    visual = CandidateVisualV2.from_dict({
        "source_type": "stock",
        "description": "aircraft main wing bending",
        "visible_components": ["aircraft", "main wing"],
        "observable_state": ["visible upward elastic bending"],
        "visible_relations_or_mechanisms": [],
    })
    verdict = match_visual_to_plan(plan, visual)
    assert not verdict.passed
    assert "relation/mechanism" in verdict.reason


def test_used_asset_is_skipped_before_classification():
    from quality_core_v2.adapters.retrieval_adapter import select_visual_for_scene
    from quality_core_v2.schemas import SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 3,
        "narration": "aircraft wing flex visible",
        "causal_role": "mechanism_input",
        "owned_claim_id": "load",
        "new_information": "wing load",
        "visual_requirement": "aircraft wing flex visible",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 3,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "search_queries": ["aircraft wing flex"],
    })
    hits = [
        {"id": "used", "url": "https://cdn.example/used.mp4",
         "thumbnail": "https://cdn.example/used.jpg", "query": "aircraft wing flex"},
        {"id": "fresh", "url": "https://cdn.example/fresh.mp4",
         "thumbnail": "https://cdn.example/fresh.jpg", "query": "aircraft wing flex"},
    ]
    classified = []

    def classify(url, plan_):
        classified.append(url)
        return json.dumps({
            "description": "aircraft wing flex visible",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
        })

    from quality_core_v2.schemas import CandidateVisualV2

    def exact_video_classifier(scene_, plan_, identity_, path_):
        return CandidateVisualV2.from_dict({
            "source_type": "stock",
            "description": "aircraft wing flex visible",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
            "provider": identity_.provider,
            "source_id": identity_.source_id,
            "media_url": path_,
            "thumbnail_url": identity_.thumbnail_url,
            "search_query": identity_.search_query,
        })

    visual, verdict = select_visual_for_scene(
        scene,
        plan,
        provider_searches=[("pexels", lambda _q: hits)],
        classify_fn=classify,
        max_classifications=2,
        download_stock_fn=lambda visual_, _scene: f"/tmp/{visual_.source_id}.mp4",
        classify_stock_video_fn=exact_video_classifier,
        used_asset_keys={"pexels:used"},
    )
    assert verdict.passed
    assert visual is not None and visual.source_id == "fresh"
    # Scene selection no longer spends vision on thumbnails; the exact
    # downloaded video is the first semantic classifier.
    assert classified == []


def test_thumbnail_pass_exact_video_fail_moves_to_next_candidate():
    from quality_core_v2.adapters.retrieval_adapter import select_visual_for_scene
    from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "aircraft wing flex visible",
        "causal_role": "phenomenon",
        "owned_claim_id": "flex",
        "new_information": "wing flex visible",
        "visual_requirement": "aircraft wing flex visible",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "search_queries": ["aircraft wing flex"],
    })
    hits = [
        {"id": "false-positive", "url": "https://cdn.example/a.mp4",
         "thumbnail": "https://cdn.example/a.jpg", "query": "aircraft wing flex"},
        {"id": "real-flex", "url": "https://cdn.example/b.mp4",
         "thumbnail": "https://cdn.example/b.jpg", "query": "aircraft wing flex"},
    ]

    def thumb_classifier(_url, plan_):
        return json.dumps({
            "description": "aircraft wing flex visible",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
        })

    def download(visual_, _scene):
        return f"/tmp/{visual_.source_id}.mp4"

    def video_classifier(scene_, plan_, identity_, path_):
        state = (
            []
            if "false-positive" in path_
            else list(plan_.required_observable_state)
        )
        return CandidateVisualV2.from_dict({
            "source_type": "stock",
            "description": (
                "aircraft wing static"
                if not state
                else "aircraft wing flex visible"
            ),
            "visible_components": list(plan_.required_visible_components),
            "observable_state": state,
            "provider": identity_.provider,
            "source_id": identity_.source_id,
            "media_url": identity_.media_url,
            "thumbnail_url": identity_.thumbnail_url,
            "search_query": identity_.search_query,
        })

    visual, verdict = select_visual_for_scene(
        scene,
        plan,
        provider_searches=[("pexels", lambda _q: hits)],
        classify_fn=thumb_classifier,
        max_classifications=2,
        download_stock_fn=download,
        classify_stock_video_fn=video_classifier,
    )
    assert verdict.passed
    assert visual is not None
    assert visual.source_id == "real-flex"
    assert visual.media_url == "/tmp/real-flex.mp4"


def test_thumbnail_is_only_coarse_gate_and_exact_video_proves_motion():
    from quality_core_v2.adapters.retrieval_adapter import select_visual_for_scene
    from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "aircraft wing flex visible",
        "causal_role": "phenomenon",
        "owned_claim_id": "flex",
        "new_information": "wing flex visible",
        "visual_requirement": "aircraft wing flex visible",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "search_queries": ["aircraft wing flex"],
    })

    def thumbnail_classifier(_url, plan_):
        return json.dumps({
            "description": "aircraft main wing",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": [],
            "visible_relations_or_mechanisms": [],
            "forbidden_visuals_present": [],
        })

    def exact_classifier(scene_, plan_, identity_, path_):
        return CandidateVisualV2.from_dict({
            "source_type": "stock",
            "description": "aircraft wing flex visible",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
            "provider": identity_.provider,
            "source_id": identity_.source_id,
            "media_url": path_,
            "thumbnail_url": identity_.thumbnail_url,
            "search_query": identity_.search_query,
        })

    visual, verdict = select_visual_for_scene(
        scene,
        plan,
        provider_searches=[(
            "pexels",
            lambda _q: [{
                "id": "dynamic-1",
                "url": "https://cdn.example/dynamic.mp4",
                "thumbnail": "https://cdn.example/dynamic.jpg",
                "query": "aircraft wing flex",
            }],
        )],
        classify_fn=thumbnail_classifier,
        max_classifications=1,
        download_stock_fn=lambda *_args: "/tmp/dynamic-1.mp4",
        classify_stock_video_fn=exact_classifier,
    )
    assert verdict.passed
    assert visual is not None
    assert visual.source_id == "dynamic-1"


def test_scene_selection_does_not_spend_vision_on_thumbnail():
    from quality_core_v2.adapters.retrieval_adapter import select_visual_for_scene
    from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "aircraft wing flex visible",
        "causal_role": "phenomenon",
        "owned_claim_id": "flex",
        "new_information": "wing flex visible",
        "visual_requirement": "aircraft wing flex visible",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward elastic bending"],
        "search_queries": ["aircraft wing flex"],
    })
    thumbnail_calls = []

    def forbidden_thumbnail_classifier(*_args):
        thumbnail_calls.append(True)
        raise AssertionError("thumbnail classifier must not be called by scene selection")

    def exact_classifier(scene_, plan_, identity_, path_):
        return CandidateVisualV2.from_dict({
            "source_type": "stock",
            "description": "aircraft wing flex visible",
            "visible_components": list(plan_.required_visible_components),
            "observable_state": list(plan_.required_observable_state),
            "provider": identity_.provider,
            "source_id": identity_.source_id,
            "media_url": path_,
            "thumbnail_url": identity_.thumbnail_url,
            "search_query": identity_.search_query,
        })

    visual, verdict = select_visual_for_scene(
        scene,
        plan,
        provider_searches=[(
            "pexels",
            lambda _q: [{
                "id": "exact-1",
                "url": "https://cdn.example/exact-1.mp4",
                "thumbnail": "https://cdn.example/exact-1.jpg",
                "query": "aircraft wing flex",
            }],
        )],
        classify_fn=forbidden_thumbnail_classifier,
        max_classifications=1,
        download_stock_fn=lambda *_args: "/tmp/exact-1.mp4",
        classify_stock_video_fn=exact_classifier,
    )
    assert verdict.passed
    assert visual is not None and visual.source_id == "exact-1"
    assert thumbnail_calls == []


def test_generation_payload_carries_canonical_subject_and_explicit_flex_geometry():
    from quality_core_v2.adapters.retrieval_adapter import _generation_scene_payload
    from quality_core_v2.schemas import SceneV2, VisualPlanV2

    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "비행 중 날개가 위로 휩니다.",
        "causal_role": "phenomenon",
        "owned_claim_id": "wing_flex",
        "new_information": "날개가 위로 휜다",
        "visual_requirement": "main wing bends upward",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["wing bending during flight"],
        "preferred_source_type": "generated",
        "search_queries": ["aircraft wing flex bending in flight"],
    })
    payload = _generation_scene_payload(scene, plan)
    profile = payload["_canonical_visual_supply"]
    assert profile["canonical_subject"] == "aircraft main wing"
    assert "main wing" in profile["canonical_terms"]
    assert "wing bending during flight" in profile["visual_discriminators"]
    assert "wingtip must sit visibly higher than the wing root plane" in payload["visual_goal"]
    assert "straight or merely banked wing is invalid" in payload["visual_goal"]

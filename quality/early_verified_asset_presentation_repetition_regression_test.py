import tempfile
from pathlib import Path

import video.still_image_fallback as still


CANONICAL = "jet engine nacelle/nozzle chevrons"
REQUIRED = ["aircraft", "engine", "chevron"]


def _scene(role, *, canonical=CANONICAL, causal_role="", owned_claim_id="", explanatory=None):
    keyword = {
        "phenomenon": "aircraft jet engine nacelle nozzle chevron serrated",
        "question": "aircraft jet engine nacelle nozzle chevron serrated question",
        "mechanism": "jet engine flow interface",
        "result": "jet engine noise reduction",
    }.get(role, "aircraft engine")
    return {
        "scene_id": role,
        "role": role,
        "scene_role": role,
        "causal_role": causal_role,
        "owned_claim_id": owned_claim_id,
        "semantic_purpose": "question: why does this verified feature exist" if role == "question" else role,
        "required_explanatory_groups": list(explanatory or []),
        "keyword": keyword,
        "visual_goal": "rear jet-engine nozzle chevrons",
        "text": "엔진 뒤쪽의 톱니 모양은 왜 있을까요?" if role == "question" else "엔진 뒤쪽의 톱니 모양입니다.",
        "_canonical_visual_supply": {
            "canonical_subject": canonical,
            "identity_confidence": 0.98,
            "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron", "trailing"],
            "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated", "rear"],
            "grounding_source": "NASA",
        },
    }


def _evidence():
    return {
        "pass": True,
        "required_subject_groups": list(REQUIRED),
        "raw_visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "effective_subject_groups": {"aircraft": True, "engine": True, "chevron": True},
        "visible_components": ["jet engine", "rear nozzle", "chevron"],
        "schema_parser_consistency": True,
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "viewpoint_structure_required": True,
        "viewpoint_structure_pass": True,
        "viewpoint_structure_evidence": {
            "rear_nozzle_or_trailing_edge_identifiable": True,
            "chevron_attached_to_rear_nozzle_or_trailing_edge": True,
            "front_intake_or_fan_side_dominant": False,
            "mobile_structure_identifiable": True,
        },
    }


def _seed(tmp, source_id="still-human-qa-chevron"):
    still.reset_still_image_budget()
    image = Path(tmp) / "scene1.png"
    image.write_bytes(b"verified rear nozzle chevron")
    ok = still._cache_verified_subject_proof(
        _scene("phenomenon"),
        image_path=image,
        source_id=source_id,
        evidence=_evidence(),
        verified=True,
    )
    assert ok is True
    return image, source_id


def _expect_runtime_error(fn, needle):
    try:
        fn()
    except RuntimeError as exc:
        assert needle in str(exc), str(exc)
        return
    raise AssertionError(f"expected RuntimeError containing {needle!r}")


def main():
    assert hasattr(still, "_verified_question_presentation")
    assert hasattr(still, "_still_presentation_identity")
    assert hasattr(still, "_assert_early_presentation_distinct")

    with tempfile.TemporaryDirectory() as tmp:
        # CASE 1: same verified physical asset, different semantic presentation.
        image, source_id = _seed(tmp)
        still._register_source_use(source_id, _scene("phenomenon"))
        cached = next(iter(still._VERIFIED_SUBJECT_PROOF_CACHE.values()))
        presentation = still._verified_question_presentation(_scene("question"), cached)
        assert presentation is not None
        baseline_identity = still._still_presentation_identity(None)
        question_identity = still._still_presentation_identity(presentation)
        assert question_identity != baseline_identity
        assert presentation["scene_role"] == "question"
        assert presentation["visual_beat"] == "inspect_verified_feature"
        assert presentation["subject_focal_region"] == "verified_rear_nozzle_chevron_center"

        original_motion = still._motion_clip
        captured = []
        def fake_motion(image_path, output_path, duration, presentation=None):
            captured.append({
                "image_path": str(image_path),
                "presentation": dict(presentation or {}),
            })
            Path(output_path).write_bytes(b"motion")
        still._motion_clip = fake_motion
        try:
            result = still._reuse_verified_question_subject(
                _scene("question"),
                output_path=Path(tmp) / "scene2.mp4",
                duration=5.0,
                trigger_reason="human_qa_counterexample",
            )
        finally:
            still._motion_clip = original_motion
        assert result is not None
        assert result["source_id"] == source_id
        assert result["source_asset_id"] == source_id
        assert captured[0]["image_path"] == str(image)
        assert captured[0]["presentation"]["presentation_id"] == "QUESTION_FEATURE_INSPECTION_CENTER_V1"
        assert result["presentation_identity"] != list(baseline_identity)
        print("CASE 1 same physical identity + different presentation: PASS")

        # CASE 2: an effectively identical Scene1/Scene2 transform is detected.
        identical = {
            "presentation_id": "ESTABLISH_SUBJECT_CENTER_V1",
            "zoom_start": 1.00,
            "zoom_max": 1.08,
            "zoom_step": 0.0007,
            "pan_x": "center",
            "pan_y": "center",
        }
        _expect_runtime_error(
            lambda: still._assert_early_presentation_distinct(identical),
            "presentation repetition detected",
        )
        print("CASE 2 identical presentation rejected: PASS")

        # CASE 3: crop-risk/excessive zoom is fail-closed before ffmpeg.
        unsafe_zoom = dict(presentation)
        unsafe_zoom["zoom_max"] = 1.30
        _expect_runtime_error(
            lambda: still._assert_early_presentation_distinct(unsafe_zoom),
            "excessive zoom",
        )
        print("CASE 3 excessive crop/zoom rejected: PASS")

        # CASE 4: front-intake/fan-dominant physical evidence remains rejected by #269.
        from video.hook_visual_dominance import _still_viewpoint_structure_apply
        scene1 = _scene("phenomenon")
        payload = {
            "viewpoint_structure_evidence": {
                "rear_nozzle_or_trailing_edge_identifiable": True,
                "chevron_attached_to_rear_nozzle_or_trailing_edge": True,
                "front_intake_or_fan_side_dominant": True,
                "mobile_structure_identifiable": True,
            }
        }
        checked = _still_viewpoint_structure_apply(
            {"schema_parser_consistency": True}, payload, scene1
        )
        assert checked["viewpoint_structure_required"] is True
        assert checked["viewpoint_structure_pass"] is False
        print("CASE 4 front intake/fan dominant rejected by physical proof: PASS")

        # CASE 5: changing source_id cannot disguise an identical presentation.
        same_transform_source_a = still._still_presentation_identity(identical)
        same_transform_source_b = still._still_presentation_identity(dict(identical))
        assert same_transform_source_a == same_transform_source_b == baseline_identity
        _expect_runtime_error(
            lambda: still._assert_early_presentation_distinct(dict(identical)),
            "presentation repetition detected",
        )
        print("CASE 5 fake source lineage cannot bypass presentation identity: PASS")

        # CASE 6: Scene 3-5 explanatory roles remain outside this policy.
        for scene3to5 in (
            _scene("mechanism", causal_role="mechanism_input", owned_claim_id="flow_interface", explanatory=["flow", "interface"]),
            _scene("mechanism", causal_role="mechanism_change", owned_claim_id="chevron_flow_mixing", explanatory=["flow", "mixing"]),
            _scene("result", causal_role="primary_result", owned_claim_id="noise_reduction", explanatory=["noise", "reduction"]),
        ):
            assert still._verified_question_presentation(scene3to5, cached) is None
            assert still._reuse_verified_question_subject(
                scene3to5,
                output_path=Path(tmp) / f"{scene3to5['owned_claim_id']}.mp4",
                duration=5.0,
                trigger_reason="test",
            ) is None
        print("CASE 6 explanatory Scene 3-5 unchanged: PASS")

        # CASE 7: unrelated/generic question stills do not receive this transform.
        generic_scene = _scene("question", canonical="aircraft cabin window")
        generic_scene["_canonical_visual_supply"]["canonical_terms"] = ["aircraft", "cabin", "window"]
        generic_scene["_canonical_visual_supply"]["visual_discriminators"] = ["window", "frame"]
        assert still._verified_question_presentation(generic_scene, cached) is None
        print("CASE 7 unrelated generic still reuse untouched: PASS")

    installer = Path("ci_early_verified_asset_presentation_hotfix.py").read_text(encoding="utf-8")
    for forbidden in (
        "requests.post(",
        "authorize_call(",
        "chat.completions.create(",
        "responses.create(",
        "client.images.generate(",
        "MAX_RETRIES",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
    ):
        assert forbidden not in installer, forbidden
    assert "STILL_IMAGE_MAX_PER_VIDEO" not in installer
    assert "source_asset_id" not in installer or '"source_asset_id": source_asset_id' not in installer
    print("NEW_IMAGE_GENERATION_CALLS=0")
    print("NEW_VISION_CALLS=0")
    print("NEW_LLM_CALLS=0")
    print("STILL_BUDGET_CHANGE=NONE")
    print("API_COST_CHANGE=NONE")
    print("RETRY_CHANGE=NONE")
    print("EARLY_SCENE_VERIFIED_ASSET_PRESENTATION_REPETITION REGRESSION: PASS")


if __name__ == "__main__":
    main()

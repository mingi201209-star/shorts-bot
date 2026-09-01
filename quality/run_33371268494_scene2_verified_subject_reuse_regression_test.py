import tempfile
from pathlib import Path

import video.still_image_fallback as still


CANONICAL = "jet engine nacelle/nozzle chevrons"
REQUIRED = ["aircraft", "engine", "chevron"]
SCENE1_KEYWORD = "aircraft jet engine nacelle nozzle chevron serrated"
SCENE2_KEYWORD = "aircraft engine chevron wing mechanism stage 2"


def scene(*, role="phenomenon", canonical=CANONICAL, keyword=None, causal_role="", owned_claim_id="", explanatory=None):
    if keyword is None:
        keyword = SCENE2_KEYWORD if role == "question" else SCENE1_KEYWORD
    return {
        "scene_id": role,
        "role": role,
        "scene_role": role,
        "causal_role": causal_role,
        "owned_claim_id": owned_claim_id,
        "semantic_purpose": "question: ask why the observed physical feature exists" if role == "question" else f"{role}: test",
        "required_explanatory_groups": list(explanatory or []),
        "keyword": keyword,
        "visual_goal": "비행기 엔진 뒤쪽 톱니 모양",
        "text": "그런데 비행기 엔진 뒤쪽의 톱니 모양은 왜 그렇게 설계되었을까요?" if role == "question" else "비행기 엔진 뒤는 톱니처럼 생겼습니다.",
        "_canonical_visual_supply": {
            "canonical_subject": canonical,
            "identity_confidence": 0.98,
            "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron"],
            "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated"],
            "grounding_source": "NASA",
        },
    }


def evidence(*, effective=None, raw=None, consistent=True, verifier_pass=True, contradiction=False):
    return {
        "pass": verifier_pass,
        "required_subject_groups": list(REQUIRED),
        "raw_visible_subject_groups": dict(raw or {"aircraft": False, "engine": True, "chevron": True}),
        "visible_subject_groups": dict(raw or {"aircraft": False, "engine": True, "chevron": True}),
        "effective_subject_groups": dict(effective or {"aircraft": True, "engine": True, "chevron": True}),
        "visible_components": ["jet engine", "nacelle", "chevron", "engine"],
        "schema_parser_consistency": consistent,
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": contradiction,
        "reason": "chevron design clearly visible",
    }


def seed(tmp, ev=None, *, verified=True, source_id="still-run33371268494-scene1"):
    still.reset_still_image_budget()
    image = Path(tmp) / "scene1.png"
    image.write_bytes(b"verified-subject-proof")
    ok = still._cache_verified_subject_proof(
        scene(role="phenomenon", keyword=SCENE1_KEYWORD),
        image_path=image,
        source_id=source_id,
        evidence=ev or evidence(),
        verified=verified,
    )
    return image, source_id, ok


def main():
    assert hasattr(still, "_cache_verified_subject_proof"), "question subject reuse hotfix not installed"
    assert hasattr(still, "_reuse_verified_question_subject"), "question subject reuse dispatch missing"

    with tempfile.TemporaryDirectory() as tmp:
        # CASE A — exact Run 33371268494 positive counterexample.
        _, source_id, cached = seed(tmp)
        assert cached is True
        exact_scene2 = scene(role="question", keyword=SCENE2_KEYWORD)
        assert still._subject_proof_required_groups(exact_scene2) == tuple(sorted(REQUIRED))
        still._register_source_use(source_id, scene(role="phenomenon", keyword=SCENE1_KEYWORD))
        original_motion = still._motion_clip
        original_generate = still._generate_image
        original_verify = still._verify_motion_clip
        calls = {"motion": 0, "generate": 0, "vision": 0}
        presentations = []

        def fake_motion(image_path, output_path, duration, presentation=None):
            calls["motion"] += 1
            presentations.append(dict(presentation or {}))
            Path(output_path).write_bytes(Path(image_path).read_bytes())

        def forbidden_generate(*args, **kwargs):
            calls["generate"] += 1
            raise AssertionError("Scene 2 question reuse must not generate a new still")

        def forbidden_vision(*args, **kwargs):
            calls["vision"] += 1
            raise AssertionError("Scene 2 question reuse must not spend another Vision call")

        still._motion_clip = fake_motion
        still._generate_image = forbidden_generate
        still._verify_motion_clip = forbidden_vision
        try:
            out = Path(tmp) / "scene2.mp4"
            result = still.generate_still_motion_fallback(
                exact_scene2,
                output_path=out,
                duration=5.28,
                trigger_reason="no_semantically_safe_stock",
            )
        finally:
            still._motion_clip = original_motion
            still._generate_image = original_generate
            still._verify_motion_clip = original_verify
        assert result is not None
        assert result["mode"] == "REUSED_VERIFIED_QUESTION_SUBJECT_MOTION"
        assert calls == {"motion": 1, "generate": 0, "vision": 0}
        assert still.still_image_generation_count() == 0
        assert still.verified_source_use_count(source_id) == 2
        assert result["source_id"] == source_id
        assert result["source_asset_id"] == source_id
        if hasattr(still, "_verified_question_presentation"):
            assert presentations and presentations[0]["presentation_id"] == "QUESTION_FEATURE_INSPECTION_CENTER_V1"
            assert result["presentation_id"] == "QUESTION_FEATURE_INSPECTION_CENTER_V1"
        print("CASE A exact verified question-subject reuse: PASS")

        # CASE B — aircraft+engine 2/3 is never cacheable/reusable.
        _, _, cached = seed(
            tmp,
            evidence(effective={"aircraft": True, "engine": True, "chevron": False}, raw={"aircraft": False, "engine": True, "chevron": False}),
        )
        assert cached is False
        assert not still._VERIFIED_SUBJECT_PROOF_CACHE
        print("CASE B aircraft+engine 2/3 rejected: PASS")

        # CASE C — structured chevron=false cannot be repaired by effective/reason text.
        _, _, cached = seed(
            tmp,
            evidence(effective={"aircraft": True, "engine": True, "chevron": True}, raw={"aircraft": False, "engine": True, "chevron": False}),
        )
        assert cached is False
        print("CASE C structured chevron=false rejected: PASS")

        # CASE D — different canonical subject cannot reuse the proof.
        seed(tmp)
        assert still._reuse_verified_question_subject(
            scene(role="question", canonical="aircraft landing gear wheel", keyword=SCENE2_KEYWORD),
            output_path=Path(tmp) / "different.mp4", duration=5.0, trigger_reason="test",
        ) is None
        print("CASE D different canonical subject rejected: PASS")

        # CASE E — Scene 3 mechanism_input requires flow/interface explanation.
        seed(tmp)
        assert still._reuse_verified_question_subject(
            scene(role="mechanism", keyword="jet engine flow interface", causal_role="mechanism_input", owned_claim_id="flow_interface", explanatory=["flow", "interface"]),
            output_path=Path(tmp) / "flow.mp4", duration=5.0, trigger_reason="test",
        ) is None
        print("CASE E FLOW_INTERFACE subject-only reuse rejected: PASS")

        # CASE F — Scene 4 mechanism_change requires flow/mixing explanation.
        assert still._reuse_verified_question_subject(
            scene(role="mechanism", keyword="jet engine chevron flow mixing", causal_role="mechanism_change", owned_claim_id="chevron_flow_mixing", explanatory=["flow", "mixing"]),
            output_path=Path(tmp) / "mixing.mp4", duration=5.0, trigger_reason="test",
        ) is None
        print("CASE F CHEVRON_FLOW_MIXING subject-only reuse rejected: PASS")

        # CASE G — Scene 5 primary_result requires noise/reduction explanation.
        assert still._reuse_verified_question_subject(
            scene(role="result", keyword="jet engine noise reduction", causal_role="primary_result", owned_claim_id="noise_reduction", explanatory=["noise", "reduction"]),
            output_path=Path(tmp) / "noise.mp4", duration=5.0, trigger_reason="test",
        ) is None
        print("CASE G NOISE_REDUCTION_RESULT subject-only reuse rejected: PASS")

        # CASE H — free-text reason cannot override structured chevron=false.
        _, _, cached = seed(
            tmp,
            evidence(effective={"aircraft": True, "engine": True, "chevron": True}, raw={"aircraft": False, "engine": True, "chevron": False}),
        )
        assert cached is False
        print("CASE H reason-only chevron rejected: PASS")

        # CASE I — unverified/generated asset cannot enter the trusted cache.
        _, _, cached = seed(tmp, verified=False)
        assert cached is False
        _, _, cached = seed(tmp, evidence(verifier_pass=False))
        assert cached is False
        print("CASE I unverified asset rejected: PASS")

        # CASE J — same physical asset keeps the same physical lineage identity.
        _, source_id, cached = seed(tmp)
        assert cached is True
        cached_record = next(iter(still._VERIFIED_SUBJECT_PROOF_CACHE.values()))
        assert cached_record["source_id"] == source_id
        assert cached_record["source_asset_id"] == source_id
        original_motion = still._motion_clip
        still._motion_clip = lambda image_path, output_path, duration, presentation=None: Path(output_path).write_bytes(b"reuse")
        try:
            reused = still._reuse_verified_question_subject(
                scene(role="question", keyword=SCENE2_KEYWORD), output_path=Path(tmp) / "same.mp4", duration=5.0, trigger_reason="test"
            )
        finally:
            still._motion_clip = original_motion
        assert reused["source_id"] == source_id
        assert reused["source_asset_id"] == source_id
        print("CASE J same physical asset lineage preserved: PASS")

        # Additional false-positive guards.
        _, _, cached = seed(tmp, evidence(effective={"aircraft": False, "engine": True, "chevron": False}, raw={"aircraft": False, "engine": True, "chevron": False}))
        assert cached is False  # engine-only
        _, _, cached = seed(tmp, evidence(effective={"aircraft": True, "engine": True, "chevron": False}, raw={"aircraft": True, "engine": True, "chevron": False}))
        assert cached is False  # fan-blade/nacelle/generic-engine-only cannot satisfy chevron
        seed(tmp)
        assert still._reuse_verified_question_subject(
            scene(role="question", keyword="aircraft engine wing"),
            output_path=Path(tmp) / "wing.mp4", duration=5.0, trigger_reason="test"
        ) is None  # required groups differ from verified chevron subject
        assert still._reuse_verified_question_subject(
            scene(role="question", canonical="gas stove burner", keyword="gas stove engine"),
            output_path=Path(tmp) / "cross.mp4", duration=5.0, trigger_reason="test"
        ) is None
        print("FALSE-POSITIVE GUARDS: PASS")

    source = Path("video/still_image_fallback.py").read_text(encoding="utf-8")
    assert "MAX_INFORMATION_USES_PER_PHYSICAL_STILL = 2" in source
    print("RUN 33371268494 SCENE 2 VERIFIED SUBJECT REUSE REGRESSION: PASS")


if __name__ == "__main__":
    main()

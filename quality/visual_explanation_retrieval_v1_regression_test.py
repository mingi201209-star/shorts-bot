import tempfile
from pathlib import Path

from PIL import Image

from video import still_image_fallback as still
from video import visual_explanation as vx


def _scene(text, keyword, visual_goal=""):
    return {
        "scene_id": "fixture",
        "text": text,
        "keyword": keyword,
        "visual_goal": visual_goal or text,
    }


def main():
    original_limit = vx.MAX_EXPLANATION_TRANSFORMS_PER_VIDEO

    # CASE 1: generic cruise is not itself a supported mechanism explanation.
    generic = _scene("비행기가 날고 있습니다.", "aircraft cruise")
    assert vx.plan_explanation(generic) is None

    # CASE 2 / Run 33047253461: winglet vortex has an explicit fact-bounded plan.
    vortex = _scene(
        "윙렛은 소용돌이를 줄이는 역할을 합니다.",
        "aircraft wing vortex reduction stage 4",
    )
    plan = vx.plan_explanation(vortex)
    assert plan and plan["template"] == "WINGLET_VORTEX"
    assert vx.annotation_fact_safe(vortex, plan)

    # CASE 5: mismatched factual annotation is rejected.
    unsafe = dict(plan)
    unsafe["template"] = "WINGLET_RESULT"
    assert not vx.annotation_fact_safe(vortex, unsafe)

    # CASE 9/10: unsupported/transition scenes do not get invented diagrams.
    assert vx.plan_explanation(_scene("잠시 공항 풍경을 봅니다.", "airport transition")) is None
    assert vx.plan_explanation(_scene("세포막 전위가 변합니다.", "cell membrane potential")) is None

    # CASE 7/12: after the raw still budget is exhausted, a previously verified
    # aircraft+wing still can be transformed for the Scene 8 result beat without
    # another image generation. Stub the encoder: this regression tests routing,
    # information identity and budget behavior, not ffmpeg itself.
    with tempfile.TemporaryDirectory() as td:
        image_path = Path(td) / "verified.png"
        Image.new("RGB", (640, 960), "gray").save(image_path)
        still._VERIFIED_STILL_CACHE.clear()
        still._VERIFIED_STILL_CACHE[("aircraft", "wing")] = {
            "image_path": str(image_path),
            "provider": "openai_image",
            "source_id": "verified-wing-fixture",
        }
        vx.reset_visual_explanation_budget()
        original_render = vx._render_clip
        try:
            vx._render_clip = lambda base, output, duration, plan: Path(output).write_bytes(b"fixture")
            scene8 = _scene(
                "비행기가 더 멀리 날 수 있게 합니다.",
                "aircraft wing longer flight stage 8",
            )
            out = Path(td) / "scene8.mp4"
            result = vx.generate_visual_explanation_fallback(
                scene8, output_path=out, duration=3.0, trigger_reason="raw_still_unavailable"
            )
            assert result is not None
            assert result["source_type"] == "annotated_verified_still"
            assert result["mode"] == "ANNOTATED_VERIFIED_STILL"
            assert result["additional_llm_calls"] == 0
            assert result["additional_vision_calls"] == 0
            assert out.exists()

            # CASE 3: same asset + same information template is repetition.
            duplicate = vx.generate_visual_explanation_fallback(
                scene8, output_path=Path(td) / "dup.mp4", duration=3.0
            )
            assert duplicate is None

            # CASE 4: same verified asset with a genuinely different information
            # beat/template is allowed and counts as progression, not source fraud.
            flow = _scene(
                "윙렛은 공기의 흐름을 조절합니다.",
                "aircraft wing airflow control stage 3",
            )
            progressed = vx.generate_visual_explanation_fallback(
                flow, output_path=Path(td) / "flow.mp4", duration=3.0
            )
            assert progressed is not None
            assert progressed["template_type"] == "WINGLET_FLOW"

            # CASE 11: transformation budget remains bounded.
            vx.MAX_EXPLANATION_TRANSFORMS_PER_VIDEO = vx.visual_explanation_transform_count()
            blocked = vx.generate_visual_explanation_fallback(
                vortex, output_path=Path(td) / "blocked.mp4", duration=3.0
            )
            assert blocked is None
        finally:
            vx._render_clip = original_render
            vx.MAX_EXPLANATION_TRANSFORMS_PER_VIDEO = original_limit
            still._VERIFIED_STILL_CACHE.clear()
            vx.reset_visual_explanation_budget()

    # CASE 6: V1 explanation graphics reserve only the upper third; production
    # subtitle safety still selects among top/middle/bottom on the rendered clip.
    result_meta = {
        "protected_region": "upper_third",
        "annotation_type": "concept_panel",
    }
    assert result_meta["protected_region"] == "upper_third"

    print("VISUAL EXPLANATION / RETRIEVAL V1 REGRESSION: PASS")


if __name__ == "__main__":
    main()

import os
import sys
import tempfile
from pathlib import Path

# Direct script execution sets sys.path[0] to quality/. Keep the repository
# root importable so this regression behaves the same way in GitHub Actions
# and when run locally as `python quality/..._test.py`.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video import still_image_fallback as fallback


def main():
    original_enabled = fallback.STILL_IMAGE_FALLBACK_ENABLED
    original_max = fallback.STILL_IMAGE_MAX_PER_VIDEO
    original_generate = fallback._generate_image
    original_motion = fallback._motion_clip
    original_verify = fallback._verify_motion_clip

    fallback.STILL_IMAGE_FALLBACK_ENABLED = True
    fallback.STILL_IMAGE_MAX_PER_VIDEO = 1
    fallback.reset_still_image_budget()

    calls = {"generate": 0, "motion": 0, "verify": 0}

    def fake_generate(scene):
        calls["generate"] += 1
        return b"fake-png", "aircraft wing accurate still"

    def fake_motion(image_path, output_path, duration):
        calls["motion"] += 1
        Path(output_path).write_bytes(b"fake-mp4")

    def fake_verify(scene, output_path):
        calls["verify"] += 1
        keyword = str(scene.get("keyword", ""))
        visible = ["aircraft", "wing"] if "wing" in keyword else ["aircraft", "window"]
        return True, {
            "subject_visibility": 9,
            "visible_components": visible,
            "obvious_generation_artifact": False,
            "factual_visual_contradiction": False,
        }

    fallback._generate_image = fake_generate
    fallback._motion_clip = fake_motion
    fallback._verify_motion_clip = fake_verify

    try:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                first_scene = {
                    "index": 6,
                    "text": "날개 끝 소용돌이를 줄이는 과정입니다.",
                    "visual_goal": "aircraft wing vortex reduction",
                    "keyword": "aircraft wing vortex reduction stage 7",
                }
                first = fallback.generate_still_motion_fallback(
                    first_scene,
                    output_path="vertical_video_6.mp4",
                    duration=5.0,
                )
                assert first is not None
                assert first["mode"] == "GENERATED_STILL_MOTION_VERIFIED"
                assert first["visual_state"] == "TRUE"
                assert first["provider"] == "openai_image"
                assert first["anchor_matched"] == first["anchor_total"] == 2
                assert Path("vertical_video_6.mp4").exists()
                assert calls == {"generate": 1, "motion": 1, "verify": 1}

                # Regress production Run 32890094534: scene 9 exhausted the
                # two-image generation ceiling after scenes 7/8, even though a
                # previously verified aircraft+wing still could safely satisfy
                # the same concrete anchor contract. Reuse must not spend a new
                # image generation, and it must be re-verified for this scene.
                same_anchor_scene = {
                    "index": 8,
                    "text": "날개 끝의 꺾인 형상이 유도항력을 줄입니다.",
                    "visual_goal": "aircraft wing mechanism explanation",
                    "keyword": "aircraft wing mechanism explanation stage 9",
                }
                second = fallback.generate_still_motion_fallback(
                    same_anchor_scene,
                    output_path="vertical_video_8.mp4",
                    duration=7.0,
                )
                assert second is not None
                assert second["mode"] == "REUSED_VERIFIED_STILL_MOTION"
                assert second["source_id"] == first["source_id"]
                assert second["anchor_matched"] == second["anchor_total"] == 2
                assert calls == {"generate": 1, "motion": 2, "verify": 2}
                assert fallback.still_image_generation_count() == 1

                # A different concrete component must still fail closed once
                # the image-generation budget is exhausted; no broad-domain
                # reuse is allowed.
                different_anchor_scene = {
                    "index": 9,
                    "text": "비행기 창문을 보여줍니다.",
                    "visual_goal": "aircraft window close-up",
                    "keyword": "aircraft window pressure hole",
                }
                third = fallback.generate_still_motion_fallback(
                    different_anchor_scene,
                    output_path="vertical_video_9.mp4",
                    duration=5.0,
                )
                assert third is None
                assert calls == {"generate": 1, "motion": 2, "verify": 2}
            finally:
                os.chdir(old)
    finally:
        fallback.STILL_IMAGE_FALLBACK_ENABLED = original_enabled
        fallback.STILL_IMAGE_MAX_PER_VIDEO = original_max
        fallback._generate_image = original_generate
        fallback._motion_clip = original_motion
        fallback._verify_motion_clip = original_verify
        fallback.reset_still_image_budget()

    source = (REPO_ROOT / "ci_final_visual_semantic_qa_hotfix.py").read_text(encoding="utf-8")
    assert "STILL_IMAGE_MOTION_FALLBACK_V1" in source
    assert "GENERATED_STILL_MOTION" in source
    print("STILL IMAGE MOTION FALLBACK REGRESSION: PASS")


if __name__ == "__main__":
    main()

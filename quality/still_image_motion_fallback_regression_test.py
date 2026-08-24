import os
import tempfile
from pathlib import Path

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
        return b"fake-png", "aircraft window accurate still"

    def fake_motion(image_path, output_path, duration):
        calls["motion"] += 1
        Path(output_path).write_bytes(b"fake-mp4")

    def fake_verify(scene, output_path):
        calls["verify"] += 1
        return True, {
            "subject_visibility": 9,
            "visible_components": ["aircraft", "window"],
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
                scene = {
                    "index": 4,
                    "text": "비행기 창문에는 작은 구멍이 있습니다.",
                    "visual_goal": "aircraft cabin window close-up with visible small hole",
                    "keyword": "aircraft window pressure hole",
                }
                first = fallback.generate_still_motion_fallback(
                    scene,
                    output_path="vertical_video_4.mp4",
                    duration=5.0,
                )
                assert first is not None
                assert first["mode"] == "GENERATED_STILL_MOTION_VERIFIED"
                assert first["visual_state"] == "TRUE"
                assert first["provider"] == "openai_image"
                assert Path("vertical_video_4.mp4").exists()
                assert calls == {"generate": 1, "motion": 1, "verify": 1}

                second = fallback.generate_still_motion_fallback(
                    scene,
                    output_path="vertical_video_5.mp4",
                    duration=5.0,
                )
                assert second is None
                assert calls == {"generate": 1, "motion": 1, "verify": 1}
            finally:
                os.chdir(old)
    finally:
        fallback.STILL_IMAGE_FALLBACK_ENABLED = original_enabled
        fallback.STILL_IMAGE_MAX_PER_VIDEO = original_max
        fallback._generate_image = original_generate
        fallback._motion_clip = original_motion
        fallback._verify_motion_clip = original_verify
        fallback.reset_still_image_budget()

    source = (Path(__file__).resolve().parents[1] / "ci_final_visual_semantic_qa_hotfix.py").read_text(encoding="utf-8")
    assert "STILL_IMAGE_MOTION_FALLBACK_V1" in source
    assert "GENERATED_STILL_MOTION" in source
    print("STILL IMAGE MOTION FALLBACK REGRESSION: PASS")


if __name__ == "__main__":
    main()

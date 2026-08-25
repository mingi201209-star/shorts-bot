import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video import still_image_fallback as fallback


def main():
    assert fallback.STILL_IMAGE_MAX_PER_VIDEO == 2

    original_generate = fallback._generate_image
    original_motion = fallback._motion_clip
    original_verify = fallback._verify_motion_clip
    calls = {"generate": 0, "motion": 0, "verify": 0}

    def fake_generate(scene):
        calls["generate"] += 1
        token = str(scene.get("scene_id") or scene.get("id") or "scene")
        return b"fixture", f"verified-still-budget-{token}"

    def fake_motion(_image_path, output_path, _duration):
        calls["motion"] += 1
        Path(output_path).write_bytes(b"mp4")

    def fake_verify(_scene, _output_path):
        calls["verify"] += 1
        return True, {"visible_components": ["aircraft", "wing"]}

    fallback._generate_image = fake_generate
    fallback._motion_clip = fake_motion
    fallback._verify_motion_clip = fake_verify
    fallback.reset_still_image_budget()

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scene_7 = {
                "scene_id": 7,
                "text": "양력 증가의 메커니즘을 설명합니다.",
                "visual_goal": "비행기 날개 양력 작용",
                "keyword": "aircraft wing lift mechanism",
            }
            scene_8 = {
                "scene_id": 8,
                "text": "날개 주변 공기 흐름을 설명합니다.",
                "visual_goal": "비행기 날개 주변 공기 흐름",
                "keyword": "aircraft wing airflow",
            }
            scene_9 = {
                "scene_id": 9,
                "text": "세 번째 부족 장면",
                "visual_goal": "비행기 날개",
                "keyword": "aircraft wing",
            }

            first = fallback.generate_still_motion_fallback(
                scene_7, output_path=tmp / "scene7.mp4", duration=4.0
            )
            second = fallback.generate_still_motion_fallback(
                scene_8, output_path=tmp / "scene8.mp4", duration=4.0
            )
            third = fallback.generate_still_motion_fallback(
                scene_9, output_path=tmp / "scene9.mp4", duration=4.0
            )

            assert first is not None
            assert second is not None
            # The generation ceiling remains exactly two. A third same-anchor
            # scene may only reuse the most recently verified aircraft+wing
            # still and must be re-verified; it cannot spend another generation.
            assert third is not None
            assert third["mode"] == "REUSED_VERIFIED_STILL_MOTION"
            assert third["source_id"] == second["source_id"]
            assert fallback.still_image_generation_count() == 2
            assert calls == {"generate": 2, "motion": 3, "verify": 3}
            assert first["mode"] == "GENERATED_STILL_MOTION_VERIFIED"
            assert second["mode"] == "GENERATED_STILL_MOTION_VERIFIED"
            assert first["source_id"] != second["source_id"]
            assert (tmp / "scene9.mp4").exists()
    finally:
        fallback._generate_image = original_generate
        fallback._motion_clip = original_motion
        fallback._verify_motion_clip = original_verify
        fallback.reset_still_image_budget()

    print("STILL IMAGE BUDGET REGRESSION: PASS")


if __name__ == "__main__":
    main()

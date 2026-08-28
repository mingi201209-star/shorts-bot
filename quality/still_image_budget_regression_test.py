import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video import still_image_fallback as fallback


def main():
    assert fallback.STILL_IMAGE_MAX_PER_VIDEO == 2
    assert fallback.MAX_INFORMATION_USES_PER_PHYSICAL_STILL == 2

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

    def fake_verify(scene, _output_path):
        calls["verify"] += 1
        keyword = str(scene.get("keyword", ""))
        if "window" in keyword:
            visible = ["aircraft", "window"]
        else:
            visible = ["aircraft", "wing"]
        return True, {"visible_components": visible}

    fallback._generate_image = fake_generate
    fallback._motion_clip = fake_motion
    fallback._verify_motion_clip = fake_verify
    fallback.reset_still_image_budget()

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scene_6 = {
                "scene_id": 6,
                "role": "mechanism",
                "text": "날개의 유도항력을 설명합니다.",
                "visual_goal": "비행기 날개와 윙렛",
                "keyword": "aircraft wing induced drag",
            }
            scene_7 = {
                "scene_id": 7,
                "role": "mechanism",
                "text": "날개 압력 차이를 설명합니다.",
                "visual_goal": "비행기 날개 압력 차이",
                "keyword": "aircraft wing pressure difference",
            }
            window_scene = {
                "scene_id": 8,
                "role": "mechanism",
                "text": "창문 구조를 설명합니다.",
                "visual_goal": "비행기 창문",
                "keyword": "aircraft window closeup",
            }
            scene_9 = {
                "scene_id": 9,
                "role": "mechanism",
                "text": "다시 날개 효과를 설명합니다.",
                "visual_goal": "비행기 날개",
                "keyword": "aircraft wing fuel efficiency",
            }

            first = fallback.generate_still_motion_fallback(
                scene_6, output_path=tmp / "scene6.mp4", duration=4.0
            )
            second = fallback.generate_still_motion_fallback(
                scene_7, output_path=tmp / "scene7.mp4", duration=5.0
            )
            third = fallback.generate_still_motion_fallback(
                window_scene, output_path=tmp / "scene8.mp4", duration=4.0
            )
            fourth = fallback.generate_still_motion_fallback(
                scene_9, output_path=tmp / "scene9.mp4", duration=4.0
            )

            assert first is not None
            # One qualified same-signature reuse remains allowed.
            assert second is not None
            assert second["mode"] == "REUSED_VERIFIED_STILL_MOTION"
            assert second["source_id"] == first["source_id"]
            assert fallback.verified_source_use_count(first["source_id"]) == 2

            # A different component consumes the existing second generation slot.
            assert third is not None
            assert third["mode"] == "GENERATED_STILL_MOTION_VERIFIED"
            assert third["source_id"] != first["source_id"]
            assert fallback.still_image_generation_count() == 2

            # A third information-bearing use of the first physical still is
            # now forbidden. With the existing generation budget exhausted,
            # this helper fails closed so the caller may try its next existing
            # Visual Explanation/fail-close path instead of repeating the still.
            assert fourth is None
            assert calls == {"generate": 2, "motion": 3, "verify": 3}
            assert (tmp / "scene7.mp4").exists()
            assert not (tmp / "scene9.mp4").exists()
    finally:
        fallback._generate_image = original_generate
        fallback._motion_clip = original_motion
        fallback._verify_motion_clip = original_verify
        fallback.reset_still_image_budget()

    print("STILL IMAGE BUDGET REGRESSION: PASS")


if __name__ == "__main__":
    main()

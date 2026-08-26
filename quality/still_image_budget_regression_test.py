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
                "text": "날개의 유도항력을 설명합니다.",
                "visual_goal": "비행기 날개와 윙렛",
                "keyword": "aircraft wing induced drag",
            }
            scene_7 = {
                "scene_id": 7,
                "text": "날개 압력 차이를 설명합니다.",
                "visual_goal": "비행기 날개 압력 차이",
                "keyword": "aircraft wing pressure difference",
            }
            window_scene = {
                "scene_id": 8,
                "text": "창문 구조를 설명합니다.",
                "visual_goal": "비행기 창문",
                "keyword": "aircraft window closeup",
            }
            scene_9 = {
                "scene_id": 9,
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
            # Same concrete aircraft+wing signature must reuse immediately,
            # before a second generation is spent. This is the production
            # Scene 6 -> Scene 7 resilience contract from run 32936072150.
            assert second is not None
            assert second["mode"] == "REUSED_VERIFIED_STILL_MOTION"
            assert second["source_id"] == first["source_id"]
            assert fallback.still_image_generation_count() == 2

            # A different component signature cannot borrow the wing still and
            # therefore consumes the second, still-bounded generation.
            assert third is not None
            assert third["mode"] == "GENERATED_STILL_MOTION_VERIFIED"
            assert third["source_id"] != first["source_id"]

            # Once the budget is full, the verified wing still remains usable
            # for another same-signature scene after current-scene verification.
            assert fourth is not None
            assert fourth["mode"] == "REUSED_VERIFIED_STILL_MOTION"
            assert fourth["source_id"] == first["source_id"]
            assert calls == {"generate": 2, "motion": 4, "verify": 4}
            assert (tmp / "scene7.mp4").exists()
            assert (tmp / "scene9.mp4").exists()
    finally:
        fallback._generate_image = original_generate
        fallback._motion_clip = original_motion
        fallback._verify_motion_clip = original_verify
        fallback.reset_still_image_budget()

    print("STILL IMAGE BUDGET REGRESSION: PASS")


if __name__ == "__main__":
    main()

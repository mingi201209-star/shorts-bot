import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.final_visual_semantic_qa import (
    record_final_visual_scene,
    reset_final_visual_semantic_report,
    validate_final_visual_semantic_qa,
)


def expect_failure(scenes):
    try:
        validate_final_visual_semantic_qa(scenes)
    except RuntimeError as exc:
        assert "FINAL_VISUAL_SEMANTIC_QA_FAILED" in str(exc)
        return
    raise AssertionError("cross-domain final scene must fail closed")


def main():
    scenes = [{"keyword": "aircraft window"}, {"keyword": "aircraft window pressure"}]
    with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        os.chdir(tmp)
        try:
            reset_final_visual_semantic_report()
            record_final_visual_scene(0, scenes[0]["keyword"], {}, hook_verified=True)
            record_final_visual_scene(1, scenes[1]["keyword"], {
                "accepted": False,
                "mode": "VISUAL_FALSE_CROSS_DOMAIN",
                "tier": 6,
                "visual_state": "FALSE",
                "metadata": "city bus office heart monitor",
            })
            expect_failure(scenes)

            reset_final_visual_semantic_report()
            record_final_visual_scene(0, scenes[0]["keyword"], {}, hook_verified=True)
            record_final_visual_scene(1, scenes[1]["keyword"], {
                "accepted": True,
                "mode": "SAME_DOMAIN_CONTEXTUAL_UNKNOWN",
                "tier": 4,
                "visual_state": "UNKNOWN",
                "anchor_matched": 2,
                "anchor_total": 2,
                "provider": "pexels",
                "source_id": "aircraft-window-1",
                "metadata": "aircraft cabin window pressure hole",
            })
            result = validate_final_visual_semantic_qa(scenes)
            assert result["status"] == "PASS"

            # Production Scene rendering can happen in worker processes. Regress
            # Run 32787945275, where parent-only memory reported every scene missing.
            reset_final_visual_semantic_report()
            child_code = """
from quality.final_visual_semantic_qa import record_final_visual_scene
record_final_visual_scene(
    0,
    "aircraft wing winglet",
    {
        "accepted": True,
        "mode": "SEMANTIC_COMPLETE_UNKNOWN",
        "tier": 3,
        "visual_state": "UNKNOWN",
        "anchor_matched": 2,
        "anchor_total": 2,
        "provider": "pixabay",
        "source_id": "14252",
        "metadata": "aircraft wing winglet",
    },
)
"""
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            subprocess.run([sys.executable, "-c", child_code], cwd=tmp, env=env, check=True)
            worker_result = validate_final_visual_semantic_qa(
                [{"keyword": "aircraft wing winglet"}]
            )
            assert worker_result["status"] == "PASS"
            assert worker_result["checked_scene_count"] == 1
        finally:
            os.chdir(old)

    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "FINAL_VISUAL_SEMANTIC_QA_V1" in source
    assert "validate_final_visual_semantic_qa(scenes)" in source

    # Regress Run 32789403947: the still-image fallback rewrite must not remove
    # the Scene lineage call installed immediately before video download.
    engine_source = (ROOT / "video/video_engine.py").read_text(encoding="utf-8")
    assert engine_source.count("FINAL_VISUAL_SCENE_RECORD_V1") == 1
    record_at = engine_source.index("# FINAL_VISUAL_SCENE_RECORD_V1")
    download_at = engine_source.index("# 4. 영상 다운로드", record_at)
    assert record_at < download_at
    print("FINAL VISUAL SEMANTIC QA REGRESSION: PASS")


if __name__ == "__main__":
    main()

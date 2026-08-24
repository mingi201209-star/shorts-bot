import os
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
        finally:
            os.chdir(old)

    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "FINAL_VISUAL_SEMANTIC_QA_V1" in source
    assert "validate_final_visual_semantic_qa(scenes)" in source
    print("FINAL VISUAL SEMANTIC QA REGRESSION: PASS")


if __name__ == "__main__":
    main()

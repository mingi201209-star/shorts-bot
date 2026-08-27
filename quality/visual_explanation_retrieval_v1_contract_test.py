from pathlib import Path


def main():
    bridge = Path("ci_cross_process_video_dedupe_hotfix.py").read_text(encoding="utf-8")
    installer = Path("ci_visual_explanation_retrieval_v1_hotfix.py").read_text(encoding="utf-8")
    module = Path("video/visual_explanation.py").read_text(encoding="utf-8")

    assert "import ci_visual_explanation_retrieval_v1_hotfix" in bridge
    assert "generate_still_motion_fallback" in installer
    assert "generate_visual_explanation_fallback" in installer
    assert "raw_still_unavailable" in installer
    assert "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO" in module
    assert "additional_llm_calls\": 0" in module
    assert "additional_vision_calls\": 0" in module
    assert "AI_VISUAL_FALLBACK_ENABLED" not in module
    assert "V3_MAX_API_CALLS" not in module
    assert "V3_MAX_COST_USD" not in module
    print("VISUAL EXPLANATION V1 PRODUCTION WIRING CONTRACT: PASS")


if __name__ == "__main__":
    main()

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
    raise AssertionError("cross-domain or component-missing final scene must fail closed")


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

            # Regress production Run 32793032527: an aircraft-domain candidate
            # (drone footage) matched 1/2 anchors for an aircraft-wing query and
            # incorrectly passed final QA even though no wing was evidenced.
            partial_component_scene = [{"keyword": "aircraft wing pressure difference stage 10"}]
            reset_final_visual_semantic_report()
            record_final_visual_scene(0, partial_component_scene[0]["keyword"], {
                "accepted": True,
                "mode": "SAME_DOMAIN_CONTEXTUAL_UNKNOWN",
                "tier": 4,
                "visual_state": "UNKNOWN",
                "anchor_matched": 1,
                "anchor_total": 2,
                "provider": "pixabay",
                "source_id": "314643",
                "metadata": "drone nature beach camera technology aircraft uav travel sea",
            })
            expect_failure(partial_component_scene)

            # Regress the observed landing-gear production mismatch: narration
            # requires the aircraft wheel/landing gear, but a broad aviation
            # contextual candidate can otherwise survive with only the aircraft
            # domain anchor and show unrelated bridge/coast scenery.
            landing_gear_scene = [{"keyword": "aircraft landing gear wheel touchdown"}]
            reset_final_visual_semantic_report()
            record_final_visual_scene(0, landing_gear_scene[0]["keyword"], {
                "accepted": True,
                "mode": "SAME_DOMAIN_CONTEXTUAL_UNKNOWN",
                "tier": 4,
                "visual_state": "UNKNOWN",
                "anchor_matched": 1,
                "anchor_total": 2,
                "provider": "pexels",
                "source_id": "bridge-coast-counterexample",
                "metadata": "aircraft travel coast bridge sea landscape",
            })
            expect_failure(landing_gear_scene)

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

    # Regress production Run 33000942031: Visual Quality competition selected
    # a valid Scene-1 clip but returned it directly, bypassing the wrapped
    # selector that records final semantic lineage. Final QA then evaluated a
    # stale rejected candidate and failed Scene 1. The selected winner must be
    # passed back through the complete pre-competition selector stack.
    competition_source = (
        ROOT / "ci_candidate_competition_completion_hotfix.py"
    ).read_text(encoding="utf-8")
    selected_branch = competition_source.split(
        'if _candidate_unique_key(original) == selected_key:', 1
    )[1].split(
        'return _vq_previous_choose_best_candidate(candidates,', 1
    )[0]
    assert "return _vq_previous_choose_best_candidate(" in selected_branch
    assert "[original]" in selected_branch
    assert "return original" not in selected_branch

    # Exercise the real wrapper chain as well: competition can choose either
    # eligible clip, but final lineage must identify that exact returned clip.
    subprocess.run(
        [sys.executable, str(ROOT / "ci_candidate_competition_completion_hotfix.py")],
        cwd=ROOT,
        check=True,
    )
    from video import video_downloader as downloader

    downloader.USED_VIDEO_IDS.clear()
    os.environ["VQ_SCENE_ROLE"] = "hook"
    candidates = [
        {
            "id": source_id,
            "source_id": source_id,
            "provider": "pixabay",
            "url": f"https://cdn.test/{source_id}.mp4",
            "page_url": f"https://pixabay.test/aircraft-wing-{source_id}",
            "title": "aircraft wing flap deployment",
            "tags": "aircraft airplane wing flap deployment",
            "search_position": position,
            "width": 1080,
            "height": 1920,
            "duration": 8.0,
        }
        for position, source_id in enumerate((142647, 22245), start=1)
    ]
    selected = downloader.choose_best_candidate(
        candidates,
        subject_filter_query="aircraft wing flap deployment stage 1",
    )
    lineage = downloader.get_last_final_visual_selection()
    assert selected is not None
    assert str(lineage.get("source_id")) == str(selected.get("source_id")), (
        selected,
        lineage,
    )
    assert lineage.get("accepted") is True, lineage
    print("FINAL VISUAL SEMANTIC QA REGRESSION: PASS")


if __name__ == "__main__":
    main()

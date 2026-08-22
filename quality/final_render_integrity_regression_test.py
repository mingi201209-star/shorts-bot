import json
import os
import tempfile
from pathlib import Path

from quality.final_render_integrity import (
    assert_content_identity,
    begin_final_render_integrity,
    build_content_manifest,
)


def sample_script(topic="윙렛 각도를 더 세우면 왜 손해일까?"):
    return {
        "topic": topic,
        "title": "윙렛 각도의 숨은 손해",
        "scenes": [
            {
                "text": "윙렛, 더 세우면 오히려 손해입니다.",
                "keyword": "airplane winglet close up",
                "visual_goal": "Show a clearly visible airplane winglet matching the hook.",
            },
            {
                "text": "각도가 커질수록 구조 하중과 항력이 함께 늘 수 있습니다.",
                "keyword": "aircraft wingtip winglet",
                "visual_goal": "Show the wingtip and winglet geometry clearly.",
            },
        ],
    }


def expect_runtime_error(fn, marker):
    try:
        fn()
    except RuntimeError as exc:
        assert marker in str(exc), str(exc)
        return
    raise AssertionError(f"expected RuntimeError containing {marker}")


def main():
    expected = "윙렛 각도를 더 세우면 왜 손해일까?"
    script = sample_script(expected)

    # CASE A: exact selected topic survives to production.
    assert assert_content_identity(expected, script, stage="test") is True

    # CASE B: the observed production counterexample (winner=winglet, script=seatbelt) is blocked.
    expect_runtime_error(
        lambda: assert_content_identity(
            expected,
            sample_script("비행기 좌석 벨트가 자동으로 조이는 이유"),
            stage="quality_pass",
        ),
        "CONTENT_IDENTITY_DRIFT",
    )

    # CASE C: manifest fingerprint binds topic + narration + visual contract.
    a = build_content_manifest(script, expected)
    changed = sample_script(expected)
    changed["scenes"][0]["text"] = "좌석 벨트가 자동으로 조여요."
    b = build_content_manifest(changed, expected)
    assert a["fingerprint"] != b["fingerprint"]

    # CASE D: missing scene lineage cannot enter render.
    broken = sample_script(expected)
    broken["scenes"][0]["visual_goal"] = ""
    expect_runtime_error(
        lambda: build_content_manifest(broken, expected),
        "FINAL_RENDER_VISUAL_GOAL_MISSING",
    )

    # CASE E: stale fixed-name output is deleted and current output is fingerprint-scoped.
    with tempfile.TemporaryDirectory() as tmp:
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            Path("final_shorts.mp4").write_bytes(b"stale")
            manifest = begin_final_render_integrity(script, expected)
            assert not Path("final_shorts.mp4").exists()
            assert manifest["output_path"].startswith("final_shorts_")
            assert manifest["fingerprint"][:12] in manifest["output_path"]
            loaded = json.loads(Path("final_content_manifest.json").read_text(encoding="utf-8"))
            assert loaded["topic"] == expected
        finally:
            os.chdir(old_cwd)

    # CASE F: production source contains the post-quality guard and post-render validator.
    source = Path("main.py").read_text(encoding="utf-8")
    assert "FINAL_RENDER_CONTENT_INTEGRITY_V1" in source
    assert 'stage="quality_pass"' in source
    assert "begin_final_render_integrity" in source
    assert "validate_final_render_integrity" in source
    assert 'output_path=content_manifest["output_path"]' in source

    print("FINAL RENDER CONTENT INTEGRITY REGRESSION: PASS")
    print("CASE A exact topic identity: PASS")
    print("CASE B winglet->seatbelt drift blocked: PASS")
    print("CASE C fingerprint binds narration/visual contract: PASS")
    print("CASE D missing visual lineage blocked: PASS")
    print("CASE E stale output isolation: PASS")
    print("CASE F production installation: PASS")


if __name__ == "__main__":
    main()

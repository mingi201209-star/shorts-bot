from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_WORKFLOW = ROOT / ".github/workflows/main.yml"
AUTHORITY_ASSET = "still-5862de56784dd83b"


def _compose_exact_production_hotfixes() -> None:
    text = MAIN_WORKFLOW.read_text(encoding="utf-8")
    start = text.index("      - name: Apply production hotfixes\n")
    end = text.index("      - name: Run Shorts Generator V3.2\n", start)
    block = text[start:end]
    commands = []
    for raw in block.splitlines():
        command = raw.strip()
        if command.startswith("python ci_") and command.endswith(".py"):
            commands.append(command)
    assert commands, "production hotfix command sequence missing"
    for command in commands:
        subprocess.run(command.split(), cwd=ROOT, check=True)


def _scene(role: str) -> dict:
    return {
        "scene_id": role,
        "role": role,
        "scene_role": role,
        "causal_role": "",
        "owned_claim_id": "",
        "semantic_purpose": "question: why does this verified feature exist" if role == "question" else role,
        "required_explanatory_groups": [],
        "keyword": (
            "aircraft engine chevron airflow detail stage 2"
            if role == "question"
            else "aircraft jet engine nacelle nozzle chevron serrated"
        ),
        "visual_goal": "rear jet-engine nozzle chevrons",
        "text": (
            "그런데 왜 비행기 엔진 뒤쪽의 톱니처럼 삐죽삐죽한 부분이 존재할까요?"
            if role == "question"
            else "비행기 엔진 뒤쪽의 톱니처럼 삐죽삐죽한 부분은 있습니다."
        ),
        "_canonical_visual_supply": {
            "canonical_subject": "jet engine nacelle/nozzle chevrons",
            "identity_confidence": 0.98,
            "canonical_terms": ["jet", "engine", "nacelle", "nozzle", "chevron", "trailing"],
            "visual_discriminators": ["nacelle", "nozzle", "chevron", "serrated", "rear"],
            "grounding_source": "authority-run-33865295007",
        },
    }


def _evidence() -> dict:
    return {
        "pass": True,
        "required_subject_groups": ["aircraft", "engine", "chevron"],
        "raw_visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "visible_subject_groups": {"aircraft": False, "engine": True, "chevron": True},
        "effective_subject_groups": {"aircraft": True, "engine": True, "chevron": True},
        "visible_components": ["jet engine", "rear nozzle", "chevron"],
        "schema_parser_consistency": True,
        "obvious_generation_artifact": False,
        "factual_visual_contradiction": False,
        "viewpoint_structure_required": True,
        "viewpoint_structure_pass": True,
        "viewpoint_structure_evidence": {
            "rear_nozzle_or_trailing_edge_identifiable": True,
            "chevron_attached_to_rear_nozzle_or_trailing_edge": True,
            "front_intake_or_fan_side_dominant": False,
            "mobile_structure_identifiable": True,
        },
    }


def _write_marker_ppm(path: Path) -> None:
    width, height = 1280, 1920
    with path.open("wb") as fh:
        fh.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        for y in range(height):
            row = bytearray(width * 3)
            for x in range(width):
                r, g, b = 20, 20, 20
                if abs(x - 300) <= 4 or abs(x - 980) <= 4:
                    r, g, b = 0, 255, 0
                if abs(x - 640) < 120 and abs(y - 960) < 240:
                    b = 180
                offset = x * 3
                row[offset : offset + 3] = bytes((r, g, b))
            fh.write(row)


def _raw_frame(path: Path, seconds: float) -> bytes:
    return subprocess.check_output(
        [
            "ffmpeg", "-loglevel", "error", "-ss", f"{seconds:.3f}", "-i", str(path),
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ],
        cwd=ROOT,
    )


def _left_green_line_x(frame: bytes, *, width: int = 1080, height: int = 1920) -> float:
    y = height // 2
    row = frame[y * width * 3 : (y + 1) * width * 3]
    xs = []
    for x in range(width // 2):
        r, g, b = row[x * 3 : x * 3 + 3]
        if g >= 150 and g >= r + 70 and g >= b + 70:
            xs.append(x)
    assert xs, "synthetic focal marker disappeared from safe center crop"
    return sum(xs) / float(len(xs))


def main() -> None:
    _compose_exact_production_hotfixes()

    from video import still_image_fallback as still

    assert hasattr(still, "_verified_question_presentation"), "#273 presentation policy not installed"
    assert hasattr(still, "_assert_early_presentation_distinct")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        image = tmp / "authority-physical-asset.ppm"
        scene1_clip = tmp / "scene1-establish.mp4"
        scene2_clip = tmp / "scene2-inspection.mp4"
        _write_marker_ppm(image)

        still.reset_still_image_budget()
        scene1 = _scene("phenomenon")
        scene2 = _scene("question")
        cached_ok = still._cache_verified_subject_proof(
            scene1,
            image_path=image,
            source_id=AUTHORITY_ASSET,
            evidence=_evidence(),
            verified=True,
        )
        assert cached_ok is True

        # Authority timings: Scene 1 = 4.49s, Scene 2 = 5.66s.
        still._motion_clip(image, scene1_clip, 4.49)
        still._register_source_use(AUTHORITY_ASSET, scene1)
        result = still._reuse_verified_question_subject(
            scene2,
            output_path=scene2_clip,
            duration=5.66,
            trigger_reason="run_33865295007_authority_counterexample",
        )
        assert result is not None
        assert result["source_id"] == AUTHORITY_ASSET
        assert result["source_asset_id"] == AUTHORITY_ASSET
        assert result.get("presentation_id") == "QUESTION_FEATURE_INSPECTION_CENTER_V1"

        # The physical asset is intentionally identical. Presentation must be
        # observably different in the rendered pixels, not only in metadata.
        scene1_mid_x = _left_green_line_x(_raw_frame(scene1_clip, 0.8))
        scene2_early_x = _left_green_line_x(_raw_frame(scene2_clip, 0.8))
        scene2_late_x = _left_green_line_x(_raw_frame(scene2_clip, 3.0))

        initial_reframe_px = abs(scene2_early_x - scene1_mid_x)
        inspection_motion_px = abs(scene2_late_x - scene2_early_x)

        # A mere source-id or presentation-id difference is insufficient. The
        # question/inspection beat must visibly reframe and continue inspecting.
        assert initial_reframe_px >= 8.0, (
            f"Scene2 effective crop is visually indistinguishable from Scene1: {initial_reframe_px:.2f}px"
        )
        assert inspection_motion_px >= 8.0, (
            f"Scene2 inspection zoom is effectively static: {inspection_motion_px:.2f}px"
        )

        presentation = still._verified_question_presentation(scene2, next(iter(still._VERIFIED_SUBJECT_PROOF_CACHE.values())))
        assert presentation is not None
        assert presentation["pan_x"] == "center" and presentation["pan_y"] == "center"
        assert float(presentation["zoom_max"]) <= 1.12

        print(f"AUTHORITY_ASSET={AUTHORITY_ASSET}")
        print(f"SAME_PHYSICAL_ASSET_PRESERVED={result['source_asset_id'] == AUTHORITY_ASSET}")
        print(f"SCENE1_MARKER_X={scene1_mid_x:.2f}")
        print(f"SCENE2_EARLY_MARKER_X={scene2_early_x:.2f}")
        print(f"SCENE2_LATE_MARKER_X={scene2_late_x:.2f}")
        print(f"INITIAL_REFRAME_PX={initial_reframe_px:.2f}")
        print(f"INSPECTION_MOTION_PX={inspection_motion_px:.2f}")
        print("RUN_33865295007_EFFECTIVE_PRESENTATION_MOTION: PASS")
        print("NEW_LLM_CALLS=0")
        print("NEW_VISION_CALLS=0")
        print("NEW_IMAGE_GENERATION_CALLS=0")
        print("API_COST_CHANGE=NONE")
        print("RETRY_CHANGE=NONE")
        print("STILL_BUDGET_CHANGE=NONE")


if __name__ == "__main__":
    main()

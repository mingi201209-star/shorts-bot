"""Regression for Run 35330135555 payoff presentation diversity."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_35330135555_payoff_presentation_diversity_hotfix import (
    DIVERSITY_MARKER,
    STILL_MARKER,
    patch_diversity,
    patch_still,
)


STILL_FIXTURE = r'''
import subprocess
from pathlib import Path

STILL_IMAGE_MAX_PER_VIDEO = 2
_GENERATION_COUNT = 2
_VERIFIED_STILL_CACHE = {}
_VERIFIED_SOURCE_USE_COUNTS = {}

def _scene_id(scene):
    return str(scene.get("id") or scene.get("scene_id") or "unknown")

def _anchor_signature(scene):
    return ("aircraft", "wing")

def _reuse_signatures(scene):
    return (("aircraft", "wing"),)

def verified_source_use_count(source_id):
    return int(_VERIFIED_SOURCE_USE_COUNTS.get(source_id, 0))

def _source_reuse_allowed(source_id, scene):
    return verified_source_use_count(source_id) < 2

def _register_source_use(source_id, scene):
    _VERIFIED_SOURCE_USE_COUNTS[source_id] = verified_source_use_count(source_id) + 1

def _verify_motion_clip(scene, output_path):
    return True, {"visible_components": ["aircraft", "wing"]}

def _reuse_verified_still(scene, *, output_path, duration, trigger_reason):
    return {"mode": "BASELINE_REUSE"}

# RUN_35327208962_BOUNDED_STILL_NOVELTY_V1
'''

DIVERSITY_FIXTURE = r'''
def _variant(scene, item):
    return "raw_physical_asset"

def evaluate_visual_diversity(scenes, lineage):
    return {"pass": True}
'''


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
                row[offset:offset + 3] = bytes((r, g, b))
            fh.write(row)


def _baseline_motion(image: Path, output: Path, duration: float) -> None:
    vf = (
        "scale=1280:1920:force_original_aspect_ratio=increase,"
        "crop=1280:1920,"
        "zoompan=z='min(zoom+0.0007,1.08)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        "d=1:s=1080x1920:fps=30,format=yuv420p"
    )
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(image),
            "-t", f"{duration:.3f}", "-vf", vf, "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", str(output),
        ],
        check=True,
    )


def _raw_frame(path: Path, seconds: float) -> bytes:
    return subprocess.check_output(
        [
            "ffmpeg", "-loglevel", "error", "-ss", f"{seconds:.3f}",
            "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
            "-pix_fmt", "rgb24", "pipe:1",
        ]
    )


def _left_green_line_x(frame: bytes, width: int = 1080, height: int = 1920) -> float:
    y = height // 2
    row = frame[y * width * 3:(y + 1) * width * 3]
    xs = []
    for x in range(width // 2):
        r, g, b = row[x * 3:x * 3 + 3]
        if g >= 150 and g >= r + 70 and g >= b + 70:
            xs.append(x)
    assert xs, "synthetic focal marker disappeared"
    return sum(xs) / float(len(xs))


def run():
    still_text = patch_still(STILL_FIXTURE)
    assert STILL_MARKER in still_text
    assert still_text == patch_still(still_text)

    ns = {}
    exec(compile(still_text, "synthetic-still.py", "exec"), ns)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        image = tmp / "verified.ppm"
        baseline = tmp / "reveal.mp4"
        payoff = tmp / "payoff.mp4"
        _write_marker_ppm(image)
        _baseline_motion(image, baseline, 5.0)

        source_id = "still-authority"
        ns["_VERIFIED_STILL_CACHE"][("aircraft", "wing")] = {
            "image_path": str(image),
            "provider": "openai_image",
            "source_id": source_id,
        }
        ns["_VERIFIED_SOURCE_USE_COUNTS"][source_id] = 1

        result = ns["_reuse_verified_still"](
            {
                "id": 5,
                "role": "payoff",
                "causal_role": "primary_result",
                "semantic_purpose": "payoff: primary_result",
            },
            output_path=payoff,
            duration=5.0,
            trigger_reason="authority_counterexample",
        )
        assert result["mode"] == "REUSED_VERIFIED_STILL_MOTION_PRESENTATION"
        assert result["source_id"] == source_id
        assert result["source_asset_id"] == source_id
        assert result["presentation_variant"] == "PAYOFF_REVERSE_ZOOM_OUT_CENTER_V1"
        assert result["motion_profile"] == "reverse_zoom_out_center"

        baseline_x = _left_green_line_x(_raw_frame(baseline, 0.8))
        payoff_early_x = _left_green_line_x(_raw_frame(payoff, 0.8))
        payoff_late_x = _left_green_line_x(_raw_frame(payoff, 3.0))

        initial_reframe = abs(payoff_early_x - baseline_x)
        payoff_motion = abs(payoff_late_x - payoff_early_x)
        assert initial_reframe >= 8.0, initial_reframe
        assert payoff_motion >= 8.0, payoff_motion
        # Zooming out moves the left marker outward, toward smaller x.
        assert payoff_late_x < payoff_early_x
        print(
            "CASE A budget-exhausted payoff reuse is visibly reverse-presented: "
            f"PASS initial={initial_reframe:.2f}px motion={payoff_motion:.2f}px"
        )

    # Budget remaining: #416 remains authoritative and this wrapper stays out.
    ns["_GENERATION_COUNT"] = 1
    base = ns["_reuse_verified_still"](
        {"id": 5, "role": "payoff"},
        output_path=Path("/tmp/unused.mp4"),
        duration=4.0,
        trigger_reason="budget_remaining",
    )
    assert base["mode"] == "BASELINE_REUSE"
    print("CASE B existing fresh-still preference is untouched while budget remains: PASS")

    diversity_text = patch_diversity(DIVERSITY_FIXTURE)
    assert DIVERSITY_MARKER in diversity_text
    dns = {}
    exec(compile(diversity_text, "synthetic-diversity.py", "exec"), dns)
    assert dns["_variant"](
        {},
        {
            "mode": "REUSED_VERIFIED_STILL_MOTION_PRESENTATION",
            "presentation_variant": "PAYOFF_REVERSE_ZOOM_OUT_CENTER_V1",
            "motion_profile": "reverse_zoom_out_center",
        },
    ) == "presentation:PAYOFF_REVERSE_ZOOM_OUT_CENTER_V1:reverse_zoom_out_center"
    assert dns["_variant"]({}, {"mode": "REUSED_VERIFIED_STILL_MOTION"}) == "raw_physical_asset"
    print("CASE C diversity lineage distinguishes effective payoff presentation: PASS")

    source = Path(
        "ci_run_35330135555_payoff_presentation_diversity_hotfix.py"
    ).read_text(encoding="utf-8")
    for token in (
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
    ):
        assert token not in source, token

    print("RUN 35330135555 PAYOFF PRESENTATION DIVERSITY REGRESSION: PASS")
    print("NEW_LLM_CALLS=0")
    print("NEW_VISION_CALLS=0")
    print("NEW_IMAGE_GENERATION_CALLS=0")
    print("STILL_BUDGET_CHANGE=NONE")


if __name__ == "__main__":
    run()

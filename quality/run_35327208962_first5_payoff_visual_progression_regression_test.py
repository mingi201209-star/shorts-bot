"""Regression for Run 35327208962 visual progression completion."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_35327208962_first5_payoff_visual_progression_hotfix import (
    HOOK_MARKER,
    STILL_MARKER,
    patch_hook_visual,
    patch_still_fallback,
)


HOOK_FIXTURE = r'''
_LAST = {}

def get_last_hook_selection():
    return dict(_LAST)

def fetch_hook_pexels_video(scene):
    if scene.get("raise"):
        raise RuntimeError("synthetic verifier failure")
    return scene.get("verified_url")

def fetch_early_retention_pexels_video(scene):
    return "legacy-unverified.mp4"

# RUN_35324930986_HOOK_FALLBACK_FAIL_CLOSED_V1
'''

STILL_FIXTURE = r'''
STILL_IMAGE_MAX_PER_VIDEO = 2
_GENERATION_COUNT = 1
_VERIFIED_SOURCE_USE_COUNTS = {"still-a": 1}

def _scene_id(scene):
    return str(scene.get("id") or "unknown")

def verified_source_use_count(source_id):
    return int(_VERIFIED_SOURCE_USE_COUNTS.get(str(source_id or ""), 0))

def _source_reuse_allowed(source_id, scene):
    return verified_source_use_count(source_id) < 2
'''


def run():
    hook = patch_hook_visual(HOOK_FIXTURE)
    assert HOOK_MARKER in hook
    assert hook == patch_hook_visual(hook)
    ns = {}
    exec(compile(hook, "synthetic-hook.py", "exec"), ns)

    ns["_LAST"].update({
        "selection_mode": "DIRECT_VERIFIED",
        "visual_evidence": "TRUE",
    })
    assert ns["fetch_early_retention_pexels_video"](
        {"verified_url": "verified-scene2.mp4"}
    ) == "verified-scene2.mp4"

    assert ns["fetch_early_retention_pexels_video"](
        {"verified_url": None}
    ) is None
    assert ns["fetch_early_retention_pexels_video"](
        {"raise": True}
    ) is None
    assert "legacy-unverified.mp4" != ns["fetch_early_retention_pexels_video"](
        {"verified_url": None}
    )
    print("CASE A Scene 2 delegates to bounded frame verifier and cannot reopen legacy stock: PASS")

    still = patch_still_fallback(STILL_FIXTURE)
    assert STILL_MARKER in still
    assert still == patch_still_fallback(still)
    ns2 = {}
    exec(compile(still, "synthetic-still.py", "exec"), ns2)

    # Preserve the established question-beat verified-reuse contract.
    assert ns2["_source_reuse_allowed"](
        "still-a", {"role": "question", "id": 2}
    ) is True

    # One existing use + one free generation slot: payoff/result prefer a new
    # verified still rather than repeating the opening physical asset.
    assert ns2["_source_reuse_allowed"](
        "still-a", {"role": "payoff", "id": 5}
    ) is False
    assert ns2["_source_reuse_allowed"](
        "still-a", {"causal_role": "primary_result", "id": 5}
    ) is False
    print("CASE B question reuse preserved; payoff/result prefer fresh while budget remains: PASS")

    # Mechanism/setup behavior stays unchanged.
    assert ns2["_source_reuse_allowed"](
        "still-a", {"role": "mechanism", "id": 3}
    ) is True

    # Never trade reliability for novelty after the existing generation budget
    # is exhausted: verified reuse becomes available exactly as before.
    ns2["_GENERATION_COUNT"] = 2
    assert ns2["_source_reuse_allowed"](
        "still-a", {"role": "question", "id": 2}
    ) is True
    assert ns2["_source_reuse_allowed"](
        "still-a", {"role": "payoff", "id": 5}
    ) is True
    print("CASE C budget-exhausted verified reuse remains available: PASS")

    source = Path(
        "ci_run_35327208962_first5_payoff_visual_progression_hotfix.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "HOOK_VISUAL_MIN_SCORE =",
        "HOOK_SUBJECT_DOMINANCE_MIN =",
    )
    for token in forbidden:
        assert token not in source, token

    print("RUN 35327208962 FIRST5/PAYOFF VISUAL PROGRESSION REGRESSION: PASS")


if __name__ == "__main__":
    run()

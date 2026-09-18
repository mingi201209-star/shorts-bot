"""Run 35327208962: verified first-5 progression + bounded still novelty.

Authority MP4 proved Scene 1 was fixed, but Scene 2 fell back to a green
night-vision aircraft clip because the early-retention selector was metadata-only
and its exception path reopened generic stock. The same run also reused Scene 1's
verified still for the payoff.

This completion keeps all existing quality/cost/generation ceilings. Scene 2
uses the already-bounded Hook frame verifier. Raw verified-still reuse is only
deferred for question/payoff roles while an existing still-generation slot is
still available; once the existing budget is exhausted, safe reuse remains
available.
"""
from pathlib import Path

HOOK = Path("video/hook_visual.py")
STILL = Path("video/still_image_fallback.py")

HOOK_MARKER = "# RUN_35327208962_VERIFIED_SCENE2_VISUAL_V1"
STILL_MARKER = "# RUN_35327208962_BOUNDED_STILL_NOVELTY_V1"

_HOOK_APPEND = r'''

# RUN_35327208962_VERIFIED_SCENE2_VISUAL_V1
# Keep the existing video_engine shape untouched. Its Scene 2 path already calls
# fetch_early_retention_pexels_video(). Make that final helper delegate to the
# bounded frame-level Hook verifier instead of metadata-only/legacy stock.
_run_35327208962_original_early_retention = fetch_early_retention_pexels_video


def fetch_early_retention_pexels_video(scene):
    try:
        video_url = fetch_hook_pexels_video(scene)
    except Exception as exc:
        print(
            "[RETENTION5] scene2_verified_stock=false "
            "fallback=verified_scene_fallback "
            f"reason={type(exc).__name__}"
        )
        return None

    if not video_url:
        print(
            "[RETENTION5] scene2_verified_stock=false "
            "fallback=verified_scene_fallback"
        )
        return None

    trace = get_last_hook_selection() or {}
    print(
        "[RETENTION5] scene2_verified_stock=true "
        f"mode={trace.get('selection_mode') or 'UNKNOWN'} "
        f"visual={trace.get('visual_evidence') or 'UNKNOWN'}"
    )
    return video_url
'''

_STILL_APPEND = r'''

# RUN_35327208962_BOUNDED_STILL_NOVELTY_V1
# Prefer a distinct still for the payoff/result when one of the existing
# generation slots is still unused. Question-beat verified reuse is preserved. This changes neither the max generation
# count nor the fail-closed verifier. If the budget is already exhausted,
# the original verified reuse policy remains authoritative.
_run_35327208962_original_source_reuse_allowed = _source_reuse_allowed


def _run_35327208962_scene_role(scene):
    scene = scene or {}
    values = (
        scene.get("retention_role"),
        scene.get("role"),
        scene.get("scene_role"),
        scene.get("causal_role"),
        scene.get("semantic_purpose"),
    )
    return " ".join(str(value or "").strip().lower() for value in values)


def _source_reuse_allowed(source_id, scene):
    prior_uses = verified_source_use_count(source_id)
    role = _run_35327208962_scene_role(scene)
    progression_role = (
        "payoff" in role
        or "primary_result" in role
        or "conclusion" in role
        or role.strip() == "result"
    )
    budget_remaining = int(_GENERATION_COUNT) < int(STILL_IMAGE_MAX_PER_VIDEO)

    if prior_uses > 0 and progression_role and budget_remaining:
        print(
            "[STILL_NOVELTY] "
            f"scene={_scene_id(scene)} status=prefer_fresh "
            f"source_id={source_id} uses={prior_uses} "
            f"generation_count={_GENERATION_COUNT}/{STILL_IMAGE_MAX_PER_VIDEO} "
            f"role={role or 'unknown'}"
        )
        return False

    return _run_35327208962_original_source_reuse_allowed(source_id, scene)
'''


def patch_hook_visual(text: str) -> str:
    if HOOK_MARKER in text:
        return text
    required = (
        "def fetch_early_retention_pexels_video(",
        "def fetch_hook_pexels_video(",
        "def get_last_hook_selection(",
        "RUN_35324930986_HOOK_FALLBACK_FAIL_CLOSED_V1",
    )
    if not all(token in text for token in required):
        raise RuntimeError(
            "Run 35327208962 Hook composition prerequisites missing"
        )
    return text.rstrip() + _HOOK_APPEND + "\n"

def patch_still_fallback(text: str) -> str:
    if STILL_MARKER in text:
        return text
    required = (
        "def _source_reuse_allowed(",
        "def verified_source_use_count(",
        "STILL_IMAGE_MAX_PER_VIDEO",
        "_GENERATION_COUNT",
    )
    if not all(token in text for token in required):
        raise RuntimeError("Run 35327208962 still novelty prerequisites missing")
    return text.rstrip() + _STILL_APPEND + "\n"


def main() -> None:
    HOOK.write_text(
        patch_hook_visual(HOOK.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    STILL.write_text(
        patch_still_fallback(STILL.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    print(
        "✅ Run 35327208962 first5/payoff visual progression installed; "
        "existing verification and still-generation ceilings unchanged"
    )


if __name__ == "__main__":
    main()

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

ENGINE = Path("video/video_engine.py")
STILL = Path("video/still_image_fallback.py")

ENGINE_MARKER = "# RUN_35327208962_VERIFIED_SCENE2_VISUAL_V1"
STILL_MARKER = "# RUN_35327208962_BOUNDED_STILL_NOVELTY_V1"

_ENGINE_OLD = '''        elif idx == 1:

            try:

                from video.hook_visual import (
                    fetch_early_retention_pexels_video,
                )

                video_url = (
                    fetch_early_retention_pexels_video(
                        item
                    )
                )

            except Exception as e:

                print(
                    "⚠️ First-5s strict visual selector 실패, "
                    "기존 Pexels 경로로 fallback: "
                    f"{e}"
                )

                video_url = (
                    fetch_pexels_video(
                        keyword
                    )
                )

'''

_ENGINE_NEW = '''        elif idx == 1:

            # RUN_35327208962_VERIFIED_SCENE2_VISUAL_V1
            # The second first-5 beat must use the same bounded frame-level
            # verifier as Scene 1. Never reopen generic stock after verification
            # fails; None intentionally falls through to the existing verified
            # still/explanatory path.
            try:

                from video.hook_visual import (
                    fetch_hook_pexels_video,
                )

                video_url = (
                    fetch_hook_pexels_video(
                        item
                    )
                )

                if not video_url:
                    print(
                        "[RETENTION5] scene2_verified_stock=false "
                        "fallback=verified_scene_fallback"
                    )

            except Exception as e:

                print(
                    "[RETENTION5] scene2_verified_stock=false "
                    "fallback=verified_scene_fallback "
                    f"reason={type(e).__name__}"
                )

                video_url = None

'''

_STILL_APPEND = r'''

# RUN_35327208962_BOUNDED_STILL_NOVELTY_V1
# Prefer a distinct still for the question/payoff when one of the existing
# generation slots is still unused. This changes neither the max generation
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
        "question" in role
        or "payoff" in role
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


def patch_video_engine(text: str) -> str:
    if ENGINE_MARKER in text:
        return text
    count = text.count(_ENGINE_OLD)
    if count != 1:
        raise RuntimeError(
            f"Run 35327208962 scene2 visual anchor mismatch: {count}"
        )
    return text.replace(_ENGINE_OLD, _ENGINE_NEW, 1)


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
    ENGINE.write_text(
        patch_video_engine(ENGINE.read_text(encoding="utf-8")),
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

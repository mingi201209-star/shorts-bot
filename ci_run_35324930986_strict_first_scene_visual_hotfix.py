"""Run 35324930986: force verified visual evidence for the first Script V2 scene.

Authority artifact showed Scene 1 rendered Pixabay 15270 as
SAME_DOMAIN_CONTEXTUAL_UNKNOWN: an aircraft was visible, but the Hook's wing-flex
phenomenon was not directly verified. This completion layer does not lower any
quality threshold or add API/image budgets. It only routes the canonical first
phenomenon scene through the existing Hook selector and refuses unverified Hook
fallbacks so the existing verified still/explanatory fallback can take over.
"""
from pathlib import Path

ENGINE = Path("video/video_engine.py")
HOOK = Path("video/hook_visual.py")

ENGINE_MARKER = "# RUN_35324930986_STRICT_FIRST_SCENE_VISUAL_V1"
HOOK_MARKER = "# RUN_35324930986_HOOK_FALLBACK_FAIL_CLOSED_V1"

_ENGINE_OLD = '''        hook_scene_enabled = (
            idx == 0
            and bool(
                item.get(
                    "hook_experiment",
                    {},
                ).get(
                    "selected",
                    False,
                )
            )
            and str(
                os.environ.get(
                    "ENABLE_HOOK_EXPERIMENT",
                    "0",
                )
            ).strip().lower()
            in {
                "1",
                "true",
                "yes",
                "on",
            }
        )
'''

_ENGINE_NEW = '''        # RUN_35324930986_STRICT_FIRST_SCENE_VISUAL_V1
        # Script V2 owns Scene 1 as retention_role=phenomenon even when the
        # experimental Hook text branch was not selected. The first rendered
        # visual still needs the same strict visual contract.
        opening_role = str(
            item.get("retention_role")
            or item.get("role")
            or ""
        ).strip().lower()
        hook_scene_enabled = (
            idx == 0
            and (
                bool(
                    item.get(
                        "hook_experiment",
                        {},
                    ).get(
                        "selected",
                        False,
                    )
                )
                or opening_role in {"phenomenon", "hook", "reveal"}
            )
            and str(
                os.environ.get(
                    "ENABLE_HOOK_EXPERIMENT",
                    "0",
                )
            ).strip().lower()
            in {
                "1",
                "true",
                "yes",
                "on",
            }
        )
'''

_HOOK_WRAPPER = r'''

# RUN_35324930986_HOOK_FALLBACK_FAIL_CLOSED_V1
# A Hook may render only evidence already verified for the visible subject.
# Metadata-only/component-context fallbacks return None so video_engine proceeds
# to the existing bounded verified-still / explanatory fallback path.
_RUN_35324930986_STRONG_HOOK_MODES = {
    "DIRECT_VERIFIED",
    "VERIFIED_COMPATIBLE_REUSE",
    "AI_GENERATED_VERIFIED",
}
_run_35324930986_original_fetch_hook_pexels_video = fetch_hook_pexels_video


def fetch_hook_pexels_video(scene):
    video_url = _run_35324930986_original_fetch_hook_pexels_video(scene)
    trace = get_last_hook_selection() or {}
    mode = str(trace.get("selection_mode") or "").strip().upper()
    visual = str(trace.get("visual_evidence") or "UNKNOWN").strip().upper()
    if (
        not video_url
        or mode not in _RUN_35324930986_STRONG_HOOK_MODES
        or visual != "TRUE"
    ):
        print(
            "[HOOK_VISUAL_STRICTNESS] "
            f"status=rejected_unverified_fallback mode={mode or 'NONE'} "
            f"visual={visual} -> verified_fallback"
        )
        return None
    print(
        "[HOOK_VISUAL_STRICTNESS] "
        f"status=verified mode={mode} visual={visual}"
    )
    return video_url
'''


def patch_video_engine(text: str) -> str:
    if ENGINE_MARKER in text:
        return text
    count = text.count(_ENGINE_OLD)
    if count != 1:
        raise RuntimeError(
            f"Run 35324930986 video_engine hook enable anchor mismatch: {count}"
        )
    return text.replace(_ENGINE_OLD, _ENGINE_NEW, 1)


def patch_hook_visual(text: str) -> str:
    if HOOK_MARKER in text:
        return text
    if "def fetch_hook_pexels_video(" not in text:
        raise RuntimeError("Run 35324930986 Hook selector missing")
    if "def get_last_hook_selection(" not in text:
        raise RuntimeError(
            "Run 35324930986 requires production Hook selection trace first"
        )
    return text.rstrip() + _HOOK_WRAPPER + "\n"


def main() -> None:
    engine_text = ENGINE.read_text(encoding="utf-8")
    hook_text = HOOK.read_text(encoding="utf-8")

    ENGINE.write_text(patch_video_engine(engine_text), encoding="utf-8")
    HOOK.write_text(patch_hook_visual(hook_text), encoding="utf-8")
    print(
        "✅ Run 35324930986 strict first-scene visual installed; "
        "unverified Hook fallbacks fail closed to existing verified fallback"
    )


if __name__ == "__main__":
    main()

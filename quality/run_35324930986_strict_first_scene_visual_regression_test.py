"""Regression for Run 35324930986 strict first-scene visual routing."""

from pathlib import Path

from ci_run_35324930986_strict_first_scene_visual_hotfix import (
    ENGINE_MARKER,
    HOOK_MARKER,
    patch_hook_visual,
    patch_video_engine,
)


ENGINE_FIXTURE = r'''import os

def create_scene(idx, item, create_voice):
        hook_scene_enabled = (
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
        return hook_scene_enabled
'''

HOOK_FIXTURE = r'''
_TRACE = {}

def get_last_hook_selection():
    return dict(_TRACE)

def fetch_hook_pexels_video(scene):
    return "stock.mp4"
'''


def _exec_hook_fixture(trace):
    patched = patch_hook_visual(HOOK_FIXTURE)
    namespace = {}
    exec(compile(patched, "synthetic-hook.py", "exec"), namespace)
    namespace["_TRACE"].update(trace)
    return patched, namespace["fetch_hook_pexels_video"]({})


def run():
    patched_engine = patch_video_engine(ENGINE_FIXTURE)
    assert ENGINE_MARKER in patched_engine
    assert patched_engine == patch_video_engine(patched_engine)

    namespace = {}
    exec(compile(patched_engine, "synthetic-engine.py", "exec"), namespace)

    import os
    old = os.environ.get("ENABLE_HOOK_EXPERIMENT")
    os.environ["ENABLE_HOOK_EXPERIMENT"] = "1"
    try:
        # Exact production counterexample: Script V2 Scene 1 is phenomenon,
        # hook_experiment.selected is false. It must still use Hook visual QA.
        assert namespace["create_scene"](
            0,
            {
                "retention_role": "phenomenon",
                "hook_experiment": {"selected": False},
            },
            None,
        ) is True
        # Later scenes never become Hook scenes merely from their role.
        assert namespace["create_scene"](
            1,
            {
                "retention_role": "phenomenon",
                "hook_experiment": {"selected": False},
            },
            None,
        ) is False
        # Existing explicit Hook-experiment behavior remains.
        assert namespace["create_scene"](
            0,
            {
                "retention_role": "setup",
                "hook_experiment": {"selected": True},
            },
            None,
        ) is True
    finally:
        if old is None:
            os.environ.pop("ENABLE_HOOK_EXPERIMENT", None)
        else:
            os.environ["ENABLE_HOOK_EXPERIMENT"] = old
    print("CASE A Script V2 phenomenon Scene 1 enters strict Hook visual selector: PASS")

    patched, result = _exec_hook_fixture({
        "selection_mode": "SAME_DOMAIN_CONTEXTUAL",
        "visual_evidence": "UNKNOWN",
    })
    assert HOOK_MARKER in patched
    assert result is None
    print("CASE B Run 35324930986 contextual/UNKNOWN Hook fallback is rejected: PASS")

    _, result = _exec_hook_fixture({
        "selection_mode": "COMPONENT_RELEVANT_FALLBACK",
        "visual_evidence": "UNKNOWN",
    })
    assert result is None
    print("CASE C metadata-complete but visually unverified Hook fallback is rejected: PASS")

    for mode in (
        "DIRECT_VERIFIED",
        "VERIFIED_COMPATIBLE_REUSE",
        "AI_GENERATED_VERIFIED",
    ):
        _, result = _exec_hook_fixture({
            "selection_mode": mode,
            "visual_evidence": "TRUE",
        })
        assert result == "stock.mp4", mode
    print("CASE D verified Hook modes remain renderable: PASS")

    _, result = _exec_hook_fixture({
        "selection_mode": "DIRECT_VERIFIED",
        "visual_evidence": "UNKNOWN",
    })
    assert result is None
    print("CASE E mode label cannot substitute for TRUE visual evidence: PASS")

    source = Path(
        "ci_run_35324930986_strict_first_scene_visual_hotfix.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "HOOK_VISUAL_MIN_SCORE =",
        "HOOK_SUBJECT_DOMINANCE_MIN =",
        "AI_MAX_GENERATIONS_PER_VIDEO =",
        "STILL_IMAGE_MAX_PER_VIDEO =",
    )
    for token in forbidden:
        assert token not in source, token

    print("RUN 35324930986 STRICT FIRST-SCENE VISUAL REGRESSION: PASS")


if __name__ == "__main__":
    run()

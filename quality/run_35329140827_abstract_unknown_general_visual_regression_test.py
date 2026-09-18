"""Regression for Run 35329140827 abstract UNKNOWN fail-close."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_run_35329140827_abstract_unknown_general_visual_hotfix import (
    MARKER,
    patch,
)


FIXTURE = r'''
# GENERAL_SCENE_VISUAL_PARITY_UNKNOWN_SAFE

def candidate_visible_component_evidence(candidate, scene_query):
    return {"state": candidate.get("visual_state", "UNKNOWN")}

def visual_specificity_decision(candidate, scene_query):
    return {
        "abstract": bool(candidate.get("abstract")),
        "label": candidate.get("label", "generic_contextual"),
        "level": candidate.get("level", 4),
    }

def general_scene_unknown_safe_tier(candidate, scene_query):
    if candidate.get("visual_state") == "TRUE":
        return 1, "VISUALLY_VERIFIED_DIRECT"
    return 4, "SAME_DOMAIN_CONTEXTUAL_UNKNOWN"
'''


def run():
    patched = patch(FIXTURE)
    assert MARKER in patched
    assert patched == patch(patched)

    ns = {}
    exec(compile(patched, "synthetic-downloader.py", "exec"), ns)
    tier = ns["general_scene_unknown_safe_tier"]

    # Exact authority shape: anchors/domain may match, but upstream specificity
    # already knows the candidate is abstract/metaphorical and visibility is UNKNOWN.
    assert tier(
        {
            "source_id": "15270",
            "visual_state": "UNKNOWN",
            "abstract": True,
            "label": "abstract_metaphorical_fallback",
            "level": 5,
        },
        "aircraft wing flexible elastic flapwise bending",
    ) == (5, "ABSTRACT_UNKNOWN_FAIL_CLOSED")
    print("CASE A abstract UNKNOWN contextual stock is forced to reject tier: PASS")

    # Scene 3 style metadata-only but non-abstract footage remains eligible under
    # the existing policy; this patch does not globally ban UNKNOWN stock.
    assert tier(
        {
            "source_id": "6522",
            "visual_state": "UNKNOWN",
            "abstract": False,
            "label": "semantic_only_visibility_unknown",
            "level": 4,
        },
        "wing flexible aircraft flight load bending response",
    ) == (4, "SAME_DOMAIN_CONTEXTUAL_UNKNOWN")
    print("CASE B non-abstract UNKNOWN general footage keeps previous tier: PASS")

    # TRUE evidence remains fully authoritative even if metadata contains a word
    # that the specificity heuristic might consider abstract.
    assert tier(
        {
            "source_id": "verified",
            "visual_state": "TRUE",
            "abstract": True,
            "label": "abstract_metaphorical_fallback",
            "level": 5,
        },
        "aircraft wing",
    ) == (1, "VISUALLY_VERIFIED_DIRECT")
    print("CASE C TRUE visual evidence is not downgraded by metadata heuristic: PASS")

    source = Path(
        "ci_run_35329140827_abstract_unknown_general_visual_hotfix.py"
    ).read_text(encoding="utf-8")
    for token in (
        "V3_MAX_COST_USD =",
        "V3_MAX_API_CALLS =",
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "HOOK_VISUAL_MIN_SCORE =",
        "HOOK_SUBJECT_DOMINANCE_MIN =",
    ):
        assert token not in source, token

    print("RUN 35329140827 ABSTRACT UNKNOWN GENERAL VISUAL REGRESSION: PASS")


if __name__ == "__main__":
    run()

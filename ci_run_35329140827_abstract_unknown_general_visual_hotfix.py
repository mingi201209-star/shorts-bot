"""Run 35329140827: fail closed abstract UNKNOWN general-scene stock.

Authority MP4 rendered Pixabay 15270 for Scene 4 even though the composed
specificity layer classified it as abstract_metaphorical_fallback / level 5.
The general UNKNOWN-safe tier returned SAME_DOMAIN_CONTEXTUAL_UNKNOWN earlier
because aircraft+wing anchors matched, so the later abstract rejection branch
was unreachable.

This completion changes no provider, threshold, retry, API, Vision, image, or
cost budget. It only prevents an already-known abstract UNKNOWN candidate from
being promoted to contextual tier 4.
"""
from pathlib import Path

PATH = Path("video/video_downloader.py")
MARKER = "# RUN_35329140827_ABSTRACT_UNKNOWN_FAIL_CLOSED_V1"

_APPEND = r'''

# RUN_35329140827_ABSTRACT_UNKNOWN_FAIL_CLOSED_V1
_run_35329140827_previous_general_scene_unknown_safe_tier = (
    general_scene_unknown_safe_tier
)


def general_scene_unknown_safe_tier(candidate, scene_query):
    visual = candidate_visible_component_evidence(candidate, scene_query)
    decision = visual_specificity_decision(candidate, scene_query)
    state = str(visual.get("state") or "UNKNOWN").upper()

    if state == "UNKNOWN" and bool(decision.get("abstract")):
        print(
            "[GENERAL_VISUAL_ABSTRACT_REJECT] "
            f"candidate={candidate.get('source_id', candidate.get('id'))} "
            f"label={decision.get('label') or 'abstract'} "
            f"level={decision.get('level', 'unknown')}"
        )
        return 5, "ABSTRACT_UNKNOWN_FAIL_CLOSED"

    return _run_35329140827_previous_general_scene_unknown_safe_tier(
        candidate,
        scene_query,
    )
'''


def patch(text: str) -> str:
    if MARKER in text:
        return text
    required = (
        "GENERAL_SCENE_VISUAL_PARITY_UNKNOWN_SAFE",
        "def general_scene_unknown_safe_tier(",
        "def visual_specificity_decision(",
        "def candidate_visible_component_evidence(",
    )
    if not all(token in text for token in required):
        raise RuntimeError(
            "Run 35329140827 general visual composition prerequisites missing"
        )
    return text.rstrip() + _APPEND + "\n"


def main() -> None:
    PATH.write_text(
        patch(PATH.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    print(
        "✅ Run 35329140827 abstract UNKNOWN general visuals fail closed; "
        "existing budgets/thresholds unchanged"
    )


if __name__ == "__main__":
    main()

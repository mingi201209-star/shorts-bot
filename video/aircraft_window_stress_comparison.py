"""PHASE 6: builds the existing V2.1 visual-explanation-contract
comparison_segment for AIRCRAFT_WINDOW_STRESS_V1's LEFT/RIGHT contrast.

Reuses quality/visual_explanation_contract_v2.py unchanged -- no new
comparison schema is defined here (task section 6). The renderer
(video/visual_explanation.py, wired in Phase 7) emits this segment directly
alongside its deterministic PIL render; a separate post-processor does not
redefine comparison meaning.
"""
from __future__ import annotations

from quality.visual_explanation_contract_v2 import semantic_validate
from quality.visual_state_registry import SubjectStateRegistry
from video.aircraft_window_stress_signature import LEFT_CLAIM_ID, RELATION_ID, RIGHT_CLAIM_ID

WINDOW_CORNER_SUBJECT = "window_corner"
STATE_SQUARISH = "SQUARISH"
STATE_ROUNDED = "ROUNDED"

# Verbatim compressions of the already-approved evidence text
# (quality/candidate_pool_grounding_records.py allowed_paraphrase_scope for
# squarish_window_stress_concentration / rounded_window_stress_distribution)
# -- not new fact generation, just panel-width-bounded captions of the exact
# same approved sentences.
LEFT_CAPTION = "각진 모서리엔 응력이 집중됩니다"
RIGHT_CAPTION = "둥근 모서리는 응력을 분산시킵니다"

_VISIBILITY = {
    "level": "CLEAR",
    "requirements": {"not_occluded": True, "sufficient_scale_for_mobile": True},
}


def build_window_corner_comparison_segment(
    *, scene_id, comparison_segment_id, start_sec, end_sec, registry=None,
):
    """Returns a validated ContractDict (task's "comparison_segment"), or
    None if it fails the existing V2.1 semantic_validate authority for any
    reason (malformed shape rather than a pipeline exception, matching task
    section 2.A)."""
    registry = registry or SubjectStateRegistry()
    claims = [
        {
            "id": LEFT_CLAIM_ID,
            "subject": WINDOW_CORNER_SUBJECT,
            "context": "aircraft passenger window corner geometry",
            "state": STATE_SQUARISH,
            "required": True,
            "visibility": dict(_VISIBILITY),
        },
        {
            "id": RIGHT_CLAIM_ID,
            "subject": WINDOW_CORNER_SUBJECT,
            "context": "aircraft passenger window corner geometry",
            "state": STATE_ROUNDED,
            "required": True,
            "visibility": dict(_VISIBILITY),
        },
    ]
    segment = {
        "id": str(comparison_segment_id),
        "presentation": "SPLIT_SCREEN",
        "start_sec": float(start_sec),
        "end_sec": float(end_sec),
        "bindings": [
            {"claim_id": LEFT_CLAIM_ID, "slot": "LEFT"},
            {"claim_id": RIGHT_CLAIM_ID, "slot": "RIGHT"},
        ],
    }
    relation = {
        "id": RELATION_ID,
        "type": "CONTRAST",
        "members": [LEFT_CLAIM_ID, RIGHT_CLAIM_ID],
        "comparison_segment_id": str(comparison_segment_id),
        "required": True,
    }
    contract = {
        "version": "visual_explanation_contract_v2.1",
        "scene_id": int(scene_id),
        "mode": "shadow",
        "claims": claims,
        "comparison_segments": [segment],
        "relations": [relation],
    }
    result = semantic_validate(contract, registry)
    if not result.ok:
        return None
    return contract


def stable_comparison_segment_id(canonical_subject_id, owned_claim_id):
    return f"seg-{canonical_subject_id}-{owned_claim_id}-contrast"

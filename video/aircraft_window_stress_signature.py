"""Stable param_signature / attempt identity for AIRCRAFT_WINDOW_STRESS_V1.

Attempt identity for the escalation ledger's reuse-ban invariant is
(method, param_signature) -- not method alone (quality/visual_escalation_ledger
.schema.json). This module builds a param_signature from stable
semantic/provenance identity only:

    (template_id, canonical_subject_id, owned_claim_id, relation_id,
     presentation=CONTRAST, grounding_fingerprint)

Never from: narration, visual_goal raw string, keyword raw string, run id,
timestamp, UUID, output path, or scene index alone. The same evidence must
always produce the same signature; a different run id, a different
timestamp, or a different scene index for the same evidence must not change
it. A different grounding provenance or a different claim identity must
change it.
"""
from __future__ import annotations

# This template's renderer always contrasts exactly these two claims,
# regardless of which of the three related claims (see
# video.aircraft_window_stress_grounding.SUPPORTED_OWNED_CLAIM_IDS) the
# scene itself owns -- the physical LEFT/RIGHT evidence is the same
# comparison either way (task's own worked example: sharp/angular corner
# stress concentration vs. rounded-corner stress distribution).
LEFT_CLAIM_ID = "squarish_window_stress_concentration"
RIGHT_CLAIM_ID = "rounded_window_stress_distribution"
RELATION_ID = "window_corner_stress_contrast"


def _text(value):
    return str(value or "").strip()


def build_grounding_fingerprint(*, canonical_subject_id, grounding_provenance_ref):
    """Stable identity from grounding/claim/relation identity only.

    Deliberately excludes: narration, visual_goal, keyword, run id,
    timestamp, UUID, output path, scene index. Two different runs producing
    the same trusted-grounding evidence for the same subject/relation must
    fingerprint identically; a different provenance source or a different
    subject must fingerprint differently.
    """
    parts = [
        "faa_comet_lessons_v1",
        _text(canonical_subject_id),
        _text(grounding_provenance_ref),
        LEFT_CLAIM_ID,
        RIGHT_CLAIM_ID,
    ]
    if not all(parts):
        return ""
    return "|".join(parts)


def build_param_signature(
    *, template_id, canonical_subject_id, owned_claim_id, presentation, grounding_fingerprint,
    relation_id=RELATION_ID,
):
    parts = [
        _text(template_id),
        _text(canonical_subject_id),
        _text(owned_claim_id),
        _text(relation_id),
        _text(presentation),
        _text(grounding_fingerprint),
    ]
    if not all(parts):
        return ""
    return "|".join(parts)


def build_deterministic_explanation_params(eligibility_params, *, comparison_segment_id):
    """Compose the full PRODUCE/DETERMINISTIC_EXPLANATION params dict
    (matching quality/aircraft_window_stress_v1.schema.json exactly) from an
    eligibility adapter's output plus the comparison_segment_id the renderer
    already emitted (Phase 6). Returns None if eligibility_params is falsy or
    a stable signature cannot be built from it.
    """
    if not eligibility_params:
        return None

    canonical_subject_id = _text(eligibility_params.get("canonical_subject_id"))
    owned_claim_id = _text(eligibility_params.get("owned_claim_id"))
    presentation = _text(eligibility_params.get("presentation")) or "CONTRAST"
    grounding_provenance_ref = _text(eligibility_params.get("grounding_provenance_ref"))

    fingerprint = build_grounding_fingerprint(
        canonical_subject_id=canonical_subject_id,
        grounding_provenance_ref=grounding_provenance_ref,
    )
    signature = build_param_signature(
        template_id=eligibility_params.get("template_id"),
        canonical_subject_id=canonical_subject_id,
        owned_claim_id=owned_claim_id,
        presentation=presentation,
        grounding_fingerprint=fingerprint,
    )
    if not fingerprint or not signature or not comparison_segment_id:
        return None

    return {
        "template_id": _text(eligibility_params.get("template_id")),
        "presentation": presentation,
        "canonical_subject_id": canonical_subject_id,
        "owned_claim_id": owned_claim_id,
        "evidence_source": _text(eligibility_params.get("evidence_source")) or "TRUSTED_GROUNDING",
        "grounding_provenance_ref": grounding_provenance_ref,
        "grounding_fingerprint": fingerprint,
        "comparison_segment_id": _text(comparison_segment_id),
        "param_signature": signature,
    }

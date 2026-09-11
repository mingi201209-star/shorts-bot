"""Grounding eligibility adapter for the AIRCRAFT_WINDOW_STRESS_V1 deterministic
explanation template.

INPUT AUTHORITY vs OUTPUT AUTHORITY (binding, restated from
quality/grounded_deterministic_explanation.py):
  This module decides WHAT may be drawn. It reads only existing trusted
  grounding / claim registry authority -- never Vision EvidenceState (VERIFIED
  from Vision never raises eligibility here). Whether the actual render is
  correct is a separate, unchanged concern for the existing downstream
  Visual Semantic QA / Visual Diversity / Director / Final Render Content
  Integrity checks.

This is an adapter, not a new classifier: it performs no new fact inference,
no keyword/narration semantic guessing, no confidence recomputation, and no
new evidence classifier. It mechanically connects already-existing grounding
output (the repo-owned FAA Comet-lessons trusted subject identity record in
quality/candidate_pool_grounding_records.py, and the canonical visual supply
profile already attached to scenes post-Script by
quality/canonical_subject_grounding_supply.py) to this one renderer
capability. Mirrors the established pattern in
video/grounded_explanatory_visual.py (chevron_flow_mixing_supported,
noise_reduction_result_supported) exactly.

Contradiction handling (task section 3): the trusted grounding *input* layer
(quality/candidate_pool_grounding_records.py) carries no negative/contradicted
state today -- records are static, always-true, evidence-vetted facts. Only
the separate, Vision-driven quality/visual_state_evidence.py::EvidenceState
has a CONTRADICTED value, and that is output-side (verifies an already
*produced* render against a claim), not an eligibility input. V1 authority:
if a future trusted-grounding input layer gains a negative/contradictory
state, that state is semantic-invalid/non-selection here; no new
contradiction-modeling enum is invented in this module.
"""
from __future__ import annotations

import re

CANONICAL_SUBJECT = "modern aircraft passenger window with rounded/oval corners"

# The three claims the repo-owned FAA Comet-lessons record
# (quality/candidate_pool_grounding_records.py) already supports under this
# canonical subject -- one connected causal chain (constraint -> mechanism
# change -> result), not three unrelated facts. A scene may legitimately own
# any one of them; the LEFT/RIGHT visual evidence is the same physical
# comparison regardless of which is owned. This is a closed, enumerated set
# read verbatim from the existing record -- not a new inferred claim family.
SUPPORTED_OWNED_CLAIM_IDS = frozenset({
    "squarish_window_stress_concentration",
    "rounded_window_stress_distribution",
    "squarish_window_fatigue_rupture",
})

_RESULT_ROLES = frozenset({"payoff", "result", "primary_result"})


def _text(value):
    return str(value or "").strip()


def canonical_subject_id(value=CANONICAL_SUBJECT):
    """Stable, deterministic slug of the existing canonical_subject string.

    Pure normalization of an already-authoritative field (lowercase,
    non-alphanumeric collapsed to underscore) -- not a new identity and not
    inferred from anything the grounding gate didn't already assert.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")
    return slug


def _window_canonical_supply_present(scene):
    """Mirrors video.grounded_explanatory_visual.trusted_grounding_present,
    scoped to this canonical subject instead of the chevron one. Requires the
    existing post-Script canonical trusted-supply provenance
    (scene["_canonical_visual_supply"]), not a keyword/narration guess.
    """
    if not isinstance(scene, dict):
        return None
    supply = scene.get("_canonical_visual_supply") or {}
    if not isinstance(supply, dict):
        return None
    canonical = _text(supply.get("canonical_subject")).lower()
    source = _text(supply.get("grounding_source"))
    if not canonical or not source:
        return None
    if not (
        "aircraft" in canonical
        and "window" in canonical
        and ("round" in canonical or "oval" in canonical)
    ):
        return None
    return supply


def _window_subject_anchor_words(scene):
    """Same anchor-word style as
    video.grounded_explanatory_visual.subject_anchor_words, scoped to the
    window subject. Reads the deterministic grounded keyword the existing
    Grounded Keyword Contract (ci_grounded_keyword_contract_hotfix.py)
    already derives from canonical_subject + owned_claim_id -- this is
    reading that structured output, not inferring new meaning from raw text.
    """
    words = set(re.findall(r"[a-z]+", _text((scene or {}).get("keyword")).lower()))
    anchors = []
    if words & {"aircraft", "airplane", "aviation", "jet"}:
        anchors.append("aircraft")
    if "window" in words:
        anchors.append("window")
    return anchors


def _owned_claim_id_from_scene(scene, candidate):
    """Runtime Script scenes do not carry the private Grounded Claim Plan
    object (owned_claim_id lives only on the Writer-facing contract, which
    does not survive into the final scene dict -- confirmed against
    ci_grounded_keyword_contract_hotfix.py). If an explicit owned_claim_id is
    present (fixtures/diagnostics, or a future runtime attachment), it must
    match; its absence is not itself disqualifying as long as the other
    grounding signals hold, mirroring
    video.grounded_explanatory_visual.chevron_flow_mixing_supported exactly.
    """
    if isinstance(scene, dict):
        explicit = _text(scene.get("owned_claim_id"))
        if explicit:
            return explicit
    if isinstance(candidate, dict):
        explicit = _text(candidate.get("owned_claim_id"))
        if explicit:
            return explicit
    return ""


def _result_scene(scene):
    if not isinstance(scene, dict):
        return False
    causal_role = _text(scene.get("causal_role")).lower()
    if causal_role:
        return causal_role == "primary_result"
    role = _text(scene.get("role")).lower()
    return role in _RESULT_ROLES


def supports_aircraft_window_stress_from_grounding(scene, candidate=None):
    """Return the eligibility params dict for AIRCRAFT_WINDOW_STRESS_V1, or
    None if this scene is not eligible.

    ALL of the following must hold (AND, not best-effort):
      - existing canonical visual supply provenance identifies this exact
        aircraft-passenger-window subject (never inferred from keyword alone)
      - the window subject anchors (aircraft + window) are present in the
        deterministic grounded keyword
      - an explicit owned_claim_id, if present, is one of the three claims
        this exact canonical record supports (never a foreign claim)
      - the scene is a result/payoff scene (matches the "result" claim_type
        that needed deterministic rescue in Run 34604725427 Scene 5; the two
        upstream mechanism claims already get real generated stills and are
        not this template's concern)
      - evidence_source is TRUSTED_GROUNDING (there is no other kind here)

    Vision EvidenceState is never consulted -- this function does not import
    quality.visual_state_evidence and never will for eligibility purposes.
    """
    if not isinstance(scene, dict):
        return None

    supply = _window_canonical_supply_present(scene)
    if supply is None:
        return None

    anchors = _window_subject_anchor_words(scene)
    if set(anchors) != {"aircraft", "window"}:
        return None

    owned_claim = _owned_claim_id_from_scene(scene, candidate)
    if owned_claim and owned_claim not in SUPPORTED_OWNED_CLAIM_IDS:
        return None

    if not _result_scene(scene):
        return None

    return {
        "template_id": "AIRCRAFT_WINDOW_STRESS_V1",
        "presentation": "CONTRAST",
        "canonical_subject_id": canonical_subject_id(supply.get("canonical_subject")),
        "owned_claim_id": owned_claim or "squarish_window_fatigue_rupture",
        "evidence_source": "TRUSTED_GROUNDING",
        "grounding_provenance_ref": _text(supply.get("grounding_source")),
        "_canonical_subject_text": _text(supply.get("canonical_subject")),
    }

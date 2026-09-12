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

# Runtime scene dicts do not preserve the private Writer-owned claim id, but
# they do preserve the already-authoritative causal/structural role. These
# closed mappings reconstruct only the exact three claim identities in the
# existing grounded plan. They do not inspect narration or invent semantics.
_CLAIM_BY_CAUSAL_ROLE = {
    "constraint": "squarish_window_stress_concentration",
    "mechanism_change": "rounded_window_stress_distribution",
    "primary_result": "squarish_window_fatigue_rupture",
}
_CLAIM_BY_STRUCTURAL_ROLE = {
    "causal_clue": "squarish_window_stress_concentration",
    "constraint": "squarish_window_stress_concentration",
    "reveal": "rounded_window_stress_distribution",
    "mechanism_change": "rounded_window_stress_distribution",
    "payoff": "squarish_window_fatigue_rupture",
    "result": "squarish_window_fatigue_rupture",
    "primary_result": "squarish_window_fatigue_rupture",
}


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


# Every word (split on "_") of the three claim ids this exact canonical
# record supports, excluding the generic "window" anchor already checked
# separately. Mirrors video.grounded_explanatory_visual.chevron_flow_mixing_
# supported's own {"chevron", "flow", "mixing"} <= words check exactly: this
# reads the deterministic grounded keyword for the claim identity's own
# structured words (the Grounded Keyword Contract already derives keyword
# terms directly from owned_claim_id.replace("_", " ")), not a new inferred
# vocabulary. Without this, a same-subject scene about an unrelated aspect
# (e.g. "why is this window small") would wrongly pass on generic
# aircraft+window anchors alone -- the required "aircraft passenger window
# but unrelated claim" negative control.
_CLAIM_DISCRIMINATOR_WORDS = frozenset({
    "squarish", "stress", "concentration", "rounded", "distribution", "fatigue", "rupture",
})


def _has_claim_discriminator_word(scene):
    words = set(re.findall(r"[a-z]+", _text((scene or {}).get("keyword")).lower()))
    return bool(words & _CLAIM_DISCRIMINATOR_WORDS)


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


def _claim_id_from_authoritative_role(scene):
    if not isinstance(scene, dict):
        return ""
    causal_role = _text(scene.get("causal_role")).lower()
    if causal_role:
        return _CLAIM_BY_CAUSAL_ROLE.get(causal_role, "")
    role = _text(scene.get("role")).lower()
    return _CLAIM_BY_STRUCTURAL_ROLE.get(role, "")


def _owned_claim_id_from_scene(scene, candidate):
    """Resolve claim identity without narration/keyword inference.

    Prefer an explicit owned_claim_id when present. Production scenes currently
    drop the private Writer claim id, so otherwise recover only the exact claim
    implied by the already-authoritative causal/structural role from the fixed
    three-claim grounded plan. Unknown roles fail closed.
    """
    explicit = ""
    if isinstance(scene, dict):
        explicit = _text(scene.get("owned_claim_id"))
    if not explicit and isinstance(candidate, dict):
        explicit = _text(candidate.get("owned_claim_id"))

    role_claim = _claim_id_from_authoritative_role(scene)
    if explicit and role_claim and explicit != role_claim:
        return ""
    return explicit or role_claim


def supports_aircraft_window_stress_from_grounding(scene, candidate=None):
    """Return the eligibility params dict for AIRCRAFT_WINDOW_STRESS_V1, or
    None if this scene is not eligible.

    ALL of the following must hold (AND, not best-effort):
      - existing canonical visual supply provenance identifies this exact
        aircraft-passenger-window subject (never inferred from keyword alone)
      - the window subject anchors (aircraft + window) are present in the
        deterministic grounded keyword
      - at least one of the three supported claims' own discriminator words
        is present in that same deterministic grounded keyword
      - exact claim ownership resolves from an explicit owned_claim_id or the
        existing authoritative causal/structural role and belongs to the
        closed three-claim trusted record
      - evidence_source is TRUSTED_GROUNDING (there is no other kind here)

    Run 34610328000 proved the previous result-only role restriction was an
    invalid runtime assumption: Scene 4 (rounded_window_stress_distribution)
    can exhaust stock/still supply before Scene 5. Eligibility therefore
    follows the already-grounded claim identity, not an assumed scene index.

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

    if not _has_claim_discriminator_word(scene):
        return None

    owned_claim = _owned_claim_id_from_scene(scene, candidate)
    if not owned_claim or owned_claim not in SUPPORTED_OWNED_CLAIM_IDS:
        return None

    return {
        "template_id": "AIRCRAFT_WINDOW_STRESS_V1",
        "presentation": "CONTRAST",
        "canonical_subject_id": canonical_subject_id(supply.get("canonical_subject")),
        "owned_claim_id": owned_claim,
        "evidence_source": "TRUSTED_GROUNDING",
        "grounding_provenance_ref": _text(supply.get("grounding_source")),
        "_canonical_subject_text": _text(supply.get("canonical_subject")),
    }


# Run 34663907508 (HUMAN QA FAILURE B): a "question" beat scene owns no
# claim yet -- by the existing grounded-plan design a question scene is
# never supposed to answer anything (content.grounded_claim_plan reserves
# claim ownership starting at scene 3). But its Writer-authored visual_goal
# can still legitimately ask for a squarish-vs-rounded shape comparison
# before any mechanism claim is revealed. The previous behaviour let a single
# reused verified still silently satisfy that comparison goal
# (REUSED_VERIFIED_QUESTION_SUBJECT_MOTION), which is a false pass: one
# photo of one window state cannot show a contrast. This is a second,
# independent eligibility path -- not a relaxation of the three-claim path
# above -- for the closed, non-causal "shape contrast intro" identity: it
# asserts only that the two corner *shapes* differ, never any stress/
# mechanism/result claim (those remain scene 3-5's exclusive authority).
SHAPE_CONTRAST_INTRO_CLAIM_ID = "window_corner_shape_contrast_intro"

_COMPARISON_INTENT_MARKERS = (
    "비교", "대비", "나란히", "차이", "대조",
    "versus", " vs ", "vs.", "side by side", "side-by-side", "before", "after",
)


def _visual_goal_expresses_comparison_intent(scene):
    if not isinstance(scene, dict):
        return False
    goal = _text(scene.get("visual_goal")).lower()
    if not goal:
        return False
    return any(marker.lower() in goal for marker in _COMPARISON_INTENT_MARKERS)


def _keyword_expresses_grounded_rounded_corner_question(scene):
    """Recognize the existing deterministic rounded-corner question query.

    Run 34675233154 showed that Script V2's neutral Scene-2 visual_goal can say
    only "emphasize the rounded corner while asking the question" even though
    the already-grounded query lock is `aircraft window why rounded corners`.
    Under the same trusted subject + question-role + no-owned-claim guards used
    below, `rounded` + `corner(s)` carries only physical shape intent; it does
    not assert stress, fatigue, or any mechanism. This lets the existing
    SHAPE_CONTRAST_INTRO render show the two shapes instead of reusing Scene 1.
    """
    if not isinstance(scene, dict):
        return False
    words = set(re.findall(r"[a-z]+", _text(scene.get("keyword")).lower()))
    return "rounded" in words and bool(words & {"corner", "corners"})


def supports_aircraft_window_shape_contrast_intro_from_grounding(scene, candidate=None):
    """Eligibility for the neutral SHAPE_CONTRAST_INTRO presentation.

    ALL of the following must hold:
      - the scene is a "question" beat (existing authoritative role) that
        owns no claim (explicit owned_claim_id absent)
      - existing canonical visual supply provenance identifies the exact
        aircraft-passenger-window subject
      - the window subject anchors (aircraft + window) are present
      - either the Writer visual_goal explicitly asks for comparison OR the
        existing grounded rounded-corner question query carries rounded+corner
        shape terms. Neither path authorizes any causal/mechanism claim.
    """
    if not isinstance(scene, dict):
        return None

    role = _text(scene.get("role")).lower()
    if role != "question":
        return None
    if _text(scene.get("owned_claim_id")):
        return None
    if not (
        _visual_goal_expresses_comparison_intent(scene)
        or _keyword_expresses_grounded_rounded_corner_question(scene)
    ):
        return None

    supply = _window_canonical_supply_present(scene)
    if supply is None:
        return None

    anchors = _window_subject_anchor_words(scene)
    if set(anchors) != {"aircraft", "window"}:
        return None

    return {
        "template_id": "AIRCRAFT_WINDOW_STRESS_V1",
        "presentation": "CONTRAST",
        "canonical_subject_id": canonical_subject_id(supply.get("canonical_subject")),
        "owned_claim_id": SHAPE_CONTRAST_INTRO_CLAIM_ID,
        "evidence_source": "TRUSTED_GROUNDING",
        "grounding_provenance_ref": _text(supply.get("grounding_source")),
        "_canonical_subject_text": _text(supply.get("canonical_subject")),
    }


# RUN_34675233154_GROUNDED_WINDOW_PROGRESSION_V1

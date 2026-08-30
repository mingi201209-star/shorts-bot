"""Grounded explanatory visual contract helpers.

This module carries factual relation semantics from an already-grounded Scene
keyword into still generation, Vision verification and deterministic explanation
fallbacks. It does not relax subject/visual gates and performs no API calls.
"""

from __future__ import annotations

import re


EXPLANATORY_TERM_GROUPS = {
    "flow": {"flow", "flows", "airflow", "airflows", "exhaust", "stream", "streams", "plume", "plumes"},
    "interface": {"interface", "interfaces", "boundary", "boundaries", "junction", "junctions", "meeting", "meet"},
    "mixing": {"mix", "mixes", "mixed", "mixing", "blend", "blends", "blended", "blending"},
    "noise": {"noise", "noisy", "sound", "sounds", "acoustic", "acoustics", "decibel", "decibels"},
    "reduction": {"reduce", "reduces", "reduced", "reduction", "decrease", "decreases", "lower", "lowering", "quieter", "quiet"},
}

_GROUP_VISIBLE_REQUIREMENTS = {
    "flow": "a flow itself must be directly visible as airflow, exhaust, a stream, or a plume",
    "interface": "a meeting/interface/boundary/junction between two distinct visible flow or fluid regions must be directly visible; a single isolated plume is not enough",
    "mixing": "two or more visible flow regions must visibly mix, blend, or interleave; a static part close-up is not enough",
    "noise": "visible evidence must directly represent sound/noise rather than merely showing the source object",
    "reduction": "the visual must directly represent a reduction/lowering comparison or state, not merely the presence of the source object",
}


def _words(value):
    return set(re.findall(r"[a-z]+", str(value or "").lower().replace("-", " ")))


def explanatory_groups(value):
    words = _words(value)
    found = []
    for canonical, aliases in EXPLANATORY_TERM_GROUPS.items():
        if words & aliases:
            found.append(canonical)
    return found


def required_explanatory_groups(scene):
    """Return the authoritative relation nucleus carried by a grounded keyword.

    Matching #254, a lone descriptive term is not promoted into a factual gate;
    two or more independent groups are required.
    """
    if not isinstance(scene, dict):
        return []
    groups = explanatory_groups(scene.get("keyword"))
    return groups if len(groups) >= 2 else []


def explanatory_signature(scene):
    return tuple(f"explain:{group}" for group in required_explanatory_groups(scene))


def generation_requirement(scene):
    groups = required_explanatory_groups(scene)
    if not groups:
        return ""
    clauses = [_GROUP_VISIBLE_REQUIREMENTS[group] for group in groups]
    return (
        "Grounded explanatory contract: the image must visibly satisfy every required relation group: "
        + ", ".join(groups)
        + ". Specifically, "
        + "; ".join(clauses)
        + ". Do not imply a missing relation from the subject name or narration."
    )


def normalize_visible_explanatory_groups(values):
    visible = []
    for value in values or []:
        group = str(value or "").strip().lower()
        if group in EXPLANATORY_TERM_GROUPS and group not in visible:
            visible.append(group)
    return visible


def explanatory_evidence_complete(scene, vision_result):
    required = required_explanatory_groups(scene)
    if not required:
        return True, [], []
    visible = normalize_visible_explanatory_groups(
        (vision_result or {}).get("visible_explanatory_groups") or []
    )
    missing = [group for group in required if group not in visible]
    return not missing, visible, missing


def subject_anchor_words(scene):
    words = _words((scene or {}).get("keyword"))
    anchors = []
    if words & {"aircraft", "airplane", "aviation", "jet"}:
        anchors.append("aircraft")
    if "engine" in words or "nacelle" in words or "nozzle" in words:
        anchors.append("engine")
    if words & {"chevron", "chevrons", "serrated", "serration", "serrations"}:
        anchors.append("chevron")
    return anchors


def trusted_grounding_present(scene):
    """Require the existing post-Script canonical trusted-supply provenance."""
    if not isinstance(scene, dict):
        return False
    supply = scene.get("_canonical_visual_supply") or {}
    if not isinstance(supply, dict):
        return False
    canonical = str(supply.get("canonical_subject") or "").strip().lower()
    source = str(supply.get("grounding_source") or "").strip()
    if not canonical or not source:
        return False
    # Keep this fallback limited to the already-grounded jet-engine chevron
    # identity. A generic engine or generic serration is not enough.
    return (
        "chevron" in canonical
        and any(term in canonical for term in ("engine", "nacelle", "nozzle"))
    )


def _scene_text(scene):
    return " ".join(
        str((scene or {}).get(key) or "").strip().lower()
        for key in ("text", "visual_goal", "keyword")
    )


def _leaks_primary_result(scene):
    value = _scene_text(scene)
    return any(
        token in value
        for token in (
            "noise reduction", "reduce noise", "reduces noise", "quieter",
            "소음 감소", "소음을 줄", "소음이 줄", "조용",
            "fuel", "efficiency", "drag", "stability", "thrust", "performance",
            "연료", "효율", "항력", "안정성", "추력", "성능",
        )
    )


def _noise_result_has_forbidden_expansion(scene):
    value = _scene_text(scene)
    if any(
        token in value
        for token in (
            "fuel", "efficiency", "drag", "stability", "thrust", "performance",
            "연료", "효율", "항력", "안정성", "추력", "성능",
        )
    ):
        return True
    if re.search(r"\b\d+(?:\.\d+)?\s*d\s*b\b", value, flags=re.IGNORECASE):
        return True
    # Scene 5 may refer back to "this mixing change" as a bridge, but it must
    # not re-own or re-explain the Scene-4 mechanism itself.
    return any(
        token in value
        for token in (
            "flow mixing mechanism", "mixing mechanism", "chevron flow mixing",
            "exhaust flow and surrounding flow mix", "exhaust and ambient flow mix",
            "배기 흐름과 주변 흐름이 섞", "배기 흐름과 바깥 흐름이 섞",
            "셰브론은 흐름을 섞", "셰브론이 흐름을 섞",
        )
    )


def chevron_flow_mixing_supported(scene):
    """Strict eligibility for the Scene-4 deterministic mechanism visual.

    Runtime Script scenes intentionally do not carry the private Grounded Claim
    Plan object. Therefore the authoritative equivalent claim signature is the
    deterministic grounded keyword (`jet engine chevron flow mixing`) plus the
    trusted canonical supply profile attached after Script generation. If an
    explicit owned_claim_id is present (fixtures/diagnostics), it must match.
    """
    if not isinstance(scene, dict):
        return False
    explicit_claim = str(scene.get("owned_claim_id") or "").strip()
    if explicit_claim and explicit_claim != "chevron_flow_mixing":
        return False
    if not trusted_grounding_present(scene):
        return False
    if set(subject_anchor_words(scene)) != {"aircraft", "engine", "chevron"}:
        return False
    if set(required_explanatory_groups(scene)) != {"flow", "mixing"}:
        return False
    if _leaks_primary_result(scene):
        return False
    # The complete subject + relation nucleus is produced by the existing
    # grounded-keyword contract from the owned trusted claim. Requiring both
    # "chevron" and "mixing" prevents a broad flow mechanism from opting in.
    words = _words(scene.get("keyword"))
    if not ({"chevron", "flow", "mixing"} <= words):
        return False
    return True


def noise_reduction_result_supported(scene):
    """Strict eligibility for the Scene-5 deterministic primary-result visual.

    This is intentionally result-only. It requires trusted jet-engine chevron
    grounding, the complete `noise + reduction` relation nucleus, and either the
    explicit Grounded Claim ownership/causal role or the exact runtime payoff
    equivalent produced by the locked five-scene plan. It never promotes a
    generic engine/noise visual and never introduces a new mechanism claim.
    """
    if not isinstance(scene, dict):
        return False

    explicit_claim = str(scene.get("owned_claim_id") or "").strip()
    if explicit_claim and explicit_claim != "noise_reduction":
        return False

    causal_role = str(scene.get("causal_role") or "").strip()
    structural_role = str(scene.get("role") or "").strip().lower()
    if causal_role:
        if causal_role != "primary_result":
            return False
    elif structural_role not in {"payoff", "result", "primary_result"}:
        return False

    if not trusted_grounding_present(scene):
        return False
    if not {"aircraft", "engine"}.issubset(set(subject_anchor_words(scene))):
        return False
    if set(required_explanatory_groups(scene)) != {"noise", "reduction"}:
        return False

    words = _words(scene.get("keyword"))
    if not ({"jet", "engine", "noise", "reduction"} <= words):
        return False
    if _noise_result_has_forbidden_expansion(scene):
        return False
    return True

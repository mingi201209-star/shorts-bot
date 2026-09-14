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
    "load": {"weight", "load", "loads", "loading", "force", "forces"},
    "wheel": {"wheel", "wheels", "tire", "tires", "tyre", "tyres", "landinggear"},
    "braking": {"brake", "brakes", "braking", "decelerate", "decelerates", "deceleration", "slow", "slowing"},
    "effect": {"effect", "effects", "effective", "effectiveness", "result", "results", "outcome", "outcomes"},
}

_GROUP_VISIBLE_REQUIREMENTS = {
    "flow": "a flow itself must be directly visible as airflow, exhaust, a stream, or a plume",
    "interface": "a meeting/interface/boundary/junction between two distinct visible flow or fluid regions must be directly visible; a single isolated plume is not enough",
    "mixing": "two or more visible flow regions must visibly mix, blend, or interleave; a static part close-up is not enough",
    "noise": "visible evidence must directly represent sound/noise rather than merely showing the source object",
    "reduction": "the visual must directly represent a reduction/lowering comparison or state, not merely the presence of the source object",
    "load": "the visual must directly represent load or weight transfer to a supported contact point; a generic aircraft or wing shot is not enough",
    "wheel": "aircraft landing gear wheels or tires must be directly visible and relevant to the represented relation",
    "braking": "the visual must directly represent aircraft braking, deceleration, or landing rollout rather than generic flight",
    "effect": "the claimed result/effect must be directly represented by a visible outcome or comparison; the causal subject alone is not enough",
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
    if not isinstance(scene, dict):
        return False
    supply = scene.get("_canonical_visual_supply") or {}
    if not isinstance(supply, dict):
        return False
    canonical = str(supply.get("canonical_subject") or "").strip().lower()
    source = str(supply.get("grounding_source") or "").strip()
    if not canonical or not source:
        return False
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
    words = _words(scene.get("keyword"))
    if not ({"chevron", "flow", "mixing"} <= words):
        return False
    return True


def noise_reduction_result_supported(scene):
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

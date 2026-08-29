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

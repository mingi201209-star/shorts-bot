"""Deterministic scene visual contract helpers.

The contract is deliberately metadata-only and budget-neutral. It does not
claim to recognize pixels; it prevents known-bad lineage from being accepted
as production-success when the selected visual never names the requested
subject component or phenomenon/action.
"""

from __future__ import annotations

import re


SUBJECT_GROUPS = {
    "aircraft": {"aircraft", "airplane", "plane", "aviation", "jet"},
    "wing": {"wing", "wings", "wingtip", "winglet"},
    "engine": {"engine", "nacelle", "nozzle", "turbine"},
    "bridge": {"bridge", "bridges"},
    "heart_valve": {"heart", "valve", "cardiac"},
    "skyscraper": {"skyscraper", "tower", "building"},
    "damper": {"damper", "mass", "pendulum"},
}

EVIDENCE_GROUPS = {
    "deformation": {
        "bend", "bends", "bending", "bent", "flex", "flexes", "flexing",
        "deform", "deforms", "deformation", "curvature", "휘어", "휘는",
    },
    "twisting": {
        "twist", "twists", "twisting", "torsion", "torsional", "비틀",
    },
    "load": {
        "load", "loads", "loading", "force", "forces", "stress", "weight",
        "하중", "응력",
    },
    "oscillation": {
        "oscillation", "oscillate", "oscillates", "oscillating", "vibration",
        "vibrate", "vibrates", "vibrating", "sway", "sways", "swaying",
        "motion", "movement", "shaking", "흔들", "진동",
    },
    "valve_motion": {
        "valve", "opening", "closing", "open", "close", "motion", "flow",
    },
    "damper_motion": {
        "damper", "pendulum", "swing", "sway", "oscillation", "motion",
    },
}

EVIDENCE_QUERY_TERMS = {
    "deformation": ("flex", "bending", "deformation"),
    "twisting": ("twisting", "torsion"),
    "load": ("load", "force"),
    "oscillation": ("oscillation", "motion"),
    "valve_motion": ("valve", "opening", "closing"),
    "damper_motion": ("damper", "motion"),
}

GENERIC_FALLBACK_TERMS = {
    "beauty", "beautiful", "generic", "cruise", "cruising", "flight",
    "flying", "cloud", "clouds", "sky", "runway", "cockpit", "landscape",
    "travel", "tourism", "background", "static", "still",
}


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("-", " "))


def _tokens(value):
    return set(re.findall(r"[a-z]+|[가-힣]+", _norm(value)))


def _contains_phrase_or_token(text, aliases):
    normalized = _norm(text)
    words = _tokens(normalized)
    for alias in aliases:
        alias_norm = _norm(alias)
        if " " in alias_norm and alias_norm in normalized:
            return True
        if alias_norm in words:
            return True
    return False


def _scene_text(scene):
    if isinstance(scene, dict):
        return " ".join(str(scene.get(key) or "") for key in ("text", "visual_goal", "keyword"))
    return str(scene or "")


def _metadata_text(selection):
    selection = dict(selection or {})
    values = [
        selection.get("metadata"),
        selection.get("title"),
        selection.get("tags"),
        selection.get("page_url"),
        selection.get("source_id"),
        selection.get("source_asset_id"),
        selection.get("template_type"),
        selection.get("mode"),
        selection.get("motion_profile"),
        selection.get("visible_components"),
        selection.get("visible_subject_groups"),
        selection.get("verification_evidence"),
        selection.get("current_scene_verification"),
    ]
    return " ".join(str(value or "") for value in values)


def build_visual_semantic_contract(scene):
    text = _scene_text(scene)
    subjects = [
        group for group, aliases in SUBJECT_GROUPS.items()
        if _contains_phrase_or_token(text, aliases)
    ]
    evidence = [
        group for group, aliases in EVIDENCE_GROUPS.items()
        if _contains_phrase_or_token(text, aliases)
    ]
    if ("deformation" in evidence or "twisting" in evidence) and "load" in evidence:
        evidence = [group for group in evidence if group != "load"]

    # Component-level aviation scenes must keep the component, not only domain.
    if "wing" in subjects and "aircraft" not in subjects:
        subjects.insert(0, "aircraft")

    forbidden = []
    if evidence:
        forbidden.extend(sorted(GENERIC_FALLBACK_TERMS))

    return {
        "required_subjects": subjects,
        "required_visual_evidence": evidence,
        "forbidden_generic_fallbacks": forbidden,
    }


def _missing_groups(required, metadata, groups):
    return [
        group for group in required
        if not _contains_phrase_or_token(metadata, groups.get(group, set()))
    ]


def evaluate_visual_semantic_contract(scene, selection):
    contract = build_visual_semantic_contract(scene)
    metadata = _metadata_text(selection)
    missing_subjects = _missing_groups(
        contract["required_subjects"],
        metadata,
        SUBJECT_GROUPS,
    )
    missing_evidence = _missing_groups(
        contract["required_visual_evidence"],
        metadata,
        EVIDENCE_GROUPS,
    )
    generic_terms = sorted(_tokens(metadata) & GENERIC_FALLBACK_TERMS)
    generic_only = bool(contract["required_visual_evidence"] and generic_terms and missing_evidence)

    if missing_subjects:
        return {
            "pass": False,
            "reason": "missing_required_subject_anchor",
            "missing_subjects": missing_subjects,
            "contract": contract,
        }
    if missing_evidence:
        return {
            "pass": False,
            "reason": "missing_required_visual_evidence",
            "missing_visual_evidence": missing_evidence,
            "generic_fallback_terms": generic_terms if generic_only else [],
            "contract": contract,
        }
    return {
        "pass": True,
        "reason": "semantic_visual_contract_pass",
        "contract": contract,
    }


def contract_requires_visual_evidence(scene_or_query):
    return bool(build_visual_semantic_contract(scene_or_query)["required_visual_evidence"])


def phenomenon_preserving_query(scene_or_query, *, base_query=None):
    """Return a retrieval query that keeps required phenomenon/action terms.

    This is deterministic and metadata-only: it does not relax acceptance, it
    only prevents retrieval from silently degrading "wing bending" into a bare
    "aircraft wing" query before candidate validation sees the request.
    """
    base = _norm(base_query if base_query is not None else _scene_text(scene_or_query))
    if not base:
        return base

    contract = build_visual_semantic_contract(scene_or_query)
    tokens = _tokens(base)
    additions = []
    for group in contract["required_visual_evidence"]:
        if _contains_phrase_or_token(base, EVIDENCE_GROUPS.get(group, set())):
            continue
        for term in EVIDENCE_QUERY_TERMS.get(group, (group,)):
            if term not in tokens and term not in additions:
                additions.append(term)

    if not additions:
        return base
    return _norm(" ".join([base] + additions))

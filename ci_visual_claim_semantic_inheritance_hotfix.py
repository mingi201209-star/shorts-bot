from pathlib import Path


path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
marker = "VISUAL_CLAIM_SEMANTIC_INHERITANCE_V1"
if marker not in text:
    text = text.rstrip() + r'''


# VISUAL_CLAIM_SEMANTIC_INHERITANCE_V1
# Preserve the owned grounded claim's explanatory semantics across the entire
# specificity ladder. Subject identity remains governed by Visual Subject Anchor
# V1/V2/#253; this layer only prevents a subject-correct but explanation-empty
# fallback asset from being promoted by GENERAL_VISUAL_PARITY.
_VISUAL_EXPLANATORY_STOP_WORDS = {
    "aircraft", "airplane", "airliner", "jet", "engine", "engines", "nacelle",
    "nacelles", "nozzle", "nozzles", "chevron", "chevrons", "wing", "wings",
    "window", "cabin", "spinner", "bridge", "tunnel", "road", "building",
    "mechanism", "detail", "stage", "closeup", "close", "view", "shot",
    "design", "structure", "system", "result", "effect",
}
_VISUAL_EXPLANATORY_ALIAS_GROUPS = (
    frozenset({"flow", "flows", "airflow", "airflows", "exhaust", "stream", "streams"}),
    frozenset({"interface", "boundary", "boundaries", "meet", "meeting", "junction", "shear"}),
    frozenset({"mix", "mixes", "mixed", "mixing", "blend", "blends", "blending"}),
    frozenset({"noise", "noisy", "acoustic", "acoustics", "sound", "sounds"}),
    frozenset({"reduce", "reduces", "reduced", "reduction", "decrease", "decreases", "lower", "lowering"}),
)
_CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT = {
    "required": False,
    "required_groups": [],
    "authority_query": "",
}


def _visual_explanatory_group_for_word(word):
    value = str(word or "").strip().lower()
    if not value or value in _VISUAL_EXPLANATORY_STOP_WORDS or value.isdigit():
        return ()
    for group in _VISUAL_EXPLANATORY_ALIAS_GROUPS:
        if value in group:
            return tuple(sorted(group))
    # Generic morphology normalization only; no topic-specific vocabulary.
    stem = value
    for suffix in ("ing", "ed", "es", "s"):
        if stem.endswith(suffix) and len(stem) - len(suffix) >= 4:
            stem = stem[:-len(suffix)]
            break
    return (stem, value) if stem != value else (value,)


def _required_explanatory_groups(authority_query):
    words = normalize_search_query(authority_query).split()
    groups = []
    seen = set()
    for word in words:
        group = _visual_explanatory_group_for_word(word)
        if not group:
            continue
        key = tuple(group)
        # Avoid treating a relation alias twice (e.g. flow/airflow).
        family_key = next((idx for idx, family in enumerate(_VISUAL_EXPLANATORY_ALIAS_GROUPS) if set(group) == set(family)), None)
        identity = ("family", family_key) if family_key is not None else ("word", group[0])
        if identity in seen:
            continue
        seen.add(identity)
        groups.append(list(group))
    return groups


def _set_visual_claim_semantic_contract(authority_query):
    global _CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT
    groups = _required_explanatory_groups(authority_query)
    _CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT = {
        "required": bool(groups),
        "required_groups": groups,
        "authority_query": normalize_search_query(authority_query),
    }
    return dict(_CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT)


def get_current_visual_claim_semantic_contract():
    return {
        "required": bool(_CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT.get("required")),
        "required_groups": [list(group) for group in _CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT.get("required_groups") or []],
        "authority_query": str(_CURRENT_VISUAL_CLAIM_SEMANTIC_CONTRACT.get("authority_query") or ""),
    }


def _candidate_supports_explanatory_contract(candidate, contract=None):
    contract = contract or get_current_visual_claim_semantic_contract()
    if not contract.get("required"):
        return True, []
    metadata_words = set(normalize_search_query(_candidate_metadata(candidate)).split())
    missing = []
    for group in contract.get("required_groups") or []:
        aliases = set(group)
        if not (metadata_words & aliases):
            missing.append(group)
    return not missing, missing


_claim_semantics_previous_subject_enforcer = enforce_visual_subject_anchor_query


def enforce_visual_subject_anchor_query(*, narration, visual_goal, query, visual_type="real_world_broll"):
    effective = _claim_semantics_previous_subject_enforcer(
        narration=narration,
        visual_goal=visual_goal,
        query=query,
        visual_type=visual_type,
    )
    # #251 already makes factual grounded keywords a deterministic retrieval
    # representation of the owned claim. Capture that ORIGINAL grounded query
    # before any specificity fallback can remove relation/state terms.
    contract = _set_visual_claim_semantic_contract(query)
    if contract.get("required"):
        print(
            "[VISUAL_CLAIM_SEMANTICS] "
            f"authority={contract.get('authority_query') or 'none'} "
            f"groups={len(contract.get('required_groups') or [])}"
        )
    return effective


_claim_semantics_previous_general_tier = general_scene_unknown_safe_tier


def general_scene_unknown_safe_tier(candidate, scene_query):
    contract = get_current_visual_claim_semantic_contract()
    supported, missing = _candidate_supports_explanatory_contract(candidate, contract)
    if contract.get("required") and not supported:
        print(
            "[VISUAL_CLAIM_SEMANTIC_REJECT] "
            f"candidate={candidate.get('source_id', candidate.get('id'))} "
            f"authority={contract.get('authority_query') or 'none'} "
            f"missing_groups={len(missing)}"
        )
        return 5, "MISSING_REQUIRED_EXPLANATORY_SEMANTICS"
    return _claim_semantics_previous_general_tier(candidate, scene_query)


_claim_semantics_previous_final_selection = get_last_final_visual_selection


def get_last_final_visual_selection():
    selection = _claim_semantics_previous_final_selection()
    contract = get_current_visual_claim_semantic_contract()
    selection["claim_semantic_contract_required"] = bool(contract.get("required"))
    selection["required_explanatory_anchors"] = [list(group) for group in contract.get("required_groups") or []]
    selection["claim_semantic_authority_query"] = str(contract.get("authority_query") or "")
    return selection
''' + "\n"
    path.write_text(text, encoding="utf-8")

print("✅ Visual claim-semantic inheritance applied: fallback keeps grounded explanatory semantics")

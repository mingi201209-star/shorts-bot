from __future__ import annotations

from copy import deepcopy
import json
import re

_PROTECTED_ROLES = {"phenomenon", "question", "hook", "reveal", "payoff", "conclusion"}
_VISUAL_INHERIT_FIELDS = (
    "visual_goal",
    "keyword",
    "search_intent",
    "visual_intent",
    "visual_contract",
)
_FACT_EVIDENCE_FIELDS = (
    "fact_id",
    "fact_ids",
    "fact_evidence",
    "fact_evidence_reference",
    "evidence_ids",
)


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _role(scene):
    return _norm((scene or {}).get("role") or (scene or {}).get("scene_role"))


def _visual_family(scene):
    scene = scene or {}
    goal = _norm(scene.get("visual_goal"))
    keyword = _norm(scene.get("keyword"))
    return (goal, keyword)


def information_fingerprint(scene):
    """Return the exact normalized narration identity for V1 compaction.

    V1 deliberately does not use fuzzy semantics, embeddings, or an LLM. Visual
    metadata is not information identity: the same narration remains one information
    beat even when Writer emitted different visual_goal/keyword values.
    """
    return (_norm((scene or {}).get("text")),)


def _stable_value(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError:
        return str(value)


def _fact_evidence_compatible(donor, recipient):
    """Fail closed when both Scenes carry conflicting explicit FACT lineage."""
    for key in _FACT_EVIDENCE_FIELDS:
        left = donor.get(key)
        right = recipient.get(key)
        if left not in (None, "", [], {}) and right not in (None, "", [], {}):
            if _stable_value(left) != _stable_value(right):
                return False
    return True


def _supported_fact_safe_visual(scene):
    """Use the existing Visual Explanation contract as the deterministic support gate."""
    try:
        from video.visual_explanation import annotation_fact_safe, plan_explanation

        plan = plan_explanation(scene)
        return bool(plan and annotation_fact_safe(scene, plan))
    except Exception:
        return False


def _inherit_supported_visual_contract(donor, recipient):
    """Return recipient with donor visual metadata only when the existing gate proves safe."""
    if not _fact_evidence_compatible(donor, recipient):
        return dict(recipient), False
    if not _supported_fact_safe_visual(donor):
        return dict(recipient), False

    candidate = dict(recipient)
    for key in _VISUAL_INHERIT_FIELDS:
        if key in donor:
            candidate[key] = deepcopy(donor[key])

    # Re-check after inheritance against the recipient's unchanged narration.
    if not _supported_fact_safe_visual(candidate):
        return dict(recipient), False
    return candidate, True


def compact_duplicate_visual_demand(script):
    """Compact exact narration duplicates while protecting terminal/story roles.

    Rules are intentionally narrow:
    - exact normalized narration only;
    - no protected Scene is deleted;
    - one protected Scene may replace earlier non-protected duplicates;
    - multiple protected duplicates are left untouched (ambiguous, fail closed);
    - when the retained protected Scene lacks a supported visual contract, an earlier
      non-protected duplicate may donate only existing, fact-safe visual metadata.
    """
    result = deepcopy(script or {})
    scenes = [dict(scene or {}) for scene in list(result.get("scenes") or [])]
    groups = {}
    for index, item in enumerate(scenes):
        text = information_fingerprint(item)[0]
        if text:
            groups.setdefault(text, []).append(index)

    remove_indexes = set()
    inheritance_by_recipient = {}

    for text, indexes in groups.items():
        if len(indexes) < 2:
            continue
        protected = [i for i in indexes if _role(scenes[i]) in _PROTECTED_ROLES]
        non_protected = [i for i in indexes if _role(scenes[i]) not in _PROTECTED_ROLES]

        # Protected/protected conflicts are intentionally not auto-compacted.
        if len(protected) > 1:
            continue

        if len(protected) == 1:
            recipient_index = protected[0]
            recipient = scenes[recipient_index]
            donors = [i for i in non_protected if i < recipient_index]
            if not donors:
                continue

            # Preserve the protected Scene. If its own visual contract is unsupported,
            # prefer the nearest earlier exact-narration donor that the existing
            # Visual Explanation gate proves supported and FACT-safe.
            if not _supported_fact_safe_visual(recipient):
                for donor_index in reversed(donors):
                    inherited, ok = _inherit_supported_visual_contract(
                        scenes[donor_index], recipient
                    )
                    if ok:
                        scenes[recipient_index] = inherited
                        inheritance_by_recipient[recipient_index] = donor_index
                        break

            # Information identity is exact narration, so the earlier intermediate
            # duplicates are redundant regardless of their visual metadata.
            remove_indexes.update(donors)
            continue

        # No protected Scene: keep the earliest information beat and compact later
        # exact narration duplicates. This is deterministic and preserves order.
        remove_indexes.update(indexes[1:])

    compacted = []
    removed = []
    for index, item in enumerate(scenes):
        if index in remove_indexes:
            removed.append({
                "scene_index": index,
                "human_scene_number": index + 1,
                "role": _role(item),
                "text": str(item.get("text") or ""),
                "visual_goal": str(item.get("visual_goal") or ""),
                "keyword": str(item.get("keyword") or ""),
                "reason": "exact_normalized_narration_duplicate",
            })
            continue
        compacted.append(item)

    inherited = []
    for recipient_index, donor_index in sorted(inheritance_by_recipient.items()):
        inherited.append({
            "recipient_scene_index": recipient_index,
            "recipient_human_scene_number": recipient_index + 1,
            "donor_scene_index": donor_index,
            "donor_human_scene_number": donor_index + 1,
            "fields": [key for key in _VISUAL_INHERIT_FIELDS if key in scenes[donor_index]],
            "reason": "supported_fact_safe_visual_contract_inheritance",
        })

    result["scenes"] = compacted
    result["script_visual_budget"] = {
        "version": "v1",
        "original_scene_count": len(scenes),
        "final_scene_count": len(compacted),
        "removed_duplicate_count": len(removed),
        "removed_duplicates": removed,
        "visual_contract_inheritance_count": len(inherited),
        "visual_contract_inheritances": inherited,
        "extra_llm_calls": 0,
    }
    if removed:
        print(
            "[SCRIPT_VISUAL_BUDGET_V1] compacted="
            f"{len(removed)} scenes={','.join(str(x['human_scene_number']) for x in removed)} "
            f"inherited={len(inherited)}"
        )
    else:
        print("[SCRIPT_VISUAL_BUDGET_V1] compacted=0 inherited=0")
    return result

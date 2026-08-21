from pathlib import Path

path = Path("video/hook_visual.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "    candidate_visible_component_evidence,\n)",
    "    candidate_visible_component_evidence,\n    safe_reuse_candidate,\n)",
    1,
)

marker = "_LAST_HOOK_SELECTION = None\n"
helper = r'''

# HOOK_FALLBACK_QUALITY_FLOOR

def _hook_fallback_quality(candidate, scene_query):
    semantic = concrete_visual_evidence(candidate, scene_query)
    visual = candidate_visible_component_evidence(candidate, scene_query)
    required = list(semantic.get("required") or [])
    detected = list(semantic.get("detected") or [])
    complete_anchor = bool(required) and len(detected) == len(required)
    same_domain = bool(required and required[0] in detected)

    if visual.get("state") == "TRUE" and complete_anchor:
        tier = 5
        label = "DIRECT_VERIFIED"
    elif visual.get("state") == "UNKNOWN" and complete_anchor:
        tier = 3
        label = "COMPONENT_RELEVANT_FALLBACK"
    elif same_domain:
        # FALSE is intentionally below UNKNOWN complete-anchor evidence.
        tier = 2 if visual.get("state") != "FALSE" else 1
        label = "SAME_DOMAIN_CONTEXTUAL"
    else:
        tier = 0
        label = "LAST_RESORT"

    return {
        "tier": tier,
        "label": label,
        "visual": visual,
        "semantic": semantic,
        "complete_anchor": complete_anchor,
        "same_domain": same_domain,
    }


def _choose_hook_fallback(scored_items, scene_query):
    reusable = safe_reuse_candidate(scene_query)
    if reusable is not None:
        visual = candidate_visible_component_evidence(reusable, scene_query)
        if visual.get("state") == "TRUE":
            return reusable, {
                "tier": 4,
                "label": "VERIFIED_COMPATIBLE_REUSE",
                "visual": visual,
                "semantic": concrete_visual_evidence(reusable, scene_query),
                "reuse": True,
            }, None

    ranked = []
    for item in scored_items or []:
        candidate = item.get("candidate")
        if not candidate:
            continue
        quality = _hook_fallback_quality(candidate, scene_query)
        ranked.append((
            -quality["tier"],
            -float(item.get("total_score", 0.0)),
            int(candidate.get("search_position", 9999)),
            candidate,
            quality,
            item,
        ))
    if not ranked:
        return None, None, None
    ranked.sort(key=lambda row: (row[0], row[1], row[2]))
    _, _, _, candidate, quality, item = ranked[0]
    return candidate, quality, item
'''
if "HOOK_FALLBACK_QUALITY_FLOOR" not in text:
    if marker not in text:
        raise RuntimeError("Hook selection marker missing")
    text = text.replace(marker, marker + helper, 1)

text = text.replace(
    "    strict_best = None\n    fallback_best = None\n    dominance_checks = 0\n",
    "    strict_best = None\n    fallback_best = None\n    fallback_scored = []\n    dominance_checks = 0\n",
    1,
)
text = text.replace(
    "        if scored and (fallback_best is None or scored[0]['total_score'] > fallback_best['total_score']):\n            fallback_best = scored[0]\n",
    "        fallback_scored.extend(scored)\n"
    "        if scored and (fallback_best is None or scored[0]['total_score'] > fallback_best['total_score']):\n"
    "            fallback_best = scored[0]\n",
    1,
)

old = '''    if fallback_best is not None:
        candidate = fallback_best['candidate']
        _mark_candidate_used(candidate)
        visual = candidate_visible_component_evidence(candidate, audit.get('effective_query') or original_query)
        audit['selected'] = {
            'id': candidate.get('id'),
            'provider': candidate.get('provider', 'pexels'),
            'source_id': candidate.get('source_id', candidate.get('id')),
            'page_url': candidate.get('page_url'),
            'scores': fallback_best.get('scores'),
            'total_score': fallback_best.get('total_score'),
            'mode': 'UNVERIFIED_CONTEXTUAL_FALLBACK',
            'visual_evidence': visual.get('state'),
        }
        _record_hook_selection(
            candidate, mode='UNVERIFIED_CONTEXTUAL_FALLBACK',
            query=audit.get('effective_query') or original_query, visual=visual,
            dominance=fallback_best.get('dominance'),
            fallback_reason=audit.get('fallback_reason'),
        )
        print(
            '[VIDEO_SELECTED] '
            f'provider={candidate.get("provider", "pexels")} '
            f'source_id={candidate.get("source_id", candidate.get("id"))} scene=hook_fallback'
        )
        print_hook_visual_audit(audit)
        return candidate['url']
'''
new = '''    if fallback_scored:
        fallback_query = audit.get('effective_query') or original_query
        candidate, quality, fallback_item = _choose_hook_fallback(fallback_scored, fallback_query)
        if candidate is not None:
            _mark_candidate_used(candidate)
            visual = quality.get('visual') or candidate_visible_component_evidence(candidate, fallback_query)
            mode = quality.get('label') or 'LAST_RESORT'
            audit['selected'] = {
                'id': candidate.get('id'),
                'provider': candidate.get('provider', 'pexels'),
                'source_id': candidate.get('source_id', candidate.get('id')),
                'page_url': candidate.get('page_url'),
                'scores': (fallback_item or {}).get('scores'),
                'total_score': (fallback_item or {}).get('total_score'),
                'mode': mode,
                'visual_evidence': visual.get('state'),
                'fallback_tier': quality.get('tier'),
                'semantic_anchor_complete': quality.get('semantic', {}).get('complete'),
                'reuse': bool(candidate.get('_safe_reuse')),
            }
            _record_hook_selection(
                candidate, mode=mode,
                query=fallback_query, visual=visual,
                dominance=(fallback_item or {}).get('dominance'),
                fallback_reason=(
                    f"quality_floor tier={quality.get('tier')} "
                    f"state={visual.get('state')} reuse={bool(candidate.get('_safe_reuse'))}"
                ),
            )
            print(
                '[HOOK_FALLBACK] '
                f'candidate_id={_stable_hook_candidate_id(candidate)} '
                f'required={"+".join(visual.get("required", [])) or "none"} '
                f'visual={visual.get("state", "UNKNOWN")} '
                f'anchor_complete={str(quality.get("semantic", {}).get("complete", False)).lower()} '
                f'reuse={str(bool(candidate.get("_safe_reuse"))).lower()} '
                f'tier={quality.get("tier")} mode={mode} '
                f'reason=quality_floor'
            )
            print_hook_visual_audit(audit)
            return candidate['url']
'''
if old not in text:
    raise RuntimeError("#27 fallback block not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("✅ Hook fallback quality floor applied; no new vision/API calls")

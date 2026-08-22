from pathlib import Path


# Production parity fix: preserve the verified Hook candidate identity/mode through
# the renderer and stop strict-gate failures from silently re-entering as direct.
path = Path("video/hook_visual.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "HOOK_DOMINANCE_MAX_CANDIDATES = 3\n",
    "HOOK_DOMINANCE_MAX_CANDIDATES = 3\n\n"
    "_LAST_HOOK_SELECTION = None\n\n"
    "def _stable_hook_candidate_id(candidate):\n"
    "    provider = str(candidate.get('provider', 'pexels') or 'pexels')\n"
    "    source_id = candidate.get('source_id', candidate.get('id'))\n"
    "    if source_id is not None:\n"
    "        return f'{provider}:{source_id}'\n"
    "    return f'url:{candidate.get(\"url\", \"unknown\")}'\n\n"
    "def _record_hook_selection(candidate, *, mode, query, visual=None, dominance=None, fallback_reason=None):\n"
    "    global _LAST_HOOK_SELECTION\n"
    "    visual = visual or {'state': 'UNKNOWN', 'required': [], 'visible': [], 'source': 'none'}\n"
    "    _LAST_HOOK_SELECTION = {\n"
    "        'candidate_id': _stable_hook_candidate_id(candidate),\n"
    "        'provider': str(candidate.get('provider', 'pexels') or 'pexels'),\n"
    "        'source_id': candidate.get('source_id', candidate.get('id')),\n"
    "        'url': candidate.get('url'),\n"
    "        'query': query,\n"
    "        'selection_mode': mode,\n"
    "        'required_components': list(visual.get('required') or []),\n"
    "        'visible_components': list(visual.get('visible') or []),\n"
    "        'visual_evidence': str(visual.get('state', 'UNKNOWN')),\n"
    "        'provenance': str(visual.get('source', 'none')),\n"
    "        'vision_segment': {'start': 0.0, 'end': 2.7} if dominance is not None else None,\n"
    "        'fallback_reason': fallback_reason,\n"
    "    }\n"
    "    return dict(_LAST_HOOK_SELECTION)\n\n"
    "def get_last_hook_selection():\n"
    "    return dict(_LAST_HOOK_SELECTION) if isinstance(_LAST_HOOK_SELECTION, dict) else None\n\n"
    "def record_last_resort_selection(video_url, scene, reason):\n"
    "    candidate = {'url': video_url, 'provider': 'unknown', 'source_id': None}\n"
    "    return _record_hook_selection(\n"
    "        candidate, mode='LAST_RESORT', query=str(scene.get('keyword', '')),\n"
    "        visual={'state': 'UNKNOWN', 'required': [], 'visible': [], 'source': 'none'},\n"
    "        fallback_reason=reason,\n"
    "    )\n\n"
    "def hook_render_contract(trace, *, render_start, render_duration, final_url):\n"
    "    trace = dict(trace or {})\n"
    "    trace['render_segment'] = {\n"
    "        'start': float(render_start),\n"
    "        'end': float(render_start) + float(render_duration),\n"
    "    }\n"
    "    trace['final_url_match'] = bool(trace.get('url') and trace.get('url') == final_url)\n"
    "    direct = trace.get('selection_mode') == 'DIRECT_VERIFIED'\n"
    "    vision = trace.get('vision_segment') or {}\n"
    "    segment_match = (not direct) or abs(float(vision.get('start', -999)) - float(render_start)) < 1e-6\n"
    "    evidence_ok = (not direct) or trace.get('visual_evidence') == 'TRUE'\n"
    "    valid = bool(trace.get('final_url_match') and segment_match and evidence_ok)\n"
    "    if direct and not valid:\n"
    "        trace['contract_violation'] = True\n"
    "        trace['selection_mode'] = 'UNVERIFIED_CONTEXTUAL_FALLBACK'\n"
    "        trace['fallback_reason'] = 'verified contract lost before render'\n"
    "    else:\n"
    "        trace['contract_violation'] = False\n"
    "    trace['render_contract_valid'] = valid\n"
    "    return trace\n",
    1,
)

text = text.replace(
    "    strict_best = None\n    dominance_checks = 0\n",
    "    strict_best = None\n    fallback_best = None\n    dominance_checks = 0\n",
    1,
)
text = text.replace(
    "        scored.sort(key=lambda item: item[\"total_score\"], reverse=True)\n",
    "        scored.sort(key=lambda item: item[\"total_score\"], reverse=True)\n"
    "        if scored and (fallback_best is None or scored[0]['total_score'] > fallback_best['total_score']):\n"
    "            fallback_best = scored[0]\n",
    1,
)
text = text.replace(
    "        print_hook_visual_audit(audit)\n        return candidate[\"url\"]\n\n    audit[\"fallback\"] = True\n",
    "        visual = candidate_visible_component_evidence(candidate, audit.get('effective_query') or original_query)\n"
    "        _record_hook_selection(\n"
    "            candidate, mode='DIRECT_VERIFIED', query=audit.get('effective_query') or original_query,\n"
    "            visual=visual, dominance=strict_best.get('dominance'),\n"
    "        )\n"
    "        print_hook_visual_audit(audit)\n        return candidate[\"url\"]\n\n    audit[\"fallback\"] = True\n",
    1,
)

fallback_new = (
    "    if fallback_best is not None:\n"
    "        candidate = fallback_best['candidate']\n"
    "        _mark_candidate_used(candidate)\n"
    "        visual = candidate_visible_component_evidence(candidate, audit.get('effective_query') or original_query)\n"
    "        audit['selected'] = {\n"
    "            'id': candidate.get('id'),\n"
    "            'provider': candidate.get('provider', 'pexels'),\n"
    "            'source_id': candidate.get('source_id', candidate.get('id')),\n"
    "            'page_url': candidate.get('page_url'),\n"
    "            'scores': fallback_best.get('scores'),\n"
    "            'total_score': fallback_best.get('total_score'),\n"
    "            'mode': 'UNVERIFIED_CONTEXTUAL_FALLBACK',\n"
    "            'visual_evidence': visual.get('state'),\n"
    "        }\n"
    "        _record_hook_selection(\n"
    "            candidate, mode='UNVERIFIED_CONTEXTUAL_FALLBACK',\n"
    "            query=audit.get('effective_query') or original_query, visual=visual,\n"
    "            dominance=fallback_best.get('dominance'),\n"
    "            fallback_reason=audit.get('fallback_reason'),\n"
    "        )\n"
    "        print(\n"
    "            '[VIDEO_SELECTED] '\n"
    "            f'provider={candidate.get(\"provider\", \"pexels\")} '\n"
    "            f'source_id={candidate.get(\"source_id\", candidate.get(\"id\"))} scene=hook_fallback'\n"
    "        )\n"
    "        print_hook_visual_audit(audit)\n"
    "        return candidate['url']\n"
    "    fallback_query = (\n"
    "        component_profile['queries'][0]\n"
    "        if component_profile else original_query\n"
    "    )\n"
    "    video_url = fetch_pexels_video(fallback_query)\n"
    "    record_last_resort_selection(video_url, {**scene, 'keyword': fallback_query}, audit.get('fallback_reason'))\n"
    "    print_hook_visual_audit(audit)\n"
    "    return video_url\n"
)

fallback_markers = [
    "    print_hook_visual_audit(audit)\n    return fetch_video(original_query)\n",
    "    print_hook_visual_audit(audit)\n    if component_profile:\n        # Do not throw away the named component at the final fallback. A targeted\n        # component query is still preferable to a generic whole-aircraft shot.\n        return fetch_pexels_video(component_profile[\"queries\"][0])\n    return fetch_pexels_video(original_query)\n",
]
if fallback_new not in text:
    matched = False
    for fallback_old in fallback_markers:
        if fallback_old in text:
            text = text.replace(fallback_old, fallback_new, 1)
            matched = True
            break
    if not matched:
        raise RuntimeError("production Hook unified fallback marker not found")
path.write_text(text, encoding="utf-8")


# Renderer parity: retain the selected candidate trace and validate that the render
# starts at the same temporal origin that the Hook vision inspected.
path = Path("video/video_engine.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "                from video.hook_visual import (\n                    fetch_hook_pexels_video,\n                )\n",
    "                from video.hook_visual import (\n"
    "                    fetch_hook_pexels_video,\n"
    "                    get_last_hook_selection,\n"
    "                    hook_render_contract,\n"
    "                    record_last_resort_selection,\n"
    "                )\n",
    1,
)
text = text.replace(
    "                video_url = (\n                    fetch_video(\n                        keyword\n                    )\n                )\n",
    "                video_url = (\n                    fetch_video(\n                        keyword\n                    )\n                )\n"
    "                try:\n"
    "                    record_last_resort_selection(video_url, item, f'hook selector exception: {type(e).__name__}')\n"
    "                except Exception:\n"
    "                    pass\n",
    1,
)
text = text.replace(
    "        if not video_url:\n\n            raise RuntimeError(\n",
    "        if hook_scene_enabled:\n"
    "            try:\n"
    "                trace = get_last_hook_selection()\n"
    "                contract = hook_render_contract(\n"
    "                    trace, render_start=0.0, render_duration=duration, final_url=video_url\n"
    "                )\n"
    "                print(\n"
    "                    '[VISUAL_TRACE] '\n"
    "                    f'scene={idx + 1} hook=true candidate_id={contract.get(\"candidate_id\")} '\n"
    "                    f'provider={contract.get(\"provider\")} query={keyword} '\n"
    "                    f'required={\"+\".join(contract.get(\"required_components\", [])) or \"none\"} '\n"
    "                    f'visual={contract.get(\"visual_evidence\", \"UNKNOWN\")} '\n"
    "                    f'provenance={contract.get(\"provenance\", \"none\")} '\n"
    "                    f'vision_segment={contract.get(\"vision_segment\")} '\n"
    "                    f'render_segment={contract.get(\"render_segment\")} '\n"
    "                    f'final_candidate_id={contract.get(\"candidate_id\")}'\n"
    "                )\n"
    "                print(\n"
    "                    '[VISUAL_CONTRACT] '\n"
    "                    f'mode={contract.get(\"selection_mode\")} valid={str(contract.get(\"render_contract_valid\")).lower()} '\n"
    "                    f'fallback_reason={contract.get(\"fallback_reason\") or \"none\"}'\n"
    "                )\n"
    "            except Exception as trace_error:\n"
    "                print(f'[VISUAL_CONTRACT] mode=LAST_RESORT valid=false fallback_reason=trace_error:{type(trace_error).__name__}')\n"
    "\n"
    "        if not video_url:\n\n            raise RuntimeError(\n",
    1,
)
path.write_text(text, encoding="utf-8")

print("✅ Hook production parity contract applied; no new vision calls")

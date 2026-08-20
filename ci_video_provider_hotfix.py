from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} marker mismatch count={text.count(old)}")
    return text.replace(old, new, 1)


# video_downloader: preserve legacy Pexels function; add unified pool beside it.
path = Path("video/video_downloader.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    "import requests\n\nfrom config import (\n",
    "import requests\n\nfrom video.video_providers import (\n    PIXABAY_API_KEY,\n    VIDEO_PROVIDER_PER_PAGE,\n    VIDEO_PROVIDER_POOL_MAX,\n    candidate_metadata_text,\n    candidate_unique_key,\n    merge_provider_candidates,\n    normalize_pexels_candidate,\n    search_pixabay_candidates,\n)\n\nfrom config import (\n",
    "provider imports",
)
text = replace_once(
    text,
    '''def _historical_candidate_safe(candidate):\n    slug = _page_slug(candidate.get("page_url"))\n''',
    '''def _candidate_metadata(candidate):\n    return normalize_search_query(candidate_metadata_text(candidate))\n\n\ndef _candidate_unique_key(candidate):\n    return candidate_unique_key(candidate)\n\n\ndef _candidate_is_used(candidate):\n    key = _candidate_unique_key(candidate)\n    if key in USED_VIDEO_IDS:\n        return True\n    return (\n        str(candidate.get("provider") or "pexels") == "pexels"\n        and candidate.get("id") in USED_VIDEO_IDS\n    )\n\n\ndef _mark_candidate_used(candidate):\n    USED_VIDEO_IDS.add(_candidate_unique_key(candidate))\n    if str(candidate.get("provider") or "pexels") == "pexels":\n        video_id = candidate.get("id")\n        if video_id is not None:\n            USED_VIDEO_IDS.add(video_id)\n\n\ndef _historical_candidate_safe(candidate):\n    slug = _candidate_metadata(candidate)\n''',
    "provider-aware candidate helpers",
)
text = text.replace(
    '_page_slug(candidate.get("page_url"))',
    '_candidate_metadata(candidate)',
)
text = replace_once(
    text,
    '''    ordered = [\n        item for item in ordered\n        if item.get("id") not in USED_VIDEO_IDS\n    ]\n''',
    '''    ordered = [\n        item for item in ordered\n        if not _candidate_is_used(item)\n    ]\n''',
    "provider-aware dedupe",
)
text = replace_once(
    text,
    '''        video_id = best.get("id")\n        if video_id is not None:\n            USED_VIDEO_IDS.add(video_id)\n\n        print(\n            "🎥 Pexels 검색 후보 "\n''',
    '''        video_id = best.get("id")\n        _mark_candidate_used(best)\n\n        print(\n            "🎥 Pexels 검색 후보 "\n''',
    "legacy pexels mark-used",
)

provider_functions = r'''

def search_video_candidates(query, per_page=None):
    """Collect a bounded normalized pool while isolating provider failures."""
    limit = VIDEO_PROVIDER_PER_PAGE if per_page is None else min(VIDEO_PROVIDER_PER_PAGE, int(per_page))
    provider_results = []

    try:
        pexels = [
            normalize_pexels_candidate(item)
            for item in search_pexels_candidates(query, per_page=limit)
        ]
        print(f"[VIDEO_PROVIDER] provider=pexels candidates={len(pexels)}")
        provider_results.append(pexels)
    except Exception as exc:
        print(f"[VIDEO_PROVIDER_SKIP] provider=pexels reason={type(exc).__name__}")

    if PIXABAY_API_KEY:
        try:
            pixabay = search_pixabay_candidates(query, per_page=limit)
            print(f"[VIDEO_PROVIDER] provider=pixabay candidates={len(pixabay)}")
            provider_results.append(pixabay)
        except Exception as exc:
            print(f"[VIDEO_PROVIDER_SKIP] provider=pixabay reason={type(exc).__name__}")
    else:
        print("[VIDEO_PROVIDER_SKIP] provider=pixabay reason=missing_api_key")

    return merge_provider_candidates(provider_results, total_limit=VIDEO_PROVIDER_POOL_MAX)


def fetch_video(query):
    """Unified provider selection. With no extra provider key, legacy Pexels path is exact."""
    if not PIXABAY_API_KEY:
        return fetch_pexels_video(query)

    original_query = str(query).strip()
    normalized_original = normalize_search_query(original_query)
    effective_query, context_lock = build_context_locked_query(original_query)
    historical = bool(context_lock)
    queries = [effective_query]

    if historical:
        fallback = _fallback_query_for_lock(context_lock)
        if fallback not in queries:
            queries.append(fallback)
    else:
        for fallback in _general_fallback_queries(effective_query):
            if fallback not in queries:
                queries.append(fallback)

    for search_query in queries:
        candidates = search_video_candidates(search_query, per_page=VIDEO_PROVIDER_PER_PAGE)
        best = choose_best_candidate(
            candidates,
            relevant_top_n=(min(3, PEXELS_RELEVANT_TOP_N) if historical else PEXELS_RELEVANT_TOP_N),
            historical=historical,
            subject_filter_query=search_query,
        )
        if not best:
            continue
        _mark_candidate_used(best)
        provider = str(best.get("provider") or "pexels")
        source_id = best.get("source_id", best.get("id"))
        print(f"[VIDEO_SELECTED] provider={provider} source_id={source_id} scene=general")
        return best["url"]

    return None

'''
text = replace_once(
    text,
    "\ndef download_video(\n",
    provider_functions + "\ndef download_video(\n",
    "unified provider functions",
)
path.write_text(text, encoding="utf-8")


# hook_visual: use the same candidate pool, scoring thresholds and dominance.
path = Path("video/hook_visual.py")
text = path.read_text(encoding="utf-8")
text = text.replace("    fetch_pexels_video,\n", "    fetch_video,\n")
text = text.replace("    search_pexels_candidates,\n", "    search_video_candidates,\n")
text = replace_once(
    text,
    "    _page_slug,\n",
    "    _page_slug,\n    _candidate_is_used,\n    _candidate_mark_used_placeholder,\n" if False else "    _page_slug,\n    _candidate_is_used,\n    _mark_candidate_used,\n    _candidate_metadata,\n",
    "hook provider helpers",
)
text = replace_once(
    text,
    '''    ordered = [\n        item for item in ordered\n        if item.get("id") not in USED_VIDEO_IDS\n    ]\n''',
    '''    ordered = [\n        item for item in ordered\n        if not _candidate_is_used(item)\n    ]\n''',
    "hook provider-aware dedupe",
)
text = text.replace(
    'slug = _page_slug(candidate.get("page_url"))',
    'slug = _candidate_metadata(candidate)',
)
text = text.replace("search_pexels_candidates(\n", "search_video_candidates(\n")
text = text.replace("fetch_pexels_video(original_query)", "fetch_video(original_query)")
text = text.replace(
    '''        video_id = candidate.get("id")\n        if video_id is not None:\n            USED_VIDEO_IDS.add(video_id)\n''',
    '''        video_id = candidate.get("id")\n        _mark_candidate_used(candidate)\n''',
)
text = text.replace(
    '_page_slug(candidate.get("page_url"))',
    '_candidate_metadata(candidate)',
)
text = text.replace(
    '''            "id": video_id,\n            "page_url": candidate.get("page_url"),\n''',
    '''            "id": video_id,\n            "provider": candidate.get("provider", "pexels"),\n            "source_id": candidate.get("source_id", video_id),\n            "page_url": candidate.get("page_url"),\n''',
)
text = text.replace(
    '''        print_hook_visual_audit(audit)\n        return candidate["url"]\n''',
    '''        print(\n            "[VIDEO_SELECTED] "\n            f"provider={candidate.get('provider', 'pexels')} "\n            f"source_id={candidate.get('source_id', video_id)} scene=hook"\n        )\n        print_hook_visual_audit(audit)\n        return candidate["url"]\n''',
    1,
)
path.write_text(text, encoding="utf-8")


# video_engine: only route normal/fallback searches through unified selector.
path = Path("video/video_engine.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''from video.video_downloader import (\n    fetch_pexels_video,\n    download_video,\n)\n''',
    '''from video.video_downloader import (\n    fetch_video,\n    download_video,\n)\n''',
    "video engine provider import",
)
text = text.replace("fetch_pexels_video(\n", "fetch_video(\n")
text = text.replace("🔎 Pexels 검색:", "🔎 Video provider search:")
text = text.replace("기존 Pexels 경로로 fallback", "기존 unified provider 경로로 fallback")
text = text.replace("Pexels에서 영상을 ", "video providers에서 영상을 ")
path.write_text(text, encoding="utf-8")

print("✅ Multi-provider video pool hotfix applied (Pexels + optional Pixabay)")

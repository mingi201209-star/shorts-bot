import os

import requests


PIXABAY_VIDEO_API = "https://pixabay.com/api/videos/"
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
VIDEO_PROVIDER_PER_PAGE = max(3, min(12, int(os.environ.get("VIDEO_PROVIDER_PER_PAGE", "6"))))
VIDEO_PROVIDER_POOL_MAX = max(6, min(24, int(os.environ.get("VIDEO_PROVIDER_POOL_MAX", "12"))))


def candidate_unique_key(candidate):
    provider = str(candidate.get("provider") or "pexels").strip().lower()
    source_id = candidate.get("source_id", candidate.get("id"))
    return f"{provider}:{source_id}"


def candidate_metadata_text(candidate):
    values = [
        candidate.get("page_url", ""),
        candidate.get("source_url", ""),
        candidate.get("metadata_text", ""),
        candidate.get("title", ""),
        candidate.get("description", ""),
        candidate.get("tags", ""),
    ]
    return " ".join(str(value or "") for value in values).strip()


def normalize_pexels_candidate(candidate):
    item = dict(candidate)
    source_id = item.get("source_id", item.get("id"))
    source_url = str(item.get("source_url") or item.get("page_url") or "")
    download_url = str(item.get("download_url") or item.get("url") or "")
    item.update({
        "provider": "pexels",
        "source_id": source_id,
        "source_url": source_url,
        "download_url": download_url,
        "provider_key": f"pexels:{source_id}",
        "license": item.get("license") or "Pexels License",
        "license_url": item.get("license_url") or "https://www.pexels.com/license/",
    })
    return item


def _best_pixabay_rendition(videos):
    options = []
    for name in ("large", "medium", "small", "tiny"):
        data = (videos or {}).get(name) or {}
        url = str(data.get("url") or "").strip()
        width = int(data.get("width", 0) or 0)
        height = int(data.get("height", 0) or 0)
        if url and width > 0 and height > 0:
            options.append((name, url, width, height, str(data.get("thumbnail") or "")))
    if not options:
        return None
    portrait = [item for item in options if item[3] >= item[2]]
    pool = portrait or options
    return max(pool, key=lambda item: (item[2] * item[3], item[3]))


def search_pixabay_candidates(query, per_page=None, requests_module=requests, api_key=None):
    key = PIXABAY_API_KEY if api_key is None else str(api_key or "").strip()
    if not key:
        raise RuntimeError("PIXABAY_API_KEY missing")

    query = str(query or "").strip()
    if not query:
        raise ValueError("Pixabay query is empty")

    limit = VIDEO_PROVIDER_PER_PAGE if per_page is None else max(3, min(12, int(per_page)))
    response = requests_module.get(
        PIXABAY_VIDEO_API,
        params={
            "key": key,
            "q": query,
            "per_page": limit,
            "safesearch": "true",
            "order": "popular",
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(f"Pixabay search failed: HTTP {response.status_code}")

    candidates = []
    for position, hit in enumerate(response.json().get("hits", []), start=1):
        rendition = _best_pixabay_rendition(hit.get("videos"))
        if not rendition:
            continue
        _, media_url, width, height, thumbnail = rendition
        source_id = hit.get("id")
        page_url = str(hit.get("pageURL") or "")
        tags = str(hit.get("tags") or "")
        candidates.append({
            "id": source_id,
            "provider": "pixabay",
            "source_id": source_id,
            "source_url": page_url,
            "download_url": media_url,
            "provider_key": f"pixabay:{source_id}",
            "url": media_url,
            "page_url": page_url,
            "thumbnail": thumbnail,
            "width": width,
            "height": height,
            "duration": float(hit.get("duration", 0) or 0),
            "query": query,
            "search_position": position,
            "tags": tags,
            "metadata_text": tags,
            "license": "Pixabay Content License",
            "license_url": "https://pixabay.com/service/license-summary/",
            "creator": str(hit.get("user") or ""),
        })
    return candidates


def merge_provider_candidates(provider_results, total_limit=None):
    limit = VIDEO_PROVIDER_POOL_MAX if total_limit is None else max(1, int(total_limit))
    merged = []
    seen_keys = set()
    seen_urls = set()
    for candidates in provider_results:
        for candidate in candidates:
            key = candidate_unique_key(candidate)
            media_url = str(candidate.get("download_url") or candidate.get("url") or "").strip()
            source_url = str(candidate.get("source_url") or candidate.get("page_url") or "").strip()
            if key in seen_keys:
                continue
            if media_url and media_url in seen_urls:
                continue
            if source_url and source_url in seen_urls:
                continue
            seen_keys.add(key)
            if media_url:
                seen_urls.add(media_url)
            if source_url:
                seen_urls.add(source_url)
            merged.append(candidate)
            if len(merged) >= limit:
                return merged
    return merged

import html
import os
import re

import requests


PIXABAY_VIDEO_API = "https://pixabay.com/api/videos/"
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
WIKIMEDIA_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_COMMONS_ENABLED = os.environ.get("WIKIMEDIA_COMMONS_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
WIKIMEDIA_COMMONS_USER_AGENT = os.environ.get(
    "WIKIMEDIA_COMMONS_USER_AGENT",
    "shorts-bot/2.0 (automated educational video retrieval; GitHub: mingi201209-star/shorts-bot)",
).strip()
VIDEO_PROVIDER_PER_PAGE = max(3, min(12, int(os.environ.get("VIDEO_PROVIDER_PER_PAGE", "6"))))
VIDEO_PROVIDER_POOL_MAX = max(6, min(24, int(os.environ.get("VIDEO_PROVIDER_POOL_MAX", "12"))))

# The current renderer has no reliable attribution sink in the YouTube description.
# Therefore Commons auto-use is deliberately limited to licenses that do not require
# attribution or share-alike. CC BY / CC BY-SA metadata is preserved but rejected.
_WIKIMEDIA_AUTO_LICENSES = {
    "cc0",
    "cc-zero",
    "public domain",
    "public-domain",
    "pd",
}


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
        candidate.get("creator", ""),
        candidate.get("license", ""),
    ]
    return " ".join(str(value or "") for value in values).strip()


def _license_fields(*, license_name, license_url, attribution_required, modification_allowed=True, commercial_use=True, review_required=False):
    return {
        "license": str(license_name or "").strip(),
        "license_url": str(license_url or "").strip(),
        "commercial_use": bool(commercial_use),
        "attribution_required": bool(attribution_required),
        "modification_allowed": bool(modification_allowed),
        "license_review_required": bool(review_required),
    }


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
        **_license_fields(
            license_name=item.get("license") or "Pexels License",
            license_url=item.get("license_url") or "https://www.pexels.com/license/",
            attribution_required=False,
        ),
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
            "creator": str(hit.get("user") or ""),
            **_license_fields(
                license_name="Pixabay Content License",
                license_url="https://pixabay.com/service/license-summary/",
                attribution_required=False,
            ),
        })
    return candidates


def _plain_metadata_value(extmetadata, key):
    raw = ((extmetadata or {}).get(key) or {}).get("value", "")
    text = html.unescape(str(raw or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _wikimedia_license_auto_usable(license_name, *, copyrighted="", restrictions=""):
    normalized = re.sub(r"\s+", " ", str(license_name or "").strip().lower())
    restriction_text = f"{copyrighted} {restrictions}".strip().lower()
    if any(token in restriction_text for token in ("noncommercial", "no derivatives", "permission required")):
        return False
    if normalized in _WIKIMEDIA_AUTO_LICENSES:
        return True
    return normalized.startswith("public domain") or normalized.startswith("cc0")


def search_wikimedia_commons_candidates(query, per_page=None, requests_module=requests):
    """Search Commons video files and return only attribution-free auto-usable assets.

    Commons exposes file license metadata via imageinfo/extmetadata. We fail closed:
    unclear licenses, CC BY, CC BY-SA, NC, ND, or restricted files are not inserted
    into the production candidate pool until an attribution/share-alike pipeline exists.
    """
    query = str(query or "").strip()
    if not query:
        raise ValueError("Wikimedia Commons query is empty")

    limit = VIDEO_PROVIDER_PER_PAGE if per_page is None else max(3, min(12, int(per_page)))
    response = requests_module.get(
        WIKIMEDIA_COMMONS_API,
        headers={"User-Agent": WIKIMEDIA_COMMONS_USER_AGENT},
        params={
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(f"Wikimedia Commons search failed: HTTP {response.status_code}")

    pages = ((response.json().get("query") or {}).get("pages") or [])
    candidates = []
    for position, page in enumerate(pages, start=1):
        info_list = page.get("imageinfo") or []
        if not info_list:
            continue
        info = info_list[0] or {}
        mime = str(info.get("mime") or "").strip().lower()
        if not mime.startswith("video/"):
            continue

        ext = info.get("extmetadata") or {}
        license_name = _plain_metadata_value(ext, "LicenseShortName") or _plain_metadata_value(ext, "UsageTerms")
        license_url = _plain_metadata_value(ext, "LicenseUrl")
        copyrighted = _plain_metadata_value(ext, "Copyrighted")
        restrictions = _plain_metadata_value(ext, "Restrictions")
        if not _wikimedia_license_auto_usable(
            license_name,
            copyrighted=copyrighted,
            restrictions=restrictions,
        ):
            continue

        media_url = str(info.get("url") or "").strip()
        if not media_url:
            continue
        title = str(page.get("title") or "").strip()
        page_url = "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_")
        source_id = page.get("pageid") or title
        creator = _plain_metadata_value(ext, "Artist")
        description = _plain_metadata_value(ext, "ImageDescription")
        credit = _plain_metadata_value(ext, "Credit")
        metadata_text = " ".join(item for item in (title, creator, description, credit) if item)

        candidates.append({
            "id": source_id,
            "provider": "wikimedia_commons",
            "source_id": source_id,
            "source_url": page_url,
            "download_url": media_url,
            "provider_key": f"wikimedia_commons:{source_id}",
            "url": media_url,
            "page_url": page_url,
            "thumbnail": str(info.get("thumburl") or ""),
            "width": int(info.get("width", 0) or 0),
            "height": int(info.get("height", 0) or 0),
            "duration": float(info.get("duration", 0) or 0),
            "query": query,
            "search_position": position,
            "title": title,
            "description": description,
            "metadata_text": metadata_text,
            "creator": creator,
            "mime": mime,
            **_license_fields(
                license_name=license_name,
                license_url=license_url,
                attribution_required=False,
                modification_allowed=True,
                commercial_use=True,
                review_required=False,
            ),
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

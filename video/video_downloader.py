import os
import re
from urllib.parse import urlparse

import requests

from config import (
    PEXELS_API_KEY,
    PEXELS_SEARCH_PER_PAGE,
    PEXELS_RELEVANT_TOP_N,
    PEXELS_MIN_DURATION,
)


PEXELS_VIDEO_API = "https://api.pexels.com/v1/videos/search"

# 한 번의 Shorts 실행 동안 유지되는 시대 문맥/중복 방지 상태.
ACTIVE_CONTEXT_LOCK = None
USED_VIDEO_IDS = set()


EXPLICIT_MODERN_TERMS = {
    "modern", "contemporary", "current", "today",
    "highway", "motorway", "asphalt",
    "excavator", "bulldozer", "paver",
}

# 역사 장면에서 그대로 검색하면 현대 B-roll로 새기 쉬운 단어.
HISTORICAL_RISK_TERMS = {
    "person", "people", "man", "men", "woman", "women",
    "girl", "boy", "crowd", "doctor", "patient", "nurse",
    "worker", "workers", "construction", "constructing",
    "building", "build", "laying", "paving", "pave",
    "installing", "installation", "research", "laboratory",
    "lab", "burning", "incense", "clothing", "clothes",
    "costume", "festival", "cosplay", "tourist", "tourists",
    "street", "city", "interaction", "interactions",
    "society", "atmosphere", "suffering", "victim", "victims",
    "actions", "action", "blood", "drink", "drinking",
}

# Pexels에서 시대가 틀려도 오해를 만들 가능성이 비교적 낮은 시각 자료.
HISTORICAL_SAFE_ANCHORS = {
    "road", "roads", "stone", "stones", "gravel",
    "bridge", "bridges", "aqueduct", "aqueducts",
    "wall", "walls", "ruin", "ruins", "castle", "castles",
    "church", "cathedral", "temple", "tomb", "pyramid",
    "mosaic", "fresco", "sculpture", "statue", "artifact",
    "artifacts", "pottery", "manuscript", "manuscripts",
    "parchment", "painting", "paintings", "illustration",
    "illustrations", "document", "documents", "record",
    "records", "archive", "archives", "relief",
}

# Pexels 페이지 URL slug에서 이 단어가 보이면 역사 장면 후보에서 제외.
# 재현행사도 실제 시대 영상처럼 오해될 수 있으므로 보수적으로 차단한다.
MODERN_SLUG_TERMS = {
    "person", "people", "man", "men", "woman", "women",
    "girl", "boy", "doctor", "nurse", "patient", "hospital",
    "car", "cars", "traffic", "smartphone", "phone", "laptop",
    "office", "worker", "workers", "construction", "street",
    "city", "tourist", "tourists", "festival", "costume",
    "cosplay",
}


SAFE_FALLBACKS = {
    "ancient roman": "ancient roman ruins stone",
    "ancient egypt": "ancient egypt ruins relief",
    "ancient greek": "ancient greek ruins sculpture",
    "medieval historical": "medieval castle ruins manuscript",
    "ancient": "ancient ruins artifact stone",
    "historical": "historical manuscript archive artifact",
}


def normalize_search_query(query):
    query = str(query or "").strip().lower()
    query = re.sub(r"[^a-z0-9\s-]", " ", query)
    return re.sub(r"\s+", " ", query).strip()


def contains_any_term(query, terms):
    return bool(set(normalize_search_query(query).split()) & set(terms))


def detect_context_lock(query):
    query = normalize_search_query(query)
    if not query:
        return None
    if "roman" in query:
        return "ancient roman"
    if "egyptian" in query or "ancient egypt" in query:
        return "ancient egypt"
    if "greek" in query and "ancient" in query:
        return "ancient greek"
    if "medieval" in query:
        return "medieval historical"
    if "ancient" in query:
        return "ancient"
    if "historical" in query:
        return "historical"
    return None


def has_explicit_modern_override(query):
    query = normalize_search_query(query)
    if not query:
        return False
    # "ancient ... modern comparison"처럼 역사 키워드가 함께 있으면
    # 역사 장면으로 간주하고 lock을 유지한다.
    if detect_context_lock(query):
        return False
    return contains_any_term(query, EXPLICIT_MODERN_TERMS)


def get_context_lock(query):
    global ACTIVE_CONTEXT_LOCK

    query = normalize_search_query(query)
    if not query or has_explicit_modern_override(query):
        return None

    detected = detect_context_lock(query)
    if detected:
        if (
            ACTIVE_CONTEXT_LOCK
            and ACTIVE_CONTEXT_LOCK != "ancient"
            and detected == "ancient"
        ):
            return ACTIVE_CONTEXT_LOCK
        ACTIVE_CONTEXT_LOCK = detected
        return detected

    return ACTIVE_CONTEXT_LOCK


def _dedupe_words(words):
    seen = set()
    result = []
    for word in words:
        if word and word not in seen:
            seen.add(word)
            result.append(word)
    return result


def _safe_historical_query(original, lock):
    words = original.split()
    lock_words = lock.split()
    word_set = set(words)

    safe_anchors = [
        word for word in words
        if word in HISTORICAL_SAFE_ANCHORS
    ]

    risky = bool(word_set & HISTORICAL_RISK_TERMS)

    # 역사 장면인데 구체적인 유물/건축/문헌 anchor가 없으면
    # 사람/행동 B-roll 대신 시대가 틀리지 않는 안전 자료로 후퇴한다.
    if risky or not safe_anchors:
        if safe_anchors:
            # 로마 도로/성/문헌처럼 안전한 대상은 살리고,
            # workers/doctor/people 등의 위험 단어는 버린다.
            words = lock_words + safe_anchors
            if any(
                item in safe_anchors
                for item in ("road", "roads", "stone", "stones", "bridge", "aqueduct")
            ):
                words.append("ruins")
            elif any(
                item in safe_anchors
                for item in ("painting", "illustration", "manuscript", "document", "record")
            ):
                words.append("historical")
        else:
            words = SAFE_FALLBACKS.get(
                lock,
                "historical manuscript ruins artifact",
            ).split()
    else:
        words = lock_words + words

    return " ".join(_dedupe_words(words)[:7]).strip()


def build_context_locked_query(query):
    """
    시대 문맥을 유지하면서 현대 B-roll로 새기 쉬운 검색어를
    유물/건축/문헌 중심의 보수적인 검색어로 바꾼다.
    """
    original = normalize_search_query(query)
    if not original:
        return "", None

    if has_explicit_modern_override(original):
        return original, None

    lock = get_context_lock(original)
    if not lock:
        return original, None

    return _safe_historical_query(original, lock), lock


def _page_slug(url):
    try:
        path = urlparse(str(url or "")).path.lower()
    except Exception:
        return ""
    path = re.sub(r"[^a-z0-9-]+", " ", path)
    return path.replace("-", " ")


def _historical_candidate_safe(candidate):
    slug = _page_slug(candidate.get("page_url"))
    if not slug:
        # 메타데이터가 없다고 바로 버리지는 않는다.
        return True

    words = set(slug.split())
    return not bool(words & MODERN_SLUG_TERMS)


def search_pexels_candidates(query, per_page=None):
    """Pexels 검색 결과의 원래 관련도 순서를 보존한다."""
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY가 없습니다.")

    query = str(query).strip()
    if not query:
        raise ValueError("Pexels 검색어가 비어 있습니다.")

    if per_page is None:
        per_page = PEXELS_SEARCH_PER_PAGE

    response = requests.get(
        PEXELS_VIDEO_API,
        headers={"Authorization": PEXELS_API_KEY},
        params={
            "query": query,
            "per_page": int(per_page),
            "orientation": "portrait",
            "locale": "en-US",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Pexels 검색 실패: HTTP {response.status_code}"
        )

    candidates = []

    for position, video in enumerate(
        response.json().get("videos", []),
        start=1,
    ):
        valid_files = []

        for file_info in video.get("video_files", []):
            width = int(file_info.get("width", 0) or 0)
            height = int(file_info.get("height", 0) or 0)
            link = str(file_info.get("link", "")).strip()

            if link and width > 0 and height > 0:
                valid_files.append({
                    "width": width,
                    "height": height,
                    "link": link,
                })

        if not valid_files:
            continue

        portrait_files = [
            item for item in valid_files
            if item["height"] >= item["width"]
        ]
        pool = portrait_files or valid_files
        selected_file = max(
            pool,
            key=lambda item: (
                item["height"] * item["width"],
                item["height"],
            ),
        )

        candidates.append({
            "id": video.get("id"),
            "url": selected_file["link"],
            "page_url": str(video.get("url", "") or ""),
            "thumbnail": str(video.get("image", "") or ""),
            "width": selected_file["width"],
            "height": selected_file["height"],
            "duration": float(video.get("duration", 0) or 0),
            "query": query,
            "search_position": position,
        })

    return candidates


def choose_best_candidate(
    candidates,
    relevant_top_n=None,
    *,
    historical=False,
):
    if not candidates:
        return None

    if relevant_top_n is None:
        relevant_top_n = PEXELS_RELEVANT_TOP_N

    ordered = sorted(
        candidates,
        key=lambda item: int(item.get("search_position", 9999)),
    )

    # 같은 Shorts 안에서 같은 Pexels clip을 재사용하지 않는다.
    ordered = [
        item for item in ordered
        if item.get("id") not in USED_VIDEO_IDS
    ]

    if historical:
        safe = [
            item for item in ordered
            if _historical_candidate_safe(item)
        ]
        if safe:
            ordered = safe
        else:
            return None

    relevant_pool = ordered[:max(1, int(relevant_top_n))]
    if not relevant_pool:
        return None

    long_enough = [
        item for item in relevant_pool
        if float(item.get("duration", 0) or 0) >= PEXELS_MIN_DURATION
    ]
    pool = long_enough or relevant_pool

    if historical:
        # 역사 장면은 관련도 순서를 화질보다 우선한다.
        return min(
            pool,
            key=lambda item: int(item.get("search_position", 9999)),
        )

    def quality_key(item):
        width = int(item.get("width", 0) or 0)
        height = int(item.get("height", 0) or 0)
        duration = float(item.get("duration", 0) or 0)
        return (
            1 if height >= width else 0,
            width * height,
            min(duration, 20.0),
        )

    return max(pool, key=quality_key)


def _fallback_query_for_lock(lock):
    return SAFE_FALLBACKS.get(
        lock,
        "historical manuscript ruins artifact",
    )


def fetch_pexels_video(query):
    """
    video_engine.py와 호환되는 단일 URL 인터페이스.

    역사 장면은:
    1) 시대 lock
    2) 사람/현대 공사/재현행사 위험 검색어 제거
    3) Pexels page slug의 명백한 현대 후보 차단
    4) 같은 clip 재사용 차단
    5) 필요 시 유적/문헌 안전 fallback
    순서로 선택한다.
    """
    original_query = str(query).strip()
    normalized_original = normalize_search_query(original_query)
    effective_query, context_lock = build_context_locked_query(
        original_query
    )

    if effective_query != normalized_original:
        print(
            "🔒 Pexels context lock: "
            f"{original_query} -> {effective_query}"
        )
    elif context_lock:
        print(f"🔒 Pexels context lock 유지: {context_lock}")

    historical = bool(context_lock)
    queries = [effective_query]

    if historical:
        fallback = _fallback_query_for_lock(context_lock)
        if fallback not in queries:
            queries.append(fallback)

    for search_query in queries:
        candidates = search_pexels_candidates(
            search_query,
            per_page=PEXELS_SEARCH_PER_PAGE,
        )

        best = choose_best_candidate(
            candidates,
            relevant_top_n=(
                min(3, PEXELS_RELEVANT_TOP_N)
                if historical
                else PEXELS_RELEVANT_TOP_N
            ),
            historical=historical,
        )

        if not best:
            if historical:
                print(
                    "🛡️ 역사 영상 후보 차단/없음: "
                    f"{search_query}"
                )
            continue

        video_id = best.get("id")
        if video_id is not None:
            USED_VIDEO_IDS.add(video_id)

        print(
            "🎥 Pexels 검색 후보 "
            f"{len(candidates)}개 / "
            f"선택 rank {best.get('search_position')}"
        )
        print(
            "✅ 선택 URL ID: "
            f"{video_id} | "
            f"history_safe={historical}"
        )

        return best["url"]

    return None


def download_video(
    video_url,
    output_path,
    requests_module=requests,
):
    """영상 URL을 로컬 MP4로 저장한다."""
    if not video_url:
        raise ValueError("다운로드할 영상 URL이 없습니다.")

    response = requests_module.get(
        video_url,
        stream=True,
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"영상 다운로드 실패: HTTP {response.status_code}"
        )

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(
            chunk_size=1024 * 1024,
        ):
            if chunk:
                f.write(chunk)

    if not os.path.exists(output_path):
        raise RuntimeError(
            f"영상 파일 생성 실패: {output_path}"
        )

    if os.path.getsize(output_path) <= 0:
        raise RuntimeError(
            f"다운로드된 영상이 비어 있습니다: {output_path}"
        )

    return output_path

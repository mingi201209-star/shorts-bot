import os
import re

import requests

from config import (
    PEXELS_API_KEY,
    PEXELS_SEARCH_PER_PAGE,
    PEXELS_RELEVANT_TOP_N,
    PEXELS_MIN_DURATION,
)


# Pexels 최신 Video Search 경로
PEXELS_VIDEO_API = (
    "https://api.pexels.com/v1/videos/search"
)


# ============================================================
# Scene Context Lock
# ============================================================
#
# 한 영상 안에서 첫 장면들이 "ancient roman" 같은 시대/대상을
# 확정하면 이후의 짧고 일반적인 검색어에도 그 맥락을 유지한다.
#
# 예:
#   ancient roman road ...
#   -> 이후 "laying stones gravel road"도
#      "ancient roman stones gravel road"로 잠근다.
#
# 단, "modern road ..."처럼 장면이 현대 비교 화면을 명시하면
# 그 장면만 historical lock을 적용하지 않는다.
# ============================================================

ACTIVE_CONTEXT_LOCK = None


EXPLICIT_MODERN_TERMS = {
    "modern",
    "contemporary",
    "current",
    "today",
    "highway",
    "motorway",
    "asphalt",
    "excavator",
    "bulldozer",
    "paver",
}


HISTORICAL_ACTION_TERMS = {
    "construction",
    "constructing",
    "worker",
    "workers",
    "building",
    "build",
    "laying",
    "paving",
    "pave",
    "installing",
    "installation",
}


SAFE_OBJECT_HINTS = {
    "road",
    "roads",
    "stone",
    "stones",
    "gravel",
    "brick",
    "bricks",
    "bridge",
    "bridges",
    "wall",
    "walls",
    "aqueduct",
    "aqueducts",
    "ruin",
    "ruins",
    "temple",
    "temples",
    "path",
    "paths",
    "pavement",
    "foundation",
    "foundations",
}


def normalize_search_query(query):
    query = str(query or "").strip().lower()
    query = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        query,
    )
    query = re.sub(
        r"\s+",
        " ",
        query,
    ).strip()
    return query


def contains_any_term(query, terms):
    words = set(
        normalize_search_query(query).split()
    )
    return bool(
        words.intersection(terms)
    )


def detect_context_lock(query):
    query = normalize_search_query(query)

    if not query:
        return None

    if "roman" in query:
        return "ancient roman"

    if (
        "egyptian" in query
        or "ancient egypt" in query
    ):
        return "ancient egypt"

    if (
        "greek" in query
        and "ancient" in query
    ):
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

    # historical/ancient와 modern이 함께 들어간 비교 검색어는
    # 원문 검색어를 그대로 보존한다.
    historical = detect_context_lock(query)

    if historical:
        return False

    return contains_any_term(
        query,
        EXPLICIT_MODERN_TERMS,
    )


def get_context_lock(query):
    global ACTIVE_CONTEXT_LOCK

    query = normalize_search_query(query)

    if not query:
        return None

    if has_explicit_modern_override(query):
        return None

    detected = detect_context_lock(
        query
    )

    if detected:
        # 이미 "ancient roman"처럼 더 구체적인 lock이 있는데
        # 이후 장면에서 "ancient"만 들어왔다고 정보량을 낮추지 않는다.
        if (
            ACTIVE_CONTEXT_LOCK
            and ACTIVE_CONTEXT_LOCK != "ancient"
            and detected == "ancient"
        ):
            return ACTIVE_CONTEXT_LOCK

        ACTIVE_CONTEXT_LOCK = detected
        return detected

    return ACTIVE_CONTEXT_LOCK


def build_context_locked_query(query):
    """
    한 영상 안에서 시대/대상 맥락을 유지한다.

    역사적 제작 과정은 Pexels에 정확한 재연 영상이 부족할 수 있으므로
    "workers / construction / laying" 같은 일반 작업 키워드가
    현대 공사 영상을 끌어오는 경우를 줄이기 위해 실제 남아 있는
    구조물/재료 중심 검색어로 안전하게 바꾼다.
    """

    original = normalize_search_query(
        query
    )

    if not original:
        return "", None

    if has_explicit_modern_override(
        original
    ):
        return original, None

    lock = get_context_lock(
        original
    )

    if not lock:
        return original, None

    words = original.split()
    word_set = set(words)

    lock_words = lock.split()

    for token in reversed(lock_words):
        if token not in word_set:
            words.insert(0, token)
            word_set.add(token)

    # 고대/역사 장면에서 일반적인 현대 작업자 B-roll로 빠지는 것을 막는다.
    # 과정 자체보다 실제 유물/재료/구조를 우선 검색한다.
    if word_set.intersection(
        HISTORICAL_ACTION_TERMS
    ):
        filtered = [
            word
            for word in words
            if word not in HISTORICAL_ACTION_TERMS
        ]

        object_words = [
            word
            for word in filtered
            if (
                word in SAFE_OBJECT_HINTS
                or word in lock_words
            )
        ]

        # object 힌트가 너무 적으면 원래의 비-action 명사를 유지한다.
        if len(object_words) < 3:
            object_words = filtered

        words = object_words

    # 중복 제거, 순서 보존
    seen = set()
    cleaned = []

    for word in words:
        if word in seen:
            continue
        seen.add(word)
        cleaned.append(word)

    # Pexels 검색은 너무 길면 오히려 관련도가 흔들리므로
    # 핵심 문맥 + 대상 위주로 7토큰 이내로 제한한다.
    cleaned = cleaned[:7]

    effective = " ".join(
        cleaned
    ).strip()

    if not effective:
        effective = original

    return effective, lock


# ============================================================
# Pexels 후보 검색
# ============================================================

def search_pexels_candidates(
    query,
    per_page=None,
):
    """Pexels 검색 결과의 원래 관련도 순서를 보존한다."""

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY가 없습니다."
        )

    query = str(query).strip()

    if not query:
        raise ValueError(
            "Pexels 검색어가 비어 있습니다."
        )

    if per_page is None:
        per_page = PEXELS_SEARCH_PER_PAGE

    headers = {
        "Authorization": PEXELS_API_KEY,
    }

    params = {
        "query": query,
        "per_page": int(per_page),
        "orientation": "portrait",
        "size": "medium",
        "locale": "en-US",
    }

    response = requests.get(
        PEXELS_VIDEO_API,
        headers=headers,
        params=params,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            "Pexels 검색 실패: "
            f"HTTP {response.status_code}"
        )

    data = response.json()

    videos = data.get(
        "videos",
        [],
    )

    candidates = []

    for position, video in enumerate(
        videos,
        start=1,
    ):

        files = video.get(
            "video_files",
            [],
        )

        if not files:
            continue

        # 하나의 Pexels 결과 안에서는 화질 좋은 세로 파일을 고른다.
        # 하지만 서로 다른 검색 결과끼리의 관련도 순서는 여기서 바꾸지 않는다.
        valid_files = []

        for file_info in files:

            width = int(
                file_info.get(
                    "width",
                    0,
                ) or 0
            )

            height = int(
                file_info.get(
                    "height",
                    0,
                ) or 0
            )

            link = str(
                file_info.get(
                    "link",
                    "",
                )
            ).strip()

            if not link:
                continue

            if width <= 0 or height <= 0:
                continue

            valid_files.append({
                "width": width,
                "height": height,
                "link": link,
            })

        if not valid_files:
            continue

        portrait_files = [
            item
            for item in valid_files
            if item["height"] >= item["width"]
        ]

        pool = (
            portrait_files
            if portrait_files
            else valid_files
        )

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
            "width": selected_file["width"],
            "height": selected_file["height"],
            "duration": float(
                video.get(
                    "duration",
                    0,
                ) or 0
            ),
            "query": query,
            "search_position": position,
        })

    return candidates


# ============================================================
# 후보 선택
# ============================================================

def choose_best_candidate(
    candidates,
    relevant_top_n=None,
):
    """
    Pexels 관련도 순위 상위 후보만 남긴 뒤 화질을 비교한다.

    핵심:
    검색 결과 전체를 해상도순으로 다시 섞지 않는다.
    """

    if not candidates:
        return None

    if relevant_top_n is None:
        relevant_top_n = (
            PEXELS_RELEVANT_TOP_N
        )

    relevant_top_n = max(
        1,
        int(relevant_top_n),
    )

    ordered = sorted(
        candidates,
        key=lambda item: int(
            item.get(
                "search_position",
                9999,
            )
        ),
    )

    relevant_pool = ordered[
        :relevant_top_n
    ]

    long_enough = [
        item
        for item in relevant_pool
        if float(
            item.get(
                "duration",
                0,
            ) or 0
        ) >= PEXELS_MIN_DURATION
    ]

    quality_pool = (
        long_enough
        if long_enough
        else relevant_pool
    )

    def quality_key(item):

        width = int(
            item.get(
                "width",
                0,
            ) or 0
        )

        height = int(
            item.get(
                "height",
                0,
            ) or 0
        )

        duration = float(
            item.get(
                "duration",
                0,
            ) or 0
        )

        portrait_bonus = (
            1
            if height >= width
            else 0
        )

        resolution = (
            width * height
        )

        return (
            portrait_bonus,
            resolution,
            min(duration, 20.0),
        )

    return max(
        quality_pool,
        key=quality_key,
    )


# ============================================================
# 기존 호환 함수
# ============================================================

def fetch_pexels_video(query):
    """
    video_engine.py와 호환되는 단일 URL 인터페이스.

    historical context가 감지되면 같은 영상 안에서 그 시대/대상을
    유지하고, Pexels 관련도 1순위 결과를 우선한다.
    """

    original_query = str(
        query
    ).strip()

    effective_query, context_lock = (
        build_context_locked_query(
            original_query
        )
    )

    if effective_query != normalize_search_query(
        original_query
    ):
        print(
            "🔒 Pexels context lock: "
            f"{original_query} -> {effective_query}"
        )

    elif context_lock:
        print(
            "🔒 Pexels context lock 유지: "
            f"{context_lock}"
        )

    candidates = search_pexels_candidates(
        effective_query,
        per_page=PEXELS_SEARCH_PER_PAGE,
    )

    # 역사/시대 잠금 장면은 검색 결과를 화질 때문에 2~3위로 넘기지 않는다.
    # Pexels 검색 관련도 1순위를 그대로 우선해 장면 이탈 가능성을 낮춘다.
    relevant_top_n = (
        1
        if context_lock
        else PEXELS_RELEVANT_TOP_N
    )

    best = choose_best_candidate(
        candidates,
        relevant_top_n=relevant_top_n,
    )

    if not best:
        return None

    print(
        "🎥 Pexels 검색 후보 "
        f"{len(candidates)}개 / "
        f"관련도 상위 {relevant_top_n}개 안에서 선택"
    )

    print(
        "✅ 선택 URL ID: "
        f"{best.get('id')} "
        f"| search rank {best.get('search_position')}"
    )

    return best["url"]


# ============================================================
# 영상 다운로드
# ============================================================

def download_video(
    video_url,
    output_path,
    requests_module=requests,
):
    """영상 URL을 로컬 MP4로 저장한다."""

    if not video_url:
        raise ValueError(
            "다운로드할 영상 URL이 없습니다."
        )

    response = requests_module.get(
        video_url,
        stream=True,
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            "영상 다운로드 실패: "
            f"HTTP {response.status_code}"
        )

    with open(
        output_path,
        "wb",
    ) as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024,
        ):

            if chunk:
                f.write(chunk)

    if not os.path.exists(
        output_path
    ):
        raise RuntimeError(
            "영상 파일 생성 실패: "
            f"{output_path}"
        )

    if os.path.getsize(
        output_path
    ) <= 0:
        raise RuntimeError(
            "다운로드된 영상이 비어 있습니다: "
            f"{output_path}"
        )

    return output_path

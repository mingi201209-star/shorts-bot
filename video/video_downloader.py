import os

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
    검색 결과 8개 전체를 해상도순으로 다시 섞지 않는다.
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

    # search_position 기준으로 원래 검색 순서를 명시적으로 복원한다.
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

    # 너무 짧은 영상은 가능하면 제외하되,
    # 전부 짧을 경우 검색 결과 자체를 버리지는 않는다.
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

        # 관련도는 이미 상위 N개로 잘랐기 때문에
        # 여기서는 실제 영상 품질만 비교한다.
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
    """video_engine.py와 호환되는 단일 URL 인터페이스."""

    candidates = search_pexels_candidates(
        query,
        per_page=PEXELS_SEARCH_PER_PAGE,
    )

    best = choose_best_candidate(
        candidates,
        relevant_top_n=(
            PEXELS_RELEVANT_TOP_N
        ),
    )

    if not best:
        return None

    print(
        "🎥 Pexels 검색 후보 "
        f"{len(candidates)}개 / "
        f"관련도 상위 {PEXELS_RELEVANT_TOP_N}개 안에서 선택"
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

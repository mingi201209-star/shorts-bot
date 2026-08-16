# video/video_downloader.py

import os
import requests

from config import PEXELS_API_KEY


PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"


# ============================================================
# Pexels 후보 검색
# ============================================================

def search_pexels_candidates(
    query,
    per_page=8,
):
    """
    하나의 검색어로 여러 영상 후보를 가져온다.

    반환값 예:
    [
        {
            "id": 123,
            "url": "...",
            "width": 1080,
            "height": 1920,
            "duration": 12.3
        }
    ]
    """

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY가 없습니다."
        )

    query = str(query).strip()

    if not query:
        raise ValueError(
            "Pexels 검색어가 비어 있습니다."
        )

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "portrait",
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

    for video in videos:

        files = video.get(
            "video_files",
            [],
        )

        # 가능한 파일 중 세로/고해상도 우선
        files = sorted(
            files,
            key=lambda item: (
                item.get("height", 0),
                item.get("width", 0),
            ),
            reverse=True,
        )

        if not files:
            continue

        selected_file = None

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

            link = file_info.get(
                "link",
                "",
            )

            if not link:
                continue

            if height >= width:
                selected_file = file_info
                break

        if selected_file is None:
            selected_file = files[0]

        link = selected_file.get(
            "link",
            "",
        )

        if not link:
            continue

        candidates.append({
            "id": video.get("id"),
            "url": link,
            "width": selected_file.get(
                "width",
                0,
            ),
            "height": selected_file.get(
                "height",
                0,
            ),
            "duration": video.get(
                "duration",
                0,
            ),
            "query": query,
        })

    return candidates


# ============================================================
# 기본 후보 선택
# ============================================================

def choose_best_candidate(
    candidates,
):
    """
    현재 단계에서는 세로형 + 해상도 기준으로 선택.

    다음 V3 단계에서 Gemini 또는 별도 영상 분석기가
    이 후보 리스트를 받아 실제 장면 맥락까지 검사하게 된다.
    """

    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda item: (
            item.get("height", 0),
            item.get("width", 0),
            item.get("duration", 0),
        ),
        reverse=True,
    )

    return ranked[0]


# ============================================================
# 기존 호환 함수
# ============================================================

def fetch_pexels_video(
    query,
):
    """
    기존 video_engine.py와의 호환을 유지한다.

    후보 여러 개를 검색한 뒤
    현재 기준에서 가장 좋은 후보의 URL을 반환한다.
    """

    candidates = search_pexels_candidates(
        query,
        per_page=8,
    )

    best = choose_best_candidate(
        candidates
    )

    if not best:
        return None

    print(
        f"🎥 Pexels 후보 {len(candidates)}개 중 선택"
    )

    print(
        f"✅ 선택 URL ID: {best.get('id')}"
    )

    return best[
        "url"
    ]


# ============================================================
# 영상 다운로드
# ============================================================

def download_video(
    video_url,
    output_path,
    requests_module=requests,
):
    """
    영상 URL을 로컬 MP4로 저장한다.
    """

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
            f"영상 파일 생성 실패: {output_path}"
        )

    if os.path.getsize(
        output_path
    ) <= 0:
        raise RuntimeError(
            f"다운로드된 영상이 비어 있습니다: "
            f"{output_path}"
        )

    return output_path

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
    현재

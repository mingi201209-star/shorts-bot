import os
import random
import requests


# ============================================================
# 기본 설정
# ============================================================

PEXELS_SEARCH_PER_PAGE = 15

MIN_WIDTH = 720
PREFERRED_WIDTH = 1080

MAX_CANDIDATES = 5


# ============================================================
# Pexels 영상 검색
# ============================================================

def fetch_pexels_video(
    query,
    api_key=None
):
    """
    Pexels에서 영상 검색 후
    가장 적합한 후보 중 하나를 선택한다.

    선택 기준:
    1. 세로 영상 우선
    2. 9:16에 가까운 영상 우선
    3. 1080 이상 우선
    4. HD 우선
    5. 지나치게 작은 영상 제외
    """

    api_key = (
        api_key
        or os.environ.get("PEXELS_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "PEXELS_API_KEY가 없습니다."
        )

    query = str(query).strip()

    if not query:
        raise ValueError(
            "Pexels 검색어가 비어 있습니다."
        )

    print("")
    print(
        f"🔎 Pexels 검색: {query}"
    )

    headers = {
        "Authorization": api_key
    }

    url = (
        "https://api.pexels.com/videos/search"
        f"?query={requests.utils.quote(query)}"
        f"&per_page={PEXELS_SEARCH_PER_PAGE}"
        "&orientation=portrait"
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        videos = data.get(
            "videos",
            []
        )

        if not videos:

            print(
                f"⚠️ Pexels 검색 결과 없음: {query}"
            )

            return None

        candidates = []

        for video in videos:

            video_id = video.get(
                "id",
                "unknown"
            )

            duration = float(
                video.get(
                    "duration",
                    0
                ) or 0
            )

            files = video.get(
                "video_files",
                []
            )

            for video_file in files:

                link = video_file.get(
                    "link"
                )

                if not link:
                    continue

                width = int(
                    video_file.get(
                        "width",
                        0
                    ) or 0
                )

                height = int(
                    video_file.get(
                        "height",
                        0
                    ) or 0
                )

                quality = str(
                    video_file.get(
                        "quality",
                        ""
                    )
                ).lower()

                if width <= 0 or height <= 0:
                    continue

                # ----------------------------------------
                # 너무 작은 영상 제외
                # ----------------------------------------

                if width < MIN_WIDTH:
                    continue

                # ----------------------------------------
                # 점수 계산
                # ----------------------------------------

                score = 0

                # 세로 영상
                if height > width:
                    score += 60

                # 9:16 비율에 가까울수록 가산
                ratio = width / height

                target_ratio = 9 / 16

                ratio_difference = abs(
                    ratio - target_ratio
                )

                if ratio_difference < 0.05:
                    score += 35

                elif ratio_difference < 0.10:
                    score += 20

                elif ratio_difference < 0.20:
                    score += 10

                # 1080 이상
                if width >= PREFERRED_WIDTH:
                    score += 30

                elif width >= 900:
                    score += 20

                elif width >= 720:
                    score += 10

                # HD
                if quality == "hd":
                    score += 20

                # 너무 짧은 영상은 약간 감점
                if duration < 3:
                    score -= 20

                elif duration >= 5:
                    score += 5

                # 너무 긴 영상도 약간 감점하지 않고 유지
                # 다양한 장면에 사용할 수 있기 때문

                candidates.append(
                    {
                        "score": score,
                        "link": link,
                        "width": width,
                        "height": height,
                        "quality": quality,
                        "duration": duration,
                        "video_id": video_id,
                    }
                )

        if not candidates:

            print(
                f"⚠️ 조건에 맞는 영상 없음: {query}"
            )

            return None

        # ----------------------------------------
        # 점수순 정렬
        # ----------------------------------------

        candidates.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        top_candidates = candidates[
            :MAX_CANDIDATES
        ]

        # ----------------------------------------
        # 상위 후보 중 랜덤 선택
        #
        # 매번 똑같은 영상이 나오는 것을 방지
        # ----------------------------------------

        selected = random.choice(
            top_candidates
        )

        print(
            "🎥 Pexels 영상 선택"
        )

        print(
            f"   검색어 : {query}"
        )

        print(
            f"   점수   : {selected['score']}"
        )

        print(
            f"   해상도 : "
            f"{selected['width']}x"
            f"{selected['height']}"
        )

        print(
            f"   품질   : "
            f"{selected['quality']}"
        )

        print(
            f"   길이   : "
            f"{selected['duration']:.1f}초"
        )

        return selected["link"]

    except requests.RequestException as e:

        print(
            f"❌ Pexels 요청 실패 "
            f"({query}): {e}"
        )

        raise

    except Exception as e:

        print(
            f"❌ Pexels 검색 처리 실패 "
            f"({query}): {e}"
        )

        raise


# ============================================================
# 영상 다운로드
# ============================================================

def download_video(
    video_url,
    output_path,
    requests_module=requests
):
    """
    Pexels 영상 다운로드
    """

    if not video_url:

        raise RuntimeError(
            "다운로드할 영상 URL이 없습니다."
        )

    print("")
    print(
        f"⬇️ 영상 다운로드 시작: "
        f"{output_path}"
    )

    try:

        response = requests_module.get(
            video_url,
            stream=True,
            timeout=60
        )

        response.raise_for_status()

        with open(
            output_path,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:

                    f.write(
                        chunk
                    )

        # ----------------------------------------
        # 파일 존재 검사
        # ----------------------------------------

        if not os.path.exists(
            output_path
        ):

            raise RuntimeError(
                "영상 파일이 생성되지 않았습니다."
            )

        # ----------------------------------------
        # 파일 크기 검사
        # ----------------------------------------

        file_size = os.path.getsize(
            output_path
        )

        if file_size < 1000:

            raise RuntimeError(
                "다운로드된 영상 파일이 "
                "비정상적으로 작습니다."
            )

        print(
            f"✅ 영상 다운로드 완료: "
            f"{file_size / 1024 / 1024:.1f} MB"
        )

        return output_path

    except Exception as e:

        print(
            f"❌ 영상 다운로드 실패: {e}"
        )

        # 실패한 파일이 남아 있으면 제거
        if os.path.exists(
            output_path
        ):

            try:

                os.remove(
                    output_path
                )

            except Exception:
                pass

        raise

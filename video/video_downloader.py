import random
import requests


PEXELS_API_KEY = None


def fetch_pexels_video(query, api_key=None):
    """
    Pexels에서 영상 검색 후 다운로드 가능한 URL 반환
    """

    key = api_key or PEXELS_API_KEY

    if not key:
        raise RuntimeError("PEXELS_API_KEY가 없습니다.")

    headers = {
        "Authorization": key
    }

    url = (
        "https://api.pexels.com/videos/search"
        f"?query={requests.utils.quote(query)}"
        "&per_page=10"
        "&orientation=portrait"
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        videos = data.get("videos", [])

        if not videos:
            print(f"⚠️ Pexels 결과 없음: {query}")
            return get_fallback_video()

        candidates = []

        for video in videos:

            for video_file in video.get(
                "video_files",
                []
            ):

                width = video_file.get(
                    "width",
                    0
                )

                height = video_file.get(
                    "height",
                    0
                )

                quality = video_file.get(
                    "quality",
                    ""
                )

                link = video_file.get("link")

                if not link:
                    continue

                score = 0

                if height > width:
                    score += 50

                if width >= 1080:
                    score += 40

                if quality == "hd":
                    score += 20

                candidates.append(
                    (score, link)
                )

        if candidates:

            candidates.sort(
                key=lambda x: x[0],
                reverse=True
            )

            top_candidates = candidates[:5]

            selected = random.choice(
                top_candidates
            )

            print(f"🎥 Pexels 선택: {query}")

            return selected[1]

    except Exception as e:

        print(
            f"⚠️ Pexels 검색 실패 "
            f"({query}): {e}"
        )

    return get_fallback_video()


def get_fallback_video():
    return (
        "https://videos.pexels.com/"
        "video-files/856987/"
        "856987-hd_1080_1920_30fps.mp4"
    )


def download_video(
    video_url,
    output_path
):
    """
    영상 URL을 파일로 다운로드
    """

    print(
        f"⬇️ 영상 다운로드: {output_path}"
    )

    response = requests.get(
        video_url,
        timeout=60
    )

    response.raise_for_status()

    with open(
        output_path,
        "wb"
    ) as f:

        f.write(
            response.content
        )

    if (
        not output_path
        or not __import__("os").path.exists(output_path)
        or __import__("os").path.getsize(output_path) < 1000
    ):
        raise RuntimeError(
            "영상 다운로드 결과가 비정상적입니다."
        )

    print("✅ 영상 다운로드 완료")

import os
import requests


def fetch_pexels_video(query, api_key=None):
    """
    Pexels에서 영상 검색

    api_key가 전달되면 그것을 사용하고,
    없으면 환경변수 PEXELS_API_KEY를 사용한다.
    """

    api_key = (
        api_key
        or os.environ.get("PEXELS_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "PEXELS_API_KEY가 없습니다."
        )

    headers = {
        "Authorization": api_key
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

                score = 0

                # 세로 영상
                if height > width:
                    score += 50

                # 1080 이상
                if width >= 1080:
                    score += 40

                # HD
                if quality == "hd":
                    score += 20

                candidates.append(
                    (
                        score,
                        link
                    )
                )

        if not candidates:
            print(
                f"⚠️ 사용 가능한 영상 없음: {query}"
            )
            return None

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        top_candidates = candidates[:5]

        selected = top_candidates[
            __import__("random").randrange(
                len(top_candidates)
            )
        ]

        print(
            f"🎥 Pexels 영상 선택: {query}"
        )

        return selected[1]

    except Exception as e:

        print(
            f"❌ Pexels 검색 실패 "
            f"({query}): {e}"
        )

        raise


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
                    f.write(chunk)

        if not os.path.exists(
            output_path
        ):
            raise RuntimeError(
                "영상 파일이 생성되지 않았습니다."
            )

        file_size = os.path.getsize(
            output_path
        )

        if file_size == 0:
            raise RuntimeError(
                "다운로드된 영상 파일의 크기가 0입니다."
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

        raise

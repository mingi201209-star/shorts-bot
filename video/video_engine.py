import os
import numpy as np

from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
)

from video.video_downloader import (
    fetch_pexels_video,
    download_video,
)

from video.video_utils import (
    process_video_clip,
)


# ============================================================
# Shorts Video Engine
# ============================================================
#
# 역할:
#   1. TTS 음성 생성
#   2. 음성 길이 측정
#   3. Pexels 영상 검색
#   4. 영상 다운로드
#   5. 9:16 세로 영상 처리
#   6. 장면별 자막 생성
#   7. 영상 + 자막 + 음성 합성
#
# main.py에서:
#
#   create_scene(
#       idx,
#       item,
#       create_voice,
#       requests
#   )
#
# 형태로 호출한다.
#
# ============================================================


# ============================================================
# 1. 기본 영상 크기
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


# ============================================================
# 2. 한글 폰트
# ============================================================

def get_safe_korean_font(size):
    """
    GitHub Actions Ubuntu 환경에서
    사용할 수 있는 한글 폰트를 순서대로 찾는다.
    """

    font_filename = "NanumGothic.ttf"

    if os.path.exists(font_filename):

        try:

            return ImageFont.truetype(
                font_filename,
                size
            )

        except Exception:
            pass

    font_paths = [

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothicExtraBold.ttf",

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothicBold.ttf",

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothic.ttf",

        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",

    ]

    for path in font_paths:

        if os.path.exists(path):

            try:

                return ImageFont.truetype(
                    path,
                    size
                )

            except Exception:
                pass

    print(
        "⚠️ 한글 폰트를 찾지 못해 기본 폰트 사용"
    )

    return ImageFont.load_default()


# ============================================================
# 3. 자막 이미지 생성
# ============================================================

def render_subtitle_image(text):
    """
    한 줄짜리 자막 PNG 이미지를 생성한다.

    1080px 전체 폭을 사용하고
    가운데 정렬한다.
    """

    target_w = VIDEO_WIDTH

    font_size = 70

    font = get_safe_korean_font(
        font_size
    )

    padding = 40

    img_h = (
        font_size
        + padding * 2
    )

    img = Image.new(
        "RGBA",
        (
            target_w,
            img_h
        ),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(img)

    # --------------------------------------------------------
    # 텍스트 실제 크기 계산
    # --------------------------------------------------------

    try:

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
            stroke_width=0
        )

        text_width = (
            bbox[2] - bbox[0]
        )

    except Exception:

        text_width = (
            len(text)
            * font_size
        )

    # --------------------------------------------------------
    # 가운데 정렬
    # --------------------------------------------------------

    x = max(
        20,
        int(
            (
                target_w
                - text_width
            )
            / 2
        )
    )

    y = padding

    # --------------------------------------------------------
    # 검은색 외곽선
    # --------------------------------------------------------

    draw.text(
        (x, y),
        text,
        font=font,
        fill="black",
        stroke_width=8,
        stroke_fill="black"
    )

    # --------------------------------------------------------
    # 노란색 본문
    # --------------------------------------------------------

    draw.text(
        (x, y),
        text,
        font=font,
        fill="#FFE600",
        stroke_width=2,
        stroke_fill="#FFE600"
    )

    return np.array(img)


# ============================================================
# 4. 자막 분할
# ============================================================

def create_split_subtitles(
    text,
    duration
):
    """
    긴 문장을 짧은 단위로 나눠
    장면 안에서 순차적으로 표시한다.

    예:
        "1955년 미국 네바다 사막에 비밀 기지가 설립됩니다."

    →

        "1955년 미국"
        "네바다 사막에"
        "비밀 기지가"
        "설립됩니다."

    """

    text = str(text).strip()

    if not text:

        return []

    words = text.split()

    if not words:

        return []

    chunks = []

    current = []

    # --------------------------------------------------------
    # 기본적으로 2단어씩 분할
    # --------------------------------------------------------

    for word in words:

        current.append(word)

        if len(current) >= 2:

            chunks.append(
                " ".join(current)
            )

            current = []

    if current:

        chunks.append(
            " ".join(current)
        )

    if not chunks:

        chunks = [text]

    # --------------------------------------------------------
    # 각 자막의 표시 시간
    # --------------------------------------------------------

    chunk_duration = (
        duration
        / len(chunks)
    )

    subtitle_clips = []

    # --------------------------------------------------------
    # 자막 클립 생성
    # --------------------------------------------------------

    for idx, chunk in enumerate(
        chunks
    ):

        subtitle_image = (
            render_subtitle_image(
                chunk
            )
        )

        start_time = (
            idx
            * chunk_duration
        )

        clip = (
            ImageClip(
                subtitle_image
            )
            .set_start(
                start_time
            )
            .set_duration(
                chunk_duration
            )
            .set_position(
                ("center", 0.72),
                relative=True
            )
        )

        subtitle_clips.append(
            clip
        )

    return subtitle_clips


# ============================================================
# 5. Pexels API Key 확인
# ============================================================

def get_pexels_api_key():
    """
    Pexels API Key를 환경변수에서 가져온다.

    GitHub Actions:
        PEXELS_API_KEY

    를 사용한다.
    """

    api_key = os.environ.get(
        "PEXELS_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "PEXELS_API_KEY가 없습니다."
        )

    return api_key


# ============================================================
# 6. 장면 하나 생성
# ============================================================

def create_scene(
    idx,
    item,
    create_voice,
    requests_module
):
    """
    Shorts 장면 하나를 생성한다.

    Parameters
    ----------
    idx:
        장면 번호

    item:
        AI가 생성한 장면 정보

    create_voice:
        main.py의 TTS 생성 함수

    requests_module:
        main.py에서 전달하는 requests 모듈

    Returns
    -------
    CompositeVideoClip
    """

    # ========================================================
    # 장면 데이터
    # ========================================================

    if not isinstance(
        item,
        dict
    ):

        raise ValueError(
            f"{idx}번 장면 데이터가 올바르지 않습니다."
        )

    text = str(
        item.get(
            "text",
            ""
        )
    ).strip()

    keyword = str(
        item.get(
            "keyword",
            "nature landscape"
        )
    ).strip()

    # ========================================================
    # 텍스트 검사
    # ========================================================

    if not text:

        raise ValueError(
            f"{idx}번 장면의 text가 비어 있습니다."
        )

    # ========================================================
    # 검색어 검사
    # ========================================================

    if not keyword:

        keyword = "nature landscape"

    # ========================================================
    # 로그
    # ========================================================

    print("")
    print(
        "=============================="
    )

    print(
        f"🎬 SCENE {idx + 1}"
    )

    print(
        "=============================="
    )

    print(
        f"대사: {text}"
    )

    print(
        f"검색어: {keyword}"
    )

    # ========================================================
    # 파일 경로
    # ========================================================

    audio_path = (
        f"scene_{idx}.mp3"
    )

    video_path = (
        f"video_{idx}.mp4"
    )

    # ========================================================
    # 1. TTS 생성
    # ========================================================

    print(
        f"🎙️ TTS 생성: {text}"
    )

    create_voice(
        text,
        audio_path
    )

    # ========================================================
    # TTS 파일 검사
    # ========================================================

    if not os.path.exists(
        audio_path
    ):

        raise RuntimeError(
            f"TTS 파일 생성 실패: "
            f"{audio_path}"
        )

    audio_size = os.path.getsize(
        audio_path
    )

    if audio_size <= 0:

        raise RuntimeError(
            f"TTS 파일 크기가 0입니다: "
            f"{audio_path}"
        )

    # ========================================================
    # 2. 오디오 길이 측정
    # ========================================================

    audio_clip = AudioFileClip(
        audio_path
    )

    duration = (
        audio_clip.duration
    )

    print(
        f"⏱️ 장면 길이: "
        f"{duration:.2f}초"
    )

    if duration <= 0:

        audio_clip.close()

        raise RuntimeError(
            f"오디오 길이가 올바르지 않습니다: "
            f"{duration}"
        )

    # ========================================================
    # 3. Pexels API Key 확인
    # ========================================================

    pexels_api_key = (
        get_pexels_api_key()
    )

    print(
        "🔑 Pexels API Key 확인 완료"
    )

    # ========================================================
    # 4. Pexels 영상 검색
    # ========================================================

    print(
        f"🔎 Pexels 검색: {keyword}"
    )

    video_url = fetch_pexels_video(
        keyword,
        pexels_api_key
    )

    if not video_url:

        audio_clip.close()

        raise RuntimeError(
            f"Pexels에서 영상을 찾지 못했습니다: "
            f"{keyword}"
        )

    print(
        "🎥 Pexels 영상 URL 확보 완료"
    )

    # ========================================================
    # 5. 영상 다운로드
    # ========================================================

    print(
        f"⬇️ 영상 다운로드: "
        f"{video_path}"
    )

    download_video(
        video_url,
        video_path,
        requests_module
    )

    # ========================================================
    # 다운로드 파일 검사
    # ========================================================

    if not os.path.exists(
        video_path
    ):

        audio_clip.close()

        raise RuntimeError(
            f"영상 다운로드 실패: "
            f"{video_path}"
        )

    video_size = os.path.getsize(
        video_path
    )

    if video_size <= 0:

        audio_clip.close()

        raise RuntimeError(
            f"다운로드된 영상 파일 크기가 0입니다: "
            f"{video_path}"
        )

    print(
        f"✅ 영상 다운로드 완료: "
        f"{video_size / 1024 / 1024:.1f} MB"
    )

    # ========================================================
    # 6. 영상 크롭 / 반복 / 9:16 변환
    # ========================================================

    print(
        "🎞️ 영상 9:16 변환 중..."
    )

    try:

        video_clip = process_video_clip(
            video_path,
            duration
        )

    except Exception:

        audio_clip.close()

        raise

    # ========================================================
    # 7. 자막 생성
    # ========================================================

    print(
        "💬 자막 생성 중..."
    )

    subtitle_clips = (
        create_split_subtitles(
            text,
            duration
        )
    )

    # ========================================================
    # 8. 영상 + 자막 + 음성 합성
    # ========================================================

    print(
        "🎬 영상 + 자막 + 음성 합성 중..."
    )

    try:

        combined = (
            CompositeVideoClip(
                [
                    video_clip
                ]
                + subtitle_clips,

                size=(
                    VIDEO_WIDTH,
                    VIDEO_HEIGHT
                )
            )
            .set_audio(
                audio_clip
            )
            .set_duration(
                duration
            )
        )

    except Exception:

        try:
            video_clip.close()
        except Exception:
            pass

        try:
            audio_clip.close()
        except Exception:
            pass

        raise

    # ========================================================
    # 9. 완료
    # ========================================================

    print(
        f"✅ SCENE {idx + 1} 생성 완료"
    )

    return combined

# video/video_engine.py

import os
import traceback
import numpy as np

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# Pillow / MoviePy 호환 패치
# ============================================================
#
# 최신 Pillow에서는 Image.ANTIALIAS가 삭제됨.
# 구버전 MoviePy는 Image.ANTIALIAS를 내부에서 사용하기 때문에
# MoviePy를 import하기 전에 호환 속성을 만들어 준다.
#
# 이 코드가 반드시 MoviePy import보다 먼저 실행되어야 한다.
# ============================================================

if not hasattr(Image, "ANTIALIAS"):
    try:
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    except AttributeError:
        Image.ANTIALIAS = Image.LANCZOS


# ============================================================
# MoviePy
# ============================================================

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
)


# ============================================================
# 프로젝트 모듈
# ============================================================

from video.video_downloader import (
    fetch_pexels_video,
    download_video,
)

from video.video_utils import (
    process_video_clip,
)


# ============================================================
# 영상 설정
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

FPS = 30


# ============================================================
# 작업 디렉터리
# ============================================================

BASE_DIR = os.getcwd()


# ============================================================
# 한글 폰트
# ============================================================

def get_safe_korean_font(size):

    font_paths = [

        # 프로젝트 루트
        os.path.join(
            BASE_DIR,
            "NanumGothic.ttf"
        ),

        os.path.join(
            BASE_DIR,
            "NanumGothicBold.ttf"
        ),

        os.path.join(
            BASE_DIR,
            "NanumGothicExtraBold.ttf"
        ),

        # Ubuntu
        "/usr/share/fonts/truetype/nanum/"
        "NanumGothicExtraBold.ttf",

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothicBold.ttf",

        "/usr/share/fonts/truetype/nanum/"
        "NanumGothic.ttf",

        # 일부 GitHub Actions 환경
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    ]

    for path in font_paths:

        if not os.path.exists(path):
            continue

        try:

            return ImageFont.truetype(
                path,
                size
            )

        except Exception:
            continue

    print(
        "⚠️ 한글 폰트를 찾지 못했습니다."
    )

    print(
        "⚠️ 기본 폰트로 계속 진행합니다."
    )

    return ImageFont.load_default()


# ============================================================
# 자막 이미지 생성
# ============================================================

def render_subtitle_image(text):

    text = str(text).strip()

    if not text:
        return np.zeros(
            (
                100,
                VIDEO_WIDTH,
                4
            ),
            dtype=np.uint8
        )

    target_width = VIDEO_WIDTH

    font_size = 70

    font = get_safe_korean_font(
        font_size
    )

    horizontal_padding = 40
    vertical_padding = 30

    # --------------------------------------------------------
    # 텍스트 크기 계산
    # --------------------------------------------------------

    temp_image = Image.new(
        "RGBA",
        (
            target_width,
            300
        ),
        (0, 0, 0, 0)
    )

    temp_draw = ImageDraw.Draw(
        temp_image
    )

    try:

        bbox = temp_draw.textbbox(
            (0, 0),
            text,
            font=font,
            stroke_width=2
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        text_height = (
            bbox[3] - bbox[1]
        )

    except Exception:

        text_width = (
            len(text)
            * font_size
        )

        text_height = font_size

    # --------------------------------------------------------
    # 자막 이미지 높이
    # --------------------------------------------------------

    image_height = max(
        140,
        text_height
        + vertical_padding * 2
    )

    img = Image.new(
        "RGBA",
        (
            target_width,
            image_height
        ),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(
        img
    )

    # --------------------------------------------------------
    # 가운데 정렬
    # --------------------------------------------------------

    x = int(
        (
            target_width
            - text_width
        )
        / 2
    )

    x = max(
        horizontal_padding,
        x
    )

    y = int(
        (
            image_height
            - text_height
        )
        / 2
    )

    # --------------------------------------------------------
    # 검은색 외곽선
    # --------------------------------------------------------

    draw.text(
        (x, y),
        text,
        font=font,
        fill="#FFE600",
        stroke_width=8,
        stroke_fill="#000000"
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

    return np.array(
        img
    )


# ============================================================
# 자막 분할
# ============================================================

def create_split_subtitles(
    text,
    duration
):

    text = str(text).strip()

    if not text:
        return []

    if duration <= 0:
        return []

    words = text.split()

    if not words:
        return []

    # --------------------------------------------------------
    # 너무 긴 자막을 적당히 분할
    # --------------------------------------------------------

    chunks = []

    current = []

    for

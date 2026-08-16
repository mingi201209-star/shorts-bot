# video/subtitle_engine.py

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import ImageClip

from config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_STROKE_WIDTH,
    SUBTITLE_TEXT_COLOR,
    SUBTITLE_STROKE_COLOR,
)


# ============================================================
# Subtitle Engine
# ============================================================
#
# 책임:
#   - 한글 폰트 로드
#   - 자막 이미지 렌더링
#   - 자막 문장 분할
#   - MoviePy 자막 클립 생성
#
# 중요:
#   한글 폰트가 없으면 절대 기본 폰트로 fallback하지 않는다.
#   실패시키는 것이 □□□ 자막 영상을 만드는 것보다 안전하다.
#
# ============================================================


# ============================================================
# 한글 폰트
# ============================================================

def get_korean_font(size):

    candidates = [
        # GitHub Actions / Ubuntu
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",

        # Nanum
        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",

        # 프로젝트 내부에 직접 넣어둔 경우
        "fonts/NotoSansCJK-Bold.ttc",
        "fonts/NotoSansCJK-Regular.ttc",
        "fonts/NanumGothicExtraBold.ttf",
        "fonts/NanumGothicBold.ttf",
        "fonts/NanumGothic.ttf",
    ]

    for path in candidates:

        if not os.path.isfile(path):
            continue

        try:

            font = ImageFont.truetype(
                path,
                size,
            )

            print(
                f"✅ 한글 폰트 사용: {path}"
            )

            return font

        except Exception as e:

            print(
                f"⚠️ 폰트 로드 실패: "
                f"{path} / {e}"
            )

    raise RuntimeError(
        "❌ 한글 폰트를 찾지 못했습니다.\n"
        "GitHub Actions에서 fonts-noto-cjk 설치가 필요합니다."
    )


# ============================================================
# 텍스트 크기
# ============================================================

def measure_text(
    text,
    font,
):

    dummy = Image.new(
        "RGBA",
        (10, 10),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        dummy
    )

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=2,
    )

    width = (
        bbox[2] - bbox[0]
    )

    height = (
        bbox[3] - bbox[1]
    )

    return (
        width,
        height,
        bbox,
    )


# ============================================================
# 자막 이미지 생성
# ============================================================

def render_subtitle_image(text):

    text = str(text).strip()

    if not text:

        return np.zeros(
            (
                120,
                VIDEO_WIDTH,
                4,
            ),
            dtype=np.uint8,
        )

    font_size = (
        SUBTITLE_FONT_SIZE
    )

    font = get_korean_font(
        font_size
    )

    padding_x = 50
    padding_y = 30

    max_width = (
        VIDEO_WIDTH
        - padding_x * 2
    )

    # --------------------------------------------------------
    # 화면을 넘으면 폰트 크기 자동 축소
    # --------------------------------------------------------

    while True:

        (
            text_width,
            text_height,
            bbox,
        ) = measure_text(
            text,
            font,
        )

        if (
            text_width <= max_width
            or font_size <= 42
        ):
            break

        font_size -= 2

        font = get_korean_font(
            font_size
        )

    img_h = max(
        120,
        text_height
        + padding_y * 2,
    )

    img = Image.new(
        "RGBA",
        (
            VIDEO_WIDTH,
            img_h,
        ),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        img
    )

    x = int(
        (
            VIDEO_WIDTH
            - text_width
        )
        / 2
        - bbox[0]
    )

    y = int(
        (
            img_h
            - text_height
        )
        / 2
        - bbox[1]
    )

    # --------------------------------------------------------
    # 노란 글씨 + 검은 외곽선
    # --------------------------------------------------------

    draw.text(
        (x, y),
        text,
        font=font,
        fill=SUBTITLE_TEXT_COLOR,
        stroke_width=SUBTITLE_STROKE_WIDTH,
        stroke_fill=SUBTITLE_STROKE_COLOR,
    )

    return np.array(
        img
    )


# ============================================================
# 자막 문장 분할
# ============================================================

def split_subtitle_text(text):

    text = str(text).strip()

    if not text:
        return []

    # --------------------------------------------------------
    # 문장부호 기준 우선 분리
    # --------------------------------------------------------

    normalized = (
        text
        .replace("!", "!\n")
        .replace("?", "?\n")
        .replace(".", ".\n")
    )

    sentences = [
        part.strip()
        for part in normalized.split("\n")
        if part.strip()
    ]

    if not sentences:
        sentences = [text]

    chunks = []

    # --------------------------------------------------------
    # 너무 긴 문장은 의미 단위에 가깝게 줄임
    # --------------------------------------------------------

    for sentence in sentences:

        if len(sentence) <= 16:

            chunks.append(
                sentence
            )

            continue

        words = sentence.split()

        current = ""

        for word in words:

            candidate = (
                f"{current} {word}".strip()
            )

            if (
                len(candidate) > 16
                and current
            ):

                chunks.append(
                    current
                )

                current = word

            else:

                current = candidate

        if current:

            chunks.append(
                current
            )

    if not chunks:

        chunks = [text]

    return chunks


# ============================================================
# 자막 클립 생성
# ============================================================

def create_subtitle_clips(
    text,
    duration,
):

    chunks = split_subtitle_text(
        text
    )

    if not chunks:

        return []

    duration = float(
        duration
    )

    if duration <= 0:

        raise ValueError(
            "자막 duration이 0 이하입니다."
        )

    # --------------------------------------------------------
    # 현재는 균등 배분
    #
    # 추후 V4에서 TTS word timestamp 기반으로
    # 정확한 싱크 가능
    # --------------------------------------------------------

    chunk_duration = (
        duration
        / len(chunks)
    )

    clips = []

    subtitle_y = int(
        VIDEO_HEIGHT * 0.70
    )

    for idx, chunk in enumerate(
        chunks
    ):

        image = render_subtitle_image(
            chunk
        )

        clip = (
            ImageClip(
                image
            )
            .set_start(
                idx * chunk_duration
            )
            .set_duration(
                chunk_duration
            )
            .set_position(
                (
                    "center",
                    subtitle_y,
                )
            )
        )

        clips.append(
            clip
        )

    return clips

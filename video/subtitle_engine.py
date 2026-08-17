# video/subtitle_engine.py

import os
import re

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

SUBTITLE_MAX_CHARS = 16
SOFT_BREAK_MIN_CHARS = 7
CONNECTIVE_WORDS = {
    "하지만", "그런데", "그래서", "반면", "그리고",
    "또한", "즉", "특히", "결국",
}


def _visible_len(text):
    return len(
        re.sub(
            r"\s+",
            "",
            str(text or ""),
        )
    )


def _ends_strong(word):
    return bool(
        re.search(
            r"[.!?…]+[\"'”’)]*$",
            word,
        )
    )


def _ends_soft(word):
    return bool(
        re.search(
            r"[,;:]+[\"'”’)]*$",
            word,
        )
    )


def _rebalance_subtitle_chunks(chunks):
    chunks = [
        chunk.strip()
        for chunk in chunks
        if chunk and chunk.strip()
    ]

    if len(chunks) < 2:
        return chunks

    # 마지막에 1~2어절짜리 아주 짧은 조각만 홀로 남는 것을 줄인다.
    last = chunks[-1]
    previous = chunks[-2]

    if (
        _visible_len(last) <= 4
        and _visible_len(previous) <= SUBTITLE_MAX_CHARS - 3
    ):
        merged = f"{previous} {last}".strip()
        if _visible_len(merged) <= SUBTITLE_MAX_CHARS + 2:
            chunks[-2:] = [merged]

    return chunks


def split_subtitle_text(text):

    text = re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )

    if not text:
        return []

    words = text.split()
    chunks = []
    current_words = []

    def flush():
        nonlocal current_words
        if current_words:
            chunks.append(
                " ".join(current_words).strip()
            )
            current_words = []

    for word in words:
        clean_word = word.lstrip("“\"'‘(")
        current_text = " ".join(current_words).strip()

        # 접속어가 새 의미 단위를 시작하면 그 앞에서 끊는다.
        if (
            current_words
            and clean_word in CONNECTIVE_WORDS
            and _visible_len(current_text) >= SOFT_BREAK_MIN_CHARS
        ):
            flush()
            current_text = ""

        candidate_words = current_words + [word]
        candidate = " ".join(candidate_words).strip()

        # 최대 길이를 넘기기 전에 기존 의미 단위를 확정한다.
        if (
            current_words
            and _visible_len(candidate) > SUBTITLE_MAX_CHARS
        ):
            flush()

        current_words.append(word)
        current_text = " ".join(current_words).strip()

        # 강한 문장부호는 바로 끊는다.
        if _ends_strong(word):
            flush()
            continue

        # 쉼표 등은 충분한 길이가 쌓였을 때만 자연스러운 호흡으로 사용한다.
        if (
            _ends_soft(word)
            and _visible_len(current_text) >= SOFT_BREAK_MIN_CHARS
        ):
            flush()

    flush()

    if not chunks:
        chunks = [text]

    return _rebalance_subtitle_chunks(
        chunks
    )


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
    # 자막 길이에 비례해 노출 시간을 배분한다.
    # 짧은 조각과 긴 조각을 똑같은 시간 동안 띄우던 현상을 줄인다.
    # TTS word timestamp 없이도 마지막 자막은 장면 끝에 정확히 맞춘다.
    # --------------------------------------------------------

    weights = [
        max(
            4,
            _visible_len(chunk),
        )
        for chunk in chunks
    ]
    total_weight = float(
        sum(weights)
    )

    clips = []

    subtitle_y = int(
        VIDEO_HEIGHT * 0.70
    )

    start = 0.0

    for idx, (chunk, weight) in enumerate(
        zip(chunks, weights)
    ):

        if idx == len(chunks) - 1:
            chunk_duration = max(
                0.01,
                duration - start,
            )
        else:
            chunk_duration = (
                duration
                * weight
                / total_weight
            )

        image = render_subtitle_image(
            chunk
        )

        clip = (
            ImageClip(
                image
            )
            .set_start(
                start
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

        start += chunk_duration

    return clips

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
#   - 실제 장면 프레임을 보고 자막 안전 위치 선택
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
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
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

SUBTITLE_SAFE_WIDTH_RATIO = 0.84
SUBTITLE_SAFE_X_MIN_RATIO = 0.07
SUBTITLE_SAFE_X_MAX_RATIO = 0.93
SUBTITLE_MAX_LINES = 2
SUBTITLE_LINE_GAP = 10


def subtitle_image_bbox(image):
    arr = np.asarray(image)
    if arr.ndim != 3 or arr.shape[2] < 4:
        return None
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if not len(xs):
        return None
    return (
        int(xs.min()),
        int(ys.min()),
        int(xs.max()) + 1,
        int(ys.max()) + 1,
    )


def _line_width(line, font):
    return measure_text(line, font)[0]


def _split_long_word(word, font, max_width):
    pieces = []
    current = ""
    for char in str(word):
        candidate = current + char
        if current and _line_width(candidate, font) > max_width:
            pieces.append(current)
            current = char
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _wrap_subtitle_lines(text, font, max_width):
    words = str(text or "").split()
    if not words:
        return []

    lines = []
    current = ""
    for word in words:
        word_parts = (
            _split_long_word(word, font, max_width)
            if _line_width(word, font) > max_width
            else [word]
        )
        for part in word_parts:
            candidate = f"{current} {part}".strip() if current else part
            if current and _line_width(candidate, font) > max_width:
                lines.append(current)
                current = part
            else:
                current = candidate
    if current:
        lines.append(current)
    return lines


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

    max_width = int(
        VIDEO_WIDTH
        * SUBTITLE_SAFE_WIDTH_RATIO
    )

    padding_y = 30

    while True:
        lines = _wrap_subtitle_lines(
            text,
            font,
            max_width,
        )
        if not lines:
            lines = [text]

        line_metrics = [
            measure_text(line, font)
            for line in lines
        ]
        text_width = max(width for width, _, _ in line_metrics)
        text_height = (
            sum(height for _, height, _ in line_metrics)
            + SUBTITLE_LINE_GAP * max(0, len(lines) - 1)
        )

        if (
            text_width <= max_width
            and len(lines) <= SUBTITLE_MAX_LINES
            or font_size <= 42
        ):
            break

        font_size -= 2

        font = get_korean_font(
            font_size
        )

    if len(lines) > SUBTITLE_MAX_LINES:
        merged_tail = " ".join(lines[SUBTITLE_MAX_LINES - 1:])
        lines = lines[:SUBTITLE_MAX_LINES - 1] + [merged_tail]
        line_metrics = [
            measure_text(line, font)
            for line in lines
        ]
        text_width = max(width for width, _, _ in line_metrics)
        text_height = (
            sum(height for _, height, _ in line_metrics)
            + SUBTITLE_LINE_GAP * max(0, len(lines) - 1)
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

    y = int(
        (
            img_h
            - text_height
        )
        / 2
    )

    for line, (line_width, line_height, bbox) in zip(lines, line_metrics):
        x = int(
            (
                VIDEO_WIDTH
                - line_width
            )
            / 2
            - bbox[0]
        )
        draw.text(
            (x, y - bbox[1]),
            line,
            font=font,
            fill=SUBTITLE_TEXT_COLOR,
            stroke_width=SUBTITLE_STROKE_WIDTH,
            stroke_fill=SUBTITLE_STROKE_COLOR,
        )
        y += line_height + SUBTITLE_LINE_GAP

    return np.array(
        img
    )


# ============================================================
# 자막 안전 위치
# ============================================================

SUBTITLE_POSITION_CANDIDATES = (
    ("top", 0.16),
    ("middle", 0.45),
    ("bottom", 0.70),
)

HOOK_SUBTITLE_POSITION_CANDIDATES = (
    ("top", 0.10),
    ("upper", 0.28),
    ("lower", 0.62),
    ("bottom", 0.78),
)

# 기존 하단 배치를 기본으로 유지하되 실제 프레임의 시각 정보가
# 더 복잡할 때만 위쪽 후보로 이동한다.
SUBTITLE_POSITION_BIAS = {
    "top": 0.030,
    "middle": 0.015,
    "bottom": 0.000,
}

HOOK_SUBTITLE_POSITION_BIAS = {
    "top": 0.010,
    "upper": 0.005,
    "lower": 0.000,
    "bottom": 0.015,
}


def _visual_region_score(frame, y_top, band_height):
    frame = np.asarray(frame)

    if frame.ndim != 3 or frame.shape[2] < 3:
        return 999.0

    height, width = frame.shape[:2]

    if height <= 0 or width <= 0:
        return 999.0

    x1 = int(width * 0.07)
    x2 = int(width * 0.93)
    y1 = max(0, int(y_top))
    y2 = min(height, int(y_top + band_height))

    if x2 <= x1 or y2 <= y1:
        return 999.0

    region = frame[
        y1:y2,
        x1:x2,
        :3,
    ].astype(np.float32)

    if region.size <= 0:
        return 999.0

    region = region[::4, ::4]

    r = region[:, :, 0]
    g = region[:, :, 1]
    b = region[:, :, 2]

    gray = (
        0.299 * r
        + 0.587 * g
        + 0.114 * b
    )

    edge_x = (
        np.mean(
            np.abs(
                np.diff(
                    gray,
                    axis=1,
                )
            )
        )
        if gray.shape[1] > 1
        else 0.0
    )

    edge_y = (
        np.mean(
            np.abs(
                np.diff(
                    gray,
                    axis=0,
                )
            )
        )
        if gray.shape[0] > 1
        else 0.0
    )

    edge_score = (
        edge_x + edge_y
    ) / 510.0

    contrast_score = (
        float(np.std(gray))
        / 255.0
    )

    max_rgb = np.maximum.reduce(
        [r, g, b]
    )
    min_rgb = np.minimum.reduce(
        [r, g, b]
    )

    skin_mask = (
        (r > 95)
        & (g > 40)
        & (b > 20)
        & ((max_rgb - min_rgb) > 15)
        & (np.abs(r - g) > 15)
        & (r > g)
        & (r > b)
    )

    skin_ratio = float(
        np.mean(
            skin_mask
        )
    )

    return (
        edge_score * 1.7
        + contrast_score * 0.55
        + skin_ratio * 1.4
    )


def choose_safe_subtitle_y(
    video_clip,
    subtitle_height=180,
    hook_mode=False,
):
    default_y = int(
        VIDEO_HEIGHT
        * (
            0.78
            if hook_mode
            else 0.70
        )
    )

    if video_clip is None:
        return default_y

    try:
        duration = float(
            video_clip.duration or 0
        )
    except Exception:
        duration = 0.0

    if duration <= 0:
        return default_y

    sample_ratios = (
        (
            0.08,
            0.22,
            0.40,
            0.60,
            0.82,
        )
        if hook_mode
        else (
            0.20,
            0.50,
            0.80,
        )
    )

    sample_times = [
        max(
            0.0,
            min(
                duration - 0.01,
                duration * ratio,
            ),
        )
        for ratio in sample_ratios
    ]

    position_candidates = (
        HOOK_SUBTITLE_POSITION_CANDIDATES
        if hook_mode
        else SUBTITLE_POSITION_CANDIDATES
    )

    position_bias = (
        HOOK_SUBTITLE_POSITION_BIAS
        if hook_mode
        else SUBTITLE_POSITION_BIAS
    )

    candidate_scores = {}

    for name, ratio in position_candidates:

        y_top = int(
            VIDEO_HEIGHT * ratio
        )

        scores = []

        for sample_time in sample_times:

            try:
                frame = video_clip.get_frame(
                    sample_time
                )
            except Exception:
                continue

            scores.append(
                _visual_region_score(
                    frame,
                    y_top,
                    subtitle_height,
                )
            )

        if not scores:
            continue

        candidate_scores[name] = (
            float(np.mean(scores))
            + position_bias.get(
                name,
                0.0,
            )
        )

    if not candidate_scores:
        return default_y

    best_name = min(
        candidate_scores,
        key=candidate_scores.get,
    )

    ratio_map = dict(
        position_candidates
    )

    best_y = int(
        VIDEO_HEIGHT
        * ratio_map[best_name]
    )

    print(
        "🧭 Subtitle safe-area"
        + (
            "[HOOK]: "
            if hook_mode
            else ": "
        )
        + " / ".join(
            f"{name}={score:.3f}"
            for name, score
            in candidate_scores.items()
        )
        + f" -> {best_name}"
    )

    return best_y


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

        if (
            current_words
            and clean_word in CONNECTIVE_WORDS
            and _visible_len(current_text) >= SOFT_BREAK_MIN_CHARS
        ):
            flush()
            current_text = ""

        candidate_words = current_words + [word]
        candidate = " ".join(candidate_words).strip()

        if (
            current_words
            and _visible_len(candidate) > SUBTITLE_MAX_CHARS
        ):
            flush()

        current_words.append(word)
        current_text = " ".join(current_words).strip()

        if _ends_strong(word):
            flush()
            continue

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
    video_clip=None,
    hook_mode=False,
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

    subtitle_y = choose_safe_subtitle_y(
        video_clip,
        hook_mode=hook_mode,
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

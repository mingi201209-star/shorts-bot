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


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


# ============================================================
# 한글 폰트
# ============================================================

def get_safe_korean_font(size):

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
        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
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
# 자막 이미지
# ============================================================

def render_subtitle_image(text):

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

    x = max(
        20,
        int(
            (target_w - text_width)
            / 2
        )
    )

    y = padding

    # 검은 외곽선
    draw.text(
        (x, y),
        text,
        font=font,
        fill="black",
        stroke_width=8,
        stroke_fill="black"
    )

    # 노란색 본문
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
# 자막 분할
# ============================================================

def create_split_subtitles(
    text,
    duration
):

    words = text.split()

    if not words:
        return []

    chunks = []

    current = []

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

    chunk_duration = (
        duration / len(chunks)
    )

    subtitle_clips = []

    for idx, chunk in enumerate(
        chunks
    ):

        subtitle_image = (
            render_subtitle_image(
                chunk
            )
        )

        start_time = (
            idx * chunk_duration
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
# 장면 하나 생성
# ============================================================

def create_scene(
    idx,
    item,
    create_voice,
    requests_module
):

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

    if not text:

        raise ValueError(
            f"{idx}번 장면의 text가 비어 있습니다."
        )

    if not keyword:

        keyword = "nature landscape"

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

    audio_path = (
        f"scene_{idx}.mp3"
    )

    video_path = (
        f"video_{idx}.mp4"
    )

    # --------------------------------------------------------
    # TTS
    # --------------------------------------------------------

    create_voice(
        text,
        audio_path
    )

    # --------------------------------------------------------
    # 오디오 길이
    # --------------------------------------------------------

    audio_clip = AudioFileClip(
        audio_path
    )

    duration = audio_clip.duration

    print(
        f"⏱️ 장면 길이: "
        f"{duration:.2f}초"
    )

    # --------------------------------------------------------
    # Pexels 검색
    # --------------------------------------------------------

    video_url = fetch_pexels_video(
        keyword
    )

    # --------------------------------------------------------
    # 영상 다운로드
    # --------------------------------------------------------

    download_video(
        video_url,
        video_path,
        requests_module
    )

    # --------------------------------------------------------
    # 영상 크롭 / 9:16 변환
    # --------------------------------------------------------

    video_clip = process_video_clip(
        video_path,
        duration
    )

    # --------------------------------------------------------
    # 자막
    # --------------------------------------------------------

    subtitle_clips = (
        create_split_subtitles(
            text,
            duration
        )
    )

    # --------------------------------------------------------
    # 영상 + 자막 + 음성
    # --------------------------------------------------------

    combined = (
        CompositeVideoClip(
            [video_clip]
            + subtitle_clips
        )
        .set_audio(
            audio_clip
        )
        .set_duration(
            duration
        )
    )

    return combined

import os
import subprocess

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


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


# ============================================================
# 한글 폰트
# ============================================================

def get_safe_korean_font(size):
    """
    GitHub Actions / Ubuntu 환경에서
    한글을 확실하게 표시할 수 있는 폰트를 찾는다.

    중요:
    DejaVuSans를 한글 fallback으로 사용하지 않는다.
    한글 글리프가 없으면 네모(□)가 발생할 수 있기 때문이다.
    """

    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",

        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",

        "NanumGothicExtraBold.ttf",
        "NanumGothicBold.ttf",
        "NanumGothic.ttf",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                print(f"✅ 한글 폰트 사용: {path}")
                return font
            except Exception as e:
                print(f"⚠️ 폰트 로드 실패: {path} / {e}")

    raise RuntimeError(
        "❌ 한글 폰트를 찾지 못했습니다.\n"
        "GitHub Actions에서 fonts-noto-cjk 설치가 필요합니다."
    )


# ============================================================
# 자막 이미지
# ============================================================

def render_subtitle_image(text):
    text = str(text).strip()

    if not text:
        return np.zeros(
            (120, VIDEO_WIDTH, 4),
            dtype=np.uint8,
        )

    target_w = VIDEO_WIDTH
    font_size = 70

    font = get_safe_korean_font(font_size)

    padding_x = 40
    padding_y = 30

    dummy = Image.new(
        "RGBA",
        (10, 10),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(dummy)

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=2,
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 화면 폭을 넘어가는 경우
    max_text_width = target_w - (padding_x * 2)

    if text_width > max_text_width:
        font_size = 60
        font = get_safe_korean_font(font_size)

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
            stroke_width=2,
        )

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

    img_h = max(
        120,
        text_height + padding_y * 2,
    )

    img = Image.new(
        "RGBA",
        (target_w, img_h),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(img)

    x = max(
        padding_x,
        int((target_w - text_width) / 2),
    )

    y = max(
        10,
        int((img_h - text_height) / 2) - 4,
    )

    # ========================================================
    # 검은 외곽선
    # ========================================================

    draw.text(
        (x, y),
        text,
        font=font,
        fill="#FFE600",
        stroke_width=9,
        stroke_fill="#000000",
    )

    # ========================================================
    # 노란 본문
    # ========================================================

    draw.text(
        (x, y),
        text,
        font=font,
        fill="#FFE600",
        stroke_width=2,
        stroke_fill="#FFE600",
    )

    return np.array(img)


# ============================================================
# 자막 분할
# ============================================================

def create_split_subtitles(text, duration):
    """
    기존의 무조건 3단어 분할 방식을 제거한다.

    우선 문장 단위로 유지하고,
    너무 긴 문장만 자연스럽게 나눈다.
    """

    text = str(text).strip()

    if not text:
        return []

    # --------------------------------------------------------
    # 문장 분리
    # --------------------------------------------------------

    normalized = (
        text
        .replace("!", "!\n")
        .replace("?", "?\n")
        .replace("。", "。\n")
        .replace("！", "！\n")
        .replace("？", "？\n")
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
    # 긴 문장만 분할
    # --------------------------------------------------------

    for sentence in sentences:

        if len(sentence) <= 14:
            chunks.append(sentence)
            continue

        words = sentence.split()

        # 띄어쓰기가 거의 없는 한국어 문장
        if len(words) <= 1:
            start = 0

            while start < len(sentence):
                chunks.append(
                    sentence[start:start + 12]
                )
                start += 12

            continue

        current = ""

        for word in words:

            candidate = (
                f"{current} {word}".strip()
            )

            if (
                len(candidate) > 14
                and current
            ):
                chunks.append(current)
                current = word
            else:
                current = candidate

        if current:
            chunks.append(current)

    if not chunks:
        chunks = [text]

    # --------------------------------------------------------
    # 자막 표시 시간
    # --------------------------------------------------------

    chunk_duration = duration / len(chunks)

    subtitle_clips = []

    for idx, chunk in enumerate(chunks):

        subtitle_image = render_subtitle_image(
            chunk
        )

        clip = (
            ImageClip(subtitle_image)
            .set_start(
                idx * chunk_duration
            )
            .set_duration(
                chunk_duration
            )
            .set_position(
                (
                    "center",
                    int(VIDEO_HEIGHT * 0.70),
                )
            )
        )

        subtitle_clips.append(clip)

    return subtitle_clips


# ============================================================
# FFmpeg 확인
# ============================================================

def check_ffmpeg():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )

        return result.returncode == 0

    except Exception:
        return False


# ============================================================
# 세로 영상 변환
# ============================================================

def prepare_vertical_video(
    input_path,
    output_path,
    duration,
):
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"원본 영상 파일이 없습니다: {input_path}"
        )

    if not check_ffmpeg():
        raise RuntimeError(
            "FFmpeg를 찾을 수 없습니다."
        )

    duration = float(duration)

    if duration <= 0:
        raise ValueError(
            f"잘못된 영상 길이: {duration}"
        )

    vf = (
        "scale="
        f"{VIDEO_WIDTH}:"
        f"{VIDEO_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        "crop="
        f"{VIDEO_WIDTH}:"
        f"{VIDEO_HEIGHT},"
        "setsar=1"
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        input_path,

        "-t",
        str(duration),

        "-vf",
        vf,

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        output_path,
    ]

    print("🎞️ FFmpeg 세로 영상 변환 시작...")

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        print(result.stderr[-4000:])

        raise RuntimeError(
            "FFmpeg 영상 변환 실패"
        )

    if not os.path.exists(output_path):
        raise RuntimeError(
            "FFmpeg 변환 결과 파일이 생성되지 않았습니다."
        )

    print(
        f"✅ 세로 영상 생성 완료: {output_path}"
    )

    return output_path


# ============================================================
# 영상 길이 맞추기
# ============================================================

def load_video_for_scene(
    video_path,
    duration,
):
    clip = VideoFileClip(video_path)

    if clip.duration <= 0:
        clip.close()

        raise RuntimeError(
            "다운로드된 영상의 길이가 0입니다."
        )

    if clip.duration > duration:

        clip = clip.subclip(
            0,
            duration,
        )

    elif clip.duration < duration:

        original_duration = clip.duration

        clips = []
        remaining = duration

        while remaining > 0:

            part_duration = min(
                original_duration,
                remaining,
            )

            clips.append(
                clip.subclip(
                    0,
                    part_duration,
                )
            )

            remaining -= part_duration

        from moviepy.editor import concatenate_videoclips

        clip = concatenate_videoclips(
            clips,
            method="compose",
        )

    return clip.set_duration(duration)


# ============================================================
# 임시 영상 파일명
# ============================================================

def get_processed_video_path(idx):
    return f"vertical_video_{idx}.mp4"


# ============================================================
# 장면 하나 생성
# ============================================================

def create_scene(
    idx,
    item,
    create_voice,
    requests_module,
):
    """
    main.py와 호환되는 장면 생성 함수
    """

    if not isinstance(item, dict):
        raise TypeError(
            "scene item은 dict여야 합니다. "
            f"현재 타입: {type(item)}"
        )

    text = str(
        item.get(
            "text",
            "",
        )
    ).strip()

    keyword = str(
        item.get(
            "keyword",
            "nature landscape",
        )
    ).strip()

    if not text:
        raise ValueError(
            f"{idx + 1}번 장면의 text가 비어 있습니다."
        )

    if not keyword:
        keyword = "nature landscape"

    print("")
    print("=" * 42)
    print(f"🎬 SCENE {idx + 1}")
    print("=" * 42)

    print(f"대사: {text}")
    print(f"검색어: {keyword}")

    audio_path = f"scene_{idx}.mp3"
    source_video_path = f"video_{idx}.mp4"
    vertical_video_path = get_processed_video_path(idx)

    # ========================================================
    # TTS
    # ========================================================

    print("🎙️ TTS 생성 시작...")

    create_voice(
        text,
        audio_path,
    )

    if not os.path.exists(audio_path):
        raise RuntimeError(
            f"TTS 파일이 생성되지 않았습니다: {audio_path}"
        )

    print(
        f"✅ TTS 생성 완료: {audio_path}"
    )

    # ========================================================
    # 오디오 길이
    # ========================================================

    audio_clip = None

    try:

        audio_clip = AudioFileClip(
            audio_path
        )

        duration = float(
            audio_clip.duration
        )

    except Exception as e:

        raise RuntimeError(
            f"TTS 오디오를 읽을 수 없습니다: {e}"
        )

    if duration <= 0:

        audio_clip.close()

        raise RuntimeError(
            "TTS 오디오 길이가 0입니다."
        )

    print(
        f"⏱️ 장면 길이: {duration:.2f}초"
    )

    # ========================================================
    # Pexels
    # ========================================================

    print(
        f"🔎 Pexels 검색: {keyword}"
    )

    video_url = fetch_pexels_video(
        keyword
    )

    if not video_url:

        audio_clip.close()

        raise RuntimeError(
            f"Pexels에서 영상을 찾지 못했습니다: {keyword}"
        )

    print(
        "✅ Pexels 영상 검색 완료"
    )

    # ========================================================
    # 다운로드
    # ========================================================

    print("⬇️ 영상 다운로드 시작...")

    download_video(
        video_url,
        source_video_path,
        requests_module,
    )

    if not os.path.exists(
        source_video_path
    ):

        audio_clip.close()

        raise RuntimeError(
            f"영상 다운로드 실패: {source_video_path}"
        )

    print(
        f"✅ 영상 다운로드 완료: {source_video_path}"
    )

    # ========================================================
    # 9:16 변환
    # ========================================================

    prepare_vertical_video(
        source_video_path,
        vertical_video_path,
        duration,
    )

    # ========================================================
    # 영상 로드
    # ========================================================

    video_clip = None

    try:

        video_clip = load_video_for_scene(
            vertical_video_path,
            duration,
        )

    except Exception:

        audio_clip.close()

        raise

    # ========================================================
    # 자막
    # ========================================================

    print("💬 자막 생성...")

    subtitle_clips = create_split_subtitles(
        text,
        duration,
    )

    print(
        f"✅ 자막 {len(subtitle_clips)}개 생성"
    )

    # ========================================================
    # 영상 + 자막
    # ========================================================

    layers = [
        video_clip
    ]

    layers.extend(
        subtitle_clips
    )

    combined = CompositeVideoClip(
        layers,
        size=(
            VIDEO_WIDTH,
            VIDEO_HEIGHT,
        ),
    )

    # ========================================================
    # 음성 연결
    # ========================================================

    combined = (
        combined
        .set_audio(audio_clip)
        .set_duration(duration)
    )

    print(
        f"✅ SCENE {idx + 1} 생성 완료"
    )

    return combined


# ============================================================
# 장면 정리
# ============================================================

def close_scene(scene):
    if scene is None:
        return

    try:
        scene.close()
    except Exception:
        pass


# ============================================================
# 임시 파일 정리
# ============================================================

def cleanup_scene_files(
    idx,
    remove_source=True,
):
    files = [
        f"scene_{idx}.mp3",
        f"video_{idx}.mp4",
        f"vertical_video_{idx}.mp4",
    ]

    for path in files:

        if (
            not remove_source
            and path == f"video_{idx}.mp4"
        ):
            continue

        try:

            if os.path.exists(path):

                os.remove(path)

                print(
                    f"🧹 삭제: {path}"
                )

        except Exception as e:

            print(
                f"⚠️ 파일 삭제 실패 "
                f"{path}: {e}"
            )


# ============================================================
# 전체 장면 결합
# ============================================================

def combine_scenes(
    scenes,
    output_path="shorts_final.mp4",
):
    """
    생성된 장면들을 하나의 Shorts 영상으로 결합
    """

    if not scenes:
        raise ValueError(
            "결합할 장면이 없습니다."
        )

    print("")
    print("=" * 42)
    print("🎬 전체 장면 결합")
    print("=" * 42)

    from moviepy.editor import concatenate_videoclips

    final_clip = None

    try:

        final_clip = concatenate_videoclips(
            scenes,
            method="compose",
        )

        final_clip.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=2,
            logger="bar",
        )

    finally:

        if final_clip is not None:

            try:
                final_clip.close()
            except Exception:
                pass

    if not os.path.exists(output_path):
        raise RuntimeError(
            f"최종 영상이 생성되지 않았습니다: {output_path}"
        )

    print("")
    print("=" * 42)
    print("🎉 전체 영상 생성 완료")
    print("=" * 42)
    print(
        f"📦 출력 파일: {output_path}"
    )

    return output_path

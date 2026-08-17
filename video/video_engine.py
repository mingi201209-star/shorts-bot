# video/video_engine.py

import os
import subprocess

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
)

from video.video_downloader import (
    fetch_pexels_video,
    download_video,
)

from video.subtitle_engine import (
    create_subtitle_clips,
)


# ============================================================
# Video Engine V3
# ============================================================
#
# 책임:
#
#   1. TTS 파일 생성 요청
#   2. 장면용 영상 검색/다운로드
#   3. 9:16 영상 변환
#   4. 영상 길이 맞추기
#   5. 자막 엔진 호출
#   6. 영상 + 음성 + 자막 조립
#
# 하지 않는 것:
#
#   - 소재 선정
#   - 대본 생성
#   - B-roll 품질 판단
#   - 자막 글꼴 처리
#   - Telegram
#
# ============================================================


def check_ffmpeg():

    try:

        result = subprocess.run(
            [
                "ffmpeg",
                "-version",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )

        return (
            result.returncode == 0
        )

    except Exception:

        return False


def prepare_vertical_video(
    input_path,
    output_path,
    duration,
):

    if not os.path.exists(
        input_path
    ):

        raise FileNotFoundError(
            f"원본 영상 파일이 없습니다: "
            f"{input_path}"
        )

    if not check_ffmpeg():

        raise RuntimeError(
            "FFmpeg를 찾을 수 없습니다."
        )

    duration = float(
        duration
    )

    if duration <= 0:

        raise ValueError(
            f"잘못된 영상 길이: "
            f"{duration}"
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

    print(
        "🎞️ FFmpeg 세로 변환 시작..."
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        print(
            result.stderr[-4000:]
        )

        raise RuntimeError(
            "FFmpeg 영상 변환 실패"
        )

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "세로 변환 결과 파일이 "
            "생성되지 않았습니다."
        )

    print(
        f"✅ 세로 영상 생성 완료: "
        f"{output_path}"
    )

    return output_path


def load_video_for_scene(
    video_path,
    duration,
):

    duration = float(
        duration
    )

    clip = VideoFileClip(
        video_path
    )

    if clip.duration <= 0:

        clip.close()

        raise RuntimeError(
            "다운로드 영상 길이가 0입니다."
        )

    if clip.duration > duration:

        clip = clip.subclip(
            0,
            duration,
        )

    elif clip.duration < duration:

        original_duration = float(
            clip.duration
        )

        if original_duration <= 0:

            clip.close()

            raise RuntimeError(
                "반복할 영상의 길이가 0입니다."
            )

        parts = []

        remaining = duration

        while remaining > 0:

            part_duration = min(
                original_duration,
                remaining,
            )

            parts.append(
                clip.subclip(
                    0,
                    part_duration,
                )
            )

            remaining -= (
                part_duration
            )

        clip = concatenate_videoclips(
            parts,
            method="compose",
        )

    return clip.set_duration(
        duration
    )


def get_scene_paths(idx):

    return {
        "audio": (
            f"scene_{idx}.mp3"
        ),
        "source_video": (
            f"video_{idx}.mp4"
        ),
        "vertical_video": (
            f"vertical_video_{idx}.mp4"
        ),
    }


def create_scene(
    idx,
    item,
    create_voice,
):
    """
    장면 하나를 생성한다.

    호출:

        create_scene(
            idx,
            item,
            create_voice,
        )

    create_voice는 integrations/tts.py에서 주입한다.
    """

    if not isinstance(
        item,
        dict,
    ):

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
            "",
        )
    ).strip()

    visual_goal = str(
        item.get(
            "visual_goal",
            text,
        )
    ).strip()

    visual_type = str(
        item.get(
            "visual_type",
            "real_world_broll",
        )
    ).strip()

    if not text:

        raise ValueError(
            f"{idx + 1}번 장면의 "
            "text가 비어 있습니다."
        )

    if not keyword:

        raise ValueError(
            f"{idx + 1}번 장면의 "
            "keyword가 비어 있습니다."
        )

    print("")
    print("=" * 48)
    print(
        f"🎬 SCENE {idx + 1}"
    )
    print("=" * 48)

    print(
        f"🗣️ 대사: {text}"
    )

    print(
        f"🎯 Visual goal: {visual_goal}"
    )

    print(
        f"🎨 Visual type: {visual_type}"
    )

    print(
        f"🔎 검색어: {keyword}"
    )

    paths = get_scene_paths(
        idx
    )

    audio_path = (
        paths["audio"]
    )

    source_video_path = (
        paths["source_video"]
    )

    vertical_video_path = (
        paths["vertical_video"]
    )

    print(
        "🎙️ TTS 생성 시작..."
    )

    create_voice(
        text,
        audio_path,
    )

    if not os.path.exists(
        audio_path
    ):

        raise RuntimeError(
            "TTS 파일이 생성되지 않았습니다: "
            f"{audio_path}"
        )

    audio_clip = None
    video_clip = None

    try:

        audio_clip = AudioFileClip(
            audio_path
        )

        duration = float(
            audio_clip.duration
        )

        if duration <= 0:

            raise RuntimeError(
                "TTS 오디오 길이가 0입니다."
            )

        print(
            f"⏱️ 장면 길이: "
            f"{duration:.2f}초"
        )

        print(
            f"🔎 Pexels 검색: {keyword}"
        )

        video_url = (
            fetch_pexels_video(
                keyword
            )
        )

        if not video_url:

            raise RuntimeError(
                "Pexels에서 영상을 "
                f"찾지 못했습니다: {keyword}"
            )

        print(
            "⬇️ 영상 다운로드 시작..."
        )

        download_video(
            video_url,
            source_video_path,
        )

        if not os.path.exists(
            source_video_path
        ):

            raise RuntimeError(
                "영상 다운로드 실패: "
                f"{source_video_path}"
            )

        prepare_vertical_video(
            source_video_path,
            vertical_video_path,
            duration,
        )

        video_clip = (
            load_video_for_scene(
                vertical_video_path,
                duration,
            )
        )

        print(
            "💬 자막 생성..."
        )

        subtitle_clips = (
            create_subtitle_clips(
                text,
                duration,
                video_clip=video_clip,
            )
        )

        print(
            f"✅ 자막 "
            f"{len(subtitle_clips)}개 생성"
        )

        layers = [
            video_clip,
        ]

        layers.extend(
            subtitle_clips
        )

        combined = (
            CompositeVideoClip(
                layers,
                size=(
                    VIDEO_WIDTH,
                    VIDEO_HEIGHT,
                ),
            )
        )

        combined = (
            combined
            .set_audio(
                audio_clip
            )
            .set_duration(
                duration
            )
        )

        print(
            f"✅ SCENE "
            f"{idx + 1} 생성 완료"
        )

        return combined

    except Exception:

        if video_clip is not None:

            try:
                video_clip.close()
            except Exception:
                pass

        if audio_clip is not None:

            try:
                audio_clip.close()
            except Exception:
                pass

        raise


def close_scene(scene):

    if scene is None:
        return

    try:

        scene.close()

    except Exception:

        pass


def cleanup_scene_files(
    idx,
):

    paths = get_scene_paths(
        idx
    )

    for path in paths.values():

        try:

            if os.path.exists(
                path
            ):

                os.remove(
                    path
                )

                print(
                    f"🧹 삭제: {path}"
                )

        except Exception as e:

            print(
                "⚠️ 임시파일 삭제 실패: "
                f"{path} / {e}"
            )

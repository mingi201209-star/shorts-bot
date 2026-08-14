from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips
)

from .video_downloader import download_video
from .video_utils import process_video_clip


VIDEO_BITRATE = "5000k"
FPS = 30
OUTPUT_VIDEO = "final_shorts.mp4"


def create_scene(
    idx,
    item,
    create_voice,
    fetch_pexels_video,
    create_split_subtitles,
    requests_module
):
    text = str(
        item.get("text", "")
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
    print("==============================")
    print(f"🎬 SCENE {idx + 1}")
    print("==============================")
    print(f"대사: {text}")
    print(f"검색어: {keyword}")

    audio_path = f"scene_{idx}.mp3"
    video_path = f"video_{idx}.mp4"

    # TTS
    create_voice(
        text,
        audio_path
    )

    # 오디오 길이
    audio_clip = AudioFileClip(
        audio_path
    )

    duration = audio_clip.duration

    print(
        f"⏱️ 장면 길이: {duration:.2f}초"
    )

    # Pexels 검색
    video_url = fetch_pexels_video(
        keyword
    )

    # 영상 다운로드
    download_video(
        video_url,
        video_path,
        requests_module
    )

    # 영상 처리
    video_clip = process_video_clip(
        video_path,
        duration
    )

    # 자막
    subtitle_clips = create_split_subtitles(
        text,
        duration
    )

    # 영상 + 자막 + 음성 합성
    combined = (
        CompositeVideoClip(
            [video_clip] + subtitle_clips
        )
        .set_audio(audio_clip)
        .set_duration(duration)
    )

    return combined


def check_total_duration(scene_clips):
    total = 0

    for scene in scene_clips:
        try:
            total += scene.duration
        except Exception:
            pass

    print(
        f"🎞️ 예상 최종 길이: "
        f"{total:.2f}초"
    )

    return total


def render_final_video(
    scene_clips,
    output_path=OUTPUT_VIDEO
):
    if not scene_clips:
        raise RuntimeError(
            "생성된 장면이 없습니다."
        )

    print("")
    print("🎞️ 모든 장면 합치는 중...")

    final_video = concatenate_videoclips(
        scene_clips,
        method="chain"
    )

    print(
        f"최종 영상 길이: "
        f"{final_video.duration:.2f}초"
    )

    print("🎬 FFmpeg 렌더링 시작...")

    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate=VIDEO_BITRATE,
        threads=2,
        preset="medium"
    )

    final_video.close()

    print("✅ 최종 영상 렌더링 완료")

    return output_path

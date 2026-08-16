# video/renderer.py

import os

from moviepy.editor import (
    concatenate_videoclips,
)

from config import (
    FPS,
    VIDEO_BITRATE,
    OUTPUT_VIDEO,
    TARGET_MIN_SECONDS,
    TARGET_MAX_SECONDS,
)


# ============================================================
# Renderer V3
# ============================================================
#
# 책임:
#   - 전체 장면 길이 계산
#   - 목표 길이 검사
#   - 장면 결합
#   - 최종 MP4 렌더링
#
# 하지 않는 것:
#   - 대본 생성
#   - TTS
#   - Pexels 검색
#   - 자막 생성
#   - Telegram
#
# ============================================================


# ============================================================
# 전체 장면 길이
# ============================================================

def get_total_duration(
    scene_clips,
):

    if not scene_clips:
        return 0.0

    total = 0.0

    for clip in scene_clips:

        try:

            duration = float(
                clip.duration or 0
            )

        except Exception:

            duration = 0.0

        total += duration

    return total


# ============================================================
# 길이 검사
# ============================================================

def validate_total_duration(
    scene_clips,
):

    total = get_total_duration(
        scene_clips
    )

    print(
        f"⏱️ 장면 합산 길이: "
        f"{total:.2f}초"
    )

    if total < TARGET_MIN_SECONDS:

        print(
            "⚠️ 목표보다 짧습니다: "
            f"{TARGET_MIN_SECONDS}초 미만"
        )

        return False, total

    if total > TARGET_MAX_SECONDS:

        print(
            "⚠️ 목표보다 깁니다: "
            f"{TARGET_MAX_SECONDS}초 초과"
        )

        return False, total

    print(
        "✅ Shorts 목표 길이 통과"
    )

    return True, total


# ============================================================
# 최종 렌더링
# ============================================================

def render_final_video(
    scene_clips,
    output_path=OUTPUT_VIDEO,
):

    if not scene_clips:

        raise RuntimeError(
            "렌더링할 장면이 없습니다."
        )

    print("")
    print("=" * 48)
    print(
        "🎞️ FINAL VIDEO RENDER"
    )
    print("=" * 48)

    total_duration = (
        get_total_duration(
            scene_clips
        )
    )

    print(
        f"🎬 최종 예상 길이: "
        f"{total_duration:.2f}초"
    )

    final_video = None

    try:

        final_video = (
            concatenate_videoclips(
                scene_clips,
                method="compose",
            )
        )

        final_video.write_videofile(

            output_path,

            fps=FPS,

            codec="libx264",

            audio_codec="aac",

            bitrate=VIDEO_BITRATE,

            threads=2,

            preset="medium",
        )

    finally:

        if final_video is not None:

            try:
                final_video.close()

            except Exception:
                pass

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "최종 영상 파일이 "
            f"생성되지 않았습니다: {output_path}"
        )

    if os.path.getsize(
        output_path
    ) <= 0:

        raise RuntimeError(
            "최종 영상 파일 크기가 0입니다."
        )

    print("")
    print(
        f"✅ 최종 영상 생성 완료: "
        f"{output_path}"
    )

    return output_path

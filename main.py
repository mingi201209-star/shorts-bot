import os
import time

from config import (
    get_missing_environment_variables,
    OUTPUT_VIDEO,
    MAX_SCENES,
)

from content.topic_selector import (
    choose_topic_direction,
)

from content.script_generator import (
    generate_script,
)

from video.video_engine import (
    create_scene,
)

from integrations.tts import (
    create_voice,
)

from integrations.telegram import (
    send_telegram_message,
    send_telegram_video,
)


# ============================================================
# Shorts Generator V3
# ============================================================
#
# 전체 흐름
#
# 1. 환경변수 검사
# 2. 콘텐츠 방향 선택
# 3. V3 소재 + 대본 생성
# 4. V3 검증 통과
# 5. 장면별 TTS + 영상 생성
# 6. 전체 영상 렌더링
# 7. Telegram 전송
#
# 각 작업은 별도 모듈이 담당한다.
#
# ============================================================


# ============================================================
# 환경변수 검사
# ============================================================

def validate_environment():

    missing = (
        get_missing_environment_variables()
    )

    if missing:

        error_message = (
            "필수 환경변수가 없습니다:\n"
            + "\n".join(
                f"- {item}"
                for item in missing
            )
        )

        print(
            f"❌ {error_message}"
        )

        send_telegram_message(
            "🚨 Shorts Generator 환경변수 오류\n\n"
            + error_message
        )

        raise RuntimeError(
            error_message
        )

    print(
        "✅ 환경변수 검사 완료"
    )


# ============================================================
# 장면 생성
# ============================================================

def generate_scenes(
    scenes
):

    scene_clips = []

    print("")
    print("=" * 42)
    print(
        f"🎬 총 {len(scenes)}개 장면 생성 시작"
    )
    print("=" * 42)

    for idx, item in enumerate(
        scenes[:MAX_SCENES]
    ):

        try:

            scene = create_scene(
                idx,
                item,
                create_voice,
            )

            scene_clips.append(
                scene
            )

            print(
                f"✅ SCENE {idx + 1} 완료"
            )

        except Exception as e:

            print(
                f"❌ SCENE {idx + 1} 실패: {e}"
            )

            # 이미 생성된 MoviePy 객체 정리
            for clip in scene_clips:

                try:
                    clip.close()

                except Exception:
                    pass

            raise

    return scene_clips


# ============================================================
# 전체 영상 렌더링
# ============================================================

def render_final_video(
    scene_clips
):

    if not scene_clips:

        raise RuntimeError(
            "렌더링할 장면이 없습니다."
        )

    from moviepy.editor import (
        concatenate_videoclips,
    )

    print("")
    print("=" * 42)
    print(
        "🎞️ 전체 영상 렌더링"
    )
    print("=" * 42)

    final_video = None

    try:

        final_video = concatenate_videoclips(
            scene_clips,
            method="compose",
        )

        print(
            f"🎬 최종 영상 길이: "
            f"{final_video.duration:.2f}초"
        )

        final_video.write_videofile(

            OUTPUT_VIDEO,

            fps=30,

            codec="libx264",

            audio_codec="aac",

            bitrate="5000k",

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
        OUTPUT_VIDEO
    ):

        raise RuntimeError(
            "최종 영상 파일이 생성되지 않았습니다."
        )

    print(
        f"✅ 최종 영상 생성 완료: "
        f"{OUTPUT_VIDEO}"
    )

    return OUTPUT_VIDEO


# ============================================================
# 임시 파일 정리
# ============================================================

def cleanup():

    print(
        "🧹 임시 파일 정리"
    )

    temp_files = []

    try:

        for filename in os.listdir("."):

            if (
                filename.startswith("scene_")
                and filename.endswith(".mp3")
            ):

                temp_files.append(
                    filename
                )

            elif (
                filename.startswith("video_")
                and filename.endswith(".mp4")
            ):

                temp_files.append(
                    filename
                )

            elif (
                filename.startswith(
                    "vertical_video_"
                )
                and filename.endswith(".mp4")
            ):

                temp_files.append(
                    filename
                )

    except Exception as e:

        print(
            f"⚠️ 임시 파일 목록 확인 실패: {e}"
        )

        return

    for path in temp_files:

        try:

            os.remove(path)

            print(
                f"삭제: {path}"
            )

        except Exception as e:

            print(
                f"⚠️ 삭제 실패 "
                f"{path}: {e}"
            )


# ============================================================
# 결과 요약
# ============================================================

def send_result_summary(
    script_data,
    duration,
):

    title = script_data.get(
        "title",
        "제목 없음",
    )

    topic = script_data.get(
        "topic",
        "소재 없음",
    )

    category = script_data.get(
        "category",
        "분야 없음",
    )

    novelty = script_data.get(
        "novelty_score",
        "?",
    )

    scenes = script_data.get(
        "scenes",
        [],
    )

    message = (
        "🎬 Shorts 생성 완료!\n\n"
        f"📂 분야: {category}\n"
        f"🧠 소재: {topic}\n"
        f"✨ 신선도: {novelty}/10\n"
        f"📝 제목: {title}\n"
        f"🎞️ 길이: {duration:.1f}초\n"
        f"🎥 장면: {len(scenes)}개\n\n"
        "📦 영상 전송 중..."
    )

    send_telegram_message(
        message
    )


# ============================================================
# 메인
# ============================================================

def main():

    start_time = time.time()

    scene_clips = []

    try:

        print("")
        print("=" * 42)
        print(
            "🚀 SHORTS GENERATOR V3 START"
        )
        print("=" * 42)

        # ----------------------------------------------------
        # 1. 환경변수
        # ----------------------------------------------------

        validate_environment()

        # ----------------------------------------------------
        # 2. 콘텐츠 방향 선택
        # ----------------------------------------------------

        print("")
        print(
            "🎯 콘텐츠 방향 선택"
        )

        topic_info = (
            choose_topic_direction()
        )

        # ----------------------------------------------------
        # 3. V3 소재 + 대본 생성
        # ----------------------------------------------------

        print("")
        print(
            "🧠 V3 콘텐츠 생성"
        )

        script_data = (
            generate_script(
                topic_info
            )
        )

        scenes = script_data.get(
            "scenes",
            [],
        )

        if not scenes:

            raise RuntimeError(
                "AI가 장면을 생성하지 않았습니다."
            )

        # ----------------------------------------------------
        # 4. 장면 생성
        # ----------------------------------------------------

        scene_clips = generate_scenes(
            scenes
        )

        # ----------------------------------------------------
        # 5. 영상 렌더링
        # ----------------------------------------------------

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ----------------------------------------------------
        # 6. 총 길이
        # ----------------------------------------------------

        total_duration = sum(
            float(
                clip.duration or 0
            )
            for clip in scene_clips
        )

        # ----------------------------------------------------
        # 7. Telegram 결과
        # ----------------------------------------------------

        send_result_summary(
            script_data,
            total_duration,
        )

        # ----------------------------------------------------
        # 8. Telegram 영상
        # ----------------------------------------------------

        send_telegram_video(
            final_path
        )

        # ----------------------------------------------------
        # 9. 완료
        # ----------------------------------------------------

        elapsed = (
            time.time()
            - start_time
        )

        print("")
        print("=" * 42)
        print(
            "🎉 SHORTS GENERATOR V3 COMPLETE"
        )
        print(
            f"⏱️ 전체 소요시간: "
            f"{elapsed / 60:.1f}분"
        )
        print("=" * 42)

    except Exception as e:

        print("")
        print("=" * 42)
        print(
            f"💀 SHORTS GENERATOR ERROR: {e}"
        )
        print("=" * 42)

        try:

            send_telegram_message(
                "🚨 Shorts 생성 실패\n\n"
                f"{str(e)[:500]}"
            )

        except Exception:
            pass

        raise

    finally:

        # ----------------------------------------------------
        # MoviePy 객체 정리
        # ----------------------------------------------------

        for clip in scene_clips:

            try:
                clip.close()

            except Exception:
                pass

        # ----------------------------------------------------
        # 임시 파일 정리
        # ----------------------------------------------------

        cleanup()


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()

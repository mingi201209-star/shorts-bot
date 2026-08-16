# main.py

import time

from config import (
    MAX_SCENES,
    get_missing_environment_variables,
)

from content.topic_selector import (
    choose_topic_direction,
)

from content.script_generator import (
    generate_script,
)

from integrations.tts import (
    create_voice,
)

from integrations.telegram import (
    send_telegram_message,
    send_telegram_video,
    send_result_summary,
)

from video.visual_selector import (
    enrich_visual_plan,
    validate_visual_plan,
)

from video.video_engine import (
    create_scene,
)

from video.renderer import (
    render_final_video,
    validate_total_duration,
)


# ============================================================
# Shorts Generator V3
# ============================================================
#
# main.py의 책임:
#
#   1. 전체 파이프라인 실행
#   2. 각 모듈 연결
#   3. 실패 처리
#   4. 리소스 정리
#
# 세부 구현은 각 모듈이 담당한다.
#
# ============================================================


# ============================================================
# 환경변수 검사
# ============================================================

def validate_environment():

    missing = (
        get_missing_environment_variables()
    )

    if not missing:

        print(
            "✅ 환경변수 검사 완료"
        )

        return

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

    # Telegram 환경변수 자체가 없는 경우도 있으므로
    # 메시지 전송 실패는 여기서 다시 예외로 만들지 않는다.
    try:

        send_telegram_message(
            "🚨 Shorts Generator 환경변수 오류\n\n"
            + error_message
        )

    except Exception:

        pass

    raise RuntimeError(
        error_message
    )


# ============================================================
# 장면 생성
# ============================================================

def generate_scenes(
    scenes,
):

    if not scenes:

        raise RuntimeError(
            "생성할 장면이 없습니다."
        )

    scene_clips = []

    print("")
    print("=" * 48)
    print(
        f"🎬 총 {len(scenes)}개 장면 생성"
    )
    print("=" * 48)

    try:

        for idx, item in enumerate(
            scenes[:MAX_SCENES]
        ):

            print("")
            print(
                f"▶ SCENE {idx + 1} 시작"
            )

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

        return scene_clips

    except Exception:

        # 중간 실패 시 이미 생성한 clip 정리
        for clip in scene_clips:

            try:
                clip.close()

            except Exception:
                pass

        raise


# ============================================================
# 메인
# ============================================================

def main():

    start_time = time.time()

    scene_clips = []

    try:

        print("")
        print("=" * 48)
        print(
            "🚀 SHORTS GENERATOR V3 START"
        )
        print("=" * 48)

        # ====================================================
        # 1. 환경변수 검사
        # ====================================================

        validate_environment()

        # ====================================================
        # 2. 콘텐츠 방향 선택
        # ====================================================

        print("")
        print(
            "🎯 콘텐츠 방향 선택..."
        )

        topic_info = (
            choose_topic_direction()
        )

        # ====================================================
        # 3. 소재 + 대본 생성
        # ====================================================

        print("")
        print(
            "🧠 소재 + 대본 생성..."
        )

        script_data = (
            generate_script(
                topic_info
            )
        )

        if not isinstance(
            script_data,
            dict,
        ):

            raise RuntimeError(
                "대본 생성 결과가 dict가 아닙니다."
            )

        scenes = script_data.get(
            "scenes",
            [],
        )

        if not scenes:

            raise RuntimeError(
                "AI가 장면을 생성하지 않았습니다."
            )

        print(
            f"📝 제목: "
            f"{script_data.get('title', '제목 없음')}"
        )

        print(
            f"🧠 소재: "
            f"{script_data.get('topic', '소재 없음')}"
        )

        print(
            f"🎬 장면 수: "
            f"{len(scenes)}"
        )

        # ====================================================
        # 4. Visual metadata 보강
        # ====================================================

        print("")
        print(
            "👁️ Visual plan 구성..."
        )

        scenes = enrich_visual_plan(
            scenes
        )

        script_data[
            "scenes"
        ] = scenes

        # ====================================================
        # 5. Visual plan 검사
        # ====================================================

        visual_ok, visual_reason = (
            validate_visual_plan(
                scenes
            )
        )

        if not visual_ok:

            raise RuntimeError(
                "Visual plan 검증 실패: "
                f"{visual_reason}"
            )

        print(
            "✅ Visual plan 검증 통과"
        )

        # ====================================================
        # 6. 장면 생성
        # ====================================================

        scene_clips = (
            generate_scenes(
                scenes
            )
        )

        # ====================================================
        # 7. 전체 길이 검사
        # ====================================================

        print("")
        print(
            "⏱️ 영상 길이 검사..."
        )

        duration_ok, total_duration = (
            validate_total_duration(
                scene_clips
            )
        )

        if not duration_ok:

            print(
                "⚠️ 목표 영상 길이 범위를 "
                "벗어났습니다."
            )

            # 현재 V3 분리 단계에서는
            # 렌더링은 계속 진행한다.
            #
            # 추후 script_validator에서
            # 재작성 루프로 연결한다.

        # ====================================================
        # 8. 최종 영상 렌더링
        # ====================================================

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ====================================================
        # 9. Telegram 결과 요약
        # ====================================================

        send_result_summary(
            script_data,
            total_duration,
        )

        # ====================================================
        # 10. Telegram 영상 전송
        # ====================================================

        send_telegram_video(
            final_path
        )

        # ====================================================
        # 완료
        # ====================================================

        elapsed = (
            time.time()
            - start_time
        )

        print("")
        print("=" * 48)
        print(
            "🎉 SHORTS GENERATOR V3 COMPLETE"
        )
        print(
            f"⏱️ 전체 소요시간: "
            f"{elapsed / 60:.1f}분"
        )
        print("=" * 48)

    except Exception as e:

        print("")
        print("=" * 48)
        print(
            "💀 SHORTS GENERATOR ERROR"
        )
        print(
            str(e)
        )
        print("=" * 48)

        try:

            send_telegram_message(
                "🚨 Shorts 생성 실패\n\n"
                f"{str(e)[:500]}"
            )

        except Exception:

            pass

        raise

    finally:

        # ====================================================
        # MoviePy 리소스 정리
        # ====================================================

        for clip in scene_clips:

            try:
                clip.close()

            except Exception:
                pass


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()

# main.py

import os
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

from quality.judge import (
    run_judge,
    print_judge_result,
)

from quality.consensus import (
    build_consensus,
    print_consensus,
)

from quality.rewrite_engine import (
    rewrite_script,
    print_rewrite_result,
)

from quality.review_router import (
    choose_review_route,
    execute_extra_review,
    merge_review_results,
    evaluate_fact_appeal,
    print_review_route,
)

from quality.budget_guard import (
    reset_budget,
    print_budget_status,
)


# ============================================================
# Shorts Generator V3.2
# ============================================================

JUDGE_MODEL = os.environ.get(
    "V3_JUDGE_MODEL",
    "gpt-4o-mini",
)

JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
]

MAX_REWRITES = 1
MAX_REVIEW_ROUNDS = 1


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
# 기본 Judge 4종 — 각각 정확히 1회
# ============================================================

def run_initial_judges(
    script_data,
):

    pool = {}

    print("")
    print("=" * 60)
    print("⚖️ V3.2 INITIAL JUDGES")
    print("=" * 60)

    for judge_type in JUDGE_TYPES:

        result = run_judge(
            judge_type,
            script_data,
            model=JUDGE_MODEL,
        )

        print_judge_result(
            result
        )

        pool[
            judge_type
        ] = [
            result
        ]

    return pool


# ============================================================
# Rewrite된 영역만 재심
# ============================================================

def rerun_changed_domains(
    pool_results,
    script_data,
    domains,
):

    new_pool = {
        key: list(value)
        for key, value
        in pool_results.items()
    }

    for domain in domains:

        if domain not in JUDGE_TYPES:
            continue

        print(
            f"🔄 수정 영역 재심: "
            f"{domain.upper()}"
        )

        result = run_judge(
            domain,
            script_data,
            model=JUDGE_MODEL,
        )

        print_judge_result(
            result
        )

        # 이전 판결 누적이 아니라
        # 수정된 콘텐츠에 대한 새 판결로 교체.
        new_pool[
            domain
        ] = [
            result
        ]

    return new_pool


# ============================================================
# 품질 Gate
# ============================================================

def run_quality_process(
    script_data,
):

    current_script = (
        script_data
    )

    rewrite_count = 0
    review_count = 0

    pool_results = (
        run_initial_judges(
            current_script
        )
    )

    while True:

        consensus = (
            build_consensus(
                pool_results
            )
        )

        print_consensus(
            consensus
        )

        decision = consensus.get(
            "decision",
            "REVIEW",
        )

        # ----------------------------------------------------
        # PASS
        # ----------------------------------------------------

        if decision == "PASS":

            return {
                "status": "PASS",
                "script_data":
                    current_script,
                "consensus":
                    consensus,
                "pool_results":
                    pool_results,
            }

        # ----------------------------------------------------
        # REWRITE
        # ----------------------------------------------------

        if decision == "REWRITE":

            if (
                rewrite_count
                >= MAX_REWRITES
            ):

                return {
                    "status": "HOLD",
                    "script_data":
                        current_script,
                    "consensus":
                        consensus,
                    "pool_results":
                        pool_results,
                    "reason":
                        "Rewrite 최대 횟수 초과",
                }

            rewrite_result = (
                rewrite_script(
                    current_script,
                    consensus,
                    model=JUDGE_MODEL,
                )
            )

            print_rewrite_result(
                rewrite_result
            )

            if not rewrite_result.get(
                "changed",
                False,
            ):

                return {
                    "status": "HOLD",
                    "script_data":
                        current_script,
                    "reason":
                        "Rewrite 대상 없음",
                }

            current_script = (
                rewrite_result[
                    "script_data"
                ]
            )

            domains = (
                rewrite_result[
                    "domains"
                ]
            )

            # Rewrite 결과에도
            # visual metadata를 다시 붙인다.
            current_script[
                "scenes"
            ] = enrich_visual_plan(
                current_script.get(
                    "scenes",
                    [],
                )
            )

            visual_ok, reason = (
                validate_visual_plan(
                    current_script[
                        "scenes"
                    ]
                )
            )

            if not visual_ok:

                return {
                    "status": "HOLD",
                    "script_data":
                        current_script,
                    "reason": (
                        "Rewrite 후 Visual 검증 실패: "
                        f"{reason}"
                    ),
                }

            rewrite_count += 1

            pool_results = (
                rerun_changed_domains(
                    pool_results,
                    current_script,
                    domains,
                )
            )

            continue

        # ----------------------------------------------------
        # REVIEW
        # ----------------------------------------------------

        if decision == "REVIEW":

            if (
                review_count
                >= MAX_REVIEW_ROUNDS
            ):

                return {
                    "status": "HOLD",
                    "script_data":
                        current_script,
                    "consensus":
                        consensus,
                    "reason":
                        "Review 최대 횟수 초과",
                }

            route = (
                choose_review_route(
                    consensus
                )
            )

            print_review_route(
                route
            )

            route_type = route.get(
                "route"
            )

            if route_type == "HOLD":

                return {
                    "status": "HOLD",
                    "script_data":
                        current_script,
                    "consensus":
                        consensus,
                    "reason":
                        route.get(
                            "reason",
                            "Review HOLD",
                        ),
                }

            if route_type in (
                "EXTRA_JUDGE",
                "FACT_EXTRA_JUDGE",
            ):

                extra = (
                    execute_extra_review(
                        current_script,
                        route,
                        model=JUDGE_MODEL,
                    )
                )

                merged = (
                    merge_review_results(
                        pool_results,
                        extra,
                    )
                )

                review_count += 1

                # Fact Appeal은 별도 안전 판단.
                if (
                    route_type
                    == "FACT_EXTRA_JUDGE"
                ):

                    appeal = (
                        evaluate_fact_appeal(
                            merged
                        )
                    )

                    print(
                        "⚖️ Fact Appeal:",
                        appeal,
                    )

                    appeal_status = (
                        appeal.get(
                            "status"
                        )
                    )

                    if (
                        appeal_status
                        in (
                            "HOLD",
                            "DISAGREEMENT",
                            "INSUFFICIENT",
                        )
                    ):

                        return {
                            "status": "HOLD",
                            "script_data":
                                current_script,
                            "consensus":
                                consensus,
                            "reason":
                                appeal.get(
                                    "reason",
                                    "Fact Appeal HOLD",
                                ),
                        }

                pool_results = (
                    merged
                )

                continue

            return {
                "status": "HOLD",
                "script_data":
                    current_script,
                "reason":
                    f"알 수 없는 Review route: {route_type}",
            }

        return {
            "status": "HOLD",
            "script_data":
                current_script,
            "reason":
                f"알 수 없는 Consensus: {decision}",
        }


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

            print(
                f"▶ SCENE {idx + 1}"
            )

            scene = create_scene(
                idx,
                item,
                create_voice,
            )

            scene_clips.append(
                scene
            )

        return scene_clips

    except Exception:

        for clip in scene_clips:

            try:
                clip.close()
            except Exception:
                pass

        raise


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = time.time()

    scene_clips = []

    # 실행 단위 Budget 초기화
    reset_budget()

    try:

        print("")
        print("=" * 60)
        print(
            "🚀 SHORTS GENERATOR V3.2 AUTONOMOUS"
        )
        print("=" * 60)

        validate_environment()

        # ----------------------------------------------------
        # 1. V3가 스스로 방향 선택
        # ----------------------------------------------------

        topic_info = (
            choose_topic_direction()
        )

        # ----------------------------------------------------
        # 2. V3가 스스로 소재 + 대본 생성
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 3. Visual Plan
        # ----------------------------------------------------

        scenes = enrich_visual_plan(
            script_data.get(
                "scenes",
                [],
            )
        )

        script_data[
            "scenes"
        ] = scenes

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

        # ----------------------------------------------------
        # 4. V3.2 품질 재판
        # ----------------------------------------------------

        quality = (
            run_quality_process(
                script_data
            )
        )

        if (
            quality.get(
                "status"
            )
            != "PASS"
        ):

            reason = quality.get(
                "reason",
                "품질 Gate HOLD",
            )

            print_budget_status()

            raise RuntimeError(
                "V3.2 Quality Gate HOLD: "
                f"{reason}"
            )

        script_data = (
            quality[
                "script_data"
            ]
        )

        scenes = script_data.get(
            "scenes",
            [],
        )

        print("")
        print(
            "🏆 V3.2 QUALITY PASS"
        )

        print(
            f"📝 제목: "
            f"{script_data.get('title')}"
        )

        print(
            f"🧠 소재: "
            f"{script_data.get('topic')}"
        )

        # ----------------------------------------------------
        # 5. 실제 영상 제작
        # ----------------------------------------------------

        scene_clips = generate_scenes(
            scenes
        )

        # ----------------------------------------------------
        # 6. 영상 길이
        # ----------------------------------------------------

        duration_ok, total_duration = (
            validate_total_duration(
                scene_clips
            )
        )

        if not duration_ok:

            print(
                "⚠️ 목표 영상 길이 범위 이탈"
            )

        # ----------------------------------------------------
        # 7. 렌더링
        # ----------------------------------------------------

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ----------------------------------------------------
        # 8. Telegram
        # ----------------------------------------------------

        send_result_summary(
            script_data,
            total_duration,
        )

        send_telegram_video(
            final_path
        )

        print_budget_status()

        elapsed = (
            time.time()
            - start_time
        )

        print("")
        print("=" * 60)
        print(
            "🎉 V3.2 AUTONOMOUS SHORT COMPLETE"
        )
        print(
            f"⏱️ {elapsed / 60:.1f}분"
        )
        print("=" * 60)

    except Exception as e:

        print("")
        print("=" * 60)
        print("💀 V3.2 ERROR")
        print(str(e))
        print("=" * 60)

        try:

            send_telegram_message(
                "🚨 V3.2 Shorts 생성 실패\n\n"
                f"{str(e)[:500]}"
            )

        except Exception:
            pass

        raise

    finally:

        for clip in scene_clips:

            try:
                clip.close()

            except Exception:
                pass


if __name__ == "__main__":
    main()

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
# Shorts Generator V3.2.1.1
# ============================================================
#
# V3.2.1:
#   Novelty가 Rewrite 후에도 실패하면 소재 폐기.
#
# V3.2.1.1:
#   소재 폐기 시 실제 Novelty Judge의
#
#   - 점수
#   - confidence
#   - reason
#   - issues
#
#   를 다음 소재 Generator에 피드백한다.
#
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


# 한 소재 최대 Rewrite
MAX_REWRITES = 1


# 한 소재 최대 추가 Review
MAX_REVIEW_ROUNDS = 1


# ------------------------------------------------------------
# 최초 소재 + 재생성 1회
#
# 이번 패치 효과 검증을 위해
# 재생성 횟수는 아직 늘리지 않는다.
# ------------------------------------------------------------

MAX_TOPIC_REGENERATIONS = 1


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
# 기본 Judge 4종
# ============================================================

def run_initial_judges(
    script_data,
):

    pool = {}

    print("")
    print("=" * 60)
    print(
        "⚖️ V3.2.1.1 INITIAL JUDGES"
    )
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
# 수정 영역만 재심
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

        print("")
        print(
            "🔄 수정 영역 재심: "
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

        # 콘텐츠가 수정되었으므로
        # 예전 판정과 평균내지 않는다.
        new_pool[
            domain
        ] = [
            result
        ]

    return new_pool


# ============================================================
# Weak Domain 조회
# ============================================================

def get_weak_domain(
    consensus,
    judge_type,
):

    for item in consensus.get(
        "weak_domains",
        [],
    ):

        if (
            item.get(
                "judge_type"
            )
            == judge_type
        ):

            return item

    return None


# ============================================================
# Novelty 지속 실패
# ============================================================

def has_persistent_novelty_failure(
    consensus,
):

    novelty = get_weak_domain(
        consensus,
        "novelty",
    )

    if not novelty:

        return False

    print("")
    print(
        "♻️ Novelty 최소 기준 미달:"
    )

    print(
        "   score =",
        novelty.get(
            "score",
            0,
        ),
    )

    print(
        "   required =",
        novelty.get(
            "minimum",
            0,
        ),
    )

    return True


# ============================================================
# V3.2.1.1
# Novelty Judge 피드백 추출
# ============================================================

def extract_novelty_feedback(
    quality_result,
):

    consensus = (
        quality_result.get(
            "consensus",
            {},
        )
        or {}
    )

    pool_results = (
        quality_result.get(
            "pool_results",
            {},
        )
        or {}
    )

    script_data = (
        quality_result.get(
            "script_data",
            {},
        )
        or {}
    )

    # --------------------------------------------------------
    # Consensus Novelty 요약
    # --------------------------------------------------------

    novelty_summary = (
        consensus
        .get(
            "domain_summaries",
            {},
        )
        .get(
            "novelty",
            {},
        )
        or {}
    )

    weak_novelty = (
        get_weak_domain(
            consensus,
            "novelty",
        )
        or {}
    )

    # --------------------------------------------------------
    # 가장 최근 Novelty Judge 결과
    # --------------------------------------------------------

    novelty_results = (
        pool_results.get(
            "novelty",
            [],
        )
        or []
    )

    latest_judge = {}

    if novelty_results:

        candidate = (
            novelty_results[-1]
        )

        if isinstance(
            candidate,
            dict,
        ):

            latest_judge = (
                candidate
            )

    feedback = {
        "rejected_topic":
            script_data.get(
                "topic",
                "",
            ),

        "rejected_title":
            script_data.get(
                "title",
                "",
            ),

        "novelty_score":
            novelty_summary.get(
                "score",
                latest_judge.get(
                    "score",
                    0,
                ),
            ),

        "required_score":
            weak_novelty.get(
                "minimum",
                6.5,
            ),

        "confidence":
            novelty_summary.get(
                "confidence",
                latest_judge.get(
                    "confidence",
                    0,
                ),
            ),

        "reason":
            latest_judge.get(
                "reason",
                "",
            ),

        "issues":
            latest_judge.get(
                "issues",
                [],
            ),

        "instruction": (
            "이전 후보가 Novelty 부족으로 탈락했습니다. "
            "제목만 바꾸지 말고 핵심 대상, 현상 또는 "
            "메커니즘 자체가 다른 더 신선한 소재를 선택하세요."
        ),
    }

    return feedback


# ============================================================
# Feedback 로그
# ============================================================

def print_generation_feedback(
    feedback,
):

    if not feedback:

        return

    print("")
    print("=" * 64)

    print(
        "🧠 V3.2.1.1 NOVELTY FEEDBACK"
    )

    print("=" * 64)

    print(
        "탈락 소재:",
        feedback.get(
            "rejected_topic",
            "",
        ),
    )

    print(
        "Novelty:",
        feedback.get(
            "novelty_score",
            0,
        ),
        "/",
        feedback.get(
            "required_score",
            0,
        ),
    )

    reason = feedback.get(
        "reason",
        "",
    )

    if reason:

        print(
            "Judge 이유:",
            reason,
        )

    issues = feedback.get(
        "issues",
        [],
    )

    if issues:

        print(
            "문제:"
        )

        for issue in issues:

            print(
                f" - {issue}"
            )

    print("=" * 64)


# ============================================================
# 품질 프로세스
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

        # ====================================================
        # PASS
        # ====================================================

        if decision == "PASS":

            return {
                "status":
                    "PASS",

                "script_data":
                    current_script,

                "consensus":
                    consensus,

                "pool_results":
                    pool_results,

                "rewrite_count":
                    rewrite_count,

                "review_count":
                    review_count,
            }

        # ====================================================
        # REWRITE
        # ====================================================

        if decision == "REWRITE":

            if (
                rewrite_count
                >= MAX_REWRITES
            ):

                # ============================================
                # Novelty 지속 실패
                # ============================================

                if (
                    has_persistent_novelty_failure(
                        consensus
                    )
                ):

                    return {
                        "status":
                            "REGENERATE_TOPIC",

                        "script_data":
                            current_script,

                        "consensus":
                            consensus,

                        "pool_results":
                            pool_results,

                        "rewrite_count":
                            rewrite_count,

                        "review_count":
                            review_count,

                        "reason": (
                            "Novelty가 선택 Rewrite 후에도 "
                            "최소 기준을 충족하지 못했습니다. "
                            "현재 소재를 폐기하고 "
                            "Novelty Judge 피드백을 사용해 "
                            "새 소재를 탐색합니다."
                        ),
                    }

                return {
                    "status":
                        "HOLD",

                    "script_data":
                        current_script,

                    "consensus":
                        consensus,

                    "pool_results":
                        pool_results,

                    "rewrite_count":
                        rewrite_count,

                    "review_count":
                        review_count,

                    "reason":
                        "Rewrite 최대 횟수 초과",
                }

            # ------------------------------------------------
            # 선택 Rewrite
            # ------------------------------------------------

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
                    "status":
                        "HOLD",

                    "script_data":
                        current_script,

                    "consensus":
                        consensus,

                    "pool_results":
                        pool_results,

                    "rewrite_count":
                        rewrite_count,

                    "review_count":
                        review_count,

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

            # ------------------------------------------------
            # Rewrite 후 Visual metadata 재생성
            # ------------------------------------------------

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
                    "status":
                        "HOLD",

                    "script_data":
                        current_script,

                    "consensus":
                        consensus,

                    "pool_results":
                        pool_results,

                    "rewrite_count":
                        rewrite_count,

                    "review_count":
                        review_count,

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

        # ====================================================
        # REVIEW
        # ====================================================

        if decision == "REVIEW":

            if (
                review_count
                >= MAX_REVIEW_ROUNDS
            ):

                return {
                    "status":
                        "HOLD",

                    "script_data":
                        current_script,

                    "consensus":
                        consensus,

                    "pool_results":
                        pool_results,

                    "rewrite_count":
                        rewrite_count,

                    "review_count":
                        review_count,

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

            route_type = (
                route.get(
                    "route"
                )
            )

            # ------------------------------------------------
            # 즉시 HOLD
            # ------------------------------------------------

            if route_type == "HOLD":

                return {
                    "status":
                        "HOLD",

                    "script_data":
                        current_script,

                    "consensus":
                        consensus,

                    "pool_results":
                        pool_results,

                    "rewrite_count":
                        rewrite_count,

                    "review_count":
                        review_count,

                    "reason":
                        route.get(
                            "reason",
                            "Review HOLD",
                        ),
                }

            # ------------------------------------------------
            # 추가 Judge
            # ------------------------------------------------

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

                # ============================================
                # Fact Appeal
                # ============================================

                if (
                    route_type
                    == "FACT_EXTRA_JUDGE"
                ):

                    appeal = (
                        evaluate_fact_appeal(
                            merged
                        )
                    )

                    print("")
                    print(
                        "⚖️ Fact Appeal:"
                    )

                    print(
                        appeal
                    )

                    appeal_status = (
                        appeal.get(
                            "status"
                        )
                    )

                    if appeal_status in (
                        "HOLD",
                        "DISAGREEMENT",
                        "INSUFFICIENT",
                    ):

                        return {
                            "status":
                                "HOLD",

                            "script_data":
                                current_script,

                            "consensus":
                                consensus,

                            "pool_results":
                                merged,

                            "rewrite_count":
                                rewrite_count,

                            "review_count":
                                review_count,

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
                "status":
                    "HOLD",

                "script_data":
                    current_script,

                "consensus":
                    consensus,

                "pool_results":
                    pool_results,

                "rewrite_count":
                    rewrite_count,

                "review_count":
                    review_count,

                "reason": (
                    "알 수 없는 Review route: "
                    f"{route_type}"
                ),
            }

        # ====================================================
        # 알 수 없는 Consensus
        # ====================================================

        return {
            "status":
                "HOLD",

            "script_data":
                current_script,

            "consensus":
                consensus,

            "pool_results":
                pool_results,

            "rewrite_count":
                rewrite_count,

            "review_count":
                review_count,

            "reason": (
                "알 수 없는 Consensus: "
                f"{decision}"
            ),
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

            print("")
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

            print(
                f"✅ SCENE {idx + 1} 완료"
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

    # 한 GitHub 실행 전체가 하나의 Budget 공유
    reset_budget()

    try:

        print("")
        print("=" * 64)

        print(
            "🚀 SHORTS GENERATOR "
            "V3.2.1.1 AUTONOMOUS"
        )

        print("=" * 64)

        validate_environment()

        final_script = None

        quality_result = None

        rejected_topics = []

        # ----------------------------------------------------
        # 다음 생성에 전달할 Novelty 피드백
        # ----------------------------------------------------

        generation_feedback = None

        total_topic_attempts = (
            MAX_TOPIC_REGENERATIONS
            + 1
        )

        # ====================================================
        # 소재 생성 + 품질 Gate
        # ====================================================

        for topic_attempt in range(
            1,
            total_topic_attempts + 1,
        ):

            print("")
            print("=" * 64)

            print(
                "🎯 TOPIC ATTEMPT "
                f"{topic_attempt}/"
                f"{total_topic_attempts}"
            )

            print("=" * 64)

            # ------------------------------------------------
            # 1. 방향 선택
            # ------------------------------------------------

            topic_info = (
                choose_topic_direction()
            )

            # ------------------------------------------------
            # 2. 소재 + 대본 생성
            #
            # V3.2.1.1:
            # 이전 Novelty 실패 이유 전달
            # ------------------------------------------------

            script_data = (
                generate_script(
                    topic_info,
                    generation_feedback=(
                        generation_feedback
                    ),
                    rejected_topics=(
                        rejected_topics
                    ),
                )
            )

            if not isinstance(
                script_data,
                dict,
            ):

                raise RuntimeError(
                    "대본 생성 결과가 dict가 아닙니다."
                )

            current_topic = str(
                script_data.get(
                    "topic",
                    "",
                )
            ).strip()

            print("")
            print(
                f"📝 제목: "
                f"{script_data.get('title', '')}"
            )

            print(
                f"🧠 소재: "
                f"{current_topic}"
            )

            # ------------------------------------------------
            # 정확히 같은 폐기 소재 재등장 방지
            # ------------------------------------------------

            if (
                current_topic
                in rejected_topics
            ):

                print(
                    "♻️ 이번 실행에서 이미 "
                    "폐기한 소재가 다시 생성됨."
                )

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    continue

                raise RuntimeError(
                    "폐기한 소재가 다시 생성되어 "
                    "새 후보 확보에 실패했습니다."
                )

            # ------------------------------------------------
            # 3. Visual Plan
            # ------------------------------------------------

            scenes = (
                enrich_visual_plan(
                    script_data.get(
                        "scenes",
                        [],
                    )
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

            # ------------------------------------------------
            # 4. 품질 프로세스
            # ------------------------------------------------

            quality_result = (
                run_quality_process(
                    script_data
                )
            )

            status = (
                quality_result.get(
                    "status"
                )
            )

            # =================================================
            # PASS
            # =================================================

            if status == "PASS":

                final_script = (
                    quality_result[
                        "script_data"
                    ]
                )

                break

            # =================================================
            # V3.2.1.1
            #
            # Novelty 실패:
            #
            # 1. 소재 폐기
            # 2. 실제 Novelty Judge 피드백 추출
            # 3. 다음 Generator에게 전달
            # =================================================

            if (
                status
                == "REGENERATE_TOPIC"
            ):

                rejected_topic = str(
                    quality_result
                    .get(
                        "script_data",
                        {}
                    )
                    .get(
                        "topic",
                        current_topic,
                    )
                ).strip()

                if (
                    rejected_topic
                    and rejected_topic
                    not in rejected_topics
                ):

                    rejected_topics.append(
                        rejected_topic
                    )

                # --------------------------------------------
                # 실제 Judge 피드백 추출
                # --------------------------------------------

                generation_feedback = (
                    extract_novelty_feedback(
                        quality_result
                    )
                )

                print_generation_feedback(
                    generation_feedback
                )

                print("")
                print("=" * 64)

                print(
                    "♻️ V3.2.1.1 "
                    "FEEDBACK TOPIC REGENERATION"
                )

                print("=" * 64)

                print(
                    "폐기 소재:",
                    rejected_topic,
                )

                print(
                    "이유:",
                    quality_result.get(
                        "reason",
                        "",
                    ),
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")
                    print(
                        "➡️ Novelty Judge의 실패 이유를 "
                        "반영해 새 소재를 탐색합니다."
                    )

                    continue

                raise RuntimeError(
                    "Novelty 기준을 만족하는 "
                    "소재를 확보하지 못했습니다."
                )

            # =================================================
            # 일반 HOLD
            # =================================================

            raise RuntimeError(
                "V3.2.1.1 Quality Gate HOLD: "
                f"{quality_result.get('reason', '')}"
            )

        # ====================================================
        # 최종 Script
        # ====================================================

        if not final_script:

            raise RuntimeError(
                "최종 PASS 대본이 없습니다."
            )

        script_data = (
            final_script
        )

        scenes = script_data.get(
            "scenes",
            [],
        )

        print("")
        print("=" * 64)

        print(
            "🏆 V3.2.1.1 QUALITY PASS"
        )

        print("=" * 64)

        print(
            f"📝 제목: "
            f"{script_data.get('title', '')}"
        )

        print(
            f"🧠 소재: "
            f"{script_data.get('topic', '')}"
        )

        # ====================================================
        # 5. 영상 제작
        # ====================================================

        scene_clips = (
            generate_scenes(
                scenes
            )
        )

        # ====================================================
        # 6. 길이 검사
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
                "⚠️ 목표 영상 길이 범위 이탈"
            )

        # ====================================================
        # 7. 렌더링
        # ====================================================

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ====================================================
        # 8. Telegram
        # ====================================================

        send_result_summary(
            script_data,
            total_duration,
        )

        send_telegram_video(
            final_path
        )

        # ====================================================
        # 비용
        # ====================================================

        print_budget_status()

        elapsed = (
            time.time()
            - start_time
        )

        print("")
        print("=" * 64)

        print(
            "🎉 V3.2.1.1 AUTONOMOUS "
            "SHORT COMPLETE"
        )

        print(
            f"⏱️ 전체 소요시간: "
            f"{elapsed / 60:.1f}분"
        )

        print("=" * 64)

    except Exception as e:

        print("")
        print("=" * 64)

        print(
            "💀 V3.2.1.1 ERROR"
        )

        print(
            str(e)
        )

        print("=" * 64)

        print_budget_status()

        try:

            send_telegram_message(
                "🚨 V3.2.1.1 Shorts 생성 실패\n\n"
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


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    main()

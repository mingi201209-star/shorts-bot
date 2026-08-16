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
# Shorts Generator V3.2.1.2
# ============================================================
#
# 핵심 변경:
#
# 기존:
#
#   Script
#     ↓
#   Hook + Novelty + Fact + Visual
#     ↓
#   Consensus
#
# 문제:
#
#   Novelty가 낮아서 어차피 폐기할 소재에도
#   Hook / Fact / Visual 비용이 발생했다.
#
#
# V3.2.1.2:
#
#   Script
#     ↓
#   Novelty Pre-Gate
#     ↓
#   FAIL ─────────→ 소재 즉시 폐기
#
#   PASS
#     ↓
#   Hook + Fact + Visual
#     ↓
#   Consensus
#
#
# 목적:
#
#   품질 기준을 낮추지 않고
#   실패 소재에 대한 API 비용을 줄인다.
#
# ============================================================


JUDGE_MODEL = os.environ.get(
    "V3_JUDGE_MODEL",
    "gpt-4o-mini",
)


# ============================================================
# Judge
# ============================================================

PRE_GATE_JUDGE = "novelty"


POST_GATE_JUDGES = [
    "hook",
    "fact",
    "visual",
]


ALL_JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
]


# ============================================================
# Novelty Pre-Gate
#
# Consensus의 최소 Novelty 기준과 맞춘다.
#
# 현재 시스템에서 실제 Novelty Judge가
# 이 기준을 넘지 못하면 나머지 Judge를 실행하지 않는다.
# ============================================================

NOVELTY_PRE_GATE_SCORE = 7.0


# 한 소재에 대한 최대 Rewrite
MAX_REWRITES = 1


# 한 소재에 대한 최대 Review
MAX_REVIEW_ROUNDS = 1


# 최초 소재 + 재생성 1회
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
# Novelty Pre-Gate
# ============================================================

def run_novelty_pre_gate(
    script_data,
):

    print("")
    print("=" * 60)
    print(
        "🚪 V3.2.1.2 NOVELTY PRE-GATE"
    )
    print("=" * 60)

    result = run_judge(
        PRE_GATE_JUDGE,
        script_data,
        model=JUDGE_MODEL,
    )

    print_judge_result(
        result
    )

    score = float(
        result.get(
            "score",
            0.0,
        )
    )

    confidence = float(
        result.get(
            "confidence",
            0.0,
        )
    )

    critical_risk = bool(
        result.get(
            "critical_risk",
            False,
        )
    )

    passed = (
        score
        >= NOVELTY_PRE_GATE_SCORE
    )

    print("")
    print(
        "Novelty score:",
        score,
    )

    print(
        "Novelty confidence:",
        confidence,
    )

    print(
        "Required:",
        NOVELTY_PRE_GATE_SCORE,
    )

    if critical_risk:

        print(
            "⚠️ Novelty critical risk detected"
        )

    if passed:

        print("")
        print(
            "✅ NOVELTY PRE-GATE PASS"
        )

    else:

        print("")
        print(
            "♻️ NOVELTY PRE-GATE FAIL"
        )

        print(
            "➡️ Hook / Fact / Visual "
            "Judge를 호출하지 않습니다."
        )

    print("=" * 60)

    return {
        "passed":
            passed,

        "result":
            result,

        "score":
            score,

        "confidence":
            confidence,

        "critical_risk":
            critical_risk,
    }


# ============================================================
# Novelty 통과 후 나머지 Judge 실행
# ============================================================

def run_post_gate_judges(
    script_data,
    novelty_result,
):

    # --------------------------------------------------------
    # 이미 실행한 Novelty 결과를 그대로 사용한다.
    #
    # Novelty를 다시 호출하지 않는다.
    # --------------------------------------------------------

    pool = {
        "novelty": [
            novelty_result
        ],
    }

    print("")
    print("=" * 60)
    print(
        "⚖️ V3.2.1.2 POST-GATE JUDGES"
    )
    print("=" * 60)

    for judge_type in (
        POST_GATE_JUDGES
    ):

        print("")
        print(
            f"🔍 {judge_type.upper()} JUDGE"
        )

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
# 수정된 영역만 재심
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

        if domain not in (
            ALL_JUDGE_TYPES
        ):

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
        # 해당 영역의 이전 판결은 교체한다.

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
        f"   score = "
        f"{novelty.get('score', 0)}"
    )

    print(
        f"   required = "
        f"{novelty.get('minimum', 0)}"
    )

    return True


# ============================================================
# 품질 프로세스
#
# 중요:
#
# 이 함수에 들어오는 시점에는
# Novelty Pre-Gate가 이미 PASS한 상태다.
# ============================================================

def run_quality_process(
    script_data,
    novelty_result,
):

    current_script = (
        script_data
    )

    rewrite_count = 0
    review_count = 0

    # --------------------------------------------------------
    # Novelty 결과 재사용 +
    # 나머지 Judge 3종
    # --------------------------------------------------------

    pool_results = (
        run_post_gate_judges(
            current_script,
            novelty_result,
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
                            "Novelty가 Rewrite 후에도 "
                            "최소 기준을 충족하지 "
                            "못했습니다."
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
            # Rewrite 후 Visual metadata 재구성
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

            # ------------------------------------------------
            # 수정된 영역만 다시 Judge
            # ------------------------------------------------

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

    # 실행 전체가 하나의 Budget을 공유한다.
    reset_budget()

    try:

        print("")
        print("=" * 64)

        print(
            "🚀 SHORTS GENERATOR "
            "V3.2.1.2 COST-GUARDED"
        )

        print("=" * 64)

        validate_environment()

        final_script = None
        quality_result = None

        rejected_topics = []

        total_topic_attempts = (
            MAX_TOPIC_REGENERATIONS
            + 1
        )

        # ====================================================
        # 소재 후보 루프
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
            # ------------------------------------------------

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
            # 이번 실행에서 이미 폐기한 소재
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

            # =================================================
            # 4. V3.2.1.2 NOVELTY PRE-GATE
            # =================================================

            novelty_gate = (
                run_novelty_pre_gate(
                    script_data
                )
            )

            novelty_result = (
                novelty_gate[
                    "result"
                ]
            )

            # ------------------------------------------------
            # Novelty FAIL
            #
            # 여기서 Hook / Fact / Visual을
            # 절대로 호출하지 않는다.
            # ------------------------------------------------

            if not novelty_gate[
                "passed"
            ]:

                if current_topic:

                    rejected_topics.append(
                        current_topic
                    )

                print("")
                print("=" * 64)

                print(
                    "♻️ TOPIC REJECTED EARLY"
                )

                print("=" * 64)

                print(
                    "폐기 소재:",
                    current_topic,
                )

                print(
                    "Novelty:",
                    novelty_gate[
                        "score"
                    ],
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")
                    print(
                        "➡️ 새 소재 후보 생성"
                    )

                    continue

                raise RuntimeError(
                    "Novelty Pre-Gate를 "
                    "통과하는 소재를 "
                    "확보하지 못했습니다."
                )

            # =================================================
            # 5. Novelty 통과
            #
            # 이제서야 나머지 Judge 실행.
            # =================================================

            quality_result = (
                run_quality_process(
                    script_data,
                    novelty_result,
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
            # Rewrite 후 Novelty가 다시 무너진 경우
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

                if rejected_topic:

                    rejected_topics.append(
                        rejected_topic
                    )

                print("")
                print("=" * 64)

                print(
                    "♻️ TOPIC REGENERATION"
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

                    print(
                        "➡️ 새 소재 탐색 시작"
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
                "V3.2.1.2 Quality Gate HOLD: "
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
            "🏆 V3.2.1.2 QUALITY PASS"
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
        # 실제 영상 제작
        # ====================================================

        scene_clips = (
            generate_scenes(
                scenes
            )
        )

        # ====================================================
        # 영상 길이
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
        # 렌더링
        # ====================================================

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ====================================================
        # Telegram
        # ====================================================

        send_result_summary(
            script_data,
            total_duration,
        )

        send_telegram_video(
            final_path
        )

        # ====================================================
        # 최종 Budget
        # ====================================================

        print_budget_status()

        elapsed = (
            time.time()
            - start_time
        )

        print("")
        print("=" * 64)

        print(
            "🎉 V3.2.1.2 "
            "AUTONOMOUS SHORT COMPLETE"
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
            "💀 V3.2.1.2 ERROR"
        )

        print(
            str(e)
        )

        print("=" * 64)

        print_budget_status()

        try:

            send_telegram_message(
                "🚨 V3.2.1.2 Shorts 생성 실패\n\n"
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

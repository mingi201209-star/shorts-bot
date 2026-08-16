# main.py

import os
import time

from config import (
    MAX_SCENES,
    get_missing_environment_variables,
)

from content.topic_selector import (
    choose_topic_direction,
    get_recent_topic_names,
)

from content.candidate_explorer import (
    explore_candidates,
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
# 핵심 구조:
#
# Topic Direction
#       ↓
# Candidate Explorer
#       ↓
# Winner + Runner-up
#       ↓
# Script Generator
#       ↓
# Visual Plan
#       ↓
# Judge Committee
#
#   Hook
#   Novelty
#   Fact
#   Visual
#
#       ↓
# Consensus
#       ↓
# PASS / REWRITE / REVIEW
#       ↓
# Video Production
#
#
# V3.2.1.2 1차 통합:
#
# - Novelty Pre-Gate 제거
# - Candidate Explorer 연결
# - Script Generator에 Winner 전달
# - 4 Judge를 동일 심사 단계로 통합
#
#
# 다음 단계:
#
# - Fact-critical Winner 실패 시
#   Runner-up 승격 / 재심 경로
#
# ============================================================


JUDGE_MODEL = os.environ.get(
    "V3_JUDGE_MODEL",
    "gpt-4o-mini",
)


# ============================================================
# Judge Committee
# ============================================================
#
# 4명의 전문 Judge가 동일 단계에서 독립 심사한다.
#
# Novelty만 먼저 통과시켜야 하는
# Pre-Gate 구조는 더 이상 사용하지 않는다.
#
# ============================================================

JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
]


ALL_JUDGE_TYPES = JUDGE_TYPES


# ============================================================
# 한 소재에 대한 최대 Rewrite
# ============================================================

MAX_REWRITES = 1


# ============================================================
# 한 소재에 대한 최대 Review
# ============================================================

MAX_REVIEW_ROUNDS = 1


# ============================================================
# Candidate Explorer 재탐색 횟수
#
# 최초 시도 + 재탐색 1회
# ============================================================

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
# Judge Committee
# ============================================================
#
# Hook / Novelty / Fact / Visual
#
# 각각 정확히 1회 실행한다.
#
# ============================================================

def run_initial_judges(
    script_data,
):

    pool = {}

    print("")
    print("=" * 60)

    print(
        "⚖️ V3.2.1.2 JUDGE COMMITTEE"
    )

    print("=" * 60)

    for judge_type in (
        JUDGE_TYPES
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

        # ----------------------------------------------------
        # Script가 수정되었으므로
        # 해당 영역의 이전 판결은
        # 새로운 판결로 교체한다.
        # ----------------------------------------------------

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
# Novelty 지속 실패 여부
# ============================================================
#
# Novelty Pre-Gate는 제거되었다.
#
# 하지만 Script Rewrite 후에도
# Novelty가 Consensus 최소 기준 아래라면
# 소재 자체가 약할 가능성이 있으므로
# Candidate Explorer 재탐색을 요청할 수 있다.
#
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
# ============================================================
#
# Candidate Explorer가 선택한 Winner로
# Script가 생성된 뒤
#
# 4 Judge가 동일 단계에서 심사한다.
#
# ============================================================

def run_quality_process(
    script_data,
):

    current_script = (
        script_data
    )

    rewrite_count = 0
    review_count = 0

    # --------------------------------------------------------
    # 최초 Judge Committee
    # --------------------------------------------------------

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

            # ------------------------------------------------
            # Rewrite 한도 도달
            # ------------------------------------------------

            if (
                rewrite_count
                >= MAX_REWRITES
            ):

                # ------------------------------------------------
                # Script 수정 이후에도
                # Novelty가 최소 기준 아래라면
                # 소재 자체 재탐색 요청.
                # ------------------------------------------------

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
                            "Candidate Explorer가 "
                            "새 후보를 탐색합니다."
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
            # 수정된 영역만 Judge 재실행
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

            # ------------------------------------------------
            # 알 수 없는 Review route
            # ------------------------------------------------

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

    # --------------------------------------------------------
    # 실행 전체 Budget 초기화
    #
    # Candidate Explorer 재탐색,
    # Script Retry,
    # Judge,
    # Rewrite,
    # Review 모두 하나의 Budget을 공유한다.
    # --------------------------------------------------------

    reset_budget()

    try:

        print("")
        print("=" * 64)

        print(
            "🚀 SHORTS GENERATOR "
            "V3.2.1.2 CANDIDATE-FIRST"
        )

        print("=" * 64)

        validate_environment()

        final_script = None
        quality_result = None

        rejected_topics = []

        # ----------------------------------------------------
        # Runner-up은 1차 통합에서는 보관만 한다.
        #
        # 다음 패치에서
        # Fact-critical fallback에 사용한다.
        # ----------------------------------------------------

        selected_runner_up = None

        total_topic_attempts = (
            MAX_TOPIC_REGENERATIONS
            + 1
        )

        # ====================================================
        # Candidate Explorer 루프
        # ====================================================

        for topic_attempt in range(
            1,
            total_topic_attempts + 1,
        ):

            print("")
            print("=" * 64)

            print(
                "🎯 CANDIDATE ATTEMPT "
                f"{topic_attempt}/"
                f"{total_topic_attempts}"
            )

            print("=" * 64)

            # =================================================
            # 1. 넓은 탐색 방향 선택
            # =================================================

            topic_info = (
                choose_topic_direction()
            )

            # =================================================
            # 2. 최근 실제 사용 소재
            # =================================================

            recent_topics = (
                get_recent_topic_names()
            )

            # =================================================
            # 3. Candidate Explorer
            # =================================================

            explorer_result = (
                explore_candidates(
                    topic_info,
                    recent_topics=recent_topics,
                    rejected_topics=rejected_topics,
                )
            )

            explorer_status = (
                explorer_result.get(
                    "status"
                )
            )

            # ------------------------------------------------
            # Explorer가 Winner를 만들지 못함
            # ------------------------------------------------

            if (
                explorer_status
                != "SELECTED"
            ):

                reason = (
                    explorer_result.get(
                        "reason",
                        (
                            "Candidate Explorer가 "
                            "후보를 선택하지 못했습니다."
                        ),
                    )
                )

                print("")
                print("=" * 64)

                print(
                    "♻️ CANDIDATE EXPLORER REGENERATE"
                )

                print("=" * 64)

                print(
                    "이유:",
                    reason,
                )

                print_budget_status()

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")
                    print(
                        "➡️ 다른 방향으로 재탐색"
                    )

                    continue

                raise RuntimeError(
                    "Candidate Explorer가 "
                    "제작 가능한 Winner를 "
                    "확보하지 못했습니다. "
                    f"마지막 이유: {reason}"
                )

            # =================================================
            # 4. Winner / Runner-up
            # =================================================

            winner = (
                explorer_result[
                    "winner"
                ]
            )

            runner_up = (
                explorer_result.get(
                    "runner_up"
                )
            )

            selected_runner_up = (
                runner_up
            )

            current_topic = str(
                winner.get(
                    "topic",
                    "",
                )
            ).strip()

            if not current_topic:

                raise RuntimeError(
                    "Candidate Explorer Winner에 "
                    "topic이 없습니다."
                )

            print("")
            print(
                "🏆 Winner:",
                current_topic,
            )

            print(
                "🎯 Core Question:",
                winner.get(
                    "core_question",
                    "",
                ),
            )

            if runner_up:

                print(
                    "🛟 Runner-up:",
                    runner_up.get(
                        "topic",
                        "",
                    ),
                )

            else:

                print(
                    "🛟 Runner-up: 없음"
                )

            # ------------------------------------------------
            # 이미 이번 실행에서 폐기한 Winner 방지
            # ------------------------------------------------

            if (
                current_topic
                in rejected_topics
            ):

                print(
                    "♻️ 이번 실행에서 이미 폐기한 "
                    "Winner가 다시 선택되었습니다."
                )

                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    continue

                raise RuntimeError(
                    "Candidate Explorer가 "
                    "폐기한 Winner를 다시 선택했습니다."
                )

            # =================================================
            # 5. Script Generator
            #
            # Candidate Explorer Winner를
            # 그대로 전달한다.
            # =================================================

            script_data = (
                generate_script(
                    topic_info,
                    winner,
                )
            )

            if not isinstance(
                script_data,
                dict,
            ):

                raise RuntimeError(
                    "대본 생성 결과가 dict가 아닙니다."
                )

            # ------------------------------------------------
            # Script Generator가 topic을 재선택하지
            # 않았는지 방어적으로 검사한다.
            # ------------------------------------------------

            generated_topic = str(
                script_data.get(
                    "topic",
                    "",
                )
            ).strip()

            if (
                generated_topic
                != current_topic
            ):

                raise RuntimeError(
                    "Script Generator의 topic이 "
                    "Candidate Explorer Winner와 "
                    "일치하지 않습니다."
                )

            print("")

            print(
                f"📝 제목: "
                f"{script_data.get('title', '')}"
            )

            print(
                f"🧠 소재: "
                f"{current_topic}"
            )

            # =================================================
            # 6. Visual Plan
            # =================================================

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
            # 7. Judge Committee + Consensus
            #
            # Hook / Novelty / Fact / Visual
            # 모두 동일 단계에서 실행.
            # =================================================

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
           

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
# Topic Direction
#       ↓
# Candidate Explorer
#       ↓
# Winner + Independent Runner-up
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
#
#
# Fact 경로:
#
# Fact 문제
#       ↓
# Fact Extra Judge
#       ↓
# Fact Appeal
#       ↓
# FACT_CRITICAL
#       ↓
# Independent Runner-up
#       ↓
# 새 Script
#       ↓
# 새 Visual Plan
#       ↓
# 4 Judge 전체 재심
#
#
# 중요:
#
# Runner-up은 일반적인 2등 후보가 아니다.
#
# Winner의 핵심 Fact가 최종적으로 무너졌을 때만
# 사용하는 독립 비상 백업이다.
#
# Hook / Novelty / Visual 문제 때문에
# Runner-up으로 갈아타지 않는다.
#
# ============================================================


JUDGE_MODEL = os.environ.get(
    "V3_JUDGE_MODEL",
    "gpt-4o-mini",
)


# ============================================================
# Judge Committee
# ============================================================

JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
]

ALL_JUDGE_TYPES = JUDGE_TYPES


# ============================================================
# Quality limits
# ============================================================

MAX_REWRITES = 1

MAX_REVIEW_ROUNDS = 1

# 최초 시도 + 재탐색 1회
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
# 최초 Judge Committee
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

    for judge_type in JUDGE_TYPES:

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
# 수정된 영역만 Judge 재심
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

        if domain not in ALL_JUDGE_TYPES:

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

        # Script가 바뀌었으므로
        # 해당 영역의 이전 판결을 새 판결로 교체한다.
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
# Novelty Pre-Gate는 없다.
#
# 다만 Script Rewrite 후에도
# Novelty가 Consensus 최소 기준을 통과하지 못하면
# 소재 자체가 약할 가능성이 있으므로
# Explorer 재탐색 대상으로 보낸다.
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
        "   score = "
        f"{novelty.get('score', 0)}"
    )

    print(
        "   required = "
        f"{novelty.get('minimum', 0)}"
    )

    return True


# ============================================================
# 품질 프로세스
# ============================================================
#
# Candidate Explorer가 선택한 후보로 만들어진 Script를
#
# Hook
# Novelty
# Fact
# Visual
#
# 4명의 Judge가 동일 단계에서 심사한다.
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

    # ========================================================
    # 최초 Judge Committee
    # ========================================================

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

                # --------------------------------------------
                # Novelty가 Rewrite 후에도 약하면
                # 소재 자체를 새로 탐색한다.
                # --------------------------------------------

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

            # ------------------------------------------------
            # 실제 수정된 영역만 재심
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
            # Review Router가 즉시 HOLD
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
            # Extra Judge
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
                # FACT EXTRA JUDGE → FACT APPEAL
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

                    # ========================================
                    # V3.2.1.2 핵심
                    #
                    # Fact Extra Judge와 Fact Appeal까지
                    # 거쳤는데도 사실성이 해결되지 않으면
                    # 일반 HOLD와 구별한다.
                    #
                    # 이 신호만 Runner-up fallback을
                    # 사용할 수 있다.
                    # ========================================

                    if appeal_status in (
                        "HOLD",
                        "DISAGREEMENT",
                        "INSUFFICIENT",
                    ):

                        return {
                            "status":
                                "HOLD",

                            "failure_type":
                                "FACT_CRITICAL",

                            "fact_appeal_status":
                                appeal_status,

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
# Runner-up Fact Fallback
# ============================================================
#
# Runner-up은 아래 조건에서만 사용한다.
#
# Winner
#   ↓
# Fact Extra Judge
#   ↓
# Fact Appeal
#   ↓
# FACT_CRITICAL
#
#
# Hook 실패 → 사용 금지
# Novelty 실패 → 사용 금지
# Visual 실패 → 사용 금지
# 일반 Rewrite 실패 → 사용 금지
#
#
# Runner-up을 사용하면
# 기존 Winner의 Script/Judge 결과는 재사용하지 않는다.
#
# Runner-up으로 완전히 새 Script를 만든 뒤
# Visual Plan과 4 Judge를 처음부터 다시 수행한다.
#
# ============================================================

def try_runner_up_fallback(
    topic_info,
    runner_up,
    failed_quality_result,
):

    failure_type = (
        failed_quality_result.get(
            "failure_type"
        )
    )

    # --------------------------------------------------------
    # Fact-critical이 아니면 fallback 금지
    # --------------------------------------------------------

    if (
        failure_type
        != "FACT_CRITICAL"
    ):

        return None

    # --------------------------------------------------------
    # Runner-up 없음
    # --------------------------------------------------------

    if not runner_up:

        print("")

        print(
            "⚠️ FACT_CRITICAL이지만 "
            "사용 가능한 Runner-up이 없습니다."
        )

        return None

    runner_topic = str(
        runner_up.get(
            "topic",
            "",
        )
    ).strip()

    if not runner_topic:

        print("")

        print(
            "⚠️ Runner-up topic이 비어 있습니다."
        )

        return None

    print("")
    print("=" * 64)

    print(
        "🛟 V3.2.1.2 RUNNER-UP FACT FALLBACK"
    )

    print("=" * 64)

    failed_script = (
        failed_quality_result.get(
            "script_data",
            {},
        )
    )

    failed_topic = str(
        failed_script.get(
            "topic",
            "",
        )
    ).strip()

    print(
        "💀 실패 Winner:",
        failed_topic,
    )

    print(
        "⚠️ 실패 이유:",
        failed_quality_result.get(
            "reason",
            "",
        ),
    )

    print(
        "🛟 승격 Runner-up:",
        runner_topic,
    )

    backup_independence = str(
        runner_up.get(
            "backup_independence",
            "",
        )
    ).strip()

    if backup_independence:

        print(
            "🔗 Backup Independence:",
            backup_independence,
        )

    print_budget_status()

    # ========================================================
    # 1. Runner-up으로 완전히 새 Script 생성
    # ========================================================

    runner_script = (
        generate_script(
            topic_info,
            runner_up,
        )
    )

    if not isinstance(
        runner_script,
        dict,
    ):

        raise RuntimeError(
            "Runner-up 대본 생성 결과가 "
            "dict가 아닙니다."
        )

    # --------------------------------------------------------
    # Runner-up Candidate Lock 확인
    # --------------------------------------------------------

    generated_topic = str(
        runner_script.get(
            "topic",
            "",
        )
    ).strip()

    if (
        generated_topic
        != runner_topic
    ):

        raise RuntimeError(
            "Runner-up Script Generator의 topic이 "
            "Candidate Explorer Runner-up과 "
            "일치하지 않습니다."
        )

    print("")

    print(
        "📝 Runner-up 제목:",
        runner_script.get(
            "title",
            "",
        ),
    )

    # ========================================================
    # 2. Runner-up Visual Plan
    # ========================================================

    scenes = (
        enrich_visual_plan(
            runner_script.get(
                "scenes",
                [],
            )
        )
    )

    runner_script[
        "scenes"
    ] = scenes

    visual_ok, visual_reason = (
        validate_visual_plan(
            scenes
        )
    )

    if not visual_ok:

        print("")

        print(
            "🚫 Runner-up Visual Plan 실패:",
            visual_reason,
        )

        return {
            "status":
                "HOLD",

            "failure_type":
                "RUNNER_UP_FAILED",

            "script_data":
                runner_script,

            "reason": (
                "Runner-up Visual Plan 검증 실패: "
                f"{visual_reason}"
            ),
        }

    # ========================================================
    # 3. Runner-up 4 Judge 전체 재심
    # ========================================================

    print("")
    print("=" * 64)

    print(
        "⚖️ RUNNER-UP JUDGE COMMITTEE RESTART"
    )

    print("=" * 64)

    runner_quality = (
        run_quality_process(
            runner_script
        )
    )

    # ========================================================
    # 임시 lineage 정보
    #
    # 정식 V4 Lineage 도입 전까지
    # fallback의 출처를 최소한으로 기록한다.
    # ========================================================

    runner_quality[
        "fallback_used"
    ] = True

    runner_quality[
        "fallback_from_topic"
    ] = failed_topic

    runner_quality[
        "fallback_to_topic"
    ] = runner_topic

    # --------------------------------------------------------
    # 중요:
    #
    # Runner-up도 FACT_CRITICAL이라고 해서
    # 다시 다른 fallback을 호출하지 않는다.
    #
    # fallback은 한 번뿐이다.
    # --------------------------------------------------------

    return runner_quality


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
    # 실행 전체가 하나의 Budget을 공유한다.
    #
    # Explorer
    # Script Generator
    # Judges
    # Rewrite
    # Review
    # Runner-up fallback
    #
    # 모두 같은 Budget Guard 아래에서 실행된다.
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

        total_topic_attempts = (
            MAX_TOPIC_REGENERATIONS
            + 1
        )

        # ====================================================
        # Candidate Explorer Loop
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
            # 1. 넓은 탐색 방향
            # =================================================

            topic_info = (
                choose_topic_direction()
            )

            # =================================================
            # 2. 최근 실제 콘텐츠
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
            # Explorer가 Winner를 선택하지 못함
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
            # 4. Winner + Independent Runner-up
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
            # 이미 이번 실행에서 죽은 소재인지 확인
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
            # 5. Winner Script Generator
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
            # Candidate Lock 확인
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
                "📝 제목:",
                script_data.get(
                    "title",
                    "",
                ),
            )

            print(
                "🧠 소재:",
                current_topic,
            )

            # =================================================
            # 6. Winner Visual Plan
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
            # 7. Winner Judge Committee
            # =================================================

            quality_result = (
                run_quality_process(
                    script_data
                )
            )

            # =================================================
            # 8. FACT_CRITICAL → Runner-up Fallback
            # =================================================

            if (
                quality_result.get(
                    "failure_type"
                )
                == "FACT_CRITICAL"
            ):

                # --------------------------------------------
                # Fact로 죽은 Winner는
                # 이후 Explorer가 다시 고르지 못하게 한다.
                # --------------------------------------------

                if (
                    current_topic
                    not in rejected_topics
                ):

                    rejected_topics.append(
                        current_topic
                    )

                fallback_result = (
                    try_runner_up_fallback(
                        topic_info,
                        runner_up,
                        quality_result,
                    )
                )

                if (
                    fallback_result
                    is not None
                ):

                    quality_result = (
                        fallback_result
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

                if quality_result.get(
                    "fallback_used",
                    False,
                ):

                    print("")
                    print("=" * 64)

                    print(
                        "🛟 RUNNER-UP FALLBACK PASS"
                    )

                    print(
                        "From:",
                        quality_result.get(
                            "fallback_from_topic",
                            "",
                        ),
                    )

                    print(
                        "To:",
                        quality_result.get(
                            "fallback_to_topic",
                            "",
                        ),
                    )

                    print("=" * 64)

                break

            # =================================================
            # Novelty persistent failure
            #
            # Winner 또는 Runner-up이
            # Novelty 문제로 살아남지 못한 경우
            # 새 Explorer 실행.
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

                    if (
                        rejected_topic
                        not in rejected_topics
                    ):

                        rejected_topics.append(
                            rejected_topic
                        )

                print("")
                print("=" * 64)

                print(
                    "♻️ CANDIDATE REGENERATION"
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
                        "➡️ Candidate Explorer 재탐색"
                    )

                    continue

                raise RuntimeError(
                    "Judge Committee 통과가 가능한 "
                    "Winner를 확보하지 못했습니다."
                )

            # =================================================
            # Runner-up도 실패
            # =================================================

            if (
                quality_result.get(
                    "fallback_used",
                    False,
                )
            ):

                fallback_topic = str(
                    quality_result.get(
                        "fallback_to_topic",
                        "",
                    )
                ).strip()

                if (
                    fallback_topic
                    and fallback_topic
                    not in rejected_topics
                ):

                    rejected_topics.append(
                        fallback_topic
                    )

                print("")
                print("=" * 64)

                print(
                    "🚫 RUNNER-UP FALLBACK FAILED"
                )

                print("=" * 64)

                print(
                    "Runner-up:",
                    fallback_topic,
                )

                print(
                    "Reason:",
                    quality_result.get(
                        "reason",
                        "",
                    ),
                )

            # =================================================
            # 일반 HOLD
            # =================================================

            raise RuntimeError(
                "V3.2.1.2 Quality Gate HOLD: "
                f"{quality_result.get('reason', '')}"
            )

        # ====================================================
        # 최종 PASS Script
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
            "📝 제목:",
            script_data.get(
                "title",
                "",
            ),
        )

        print(
            "🧠 소재:",
            script_data.get(
                "topic",
                "",
            ),
        )

        # ====================================================
        # 9. 실제 영상 제작
        # ====================================================

        scene_clips = (
            generate_scenes(
                scenes
            )
        )

        # ====================================================
        # 10. 영상 길이 검사
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
        # 11. 렌더링
        # ====================================================

        final_path = (
            render_final_video(
                scene_clips
            )
        )

        # ====================================================
        # 12. Telegram
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
            "⏱️ 전체 소요시간: "
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

# quality/integration_test.py

import os
import json

from quality.judge import (
    run_judge,
    print_judge_result,
)

from quality.consensus import (
    build_consensus,
    print_consensus,
)


# ============================================================
# V3 AI Judge Integration Test
# ============================================================
#
# 목적:
#   실제 OpenAI API를 사용해서
#
#   Judge
#     ↓
#   실제 JSON 응답
#     ↓
#   Consensus
#
#   연결이 정상 동작하는지 확인한다.
#
# 비용 최소화를 위해:
#   Hook     1회
#   Novelty  1회
#   Fact     1회
#   Visual   1회
#
# 총 4회 Judge 호출만 한다.
#
# 아직 테스트하지 않는 것:
#   - 자동 EXTRA_JUDGE
#   - Rewrite
#   - Quality Gate 전체 루프
#
# ============================================================


MODEL = os.environ.get(
    "V3_JUDGE_MODEL",
    "gpt-4o-mini",
)


JUDGE_TYPES = [
    "hook",
    "novelty",
    "fact",
    "visual",
]


# ============================================================
# 테스트 대본
# ============================================================

TEST_SCRIPT = {
    "title": (
        "기차 레일은 왜 일부러 "
        "한쪽을 더 높게 만들까?"
    ),

    "topic": (
        "기차가 곡선을 돌 때 "
        "바깥쪽 레일을 높이는 이유"
    ),

    "category": "교통",

    "scenes": [
        {
            "text":
                "이 철길, 자세히 보면 "
                "양쪽 높이가 다릅니다.",

            "visual_goal":
                "railway curve with raised outer rail",

            "visual_type":
                "railway_closeup",

            "keyword":
                "curved railway tracks",
        },

        {
            "text":
                "시공이 잘못된 게 아니라 "
                "일부러 이렇게 만든 겁니다.",

            "visual_goal":
                "train moving through railway curve",

            "visual_type":
                "moving_train",

            "keyword":
                "train railway curve",
        },

        {
            "text":
                "기차가 빠르게 곡선을 돌면 "
                "바깥쪽으로 밀리는 느낌이 생깁니다.",

            "visual_goal":
                "fast train entering curve",

            "visual_type":
                "motion",

            "keyword":
                "fast train curve",
        },

        {
            "text":
                "레일이 완전히 평평하다면 "
                "승객도 더 크게 흔들릴 수 있습니다.",

            "visual_goal":
                "passenger train on curved track",

            "visual_type":
                "passenger_train",

            "keyword":
                "passenger train curve",
        },

        {
            "text":
                "그래서 바깥쪽 레일을 "
                "안쪽보다 조금 높입니다.",

            "visual_goal":
                "rail elevation on curved railway",

            "visual_type":
                "rail_closeup",

            "keyword":
                "elevated railway rail",
        },

        {
            "text":
                "그러면 기차 자체가 "
                "곡선 안쪽으로 살짝 기울게 됩니다.",

            "visual_goal":
                "train leaning into curve",

            "visual_type":
                "moving_train",

            "keyword":
                "tilting train curve",
        },

        {
            "text":
                "이 기울기가 곡선에서 생기는 힘을 "
                "일부 상쇄해 줍니다.",

            "visual_goal":
                "train banking on railway curve",

            "visual_type":
                "engineering_motion",

            "keyword":
                "banked railway curve",
        },

        {
            "text":
                "자동차가 경사진 트랙을 "
                "도는 것과 비슷한 원리입니다.",

            "visual_goal":
                "car driving banked track",

            "visual_type":
                "comparison",

            "keyword":
                "car banked track",
        },

        {
            "text":
                "하지만 무조건 높게 만들면 "
                "좋은 것도 아닙니다.",

            "visual_goal":
                "railway engineering inspection",

            "visual_type":
                "inspection",

            "keyword":
                "railway track inspection",
        },

        {
            "text":
                "기차 속도와 곡선 반지름에 맞춰 "
                "적절한 높이를 정해야 합니다.",

            "visual_goal":
                "engineers inspecting curved railway",

            "visual_type":
                "engineering",

            "keyword":
                "railway engineers tracks",
        },

        {
            "text":
                "너무 느린 기차라면 오히려 "
                "반대쪽으로 기울어진 느낌이 날 수도 있습니다.",

            "visual_goal":
                "slow train on curved tracks",

            "visual_type":
                "moving_train",

            "keyword":
                "slow train curve",
        },

        {
            "text":
                "그래서 철도 곡선은 단순히 "
                "휘어진 레일이 아닙니다.",

            "visual_goal":
                "aerial curved railway",

            "visual_type":
                "aerial",

            "keyword":
                "curved railway aerial",
        },

        {
            "text":
                "우리가 편하게 지나가는 곡선에도 "
                "속도와 힘을 계산한 설계가 숨어 있습니다.",

            "visual_goal":
                "train smoothly passing curve",

            "visual_type":
                "ending",

            "keyword":
                "train passing curve",
        },
    ],
}


# ============================================================
# 결과 기본 검증
# ============================================================

def validate_judge_result(
    judge_type,
    result,
):

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            f"{judge_type} Judge 결과가 dict가 아닙니다."
        )

    required_fields = [
        "judge_type",
        "score",
        "confidence",
        "reason",
        "issues",
        "critical_risk",
    ]

    for field in required_fields:

        if field not in result:

            raise RuntimeError(
                f"{judge_type} Judge 필드 누락: "
                f"{field}"
            )

    score = float(
        result["score"]
    )

    confidence = float(
        result["confidence"]
    )

    if not (
        0.0 <= score <= 10.0
    ):

        raise RuntimeError(
            f"{judge_type} score 범위 오류: "
            f"{score}"
        )

    if not (
        0.0 <= confidence <= 1.0
    ):

        raise RuntimeError(
            f"{judge_type} confidence 범위 오류: "
            f"{confidence}"
        )

    if not isinstance(
        result["issues"],
        list,
    ):

        raise RuntimeError(
            f"{judge_type} issues가 list가 아닙니다."
        )

    return True


# ============================================================
# Integration Test
# ============================================================

def run_integration_test():

    print("")
    print("=" * 64)
    print(
        "🤖 SHORTS V3 AI JUDGE INTEGRATION TEST"
    )
    print("=" * 64)

    print(
        f"Model: {MODEL}"
    )

    if not os.environ.get(
        "OPENAI_KEY"
    ):

        raise RuntimeError(
            "OPENAI_KEY 환경변수가 없습니다."
        )

    pool_results = {}

    # ========================================================
    # Judge 4종 각각 정확히 1회
    # ========================================================

    for judge_type in JUDGE_TYPES:

        print("")
        print(
            f"▶ REAL JUDGE: "
            f"{judge_type.upper()}"
        )

        result = run_judge(
            judge_type,
            TEST_SCRIPT,
            model=MODEL,
        )

        validate_judge_result(
            judge_type,
            result,
        )

        print_judge_result(
            result
        )

        pool_results[
            judge_type
        ] = [
            result
        ]

    # ========================================================
    # Consensus
    # ========================================================

    consensus = build_consensus(
        pool_results
    )

    print_consensus(
        consensus
    )

    decision = consensus.get(
        "decision"
    )

    if decision not in (
        "PASS",
        "REWRITE",
        "REVIEW",
    ):

        raise RuntimeError(
            "알 수 없는 Consensus 결정: "
            f"{decision}"
        )

    # ========================================================
    # 결과 요약
    # ========================================================

    print("")
    print("=" * 64)
    print(
        "📊 REAL AI INTEGRATION TEST RESULT"
    )
    print("=" * 64)

    print(
        f"Decision: {decision}"
    )

    print(
        "Weighted score:",
        consensus.get(
            "weighted_score",
            0.0,
        )
    )

    print("")
    print(
        "Judge calls: 4"
    )

    print("")
    print(
        "✅ REAL AI JUDGE INTEGRATION TEST PASSED"
    )

    print("=" * 64)

    return {
        "pool_results":
            pool_results,

        "consensus":
            consensus,
    }


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    run_integration_test()

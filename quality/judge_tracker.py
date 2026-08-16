# quality/judge_tracker.py

import os
import json
from datetime import datetime, timezone
from collections import defaultdict


# ============================================================
# Judge Tracker V3
# ============================================================
#
# 목적:
#   Judge도 평가 대상이다.
#
# 기록:
#   - Judge별 점수
#   - confidence
#   - 다른 Judge와의 불일치
#   - critical risk 발생
#   - Consensus 결과
#   - 나중에 들어오는 실제 outcome
#
# 중요:
#   outcome이 없는데 Judge를 "오판"이라고 단정하지 않는다.
#
# ============================================================


JUDGE_HISTORY_FILE = "data/judge_history.json"

MAX_HISTORY = 5000

DEFAULT_RELIABILITY = 1.0

MIN_RELIABILITY = 0.50
MAX_RELIABILITY = 1.25


# ============================================================
# 파일 유틸
# ============================================================

def _ensure_data_dir():

    directory = os.path.dirname(
        JUDGE_HISTORY_FILE
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )


def _now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def load_judge_history():

    _ensure_data_dir()

    if not os.path.exists(
        JUDGE_HISTORY_FILE
    ):
        return []

    try:

        with open(
            JUDGE_HISTORY_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:

        print(
            f"⚠️ Judge history 읽기 실패: {e}"
        )

    return []


def save_judge_history(history):

    _ensure_data_dir()

    history = history[
        -MAX_HISTORY:
    ]

    temp_path = (
        JUDGE_HISTORY_FILE
        + ".tmp"
    )

    try:

        with open(
            temp_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temp_path,
            JUDGE_HISTORY_FILE,
        )

    except Exception as e:

        print(
            f"⚠️ Judge history 저장 실패: {e}"
        )


# ============================================================
# Judge Pool 결과 기록
# ============================================================

def record_judge_pool(
    *,
    run_id,
    engine_version,
    pool_results,
    consensus,
):

    history = load_judge_history()

    domain_summaries = consensus.get(
        "domain_summaries",
        {},
    )

    for judge_type, results in (
        pool_results.items()
    ):

        summary = domain_summaries.get(
            judge_type,
            {},
        )

        for review_index, result in enumerate(
            results,
            start=1,
        ):

            event = {
                "timestamp": _now(),
                "run_id": str(run_id),
                "engine_version": str(
                    engine_version
                ),

                "judge_type": judge_type,
                "review_index": review_index,

                "score": result.get(
                    "score",
                    0.0,
                ),

                "confidence": result.get(
                    "confidence",
                    0.0,
                ),

                "critical_risk": result.get(
                    "critical_risk",
                    False,
                ),

                "issues": result.get(
                    "issues",
                    [],
                ),

                "domain_average": summary.get(
                    "score",
                    0.0,
                ),

                "domain_disagreement": summary.get(
                    "disagreement",
                    0.0,
                ),

                "consensus_decision":
                    consensus.get(
                        "decision",
                        "UNKNOWN",
                    ),

                # 실제 결과는 나중에 입력
                "outcome": None,

                # 아직 정답을 모르므로
                # 오판 여부도 미정
                "error": None,
            }

            history.append(
                event
            )

    save_judge_history(
        history
    )


# ============================================================
# 실제 Outcome 연결
# ============================================================

def attach_outcome(
    run_id,
    outcome,
):

    """
    outcome 예:

    {
        "final_review": "PASS",
        "published": True,

        "metrics": {
            "view_3s_rate": 0.81,
            "completion_rate": 0.64
        },

        "domain_results": {
            "hook": 8.4,
            "novelty": 7.9,
            "fact": 9.0,
            "visual": 6.8
        }
    }
    """

    history = load_judge_history()

    changed = False

    for item in history:

        if (
            item.get("run_id")
            == str(run_id)
        ):

            item["outcome"] = outcome
            changed = True

    if changed:

        save_judge_history(
            history
        )

    return changed


# ============================================================
# Judge 결과와 Outcome 차이 계산
# ============================================================

def calculate_judge_error(
    judge_event,
):

    outcome = judge_event.get(
        "outcome"
    )

    if not isinstance(
        outcome,
        dict,
    ):
        return None

    domain_results = outcome.get(
        "domain_results",
        {},
    )

    judge_type = judge_event.get(
        "judge_type"
    )

    if judge_type not in domain_results:
        return None

    try:

        predicted = float(
            judge_event.get(
                "score",
                0.0,
            )
        )

        actual = float(
            domain_results[
                judge_type
            ]
        )

    except Exception:
        return None

    return abs(
        predicted
        - actual
    )


# ============================================================
# Judge별 성능 계산
# ============================================================

def calculate_judge_statistics():

    history = load_judge_history()

    stats = defaultdict(
        lambda: {
            "evaluated": 0,
            "total_error": 0.0,
            "high_confidence_errors": 0,
            "critical_calls": 0,
        }
    )

    for item in history:

        judge_type = item.get(
            "judge_type",
            "unknown",
        )

        error = calculate_judge_error(
            item
        )

        if error is None:
            continue

        stats[
            judge_type
        ]["evaluated"] += 1

        stats[
            judge_type
        ]["total_error"] += error

        confidence = float(
            item.get(
                "confidence",
                0.0,
            )
        )

        if (
            confidence >= 0.85
            and error >= 2.5
        ):

            stats[
                judge_type
            ][
                "high_confidence_errors"
            ] += 1

        if item.get(
            "critical_risk",
            False,
        ):

            stats[
                judge_type
            ]["critical_calls"] += 1

    result = {}

    for judge_type, data in (
        stats.items()
    ):

        evaluated = data[
            "evaluated"
        ]

        average_error = (
            data["total_error"]
            / evaluated
            if evaluated
            else 0.0
        )

        result[
            judge_type
        ] = {
            "evaluated": evaluated,
            "average_error": round(
                average_error,
                3,
            ),
            "high_confidence_errors":
                data[
                    "high_confidence_errors"
                ],
            "critical_calls":
                data[
                    "critical_calls"
                ],
        }

    return result


# ============================================================
# Reliability 계산
# ============================================================

def calculate_reliability(
    judge_type,
):

    stats = (
        calculate_judge_statistics()
        .get(
            judge_type
        )
    )

    # 아직 데이터가 없으면
    # 중립 신뢰도
    if not stats:

        return DEFAULT_RELIABILITY

    evaluated = stats.get(
        "evaluated",
        0,
    )

    # 표본이 너무 적으면
    # 신뢰도를 크게 움직이지 않는다.
    if evaluated < 10:

        return DEFAULT_RELIABILITY

    average_error = stats.get(
        "average_error",
        0.0,
    )

    high_confidence_errors = (
        stats.get(
            "high_confidence_errors",
            0,
        )
    )

    # 기본 1.0에서 시작
    reliability = 1.0

    # 평균 오차
    if average_error <= 0.75:
        reliability += 0.10

    elif average_error <= 1.25:
        reliability += 0.03

    elif average_error >= 2.5:
        reliability -= 0.25

    elif average_error >= 1.75:
        reliability -= 0.12

    # 확신하면서 크게 틀린 경우는
    # 더 위험하므로 추가 감점
    high_confidence_rate = (
        high_confidence_errors
        / evaluated
    )

    if high_confidence_rate >= 0.20:
        reliability -= 0.20

    elif high_confidence_rate >= 0.10:
        reliability -= 0.10

    reliability = max(
        MIN_RELIABILITY,
        min(
            reliability,
            MAX_RELIABILITY,
        ),
    )

    return round(
        reliability,
        3,
    )


# ============================================================
# 전체 Judge Reliability
# ============================================================

def build_reliability_report():

    statistics = (
        calculate_judge_statistics()
    )

    result = {}

    judge_types = {
        "hook",
        "novelty",
        "fact",
        "visual",
    }

    for judge_type in judge_types:

        result[
            judge_type
        ] = {
            "reliability":
                calculate_reliability(
                    judge_type
                ),
            "statistics":
                statistics.get(
                    judge_type,
                    {
                        "evaluated": 0,
                        "average_error": 0.0,
                        "high_confidence_errors": 0,
                        "critical_calls": 0,
                    },
                ),
        }

    return result


# ============================================================
# 이상 Judge 탐지
# ============================================================

def find_suspicious_judges():

    report = (
        build_reliability_report()
    )

    suspicious = []

    for judge_type, data in (
        report.items()
    ):

        reliability = data.get(
            "reliability",
            DEFAULT_RELIABILITY,
        )

        stats = data.get(
            "statistics",
            {},
        )

        if (
            stats.get(
                "evaluated",
                0,
            ) >= 10
            and reliability < 0.80
        ):

            suspicious.append({
                "judge_type": judge_type,
                "reliability": reliability,
                "statistics": stats,
            })

    return suspicious


# ============================================================
# 콘솔 출력
# ============================================================

def print_judge_reliability():

    report = (
        build_reliability_report()
    )

    print("")
    print("=" * 60)
    print("🧪 V3 JUDGE RELIABILITY")
    print("=" * 60)

    for judge_type, data in (
        report.items()
    ):

        stats = data[
            "statistics"
        ]

        print(
            f"{judge_type.upper():10} "
            f"| reliability "
            f"{data['reliability']:.3f} "
            f"| samples "
            f"{stats['evaluated']} "
            f"| avg error "
            f"{stats['average_error']:.3f}"
        )

    suspicious = (
        find_suspicious_judges()
    )

    if suspicious:

        print("")
        print(
            "🚨 JUDGE SUSPECT"
        )

        for item in suspicious:

            print(
                f" - {item['judge_type']} "
                f"| reliability "
                f"{item['reliability']:.3f}"
            )

    print("=" * 60)

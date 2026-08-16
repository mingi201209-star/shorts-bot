# quality/failure_monitor.py

import os
import json
import hashlib
from datetime import datetime, timezone
from collections import Counter

from quality.run_tracker import (
    load_run_history,
)


# ============================================================
# V3.1 Failure Monitor
# ============================================================
#
# 목적:
#   반복되는 실패가
#   - 콘텐츠 문제인지
#   - 시스템 문제인지
#   - Validator 문제인지
#   - Judge 문제인지
#   탐지한다.
#
# V3.1 변경:
#   실패율의 분모를 failure_history가 아니라
#   run_tracker의 실제 완료 RUN(SUCCESS + FAILED)로 계산한다.
#
# 절대 하지 않는 것:
#   - 코드 자동 수정
#   - Validator 기준 자동 변경
#   - Judge 결과 자동 채택
#
# ============================================================


FAILURE_HISTORY_FILE = "data/failure_history.json"

MAX_HISTORY = 2000

RECENT_WINDOW = 20

WARNING_COUNT = 3
CRITICAL_COUNT = 5

WARNING_RATE = 0.30
CRITICAL_RATE = 0.60

WARNING_STREAK = 3
CRITICAL_STREAK = 5


# ============================================================
# 실패 종류
# ============================================================

CONTENT_FAILURE = "CONTENT_FAILURE"
SYSTEM_FAILURE = "SYSTEM_FAILURE"
VALIDATOR_SUSPECT = "VALIDATOR_SUSPECT"
JUDGE_SUSPECT = "JUDGE_SUSPECT"
UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


# ============================================================
# 기본 유틸
# ============================================================

def ensure_data_directory():

    directory = os.path.dirname(
        FAILURE_HISTORY_FILE
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )


def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def normalize_string(value):

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


# ============================================================
# Fingerprint
# ============================================================

def create_fingerprint(
    stage,
    module,
    error_type,
    rule_id=None,
    judge_id=None,
):

    raw = "|".join([
        normalize_string(stage),
        normalize_string(module),
        normalize_string(error_type),
        normalize_string(rule_id),
        normalize_string(judge_id),
    ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]


# ============================================================
# Failure History
# ============================================================

def load_failure_history():

    ensure_data_directory()

    if not os.path.exists(
        FAILURE_HISTORY_FILE
    ):
        return []

    try:

        with open(
            FAILURE_HISTORY_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:

        print(
            f"⚠️ Failure history 읽기 실패: {e}"
        )

    return []


def save_failure_history(history):

    ensure_data_directory()

    history = history[
        -MAX_HISTORY:
    ]

    temp_path = (
        FAILURE_HISTORY_FILE
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
            FAILURE_HISTORY_FILE,
        )

    except Exception as e:

        print(
            f"⚠️ Failure history 저장 실패: {e}"
        )

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


# ============================================================
# 실패 분류
# ============================================================

def classify_failure(
    stage,
    module,
    error_type,
):

    stage_n = normalize_string(
        stage
    )

    module_n = normalize_string(
        module
    )

    error_n = normalize_string(
        error_type
    )

    combined = " ".join([
        stage_n,
        module_n,
        error_n,
    ])

    # --------------------------------------------------------
    # Validator 자체 의심
    # --------------------------------------------------------

    if (
        "validator" in module_n
        or "validator" in stage_n
    ):

        return VALIDATOR_SUSPECT

    # --------------------------------------------------------
    # Judge 자체 의심
    # --------------------------------------------------------

    if (
        "judge" in module_n
        or "judge" in stage_n
    ):

        return JUDGE_SUSPECT

    # --------------------------------------------------------
    # 시스템 실패
    # --------------------------------------------------------

    system_terms = [
        "ffmpeg",
        "font",
        "pexels",
        "download",
        "render",
        "renderer",
        "subtitle",
        "tts",
        "telegram",
        "network",
        "timeout",
        "file",
        "video_engine",
        "video_downloader",
        "audio",
        "moviepy",
        "http",
        "api",
    ]

    if any(
        term in combined
        for term in system_terms
    ):

        return SYSTEM_FAILURE

    # --------------------------------------------------------
    # 콘텐츠 실패
    # --------------------------------------------------------

    content_terms = [
        "hook",
        "novelty",
        "topic",
        "script",
        "scene",
        "keyword",
        "broll",
        "b-roll",
        "visual_match",
        "retention",
        "opening",
        "traffic",
        "story",
    ]

    if any(
        term in combined
        for term in content_terms
    ):

        return CONTENT_FAILURE

    return UNKNOWN_FAILURE


# ============================================================
# 실패 기록
# ============================================================

def record_failure(
    *,
    run_id,
    engine_version,
    stage,
    module,
    error_type,
    message="",
    rule_id=None,
    judge_id=None,
    failure_class=None,
    metadata=None,
):

    if not failure_class:

        failure_class = classify_failure(
            stage,
            module,
            error_type,
        )

    fingerprint = create_fingerprint(
        stage,
        module,
        error_type,
        rule_id,
        judge_id,
    )

    event = {
        "timestamp": utc_now(),
        "run_id": str(run_id),
        "engine_version": str(
            engine_version
        ),
        "stage": str(stage),
        "module": str(module),
        "error_type": str(
            error_type
        ),
        "failure_class": failure_class,
        "fingerprint": fingerprint,
        "message": str(message)[:1000],
        "rule_id": rule_id,
        "judge_id": judge_id,
        "metadata": (
            metadata
            if isinstance(metadata, dict)
            else {}
        ),
    }

    history = load_failure_history()

    history.append(
        event
    )

    save_failure_history(
        history
    )

    return event


# ============================================================
# 실제 완료 RUN 가져오기
# ============================================================

def get_recent_finished_runs(
    window=RECENT_WINDOW,
    engine_version=None,
):

    run_history = load_run_history()

    finished = []

    for item in run_history:

        status = item.get(
            "status"
        )

        if status not in (
            "SUCCESS",
            "FAILED",
        ):
            continue

        if (
            engine_version is not None
            and str(
                item.get(
                    "engine_version",
                    ""
                )
            )
            != str(engine_version)
        ):
            continue

        finished.append(
            item
        )

    return finished[
        -window:
    ]


# ============================================================
# Fingerprint 통계
# ============================================================

def analyze_fingerprint(
    fingerprint,
    window=RECENT_WINDOW,
    engine_version=None,
):

    failure_history = (
        load_failure_history()
    )

    recent_runs = (
        get_recent_finished_runs(
            window=window,
            engine_version=engine_version,
        )
    )

    if not recent_runs:

        return {
            "fingerprint": fingerprint,
            "status": "NO_DATA",
            "count": 0,
            "rate": 0.0,
            "streak": 0,
            "recent_runs": 0,
        }

    recent_run_ids = [
        item.get(
            "run_id"
        )
        for item in recent_runs
    ]

    recent_run_set = set(
        recent_run_ids
    )

    matching_events = [
        item
        for item in failure_history
        if (
            item.get(
                "fingerprint"
            )
            == fingerprint
            and item.get(
                "run_id"
            )
            in recent_run_set
        )
    ]

    failed_runs = {
        item.get(
            "run_id"
        )
        for item in matching_events
    }

    total_runs = len(
        recent_run_ids
    )

    failure_count = len(
        failed_runs
    )

    rate = (
        failure_count
        / total_runs
        if total_runs
        else 0.0
    )

    # --------------------------------------------------------
    # 연속 발생 횟수
    # --------------------------------------------------------

    streak = 0

    for run_id in reversed(
        recent_run_ids
    ):

        if run_id in failed_runs:
            streak += 1
        else:
            break

    # --------------------------------------------------------
    # 상태
    # --------------------------------------------------------

    status = "NORMAL"

    if (
        (
            failure_count
            >= CRITICAL_COUNT
            and rate
            >= CRITICAL_RATE
        )
        or streak
        >= CRITICAL_STREAK
    ):

        status = (
            "SUSPECTED_ENGINE_ISSUE"
        )

    elif (
        (
            failure_count
            >= WARNING_COUNT
            and rate
            >= WARNING_RATE
        )
        or streak
        >= WARNING_STREAK
    ):

        status = "WARNING"

    return {
        "fingerprint": fingerprint,
        "status": status,
        "count": failure_count,
        "rate": round(
            rate,
            3,
        ),
        "streak": streak,
        "recent_runs": total_runs,
    }


# ============================================================
# 기록 + 즉시 분석
# ============================================================

def record_and_analyze_failure(
    **kwargs,
):

    event = record_failure(
        **kwargs
    )

    analysis = analyze_fingerprint(
        event["fingerprint"],
        engine_version=event[
            "engine_version"
        ],
    )

    return {
        "event": event,
        "analysis": analysis,
    }


# ============================================================
# 모듈별 통계
# ============================================================

def analyze_modules(
    window=RECENT_WINDOW,
    engine_version=None,
):

    failure_history = (
        load_failure_history()
    )

    recent_runs = (
        get_recent_finished_runs(
            window=window,
            engine_version=engine_version,
        )
    )

    recent_run_ids = [
        item.get(
            "run_id"
        )
        for item in recent_runs
    ]

    recent_run_set = set(
        recent_run_ids
    )

    total_runs = len(
        recent_run_ids
    )

    module_runs = {}

    for item in failure_history:

        run_id = item.get(
            "run_id"
        )

        if run_id not in recent_run_set:
            continue

        module = item.get(
            "module",
            "unknown"
        )

        module_runs.setdefault(
            module,
            set()
        ).add(
            run_id
        )

    results = []

    for module, failed_runs in (
        module_runs.items()
    ):

        count = len(
            failed_runs
        )

        rate = (
            count / total_runs
            if total_runs
            else 0.0
        )

        status = "NORMAL"

        if (
            count >= CRITICAL_COUNT
            and rate >= CRITICAL_RATE
        ):

            status = (
                "SUSPECTED_ENGINE_ISSUE"
            )

        elif (
            count >= WARNING_COUNT
            and rate >= WARNING_RATE
        ):

            status = "WARNING"

        results.append({
            "module": module,
            "failed_runs": count,
            "rate": round(
                rate,
                3,
            ),
            "status": status,
        })

    results.sort(
        key=lambda item: (
            item["failed_runs"],
            item["rate"],
        ),
        reverse=True,
    )

    return results


# ============================================================
# 실패 종류별 분석
# ============================================================

def analyze_failure_classes(
    window=RECENT_WINDOW,
    engine_version=None,
):

    failure_history = (
        load_failure_history()
    )

    recent_runs = (
        get_recent_finished_runs(
            window=window,
            engine_version=engine_version,
        )
    )

    recent_run_ids = {
        item.get(
            "run_id"
        )
        for item in recent_runs
    }

    counts = Counter()

    for item in failure_history:

        if (
            item.get(
                "run_id"
            )
            not in recent_run_ids
        ):
            continue

        failure_class = item.get(
            "failure_class",
            UNKNOWN_FAILURE,
        )

        counts[
            failure_class
        ] += 1

    return dict(
        counts
    )


# ============================================================
# 버전 간 오류율 비교
# ============================================================

def compare_engine_versions(
    fingerprint,
    old_version,
    new_version,
    window=RECENT_WINDOW,
):

    old_stats = analyze_fingerprint(
        fingerprint,
        window=window,
        engine_version=old_version,
    )

    new_stats = analyze_fingerprint(
        fingerprint,
        window=window,
        engine_version=new_version,
    )

    old_rate = old_stats.get(
        "rate",
        0.0,
    )

    new_rate = new_stats.get(
        "rate",
        0.0,
    )

    delta = (
        new_rate
        - old_rate
    )

    regression = False

    # 단순 임계값.
    # 추후 regression.py에서 더 정교하게 교체.
    if (
        new_stats.get(
            "recent_runs",
            0,
        )
        >= 5
        and delta
        >= 0.25
    ):

        regression = True

    return {
        "fingerprint": fingerprint,
        "old_version": old_version,
        "new_version": new_version,
        "old_rate": old_rate,
        "new_rate": new_rate,
        "delta": round(
            delta,
            3,
        ),
        "regression_suspected": (
            regression
        ),
    }


# ============================================================
# 전체 Health Report
# ============================================================

def build_health_report(
    window=RECENT_WINDOW,
    engine_version=None,
):

    recent_runs = (
        get_recent_finished_runs(
            window=window,
            engine_version=engine_version,
        )
    )

    if not recent_runs:

        return {
            "status": "NO_DATA",
            "engine_version": engine_version,
            "recent_runs": 0,
            "suspected_modules": [],
            "warnings": [],
            "failure_classes": {},
        }

    modules = analyze_modules(
        window=window,
        engine_version=engine_version,
    )

    suspected = [
        item
        for item in modules
        if item["status"]
        == "SUSPECTED_ENGINE_ISSUE"
    ]

    warnings = [
        item
        for item in modules
        if item["status"]
        == "WARNING"
    ]

    if suspected:

        overall_status = (
            "SUSPECTED_ENGINE_ISSUE"
        )

    elif warnings:

        overall_status = "WARNING"

    else:

        overall_status = "HEALTHY"

    return {
        "status": overall_status,
        "engine_version": engine_version,
        "recent_runs": len(
            recent_runs
        ),
        "suspected_modules": suspected,
        "warnings": warnings,
        "failure_classes":
            analyze_failure_classes(
                window=window,
                engine_version=engine_version,
            ),
    }


# ============================================================
# 콘솔 출력
# ============================================================

def print_health_report(
    report=None,
):

    if report is None:

        report = (
            build_health_report()
        )

    print("")
    print("=" * 58)
    print(
        "🩺 V3.1 FAILURE MONITOR"
    )
    print("=" * 58)

    print(
        "상태:",
        report.get(
            "status",
            "UNKNOWN"
        ),
    )

    print(
        "엔진:",
        report.get(
            "engine_version",
            "ALL"
        ),
    )

    print(
        "완료 RUN:",
        report.get(
            "recent_runs",
            0,
        ),
    )

    suspected = report.get(
        "suspected_modules",
        [],
    )

    if suspected:

        print("")
        print(
            "🚨 엔진 이상 의심"
        )

        for item in suspected:

            print(
                f" - {item['module']} "
                f"| 실패 RUN "
                f"{item['failed_runs']}회 "
                f"| 실제 발생률 "
                f"{item['rate'] * 100:.1f}%"
            )

    warnings = report.get(
        "warnings",
        [],
    )

    if warnings:

        print("")
        print(
            "⚠️ 반복 실패 경고"
        )

        for item in warnings:

            print(
                f" - {item['module']} "
                f"| 실패 RUN "
                f"{item['failed_runs']}회 "
                f"| 실제 발생률 "
                f"{item['rate'] * 100:.1f}%"
            )

    classes = report.get(
        "failure_classes",
        {},
    )

    if classes:

        print("")
        print(
            "📊 실패 분류"
        )

        for key, value in (
            classes.items()
        ):

            print(
                f" - {key}: {value}"
            )

    print("=" * 58)

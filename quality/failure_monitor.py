# quality/failure_monitor.py

import os
import json
import hashlib
from datetime import datetime, timezone
from collections import Counter


# ============================================================
# V3 Failure Monitor
# ============================================================
#
# 목적:
#   "같은 실패가 반복될 때 결과물만 계속 고치지 말고,
#    엔진 자체의 문제 가능성을 탐지한다."
#
# 이 모듈은:
#   - 오류를 기록한다.
#   - 같은 오류를 fingerprint로 묶는다.
#   - 최근 발생률을 계산한다.
#   - 연속 실패를 탐지한다.
#   - 의심되는 엔진/모듈을 표시한다.
#
# 이 모듈은 절대로:
#   - 코드를 자동 수정하지 않는다.
#   - Validator 기준을 자동 변경하지 않는다.
#   - AI Judge 판단을 자동 채택하지 않는다.
#
# ============================================================


FAILURE_HISTORY_FILE = "data/failure_history.json"

MAX_HISTORY = 1000

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
# 데이터 디렉터리
# ============================================================

def ensure_data_directory():

    directory = os.path.dirname(
        FAILURE_HISTORY_FILE
    )

    if directory:

        os.makedirs(
            directory,
            exist_ok=True
        )


# ============================================================
# 시간
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# 문자열 정규화
# ============================================================

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
# fingerprint 생성
# ============================================================

def create_fingerprint(
    stage,
    module,
    error_type,
    rule_id=None,
    judge_id=None
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
# 기록 불러오기
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
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:

        print(
            f"⚠️ Failure history 읽기 실패: {e}"
        )

    return []


# ============================================================
# 기록 저장
# ============================================================

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
            encoding="utf-8"
        ) as f:

            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_path,
            FAILURE_HISTORY_FILE
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
    error_type
):

    stage_n = normalize_string(stage)
    module_n = normalize_string(module)
    error_n = normalize_string(error_type)

    combined = " ".join([
        stage_n,
        module_n,
        error_n
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
    # Judge 관련
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
    metadata=None
):

    if not failure_class:

        failure_class = classify_failure(
            stage,
            module,
            error_type
        )

    fingerprint = create_fingerprint(
        stage,
        module,
        error_type,
        rule_id,
        judge_id
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
        "failure_class": (
            failure_class
        ),
        "fingerprint": fingerprint,
        "message": str(message)[:1000],
        "rule_id": rule_id,
        "judge_id": judge_id,
        "metadata": (
            metadata
            if isinstance(metadata, dict)
            else {}
        )
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
# 최근 RUN 추출
# ============================================================

def get_recent_runs(
    history,
    window=RECENT_WINDOW
):

    run_ids = []

    for item in reversed(history):

        run_id = item.get(
            "run_id"
        )

        if not run_id:
            continue

        if run_id not in run_ids:

            run_ids.append(
                run_id
            )

        if len(run_ids) >= window:
            break

    return list(
        reversed(run_ids)
    )


# ============================================================
# 특정 fingerprint 통계
# ============================================================

def analyze_fingerprint(
    fingerprint,
    window=RECENT_WINDOW
):

    history = load_failure_history()

    if not history:

        return {
            "fingerprint": fingerprint,
            "status": "NORMAL",
            "count": 0,
            "rate": 0.0,
            "streak": 0,
            "recent_runs": 0
        }

    recent_run_ids = get_recent_runs(
        history,
        window
    )

    recent_run_set = set(
        recent_run_ids
    )

    matching_events = [
        item
        for item in history
        if (
            item.get("fingerprint")
            == fingerprint
            and item.get("run_id")
            in recent_run_set
        )
    ]

    failed_runs = {
        item.get("run_id")
        for item in matching_events
    }

    run_count = len(
        recent_run_ids
    )

    failure_count = len(
        failed_runs
    )

    rate = (
        failure_count / run_count
        if run_count
        else 0.0
    )

    # --------------------------------------------------------
    # 연속 실패 계산
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
    # 상태 결정
    # --------------------------------------------------------

    status = "NORMAL"

    if (
        failure_count >= CRITICAL_COUNT
        and rate >= CRITICAL_RATE
    ) or streak >= CRITICAL_STREAK:

        status = (
            "SUSPECTED_ENGINE_ISSUE"
        )

    elif (
        failure_count >= WARNING_COUNT
        and rate >= WARNING_RATE
    ) or streak >= WARNING_STREAK:

        status = "WARNING"

    return {
        "fingerprint": fingerprint,
        "status": status,
        "count": failure_count,
        "rate": round(rate, 3),
        "streak": streak,
        "recent_runs": run_count
    }


# ============================================================
# 특정 실패 기록 + 즉시 분석
# ============================================================

def record_and_analyze_failure(
    **kwargs
):

    event = record_failure(
        **kwargs
    )

    analysis = analyze_fingerprint(
        event["fingerprint"]
    )

    return {
        "event": event,
        "analysis": analysis
    }


# ============================================================
# 모듈별 반복 실패 분석
# ============================================================

def analyze_modules(
    window=RECENT_WINDOW
):

    history = load_failure_history()

    recent_run_ids = get_recent_runs(
        history,
        window
    )

    recent_run_set = set(
        recent_run_ids
    )

    module_runs = {}

    for item in history:

        if (
            item.get("run_id")
            not in recent_run_set
        ):
            continue

        module = item.get(
            "module",
            "unknown"
        )

        module_runs.setdefault(
            module,
            set()
        ).add(
            item.get("run_id")
        )

    results = []

    total_runs = len(
        recent_run_ids
    )

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
                3
            ),
            "status": status
        })

    results.sort(
        key=lambda item: (
            item["failed_runs"],
            item["rate"]
        ),
        reverse=True
    )

    return results


# ============================================================
# 실패 클래스 분석
# ============================================================

def analyze_failure_classes(
    window=RECENT_WINDOW
):

    history = load_failure_history()

    recent_run_ids = get_recent_runs(
        history,
        window
    )

    recent_run_set = set(
        recent_run_ids
    )

    counts = Counter()

    for item in history:

        if (
            item.get("run_id")
            not in recent_run_set
        ):
            continue

        failure_class = item.get(
            "failure_class",
            UNKNOWN_FAILURE
        )

        counts[
            failure_class
        ] += 1

    return dict(
        counts
    )


# ============================================================
# 전체 Health Report
# ============================================================

def build_health_report(
    window=RECENT_WINDOW
):

    history = load_failure_history()

    if not history:

        return {
            "status": "HEALTHY",
            "recent_runs": 0,
            "suspected_modules": [],
            "warnings": [],
            "failure_classes": {}
        }

    modules = analyze_modules(
        window
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

    recent_runs = get_recent_runs(
        history,
        window
    )

    return {
        "status": overall_status,
        "recent_runs": len(
            recent_runs
        ),
        "suspected_modules": suspected,
        "warnings": warnings,
        "failure_classes":
            analyze_failure_classes(
                window
            )
    }


# ============================================================
# 콘솔 리포트
# ============================================================

def print_health_report(
    report=None
):

    if report is None:

        report = build_health_report()

    print("")
    print("=" * 55)
    print("🩺 V3 FAILURE MONITOR")
    print("=" * 55)

    print(
        "상태:",
        report.get(
            "status",
            "UNKNOWN"
        )
    )

    print(
        "분석 RUN:",
        report.get(
            "recent_runs",
            0
        )
    )

    suspected = report.get(
        "suspected_modules",
        []
    )

    if suspected:

        print("")
        print(
            "🚨 엔진 이상 의심"
        )

        for item in suspected:

            print(
                f" - {item['module']} "
                f"| 실패 {item['failed_runs']}회 "
                f"| 발생률 "
                f"{item['rate'] * 100:.1f}%"
            )

    warnings = report.get(
        "warnings",
        []
    )

    if warnings:

        print("")
        print(
            "⚠️ 반복 실패 경고"
        )

        for item in warnings:

            print(
                f" - {item['module']} "
                f"| 실패 {item['failed_runs']}회 "
                f"| 발생률 "
                f"{item['rate'] * 100:.1f}%"
            )

    classes = report.get(
        "failure_classes",
        {}
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

    print("=" * 55)

# quality/run_tracker.py

import os
import json
import uuid
from datetime import datetime, timezone


RUN_HISTORY_FILE = "data/run_history.json"
MAX_RUN_HISTORY = 500


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ensure_data_dir():
    directory = os.path.dirname(RUN_HISTORY_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_run_history():
    _ensure_data_dir()

    if not os.path.exists(RUN_HISTORY_FILE):
        return []

    try:
        with open(RUN_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:
        print(f"⚠️ Run history 읽기 실패: {e}")

    return []


def save_run_history(history):
    _ensure_data_dir()

    history = history[-MAX_RUN_HISTORY:]
    temp_path = RUN_HISTORY_FILE + ".tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_path, RUN_HISTORY_FILE)

    except Exception as e:
        print(f"⚠️ Run history 저장 실패: {e}")

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def start_run(engine_version="V3"):
    """
    새로운 Shorts 생성 RUN을 시작한다.
    """

    run_id = uuid.uuid4().hex[:12]

    event = {
        "run_id": run_id,
        "engine_version": engine_version,
        "status": "RUNNING",
        "started_at": _now(),
        "finished_at": None,
        "stage": "startup",
        "error": None,
    }

    history = load_run_history()
    history.append(event)
    save_run_history(history)

    print(f"🚀 RUN START: {run_id}")

    return run_id


def _update_run(run_id, **updates):
    history = load_run_history()

    found = False

    for item in reversed(history):
        if item.get("run_id") == run_id:
            item.update(updates)
            found = True
            break

    if not found:
        print(f"⚠️ RUN을 찾을 수 없음: {run_id}")
        return False

    save_run_history(history)
    return True


def update_run_stage(run_id, stage):
    """
    현재 파이프라인 위치 기록.

    예:
    topic_selection
    script_generation
    hard_validation
    rendering
    telegram
    """

    return _update_run(
        run_id,
        stage=str(stage)
    )


def complete_run(run_id):
    """
    RUN 정상 완료.
    """

    success = _update_run(
        run_id,
        status="SUCCESS",
        stage="complete",
        finished_at=_now(),
        error=None
    )

    if success:
        print(f"✅ RUN SUCCESS: {run_id}")

    return success


def fail_run(
    run_id,
    error,
    stage=None
):
    """
    RUN 실패.
    """

    updates = {
        "status": "FAILED",
        "finished_at": _now(),
        "error": str(error)[:1000],
    }

    if stage:
        updates["stage"] = str(stage)

    success = _update_run(
        run_id,
        **updates
    )

    if success:
        print(f"❌ RUN FAILED: {run_id}")

    return success


def get_recent_runs(limit=20):
    history = load_run_history()

    return history[-limit:]


def get_run(run_id):
    history = load_run_history()

    for item in reversed(history):
        if item.get("run_id") == run_id:
            return item

    return None


def get_run_stats(limit=20):
    """
    최근 RUN의 기본 성공/실패 통계.
    RUNNING 상태는 성공률 계산에서 제외한다.
    """

    recent = get_recent_runs(limit)

    finished = [
        item for item in recent
        if item.get("status") in (
            "SUCCESS",
            "FAILED"
        )
    ]

    success_count = sum(
        1 for item in finished
        if item.get("status") == "SUCCESS"
    )

    failed_count = sum(
        1 for item in finished
        if item.get("status") == "FAILED"
    )

    total = len(finished)

    return {
        "total_finished": total,
        "success": success_count,
        "failed": failed_count,
        "success_rate": (
            round(success_count / total, 3)
            if total else 0.0
        ),
        "failure_rate": (
            round(failed_count / total, 3)
            if total else 0.0
        ),
        "running": sum(
            1 for item in recent
            if item.get("status") == "RUNNING"
        )
  }

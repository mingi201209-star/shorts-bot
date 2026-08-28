from __future__ import annotations

import json
import os
import re
import tempfile
import traceback as traceback_module
from pathlib import Path
from typing import Any, Dict, Optional

from quality.budget_guard import get_budget_status


DIAGNOSTICS_DIR = Path(os.environ.get("SHORTS_DIAGNOSTICS_DIR", "artifacts/diagnostics"))
GENERATOR_LOG_PATH = DIAGNOSTICS_DIR / "generator.log"
FAILURE_SUMMARY_PATH = DIAGNOSTICS_DIR / "failure_summary.json"
TRACEBACK_PATH = DIAGNOSTICS_DIR / "traceback.txt"
PROGRESS_PATH = DIAGNOSTICS_DIR / "progress.json"
SCENE_TRACE_PATH = DIAGNOSTICS_DIR / "scene_trace.jsonl"

MAX_LOG_BYTES = 5 * 1024 * 1024
MAX_TRACE_LINES = 256
MAX_STRING = 2000

_PROGRESS: Dict[str, Any] = {
    "current_stage": "not_started",
    "last_completed_stage": None,
    "current_scene_index": None,
    "current_scene_role": None,
    "current_narration": None,
    "current_visual_goal": None,
    "retrieval_stage": None,
    "selected_source_type": None,
    "visual_explanation_template": None,
    "director_stage": None,
}
_TRACE_LINES = 0

_SECRET_NAME_RE = re.compile(r"(api[_-]?key|(?:^|[_-])key$|token|secret|credential|password|authorization)", re.I)
_BEARER_RE = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+")
_KEY_VALUE_RE = re.compile(r"(?i)\b(api[_-]?key|token|secret|password|credential)\b\s*[:=]\s*[^\s,;]+")


def _safe_string(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > MAX_STRING:
        text = text[:MAX_STRING] + "...[truncated]"
    return redact_text(text)


def _secret_values() -> list[str]:
    values = []
    for name, value in os.environ.items():
        if not value or len(value) < 8:
            continue
        if _SECRET_NAME_RE.search(name):
            values.append(value)
    values.sort(key=len, reverse=True)
    return values


def redact_text(text: str) -> str:
    redacted = _BEARER_RE.sub(r"\1[REDACTED]", str(text))
    redacted = _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
    for secret in _secret_values():
        if secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _ensure_dir() -> None:
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_json_write(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_dir()
    clean = {key: _sanitize_value(value) for key, value in payload.items()}
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(DIAGNOSTICS_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(clean, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except Exception:
            pass


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(v) for v in value]
    return _safe_string(value)


def initialize_progress() -> None:
    global _PROGRESS, _TRACE_LINES
    _TRACE_LINES = 0
    _PROGRESS = {
        "current_stage": "generator_entry",
        "last_completed_stage": None,
        "current_scene_index": None,
        "current_scene_role": None,
        "current_narration": None,
        "current_visual_goal": None,
        "retrieval_stage": None,
        "selected_source_type": None,
        "visual_explanation_template": None,
        "director_stage": None,
    }
    try:
        _atomic_json_write(PROGRESS_PATH, _PROGRESS)
    except Exception:
        pass


def update_progress(**updates: Any) -> None:
    try:
        for key, value in updates.items():
            if key in _PROGRESS:
                _PROGRESS[key] = _sanitize_value(value)
        _atomic_json_write(PROGRESS_PATH, _PROGRESS)
    except Exception:
        pass


def _first(item: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def scene_started(scene_index: int, item: Dict[str, Any]) -> None:
    role = _first(item, "role", "scene_role")
    narration = _first(item, "text", "narration")
    visual_goal = _first(item, "visual_goal")
    source_type = _first(item, "selected_source_type", "source_type", "provider")
    template = _first(item, "visual_explanation_template", "explanation_template", "template")
    director = _first(item, "director_stage", "director_status")

    update_progress(
        current_stage="scene_generation",
        current_scene_index=scene_index + 1,
        current_scene_role=role,
        current_narration=narration,
        current_visual_goal=visual_goal,
        retrieval_stage="started",
        selected_source_type=source_type,
        visual_explanation_template=template,
        director_stage=director,
    )
    append_scene_trace(
        {
            "scene_index": scene_index + 1,
            "role": role,
            "retrieval_started": True,
            "source_selected": source_type is not None,
            "source_type": source_type,
            "visual_explanation_template": template,
            "validation_result": None,
            "completed": False,
        }
    )


def scene_completed(scene_index: int, item: Dict[str, Any]) -> None:
    source_type = _first(item, "selected_source_type", "source_type", "provider")
    template = _first(item, "visual_explanation_template", "explanation_template", "template")
    update_progress(
        current_stage="scene_generation",
        last_completed_stage=f"scene_{scene_index + 1}",
        current_scene_index=scene_index + 1,
        retrieval_stage="completed",
        selected_source_type=source_type,
        visual_explanation_template=template,
    )
    append_scene_trace(
        {
            "scene_index": scene_index + 1,
            "role": _first(item, "role", "scene_role"),
            "retrieval_started": True,
            "source_selected": source_type is not None,
            "source_type": source_type,
            "visual_explanation_template": template,
            "validation_result": "completed",
            "completed": True,
        }
    )


def scene_failed(scene_index: int, item: Dict[str, Any], exc: BaseException) -> None:
    update_progress(
        current_stage="scene_generation",
        current_scene_index=scene_index + 1,
        retrieval_stage="failed",
    )
    append_scene_trace(
        {
            "scene_index": scene_index + 1,
            "role": _first(item, "role", "scene_role"),
            "retrieval_started": True,
            "source_selected": _first(item, "selected_source_type", "source_type", "provider") is not None,
            "source_type": _first(item, "selected_source_type", "source_type", "provider"),
            "visual_explanation_template": _first(item, "visual_explanation_template", "explanation_template", "template"),
            "validation_result": f"exception:{type(exc).__name__}",
            "completed": False,
        }
    )


def append_scene_trace(payload: Dict[str, Any]) -> None:
    global _TRACE_LINES
    try:
        if _TRACE_LINES >= MAX_TRACE_LINES:
            return
        _ensure_dir()
        with SCENE_TRACE_PATH.open("a", encoding="utf-8") as handle:
            json.dump(_sanitize_value(payload), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        _TRACE_LINES += 1
    except Exception:
        pass


def budget_snapshot() -> Dict[str, Any]:
    try:
        status = get_budget_status()
        return {
            "api_calls_used": status.get("calls"),
            "api_calls_limit": status.get("max_calls"),
            "openai_cost_usd": status.get("cost_usd"),
            "cost_limit_usd": status.get("max_cost_usd"),
        }
    except Exception:
        return {
            "api_calls_used": None,
            "api_calls_limit": None,
            "openai_cost_usd": None,
            "cost_limit_usd": None,
        }


def capture_failure(exc: BaseException, traceback_text: Optional[str] = None) -> None:
    try:
        _ensure_dir()
        tb = traceback_text if traceback_text is not None else "".join(
            traceback_module.format_exception(type(exc), exc, exc.__traceback__)
        )
        TRACEBACK_PATH.write_text(redact_text(tb), encoding="utf-8")
    except Exception:
        tb = None

    snapshot = budget_snapshot()
    summary = {
        "run_stage": "generator",
        "status": "failed",
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "last_scene_index": _PROGRESS.get("current_scene_index"),
        "last_scene_role": _PROGRESS.get("current_scene_role"),
        "last_scene_narration": _PROGRESS.get("current_narration"),
        "last_visual_goal": _PROGRESS.get("current_visual_goal"),
        "last_source_type": _PROGRESS.get("selected_source_type"),
        "last_visual_explanation_template": _PROGRESS.get("visual_explanation_template"),
        "api_calls_used": snapshot.get("api_calls_used"),
        "api_calls_limit": snapshot.get("api_calls_limit"),
        "openai_cost_usd": snapshot.get("openai_cost_usd"),
        "cost_limit_usd": snapshot.get("cost_limit_usd"),
        "ai_video_enabled": str(os.environ.get("AI_VISUAL_FALLBACK_ENABLED", "false")).strip().lower() in {"1", "true", "yes", "on"},
        "still_fallback_usage": None,
        "visual_explanation_transform_usage": None,
        "traceback_available": bool(tb),
    }
    try:
        _atomic_json_write(FAILURE_SUMMARY_PATH, summary)
    except Exception:
        pass


def mark_success() -> None:
    update_progress(current_stage="completed", last_completed_stage="generator")


class BoundedArtifactLog:
    def __init__(self, path: Path = GENERATOR_LOG_PATH, max_bytes: int = MAX_LOG_BYTES):
        self.path = path
        self.max_bytes = max_bytes
        self._written = 0
        self._truncated = False
        _ensure_dir()
        self._handle = path.open("w", encoding="utf-8")

    def write(self, text: str) -> None:
        if self._truncated:
            return
        redacted = redact_text(text)
        data = redacted.encode("utf-8", errors="replace")
        remaining = self.max_bytes - self._written
        if remaining <= 0:
            self._truncate_marker()
            return
        if len(data) > remaining:
            clipped = data[:remaining].decode("utf-8", errors="ignore")
            self._handle.write(clipped)
            self._written += len(clipped.encode("utf-8"))
            self._truncate_marker()
            return
        self._handle.write(redacted)
        self._handle.flush()
        self._written += len(data)

    def _truncate_marker(self) -> None:
        if not self._truncated:
            self._handle.write("\n[DIAGNOSTICS LOG TRUNCATED]\n")
            self._handle.flush()
            self._truncated = True

    def flush(self) -> None:
        try:
            self._handle.flush()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self._handle.close()
        except Exception:
            pass


class TeeStream:
    def __init__(self, console, artifact_log: BoundedArtifactLog):
        self.console = console
        self.artifact_log = artifact_log

    def write(self, text: str):
        result = self.console.write(text)
        self.console.flush()
        try:
            self.artifact_log.write(text)
        except Exception:
            pass
        return result

    def flush(self):
        self.console.flush()
        self.artifact_log.flush()

    def isatty(self):
        return False

    @property
    def encoding(self):
        return getattr(self.console, "encoding", "utf-8")

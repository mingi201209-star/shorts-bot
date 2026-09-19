from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


_STARTED_PATHS: set[str] = set()
_EVENT_COUNTER = 0

_TRACKED_SUFFIXES = {".py", ".yml", ".yaml", ".json", ".txt", ".md"}
_TRACKED_ROOTS = (
    ".github",
    "analytics",
    "content",
    "diagnostics",
    "integrations",
    "quality",
    "video",
)
_SIGNAL_PATTERNS = {
    "fallback": re.compile(r"fallback|FALLBACK|복구|재생성|recovery", re.I),
    "retry": re.compile(r"retry|RETRY|attempt|시도", re.I),
    "cache": re.compile(r"cache|cached|CACHE", re.I),
    "temp": re.compile(r"temp|temporary|workspace/temp", re.I),
}


def _redact(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    for name, secret in os.environ.items():
        lowered = name.lower()
        if not secret or len(secret) < 8:
            continue
        if any(part in lowered for part in ("key", "token", "secret", "credential", "password")):
            text = text.replace(secret, "[REDACTED]")
    return text


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return _redact(value)


def _ensure_started() -> None:
    path = str(trace_jsonl_path().resolve())
    if path in _STARTED_PATHS:
        return
    trace_dir().mkdir(parents=True, exist_ok=True)
    if os.environ.get("SHORTS_TRACE_APPEND", "").strip().lower() not in {"1", "true", "yes"}:
        try:
            trace_jsonl_path().unlink()
        except FileNotFoundError:
            pass
    _STARTED_PATHS.add(path)


def record_event(event_type: str, **payload: Any) -> dict[str, Any]:
    global _EVENT_COUNTER
    _ensure_started()
    _EVENT_COUNTER += 1
    event = {
        "seq": _EVENT_COUNTER,
        "event_type": str(event_type),
        "run_label": os.environ.get("SHORTS_TRACE_RUN_LABEL", ""),
        "timestamp_unix": round(time.time(), 6),
        "payload": _clean(payload),
    }
    with trace_jsonl_path().open("a", encoding="utf-8") as handle:
        json.dump(event, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return event


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def fingerprint_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists() or not target.is_file():
        return {"exists": False, "path": str(target)}
    data = target.read_bytes()
    return {
        "exists": True,
        "path": str(target),
        "size": len(data),
        "sha256": sha256_bytes(data),
    }


def _tracked_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in _TRACKED_ROOTS:
        base = root / relative
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in _TRACKED_SUFFIXES:
                files.append(path)
    for path in root.glob("ci_*_hotfix.py"):
        if path.is_file():
            files.append(path)
    for name in ("main.py", "config.py", "requirements.txt"):
        path = root / name
        if path.is_file():
            files.append(path)
    return sorted(set(files), key=lambda p: p.as_posix())


def snapshot_tree(root: str | Path = ".") -> dict[str, dict[str, Any]]:
    root_path = Path(root).resolve()
    snapshot: dict[str, dict[str, Any]] = {}
    for path in _tracked_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        snapshot[rel] = fingerprint_file(path)
    return snapshot


def _symbol_hashes(source: str) -> dict[str, str]:
    try:
        tree = ast.parse(source)
    except Exception:
        return {}
    symbols: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = getattr(node, "name", "")
            if not name:
                continue
            try:
                segment = ast.get_source_segment(source, node) or ""
            except Exception:
                segment = ""
            symbols[name] = fingerprint_text(segment)
    return symbols


def changed_symbols(before_text: str, after_text: str) -> list[str]:
    before = _symbol_hashes(before_text)
    after = _symbol_hashes(after_text)
    names = sorted(set(before) | set(after))
    return [name for name in names if before.get(name) != after.get(name)]


def diff_snapshots(root: str | Path, before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    root_path = Path(root).resolve()
    changes: list[dict[str, Any]] = []
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel, {})
        new = after.get(rel, {})
        if old.get("sha256") == new.get("sha256") and old.get("exists") == new.get("exists"):
            continue
        item = {
            "path": rel,
            "before_sha256": old.get("sha256"),
            "after_sha256": new.get("sha256"),
            "before_size": old.get("size"),
            "after_size": new.get("size"),
            "changed_symbols": [],
        }
        path = root_path / rel
        try:
            if path.suffix == ".py":
                old_text = path.read_text(encoding="utf-8") if old.get("exists") else ""
                # The before source is no longer on disk; this symbol diff is
                # best-effort and stays empty unless callers passed file text.
                item["changed_symbols"] = []
        except Exception:
            pass
        changes.append(item)
    return changes


def snapshot_runtime_state(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    files = [
        "final_visual_semantic_qa.json",
        "visual_diversity_preflight.json",
        "final_director_qa.json",
        "final_content_manifest.json",
        "recent_topics.json",
    ]
    outputs = {name: fingerprint_file(root_path / name) for name in files}
    outputs["final_mp4_candidates"] = [
        fingerprint_file(path)
        for path in sorted(root_path.glob("final_shorts_*.mp4"))
    ]
    temp = root_path / "workspace" / "temp"
    if temp.exists():
        temp_files = [path for path in temp.rglob("*") if path.is_file()]
        outputs["workspace_temp"] = {
            "exists": True,
            "file_count": len(temp_files),
            "total_bytes": sum(path.stat().st_size for path in temp_files),
            "fingerprint": fingerprint_text(
                "\n".join(
                    f"{path.relative_to(temp).as_posix()}:{path.stat().st_size}:{fingerprint_file(path).get('sha256')}"
                    for path in sorted(temp_files)
                )
            ),
        }
    else:
        outputs["workspace_temp"] = {"exists": False, "file_count": 0, "total_bytes": 0}
    return outputs


def input_fingerprint() -> dict[str, Any]:
    env = {
        "SHORTS_TOPIC": os.environ.get("SHORTS_TOPIC", ""),
        "SHORTS_CANDIDATE_SCOPE": os.environ.get("SHORTS_CANDIDATE_SCOPE", ""),
        "GITHUB_SHA": os.environ.get("GITHUB_SHA", ""),
        "GITHUB_RUN_ID": os.environ.get("GITHUB_RUN_ID", ""),
        "GITHUB_RUN_ATTEMPT": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "ENABLE_YOUTUBE_UPLOAD": os.environ.get("ENABLE_YOUTUBE_UPLOAD", ""),
        "V3_MAX_API_CALLS": os.environ.get("V3_MAX_API_CALLS", ""),
        "V3_MAX_COST_USD": os.environ.get("V3_MAX_COST_USD", ""),
        "AI_VISUAL_FALLBACK_ENABLED": os.environ.get("AI_VISUAL_FALLBACK_ENABLED", ""),
    }
    secret_presence = {
        name: bool(os.environ.get(name))
        for name in ("OPENAI_KEY", "PEXELS_API_KEY", "PIXABAY_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
    }
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        git_sha = ""
    return {
        "env": env,
        "secret_presence": secret_presence,
        "git_head": git_sha,
        "fingerprint": fingerprint_text(json.dumps({"env": env, "git_head": git_sha}, sort_keys=True)),
    }


def log_signal_summary(log_text: str) -> dict[str, Any]:
    lines = log_text.splitlines()
    result: dict[str, Any] = {}
    for name, pattern in _SIGNAL_PATTERNS.items():
        matched = [line[:300] for line in lines if pattern.search(line)]
        result[name] = {
            "occurred": bool(matched),
            "count": len(matched),
            "samples": matched[:20],
        }
    return result


def load_events(path: str | Path | None = None) -> list[dict[str, Any]]:
    source = Path(path) if path is not None else trace_jsonl_path()
    if not source.exists():
        return []
    events = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def write_summary(status: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    events = load_events()
    log_path = trace_dir() / "generator.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    summary = {
        "status": status,
        "input": input_fingerprint(),
        "runtime_state": snapshot_runtime_state(),
        "event_count": len(events),
        "hotfix_order": [
            event.get("payload", {}).get("hotfix")
            for event in events
            if event.get("event_type") == "hotfix_end"
        ],
        "fallback_retry_cache_temp": log_signal_summary(log_text),
        "final_mp4_qa": _read_json_if_exists("final_visual_semantic_qa.json"),
        "visual_diversity_qa": _read_json_if_exists("visual_diversity_preflight.json"),
        "director_qa": _read_json_if_exists("final_director_qa.json"),
        "extra": extra or {},
    }
    trace_dir().mkdir(parents=True, exist_ok=True)
    trace_summary_path().write_text(json.dumps(_clean(summary), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _read_json_if_exists(path: str | Path) -> Any:
    target = Path(path)
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"unreadable": type(exc).__name__, "fingerprint": fingerprint_file(target)}
def trace_dir() -> Path:
    return Path(os.environ.get("SHORTS_DIAGNOSTICS_DIR", "artifacts/diagnostics"))


def trace_jsonl_path() -> Path:
    return trace_dir() / "production_execution_trace.jsonl"


def trace_summary_path() -> Path:
    return trace_dir() / "production_execution_trace_summary.json"


from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


VOLATILE_INPUT_KEYS = {
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
}
VOLATILE_EVENT_KEYS = {
    "timestamp_unix",
    "seq",
    "run_label",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if key in VOLATILE_EVENT_KEYS:
                continue
            if key == "env" and isinstance(item, dict):
                clean[key] = {
                    subkey: _normalize(subvalue)
                    for subkey, subvalue in item.items()
                    if subkey not in VOLATILE_INPUT_KEYS
                }
                continue
            clean[key] = _normalize(item)
        return clean
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _fingerprints(summary: dict[str, Any]) -> dict[str, Any]:
    state = summary.get("runtime_state") or {}
    return {
        "input": _normalize(summary.get("input") or {}),
        "hotfix_order": summary.get("hotfix_order") or [],
        "final_mp4_candidates": state.get("final_mp4_candidates") or [],
        "final_visual_semantic_qa": state.get("final_visual_semantic_qa.json") or {},
        "visual_diversity_preflight": state.get("visual_diversity_preflight.json") or {},
        "final_director_qa": state.get("final_director_qa.json") or {},
        "workspace_temp": state.get("workspace_temp") or {},
        "fallback_retry_cache_temp": summary.get("fallback_retry_cache_temp") or {},
        "final_mp4_qa_status": (summary.get("final_mp4_qa") or {}).get("status"),
        "visual_diversity_pass": (summary.get("visual_diversity_qa") or {}).get("pass"),
        "director_overall_pass": (summary.get("director_qa") or {}).get("overall_pass"),
    }


def _classify(path: str, left: Any, right: Any) -> str:
    lowered = path.lower()
    if "workspace_temp" in lowered or "recent_topics" in lowered or "cache" in lowered:
        return "hidden_state"
    if "final_mp4_candidates" in lowered or "sha256" in lowered or "size" in lowered:
        return "nondeterminism"
    if "fallback" in lowered or "retry" in lowered or "hotfix_order" in lowered:
        return "execution_graph"
    return "nondeterminism"


def _diff(path: str, left: Any, right: Any, out: list[dict[str, Any]]) -> None:
    if left == right:
        return
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            _diff(f"{path}.{key}" if path else str(key), left.get(key), right.get(key), out)
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            out.append(
                {
                    "path": path,
                    "classification": _classify(path, left, right),
                    "left_length": len(left),
                    "right_length": len(right),
                }
            )
            return
        for index, (a, b) in enumerate(zip(left, right)):
            _diff(f"{path}[{index}]", a, b, out)
        return
    out.append(
        {
            "path": path,
            "classification": _classify(path, left, right),
            "left": left,
            "right": right,
        }
    )


def compare(left_summary: Path, right_summary: Path) -> dict[str, Any]:
    left = _fingerprints(_load_json(left_summary))
    right = _fingerprints(_load_json(right_summary))
    differences: list[dict[str, Any]] = []
    _diff("", left, right, differences)
    classes = sorted({item["classification"] for item in differences})
    return {
        "status": "MATCH" if not differences else "DIFF",
        "left": str(left_summary),
        "right": str(right_summary),
        "difference_count": len(differences),
        "classifications": classes,
        "differences": differences[:500],
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) not in {2, 3}:
        print(
            "usage: python -m quality.production_execution_trace_compare "
            "RUN1_SUMMARY RUN2_SUMMARY [OUTPUT_JSON]",
            file=sys.stderr,
        )
        return 2
    result = compare(Path(args[0]), Path(args[1]))
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if len(args) == 3:
        Path(args[2]).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())

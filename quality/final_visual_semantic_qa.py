import json
from pathlib import Path


REPORT_PATH = Path("final_visual_semantic_qa.json")
_SCENE_REPORT = []


def reset_final_visual_semantic_report():
    _SCENE_REPORT.clear()
    try:
        REPORT_PATH.unlink()
    except FileNotFoundError:
        pass


def record_final_visual_scene(scene_index, query, selection, *, hook_verified=False):
    if hook_verified:
        entry = {
            "scene_index": int(scene_index),
            "query": str(query or "").strip(),
            "accepted": True,
            "mode": "EXISTING_STRICT_HOOK_GATE",
        }
    else:
        selection = dict(selection or {})
        entry = {
            "scene_index": int(scene_index),
            "query": str(query or "").strip(),
            "accepted": bool(selection.get("accepted", False)),
            "mode": str(selection.get("mode") or "MISSING_SELECTION_LINEAGE"),
            "tier": int(selection.get("tier", 99) or 99),
            "visual_state": str(selection.get("visual_state") or "UNKNOWN"),
            "anchor_matched": int(selection.get("anchor_matched", 0) or 0),
            "anchor_total": int(selection.get("anchor_total", 0) or 0),
            "provider": str(selection.get("provider") or ""),
            "source_id": str(selection.get("source_id") or ""),
            "metadata": str(selection.get("metadata") or "")[:500],
        }
    _SCENE_REPORT.append(entry)
    return entry


def validate_final_visual_semantic_qa(scenes):
    expected = len(list(scenes or []))
    ordered = sorted(_SCENE_REPORT, key=lambda item: item["scene_index"])
    failures = [item for item in ordered if not item.get("accepted")]
    seen = {item["scene_index"] for item in ordered}
    missing = [idx for idx in range(expected) if idx not in seen]
    payload = {
        "status": "PASS" if not failures and not missing and len(ordered) == expected else "FAIL",
        "scene_count": expected,
        "checked_scene_count": len(ordered),
        "missing_scene_indexes": missing,
        "failed_scenes": failures,
        "scenes": ordered,
    }
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if payload["status"] != "PASS":
        raise RuntimeError(
            "FINAL_VISUAL_SEMANTIC_QA_FAILED "
            f"missing={missing} failed={[item['scene_index'] for item in failures]}"
        )
    print(
        "FINAL_VISUAL_SEMANTIC_QA PASS "
        f"scenes={expected} report={REPORT_PATH}"
    )
    return payload

from pathlib import Path
import runpy


BASE_PATH = Path("ci_script_v2_visual_goal_hotfix_legacy_base.py")
RUNNER_PATH = Path("content/script_engine_v2_runner.py")


def _apply_single_missing_scene_recovery():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    marker = "# V2_SINGLE_MISSING_MIDDLE_SCENE_RECOVERY_V1"
    if marker in text:
        print("✅ Script V2 single-missing-scene recovery already applied")
        return

    helper_anchor = "\ndef _normalize_repair_item(item: Dict[str, Any]) -> Dict[str, Any]:\n"
    helper = r'''

# V2_SINGLE_MISSING_MIDDLE_SCENE_RECOVERY_V1
def _recover_single_missing_middle_scene(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Recover only target-1 output; every other count mismatch remains fail-closed."""
    result = deepcopy(script)
    scenes = result.get("scenes")
    contracts = plan.get("contracts") or []
    if not isinstance(scenes, list) or not isinstance(contracts, list):
        return result
    if len(contracts) < 7 or len(scenes) != len(contracts) - 1:
        return result
    if not (
        isinstance(contracts[-2], dict)
        and isinstance(contracts[-1], dict)
        and contracts[-2].get("locked")
        and contracts[-1].get("locked")
        and contracts[-2].get("role") == "reveal"
        and contracts[-1].get("role") == "payoff"
    ):
        return result
    if len(scenes) < 2 or not all(isinstance(scene, dict) for scene in scenes[-2:]):
        return result

    before = len(scenes)
    insert_at = len(contracts) - 3
    scenes.insert(insert_at, {"text": "", "visual_goal": "", "keyword": ""})
    result["scenes"] = scenes
    print(
        "🧩 V2 single missing middle scene reserved for local repair: "
        f"{before}/{len(contracts)} -> {len(scenes)}/{len(contracts)} "
        f"scene={insert_at + 1}"
    )
    return result
'''
    if helper_anchor not in text:
        raise RuntimeError("Script V2 missing-scene helper anchor not found")
    text = text.replace(helper_anchor, helper + helper_anchor, 1)

    flow_marker = "    generated = _normalize_writer_envelope(generated)\n    script = apply_locked_scenes(generated, plan)\n"
    flow_replacement = (
        "    generated = _normalize_writer_envelope(generated)\n"
        "    generated = _recover_single_missing_middle_scene(generated, plan)\n"
        "    script = apply_locked_scenes(generated, plan)\n"
    )
    if flow_marker not in text:
        raise RuntimeError("Script V2 missing-scene flow anchor not found")
    text = text.replace(flow_marker, flow_replacement, 1)
    RUNNER_PATH.write_text(text, encoding="utf-8")
    print("✅ Script V2 target-1 scene output routed into bounded local repair")


def main():
    runpy.run_path(str(BASE_PATH), run_name="__main__")
    _apply_single_missing_scene_recovery()


if __name__ == "__main__":
    main()

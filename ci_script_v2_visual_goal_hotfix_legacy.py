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
    """Recover only an unambiguous target-1 middle omission; otherwise fail closed."""
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

    # Only infer a missing middle beat when the surviving writer output proves
    # that all four immutable narrative anchors are still in their expected
    # positions. This avoids silently reinterpreting a missing ending as a
    # middle omission.
    anchor_pairs = ((0, 0), (1, 1), (-2, -2), (-1, -1))
    for scene_pos, contract_pos in anchor_pairs:
        scene = scenes[scene_pos] if len(scenes) >= abs(scene_pos) else None
        contract = contracts[contract_pos]
        if not isinstance(scene, dict) or not isinstance(contract, dict):
            return result
        if str(scene.get("text", "")).strip() != str(contract.get("locked_text", "")).strip():
            return result

    before = len(scenes)
    insert_at = len(contracts) - 3
    scenes.insert(insert_at, {"text": "", "visual_goal": "", "keyword": ""})
    result["scenes"] = scenes
    print(
        "🧩 V2 single missing middle scene reserved for bounded recovery: "
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
    print("✅ Script V2 target-1 middle omission routed into bounded recovery")


def main():
    runpy.run_path(str(BASE_PATH), run_name="__main__")
    _apply_single_missing_scene_recovery()


if __name__ == "__main__":
    main()

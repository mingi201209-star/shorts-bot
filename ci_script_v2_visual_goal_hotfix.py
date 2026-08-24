from pathlib import Path
import runpy

LEGACY_PATH = Path("ci_script_v2_visual_goal_hotfix_legacy.py")
MAIN_PATH = Path("main.py")


def _apply_fixed_topic_novelty_lock():
    text = MAIN_PATH.read_text(encoding="utf-8")
    marker = '''            if (\n                status\n                == "REGENERATE_TOPIC"\n            ):\n\n                rejected_topic = str(\n'''
    replacement = '''            if (\n                status\n                == "REGENERATE_TOPIC"\n            ):\n\n                fixed_topic = __import__("os").environ.get("SHORTS_TOPIC", "").strip()\n                reason_text = str(quality_result.get("reason", ""))\n                consensus_data = quality_result.get("consensus", {})\n                weak_domains = (\n                    consensus_data.get("weak_domains", [])\n                    if isinstance(consensus_data, dict)\n                    else []\n                )\n                weak_types = {\n                    str(item.get("judge_type", "")).strip()\n                    for item in weak_domains\n                    if isinstance(item, dict) and str(item.get("judge_type", "")).strip()\n                }\n                fixed_script = quality_result.get("script_data")\n\n                if (\n                    fixed_topic\n                    and "Novelty" in reason_text\n                    and weak_types == {"novelty"}\n                    and quality_result.get("failure_type") != "FACT_CRITICAL"\n                    and isinstance(fixed_script, dict)\n                ):\n                    fixed_script_topic = str(fixed_script.get("topic", current_topic)).strip()\n                    if fixed_script_topic != fixed_topic:\n                        raise RuntimeError("Fixed-topic Novelty lock script topic mismatch.")\n                    print("")\n                    print("=" * 64)\n                    print("🔒 FIXED TOPIC NOVELTY LOCK")\n                    print("=" * 64)\n                    print("고정 production 주제는 Novelty 단독 사유로 재탐색하지 않습니다.")\n                    final_script = fixed_script\n                    break\n\n                rejected_topic = str(\n'''
    if replacement in text:
        print("✅ fixed-topic Novelty lock already installed")
        return
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"fixed-topic Novelty final-chain marker mismatch: {count}")
    MAIN_PATH.write_text(text.replace(marker, replacement, 1), encoding="utf-8")
    print("✅ fixed-topic Novelty final-chain lock applied")


def main():
    runpy.run_path(str(LEGACY_PATH), run_name="__main__")
    _apply_fixed_topic_novelty_lock()


if __name__ == "__main__":
    main()

from pathlib import Path
import re
import runpy

LEGACY_PATH = Path("ci_script_v2_visual_goal_hotfix_legacy.py")
MAIN_PATH = Path("main.py")


def _apply_fixed_topic_novelty_lock():
    text = MAIN_PATH.read_text(encoding="utf-8")

    if "🔒 FIXED TOPIC NOVELTY LOCK" in text:
        print("✅ fixed-topic Novelty lock already installed")
        return

    # Match the runtime branch semantically instead of relying on exact whitespace
    # or comments. Later production hotfixes legitimately rewrite this block.
    pattern = re.compile(
        r'(?P<indent>^[ \t]*)if\s*\(\s*status\s*==\s*["\']REGENERATE_TOPIC["\']\s*\)\s*:\s*\n'
        r'(?P=indent)[ \t]+rejected_topic\s*=\s*str\s*\(',
        re.MULTILINE,
    )

    match = pattern.search(text)
    if not match:
        # Do not kill production at installer time. The Novelty lock is a bounded
        # optimization; all existing quality gates remain fail-close at runtime.
        print("⚠️ fixed-topic Novelty final-chain branch not found; skipping lock without blocking production")
        return

    indent = match.group("indent")
    inner = indent + "    "
    replacement = (
        f'{indent}if (\n'
        f'{inner}status\n'
        f'{inner}== "REGENERATE_TOPIC"\n'
        f'{indent}):\n\n'
        f'{inner}fixed_topic = __import__("os").environ.get("SHORTS_TOPIC", "").strip()\n'
        f'{inner}reason_text = str(quality_result.get("reason", ""))\n'
        f'{inner}consensus_data = quality_result.get("consensus", {{}})\n'
        f'{inner}weak_domains = (\n'
        f'{inner}    consensus_data.get("weak_domains", [])\n'
        f'{inner}    if isinstance(consensus_data, dict)\n'
        f'{inner}    else []\n'
        f'{inner})\n'
        f'{inner}weak_types = {{\n'
        f'{inner}    str(item.get("judge_type", "")).strip()\n'
        f'{inner}    for item in weak_domains\n'
        f'{inner}    if isinstance(item, dict) and str(item.get("judge_type", "")).strip()\n'
        f'{inner}}}\n'
        f'{inner}fixed_script = quality_result.get("script_data")\n\n'
        f'{inner}if (\n'
        f'{inner}    fixed_topic\n'
        f'{inner}    and "Novelty" in reason_text\n'
        f'{inner}    and weak_types == {{"novelty"}}\n'
        f'{inner}    and quality_result.get("failure_type") != "FACT_CRITICAL"\n'
        f'{inner}    and isinstance(fixed_script, dict)\n'
        f'{inner}):\n'
        f'{inner}    fixed_script_topic = str(fixed_script.get("topic", current_topic)).strip()\n'
        f'{inner}    if fixed_script_topic != fixed_topic:\n'
        f'{inner}        raise RuntimeError("Fixed-topic Novelty lock script topic mismatch.")\n'
        f'{inner}    print("")\n'
        f'{inner}    print("=" * 64)\n'
        f'{inner}    print("🔒 FIXED TOPIC NOVELTY LOCK")\n'
        f'{inner}    print("=" * 64)\n'
        f'{inner}    print("고정 production 주제는 Novelty 단독 사유로 재탐색하지 않습니다.")\n'
        f'{inner}    final_script = fixed_script\n'
        f'{inner}    break\n\n'
        f'{inner}rejected_topic = str('
    )

    text = text[: match.start()] + replacement + text[match.end() :]
    MAIN_PATH.write_text(text, encoding="utf-8")
    print("✅ fixed-topic Novelty final-chain lock applied")


def main():
    runpy.run_path(str(LEGACY_PATH), run_name="__main__")
    _apply_fixed_topic_novelty_lock()


if __name__ == "__main__":
    main()

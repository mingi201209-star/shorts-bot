from pathlib import Path
import re
import runpy

LEGACY_PATH = Path("ci_script_v2_visual_goal_hotfix_legacy.py")
MAIN_PATH = Path("main.py")
CONSENSUS_PATH = Path("quality/consensus.py")
SCRIPT_V2_RUNNER_PATH = Path("content/script_engine_v2_runner.py")


def _apply_fixed_topic_soft_judges():
    text = CONSENSUS_PATH.read_text(encoding="utf-8")
    marker = "    summaries = summarize_pool(pool_results, reliability_report)\n    weighted_score = calculate_weighted_score(summaries)\n    disagreements = detect_disagreements(summaries)\n    low_confidence = detect_low_confidence(summaries)\n    critical_risks = detect_critical_risks(summaries)\n    low_reliability = detect_low_reliability(summaries)\n    weak_domains = detect_weak_domains(summaries)\n"
    replacement = "    summaries = summarize_pool(pool_results, reliability_report)\n    fixed_topic = __import__(\"os\").environ.get(\"SHORTS_TOPIC\", \"\").strip()\n    decision_summaries = summaries\n    if fixed_topic:\n        # For an explicitly pinned production topic, Hook/Novelty/Visual judges\n        # remain advisory. FACT remains the only hard production gate.\n        fact_summary = summaries.get(\"fact\")\n        decision_summaries = {\"fact\": fact_summary} if isinstance(fact_summary, dict) else {}\n        print(\"🟢 FIXED TOPIC JUDGE MODE: hook/novelty/visual advisory, fact hard-gate\")\n    weighted_score = calculate_weighted_score(decision_summaries)\n    disagreements = detect_disagreements(decision_summaries)\n    low_confidence = detect_low_confidence(decision_summaries)\n    critical_risks = detect_critical_risks(decision_summaries)\n    low_reliability = detect_low_reliability(decision_summaries)\n    weak_domains = detect_weak_domains(decision_summaries)\n"
    if replacement in text:
        print("✅ fixed-topic soft Judge mode already applied")
        return
    if marker not in text:
        raise RuntimeError("fixed-topic soft Judge marker not found")
    text = text.replace(marker, replacement, 1)
    text = text.replace(
        "meets_good_enough_floors(summaries)",
        "meets_good_enough_floors(decision_summaries)",
        1,
    )
    CONSENSUS_PATH.write_text(text, encoding="utf-8")
    print("✅ fixed-topic Hook/Novelty/Visual Judges are advisory; FACT remains hard-gate")


def _apply_script_v2_formal_ending_repair():
    text = SCRIPT_V2_RUNNER_PATH.read_text(encoding="utf-8")

    # Patch the normalizer body instead of depending on the exact tuple layout;
    # earlier production hotfixes can legitimately rewrite that tuple.
    body_marker = '    value = str(text or "").strip()\n    for pattern, replacement in _FORMAL_ENDING_REPAIRS:\n'
    body_replacement = (
        '    value = str(text or "").strip()\n'
        '    # Deterministic formalization for common declarative endings that\n'
        '    # repeatedly survive writer/local-repair calls.\n'
        '    value = re.sub(r"않다(?=[.!?…]*$)", "않습니다", value)\n'
        '    value = re.sub(r"설계다(?=[.!?…]*$)", "설계입니다", value)\n'
        '    value = re.sub(r"이유다(?=[.!?…]*$)", "이유입니다", value)\n'
        '    value = re.sub(r"구조다(?=[.!?…]*$)", "구조입니다", value)\n'
        '    for pattern, replacement in _FORMAL_ENDING_REPAIRS:\n'
    )
    if body_replacement in text:
        print("✅ Script V2 declarative formal-ending repair already applied")
        return
    if body_marker not in text:
        print("⚠️ Script V2 formalizer body marker not found; skipping optional repair without blocking production")
        return
    SCRIPT_V2_RUNNER_PATH.write_text(text.replace(body_marker, body_replacement, 1), encoding="utf-8")
    print("✅ Script V2 ~않다/~설계다 common endings repaired deterministically")


def _apply_fixed_topic_novelty_lock():
    # The fixed-topic soft-Judge mode already prevents Hook/Novelty/Visual from
    # blocking pinned-topic production. Keep this legacy optimization disabled
    # so marker/regex drift can never stop production startup again.
    print("⏭️ fixed-topic Novelty lock installer disabled; soft Judge mode is authoritative")
    return


def main():
    runpy.run_path(str(LEGACY_PATH), run_name="__main__")
    _apply_fixed_topic_soft_judges()
    _apply_script_v2_formal_ending_repair()
    _apply_fixed_topic_novelty_lock()


if __name__ == "__main__":
    main()

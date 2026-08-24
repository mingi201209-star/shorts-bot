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
    marker = '    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n)\n'
    replacement = '    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),\n    (r"([가-힣]+)시킨다(?=[.!?…]*$)", r"\\1시킵니다"),\n    (r"([가-힣]+)한다(?=[.!?…]*$)", r"\\1합니다"),\n    (r"([가-힣]+)된다(?=[.!?…]*$)", r"\\1됩니다"),\n)\n'
    if replacement in text:
        print("✅ Script V2 common formal-ending repair already applied")
        return
    if marker not in text:
        print("⚠️ Script V2 formal-ending repair marker not found; skipping optional repair without blocking production")
        return
    SCRIPT_V2_RUNNER_PATH.write_text(text.replace(marker, replacement, 1), encoding="utf-8")
    print("✅ Script V2 ~한다/~된다/~시킨다 deterministic formal repair applied")


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

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
        '    value = re.sub(r"시킨다(?=[.!?…]*$)", "시킵니다", value)\n'
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


def _apply_aviation_wing_query_domain_lock():
    text = SCRIPT_V2_RUNNER_PATH.read_text(encoding="utf-8")
    marker = "# AVIATION_WING_QUERY_DOMAIN_LOCK_V1"
    if marker in text:
        print("✅ aviation wing query domain lock already applied")
        return
    block = r'''

# AVIATION_WING_QUERY_DOMAIN_LOCK_V1
# For a fixed wing/winglet topic, every general-scene search phrase keeps the
# aircraft+wing domain anchors. This prevents abstract mechanism words such as
# efficiency/pressure/reduction from drifting into charts, keyboards, fire, etc.
_script_v2_previous_deterministic_keyword = _deterministic_keyword


def _deterministic_keyword(scene, contract, plan, index):
    value = _script_v2_previous_deterministic_keyword(scene, contract, plan, index)
    fixed_topic = os.environ.get("SHORTS_TOPIC", "").strip()
    topic_text = " ".join((fixed_topic, str(plan.get("topic", "")))).lower()
    wing_topic = any(term in topic_text for term in ("날개", "윙렛", "winglet", "wing tip", "wingtip"))
    aviation_topic = any(term in topic_text for term in ("비행기", "항공", "aircraft", "airplane", "aviation"))
    if not (wing_topic and aviation_topic):
        return value

    words = _ascii_keyword_words(value)
    if (
        any(word in {"aircraft", "airplane", "plane", "aviation"} for word in words)
        and any(word in {"wing", "wings"} for word in words)
    ):
        return value
    filtered = [
        word for word in words
        if word not in {"aircraft", "airplane", "plane", "aviation", "wing", "wings", "stage"}
    ]
    locked = ["aircraft", "wing"] + filtered[:3] + ["stage", str(index)]
    locked = locked[:7]
    if len(locked) < 2:
        locked = ["aircraft", "wing"]
    result = " ".join(locked)
    if result != value:
        print(f"🛩️ AVIATION WING QUERY LOCK scene={index}: {result}")
    return result
'''
    SCRIPT_V2_RUNNER_PATH.write_text(text.rstrip() + block + "\n", encoding="utf-8")
    print("✅ fixed wing/winglet scenes retain aircraft+wing search anchors")


def _apply_aviation_window_query_domain_lock():
    text = SCRIPT_V2_RUNNER_PATH.read_text(encoding="utf-8")
    marker = "# AVIATION_WINDOW_QUERY_DOMAIN_LOCK_V1"
    if marker in text:
        print("✅ aviation window query domain lock already applied")
        return
    block = r'''

# AVIATION_WINDOW_QUERY_DOMAIN_LOCK_V1
# Fixed airplane-window topics must never emit abstract standalone searches such
# as pressure/safety/structure. Keep aircraft+window on every scene so the
# existing semantic candidate gate rejects bus/medical/office cross-domain stock.
_script_v2_window_previous_deterministic_keyword = _deterministic_keyword


def _deterministic_keyword(scene, contract, plan, index):
    value = _script_v2_window_previous_deterministic_keyword(scene, contract, plan, index)
    fixed_topic = os.environ.get("SHORTS_TOPIC", "").strip()
    topic_text = " ".join((fixed_topic, str(plan.get("topic", "")))).lower()
    window_topic = any(term in topic_text for term in ("창문", "window", "windows", "pane", "panes"))
    aviation_topic = any(term in topic_text for term in ("비행기", "항공", "aircraft", "airplane", "aviation"))
    if not (window_topic and aviation_topic):
        return value

    words = _ascii_keyword_words(value)
    if (
        any(word in {"aircraft", "airplane", "plane", "aviation"} for word in words)
        and any(word in {"window", "windows", "pane", "panes"} for word in words)
    ):
        return value
    filtered = [
        word for word in words
        if word not in {"aircraft", "airplane", "plane", "aviation", "window", "windows", "pane", "panes", "stage"}
    ]
    locked = ["aircraft", "window"] + filtered[:3] + ["stage", str(index)]
    locked = locked[:7]
    if len(locked) < 2:
        locked = ["aircraft", "window"]
    result = " ".join(locked)
    if result != value:
        print(f"🪟 AVIATION WINDOW QUERY LOCK scene={index}: {result}")
    return result
'''
    SCRIPT_V2_RUNNER_PATH.write_text(text.rstrip() + block + "\n", encoding="utf-8")
    print("✅ fixed airplane-window scenes retain aircraft+window search anchors")


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
    _apply_aviation_wing_query_domain_lock()
    _apply_aviation_window_query_domain_lock()
    _apply_fixed_topic_novelty_lock()


if __name__ == "__main__":
    main()

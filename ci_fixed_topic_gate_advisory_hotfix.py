from pathlib import Path


MAIN_PATH = Path("main.py")
CONSENSUS_PATH = Path("quality/consensus.py")
MARKER = "[FIXED_TOPIC_GATE_ADVISORY]"
HOOK_GUARD_MARKER = "# FIXED_TOPIC_HOOK_QUALITY_GUARD_V1"


def apply_fixed_topic_gate_advisory(text):
    if MARKER in text:
        return text

    old = '''                if (\n                    topic_attempt\n                    < total_topic_attempts\n                ):\n\n                    print(\"\")\n\n                    print(\n                        \"➡️ Candidate Explorer 재탐색\"\n                    )\n\n                    continue\n\n                raise RuntimeError(\n                    \"Candidate Gate를 통과하는 \"\n                    \"Winner를 확보하지 못했습니다. \"\n                    \"마지막 이유: \"\n                    f\"{winner_gate.get('reason', '')}\"\n                )\n'''

    new = '''                if forced_topic:\n\n                    if topic_attempt == 1:\n\n                        print(\"\")\n                        print(\n                            \"➡️ 지정 주제 Gate 피드백으로 1회 재탐색\"\n                        )\n\n                        continue\n\n                    print(\"\")\n                    print(\n                        \"⚠️ [FIXED_TOPIC_GATE_ADVISORY] \"\n                        \"편집성 Candidate Gate 거절은 1회 피드백 후 \"\n                        \"advisory로 전환; FACT 및 downstream 품질 Gate는 유지\"\n                    )\n\n                else:\n\n                    if (\n                        topic_attempt\n                        < total_topic_attempts\n                    ):\n\n                        print(\"\")\n\n                        print(\n                            \"➡️ Candidate Explorer 재탐색\"\n                        )\n\n                        continue\n\n                    raise RuntimeError(\n                        \"Candidate Gate를 통과하는 \"\n                        \"Winner를 확보하지 못했습니다. \"\n                        \"마지막 이유: \"\n                        f\"{winner_gate.get('reason', '')}\"\n                    )\n'''

    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"fixed-topic Candidate Gate tail marker count mismatch: {count}"
        )

    return text.replace(old, new, 1)


def apply_fixed_topic_hook_quality_guard(text):
    """Keep the existing Hook Good-Enough floor authoritative for pinned topics.

    The later Script-V2 composition intentionally makes Novelty/Visual advisory
    for an explicitly pinned canary topic so the engine does not silently swap
    the requested subject.  Hook quality is different: a weak opening can still
    be repaired without changing the topic.  This post-consensus wrapper keeps
    the repo's existing GOOD_ENOUGH_FLOORS['hook'] value unchanged and turns an
    otherwise-PASS fixed-topic result into REWRITE when that floor is missed.
    """
    if HOOK_GUARD_MARKER in text:
        return text
    if "def build_consensus(pool_results, reliability_report=None):" not in text:
        raise RuntimeError("fixed-topic Hook quality guard requires build_consensus")

    block = r'''

# FIXED_TOPIC_HOOK_QUALITY_GUARD_V1
_fixed_topic_hook_guard_original_build_consensus = build_consensus


def build_consensus(pool_results, reliability_report=None):
    result = _fixed_topic_hook_guard_original_build_consensus(
        pool_results, reliability_report
    )
    fixed_topic = __import__("os").environ.get("SHORTS_TOPIC", "").strip()
    if not fixed_topic or not isinstance(result, dict):
        return result

    summaries = result.get("domain_summaries") or {}
    hook_summary = summaries.get("hook") or {}
    hook_floor = safe_float(GOOD_ENOUGH_FLOORS.get("hook", 0.0), 0.0)
    hook_score = safe_float(hook_summary.get("score", 0.0), 0.0)

    # Only tighten a result that the fixed-topic advisory composition would
    # otherwise approve. REVIEW/HOLD paths and all non-fixed topics are left
    # exactly as the existing consensus engine decided them.
    if result.get("decision") != "PASS" or hook_score >= hook_floor:
        return result

    rewritten = dict(result)
    rewritten["decision"] = "REWRITE"
    rewritten["pass_tier"] = None

    weak_domains = [dict(item) for item in (result.get("weak_domains") or [])]
    if not any(item.get("judge_type") == "hook" for item in weak_domains):
        weak_domains.append({
            "judge_type": "hook",
            "score": round(hook_score, 3),
            "minimum": hook_floor,
        })
    rewritten["weak_domains"] = weak_domains

    reasons = list(result.get("reasons") or [])
    reasons.append(
        "지정 주제라도 첫 훅은 기존 Good Enough 최소 기준을 충족해야 합니다."
    )
    rewritten["reasons"] = reasons
    print(
        "🟠 FIXED TOPIC HOOK FLOOR: "
        f"score={hook_score:.2f} required={hook_floor:.2f} action=REWRITE"
    )
    return rewritten
'''
    return text.rstrip() + "\n" + block.strip() + "\n"


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    patched = apply_fixed_topic_gate_advisory(text)
    MAIN_PATH.write_text(patched, encoding="utf-8")

    consensus_text = CONSENSUS_PATH.read_text(encoding="utf-8")
    consensus_patched = apply_fixed_topic_hook_quality_guard(consensus_text)
    CONSENSUS_PATH.write_text(consensus_patched, encoding="utf-8")

    print("✅ Fixed-topic Candidate Gate bounded advisory hotfix applied")
    print("✅ Fixed-topic Hook Good-Enough floor remains a rewrite gate")


if __name__ == "__main__":
    main()

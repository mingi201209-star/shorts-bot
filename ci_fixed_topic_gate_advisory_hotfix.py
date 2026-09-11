from pathlib import Path


MAIN_PATH = Path("main.py")
CONSENSUS_PATH = Path("quality/consensus.py")
MARKER = "[FIXED_TOPIC_GATE_ADVISORY]"
HOOK_GUARD_MARKER = "# FIXED_TOPIC_HOOK_QUALITY_GUARD_V1"
HOOK_EXHAUSTION_MARKER = "# FIXED_TOPIC_HOOK_EXHAUSTION_RECOVERY_V1"


def _apply_hook_guard_to_consensus_file():
    """Install the pinned-topic Hook floor into the live composed consensus.

    ci_topic_input_hotfix imports this module and calls
    apply_fixed_topic_gate_advisory() on the full production main.py before the
    later Script-V2 soft-judge installer rewrites the original consensus body.
    Installing the wrapper here keeps the existing Hook Good-Enough floor
    authoritative in the real production composition, not only in isolated
    regression fixtures.
    """
    consensus_text = CONSENSUS_PATH.read_text(encoding="utf-8")
    patched = apply_fixed_topic_hook_quality_guard(consensus_text)
    if patched != consensus_text:
        CONSENSUS_PATH.write_text(patched, encoding="utf-8")
        print("✅ Fixed-topic Hook Good-Enough floor installed in composed consensus")


def apply_fixed_topic_hook_exhaustion_recovery(text):
    """Regenerate the same pinned topic when its Hook floor survives one rewrite.

    This does not add rewrites, retries, model calls, or relax the Hook floor.
    It only reuses the already-bounded Candidate regeneration path after the
    existing single rewrite has been exhausted by a fixed-topic Hook miss.
    """
    if HOOK_EXHAUSTION_MARKER in text:
        return text

    rewrite_anchor = '''            if (
                rewrite_count
                >= MAX_REWRITES
            ):

                if (
                    has_persistent_novelty_failure(
                        consensus
                    )
                ):
'''
    rewrite_replacement = '''            if (
                rewrite_count
                >= MAX_REWRITES
            ):

                # FIXED_TOPIC_HOOK_EXHAUSTION_RECOVERY_V1
                # Run 34641471858: the pinned rounded-window canary remained
                # Hook=6.0 after the one allowed rewrite while FACT/Visual
                # stayed healthy. Do not lower the Hook floor or add rewrites;
                # reuse the existing bounded Candidate regeneration path so
                # the same forced topic can supply a stronger opening.
                if (
                    __import__("os").environ.get("SHORTS_TOPIC", "").strip()
                    and consensus.get("fixed_topic_hook_floor_miss")
                ):
                    hook_summary = (
                        (consensus.get("domain_summaries") or {})
                        .get("hook", {})
                    ) or {}
                    hook_reason = str(
                        hook_summary.get("reason", "")
                    ).strip()
                    hook_issues = [
                        str(issue).strip()
                        for issue in (hook_summary.get("issues") or [])
                        if str(issue).strip()
                    ]
                    hook_details = "; ".join(
                        item
                        for item in (
                            hook_reason,
                            ", ".join(hook_issues),
                        )
                        if item
                    )
                    reason = (
                        "Fixed-topic Hook가 bounded rewrite 후에도 "
                        "기존 품질 floor 미달"
                    )
                    if hook_details:
                        reason += f": {hook_details}"

                    print(
                        "\\n🔁 Fixed-topic Hook 지속 실패 → "
                        "같은 주제 Candidate Explorer 재생성"
                    )
                    return {
                        "status": "REGENERATE_TOPIC",
                        "script_data": current_script,
                        "consensus": consensus,
                        "rewrite_count": rewrite_count,
                        "review_count": review_count,
                        "reason": reason,
                    }

                if (
                    has_persistent_novelty_failure(
                        consensus
                    )
                ):
'''
    rewrite_count = text.count(rewrite_anchor)
    if rewrite_count != 1:
        raise RuntimeError(
            "fixed-topic Hook exhaustion rewrite marker count mismatch: "
            f"{rewrite_count}"
        )
    text = text.replace(rewrite_anchor, rewrite_replacement, 1)
    return text


def apply_fixed_topic_gate_advisory(text):
    # Production call path supplies the whole main.py.  Fixture-only unit tests
    # intentionally do not mutate repository consensus state.
    if "def run_quality_process(" in text:
        _apply_hook_guard_to_consensus_file()

    if MARKER in text:
        return apply_fixed_topic_hook_exhaustion_recovery(text)

    old = '''                if (
                    topic_attempt
                    < total_topic_attempts
                ):

                    print("")

                    print(
                        "➡️ Candidate Explorer 재탐색"
                    )

                    continue

                raise RuntimeError(
                    "Candidate Gate를 통과하는 "
                    "Winner를 확보하지 못했습니다. "
                    "마지막 이유: "
                    f"{winner_gate.get('reason', '')}"
                )
'''

    new = '''                if forced_topic:

                    if topic_attempt == 1:

                        print("")
                        print(
                            "➡️ 지정 주제 Gate 피드백으로 1회 재탐색"
                        )

                        continue

                    print("")
                    print(
                        "⚠️ [FIXED_TOPIC_GATE_ADVISORY] "
                        "편집성 Candidate Gate 거절은 1회 피드백 후 "
                        "advisory로 전환; FACT 및 downstream 품질 Gate는 유지"
                    )

                else:

                    if (
                        topic_attempt
                        < total_topic_attempts
                    ):

                        print("")

                        print(
                            "➡️ Candidate Explorer 재탐색"
                        )

                        continue

                    raise RuntimeError(
                        "Candidate Gate를 통과하는 "
                        "Winner를 확보하지 못했습니다. "
                        "마지막 이유: "
                        f"{winner_gate.get('reason', '')}"
                    )
'''

    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"fixed-topic Candidate Gate tail marker count mismatch: {count}"
        )

    patched = text.replace(old, new, 1)
    return apply_fixed_topic_hook_exhaustion_recovery(patched)


def apply_fixed_topic_hook_quality_guard(text):
    """Keep the existing Hook Good-Enough floor authoritative for pinned topics.

    The later Script-V2 composition intentionally makes Novelty/Visual advisory
    for an explicitly pinned canary topic so the engine does not silently swap
    the requested subject. Hook quality is different: a weak opening can still
    be repaired without changing the topic. This post-consensus wrapper keeps
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

    if result.get("decision") != "PASS" or hook_score >= hook_floor:
        return result

    rewritten = dict(result)
    rewritten["decision"] = "REWRITE"
    rewritten["pass_tier"] = None
    rewritten["fixed_topic_hook_floor_miss"] = True

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

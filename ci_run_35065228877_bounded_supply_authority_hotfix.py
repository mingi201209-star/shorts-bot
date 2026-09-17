from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "# RUN_35065228877_BOUNDED_SUPPLY_AUTHORITY_V1"

PATCH = r'''

# RUN_35065228877_BOUNDED_SUPPLY_AUTHORITY_V1
# Run 35065228877 proved that default automatic exploration can exhaust all
# seven normal attempts through model-side editorial self-withholding even when
# a concrete, fact-reviewable subject exists. This patch changes only the
# ALREADY-BOUNDED one-call supply-recovery path. Candidate Gate remains the
# independent editorial authority; FACT/canonical grounding remain fail-closed.

_run_35065228877_previous_zero_supply_reason = (
    _candidate_supply_reason_is_zero_usable
)


def _candidate_supply_reason_is_zero_usable(result):
    if _run_35065228877_previous_zero_supply_reason(result):
        return True
    if not isinstance(result, dict):
        return False
    if str(result.get("status", "")).strip().upper() != "REGENERATE":
        return False

    reason = " ".join(str(result.get("reason", "")).strip().lower().split())

    # Recognize only explicit whole-pool supply exhaustion. Editorial weakness
    # by itself (broad/generic/predictable/weak payoff) still does NOT spend the
    # single recovery opportunity.
    all_failed = (
        "모든 후보" in reason
        and (
            "실패" in reason
            or "통과하지 못" in reason
            or "찾지 못" in reason
        )
    )
    concrete_supply_missing = any(
        marker in reason
        for marker in (
            "구체적인 질문",
            "구체적인 메커니즘",
            "구체적인 사례",
            "구체적인 후보",
            "구체적 질문",
            "구체적 메커니즘",
            "구체적 사례",
            "concrete question",
            "concrete mechanism",
            "concrete case",
            "concrete candidate",
        )
    )
    insufficiency = any(
        marker in reason
        for marker in (
            "찾지 못",
            "부족",
            "없었",
            "없음",
            "insufficient",
            "could not find",
            "unable to find",
        )
    )
    return bool(all_failed and concrete_supply_missing and insufficiency)


_run_35065228877_previous_recovery_context = (
    _build_candidate_supply_recovery_context
)


def _build_candidate_supply_recovery_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic_gate_feedback="",
    original_reason="",
):
    context = _run_35065228877_previous_recovery_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        original_reason=original_reason,
    )

    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    forced_topic = bool(os.environ.get("SHORTS_TOPIC", "").strip())
    if aviation_scope or forced_topic:
        return context

    return context + r"""

============================================================
[DEFAULT AUTOMATIC SUPPLY RECOVERY AUTHORITY — RUN 35065228877]
============================================================
This block applies ONLY to this already-bounded final supply-recovery call.
It does not change the normal seven-attempt exploration loop and does not relax
Candidate Gate, canonical grounding, FACT, visual, Script, or Director floors.

RESPONSIBILITY IN THIS RECOVERY CALL:
- Explorer = fact-safe Candidate SUPPLIER
- Candidate Gate = independent EDITORIAL authority

Do not return REGENERATE solely because a candidate might later be judged:
- broad or generic in editorial framing,
- predictable in payoff,
- weak in novelty,
- not yet maximally hookable.

Those are Candidate Gate judgments in this final supply-recovery opportunity.
If at least one candidate has ALL of the following, return it as normal
`status=SELECTED` so the unchanged Candidate Gate can judge it:
- one real, recognizable concrete subject or observable phenomenon,
- one specific question tied to that subject,
- one named mechanism / constraint / causal relation that is not fabricated,
- one concrete visual-proof target,
- enough factual grounding to state what must be checked in fact_check_focus.

Still return REGENERATE when supply truly fails because of malformed schema,
missing concrete subject, fabricated or impossible causal linkage, unresolved
identity that cannot be stated honestly, no specific mechanism/constraint, or
no plausible visual proof. Never invent facts, identity, provenance, history,
numbers, or causal links merely to produce SELECTED.

Output the existing normal SELECTED schema, NOT CANDIDATE_POOL.
This call remains one bounded recovery call; no retry/API/cost ceiling changes.
"""
'''


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ Run 35065228877 bounded supply authority already applied")
        return
    if "# CANDIDATE_SUPPLY_RECOVERY_V1" not in text:
        print("⏭️ Run 35065228877 bounded supply authority deferred: supply recovery not installed")
        return
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print(
        "✅ Run 35065228877 explicit zero-supply recognition + final bounded "
        "supplier/Gate authority separation applied; limits unchanged"
    )


main()

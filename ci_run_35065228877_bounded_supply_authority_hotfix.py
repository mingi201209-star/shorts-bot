from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MAIN_PATH = Path("main.py")
MARKER = "# RUN_35065228877_BOUNDED_SUPPLY_AUTHORITY_V1"
MAIN_MARKER = "# RUN_35180822768_FINAL_ATTEMPT_RECOVERY_V1"

PATCH = r'''

# RUN_35065228877_BOUNDED_SUPPLY_AUTHORITY_V1
# Runs 35065228877 and 35180049273 proved that default automatic exploration
# can exhaust all seven normal attempts through model-side editorial
# self-withholding. The single recovery must not be spent on an intermediate
# broad shortage phrase; default automatic reserves it for explicit whole-pool
# exhaustion. Aviation/fixed-topic trigger contracts remain unchanged.
# Candidate Gate remains the independent editorial authority and all
# FACT/canonical grounding checks remain fail-closed.

_run_35065228877_previous_zero_supply_reason = (
    _candidate_supply_reason_is_zero_usable
)


def _candidate_supply_reason_is_zero_usable(result):
    previous_match = _run_35065228877_previous_zero_supply_reason(result)
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    forced_topic = bool(os.environ.get("SHORTS_TOPIC", "").strip())

    # Preserve the established trigger contract for aviation and fixed-topic
    # production. In default automatic mode, however, the broad legacy
    # "concrete candidate shortage" wording can appear on an intermediate
    # direction and spend the one recovery call too early (Run 35180049273).
    # Default automatic therefore requires the explicit whole-pool form below.
    if aviation_scope or forced_topic:
        return previous_match

    # Run 35180822768 proved that even explicit whole-pool wording can occur on
    # an intermediate direction. In default automatic mode the single 1/1 call
    # is therefore eligible only on the host loop's final normal attempt.
    # The host now always sends 0/1. Treat an absent flag as legacy/standalone
    # final context so established focused tests and non-host callers retain
    # their previous one-shot recovery contract.
    final_attempt = (
        os.environ.get("SHORTS_CANDIDATE_FINAL_ATTEMPT", "1").strip() != "0"
    )
    if not final_attempt:
        return False
    if not isinstance(result, dict):
        return False
    if str(result.get("status", "")).strip().upper() != "REGENERATE":
        return False

    reason = " ".join(str(result.get("reason", "")).strip().lower().split())

    # Preserve unambiguous legacy zero-supply and all-hard-gate exhaustion
    # signals. Only the broad intermediate "concrete candidate shortage"
    # family is deferred in default automatic mode.
    explicit_literal_zero = (
        "usable grounded candidate" in reason
        and (
            "0개" in reason
            or "zero" in reason
            or "no usable" in reason
            or "없" in reason
        )
    )
    hard_gate_exhaustion = (
        "구조·사실성 hard gate" in reason
        and "모든 후보" in reason
        and (
            "통과하지 못" in reason
            or "실패" in reason
        )
    )
    if previous_match and (explicit_literal_zero or hard_gate_exhaustion):
        return True

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


MAIN_BEFORE_TRY_OLD = r'''            try:
                explorer_result = (
'''

MAIN_BEFORE_DIRECT_OLD = r'''            explorer_result = (
                explore_candidates(
'''

MAIN_SIGNAL = r'''            # RUN_35180822768_FINAL_ATTEMPT_RECOVERY_V1
            # Expose only host-owned loop position. Default automatic supply
            # recovery remains 1/1 and can spend it only on the final normal
            # attempt.
            _previous_final_attempt = os.environ.get(
                "SHORTS_CANDIDATE_FINAL_ATTEMPT"
            )
            os.environ["SHORTS_CANDIDATE_FINAL_ATTEMPT"] = (
                "1"
                if topic_attempt == total_topic_attempts
                else "0"
            )

'''

MAIN_BEFORE_TRY_NEW = MAIN_SIGNAL + r'''            try:
                explorer_result = (
'''

MAIN_BEFORE_DIRECT_NEW = MAIN_SIGNAL + r'''            explorer_result = (
                explore_candidates(
'''

MAIN_AFTER_OLD = r'''
            explorer_status = (
'''

MAIN_AFTER_NEW = r'''
            if _previous_final_attempt is None:
                os.environ.pop(
                    "SHORTS_CANDIDATE_FINAL_ATTEMPT",
                    None,
                )
            else:
                os.environ[
                    "SHORTS_CANDIDATE_FINAL_ATTEMPT"
                ] = _previous_final_attempt

            explorer_status = (
'''

def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER not in text:
        if "# CANDIDATE_SUPPLY_RECOVERY_V1" not in text:
            print("⏭️ Run 35065228877 bounded supply authority deferred: supply recovery not installed")
            return
        EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
        print(
            "✅ Run 35065228877/35180049273 bounded supply authority applied; "
            "limits unchanged"
        )
    else:
        print("ℹ️ Run 35065228877 bounded supply authority already applied")

    main_text = MAIN_PATH.read_text(encoding="utf-8")
    if MAIN_MARKER in main_text:
        print("ℹ️ Run 35180822768 final-attempt signal already applied")
        return
    if MAIN_AFTER_OLD not in main_text:
        raise RuntimeError("Run 35180822768 main post-Explorer anchor not found")
    if MAIN_BEFORE_TRY_OLD in main_text:
        main_text = main_text.replace(
            MAIN_BEFORE_TRY_OLD,
            MAIN_BEFORE_TRY_NEW,
            1,
        )
    elif MAIN_BEFORE_DIRECT_OLD in main_text:
        main_text = main_text.replace(
            MAIN_BEFORE_DIRECT_OLD,
            MAIN_BEFORE_DIRECT_NEW,
            1,
        )
    else:
        raise RuntimeError("Run 35180822768 main pre-Explorer anchor not found")
    main_text = main_text.replace(MAIN_AFTER_OLD, MAIN_AFTER_NEW, 1)
    MAIN_PATH.write_text(main_text, encoding="utf-8")
    print(
        "✅ Run 35180822768 default automatic recovery reserved for final "
        "host attempt; aviation/fixed-topic unchanged"
    )


main()

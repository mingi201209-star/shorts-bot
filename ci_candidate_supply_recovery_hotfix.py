from pathlib import Path


path = Path("content/candidate_explorer.py")
text = path.read_text(encoding="utf-8")

MARKER = "# CANDIDATE_SUPPLY_RECOVERY_V1"

PATCH = r'''

# CANDIDATE_SUPPLY_RECOVERY_V1
# A production generation process may spend at most one extra Explorer call
# when the normal Explorer returns REGENERATE specifically because it found
# zero usable grounded candidates. This is supply recovery only: the recovered
# payload must still satisfy the normal Explorer output validator and all
# downstream Candidate Gate / fact / quality checks remain unchanged.
_candidate_supply_recovery_used = False
_original_explore_candidates_before_supply_recovery = explore_candidates


def _candidate_supply_reason_is_zero_usable(result):
    if not isinstance(result, dict):
        return False
    if str(result.get("status", "")).strip().upper() != "REGENERATE":
        return False

    reason = str(result.get("reason", "")).strip().lower()
    normalized = " ".join(reason.split())
    return (
        "usable grounded candidate" in normalized
        and (
            "0개" in normalized
            or "zero" in normalized
            or "없" in normalized
        )
    )


def _reset_candidate_supply_recovery_for_tests():
    global _candidate_supply_recovery_used
    _candidate_supply_recovery_used = False


def _build_candidate_supply_recovery_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    original_reason="",
):
    base = build_execution_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
    )

    return base + f"""

============================================================
[BOUNDED SUPPLY RECOVERY]
============================================================

The normal Candidate Explorer returned REGENERATE because it found zero usable
grounded candidates.

Original reason:
{original_reason}

This is the only supply-recovery opportunity for this generation run.
Do NOT relax any Candidate Explorer hard gate, anti-cliche rule, anti-fabrication
rule, final sanity rule, or fact-safety rule.

Search again for at least one concrete candidate that is:
- a real, recognizable subject or observable detail,
- driven by a specific non-obvious mechanism, purpose, constraint, or effect,
- independently verifiable,
- visually provable enough for a Short,
- explainable within the normal target duration.

Do not invent hidden purposes, historical accidents, causal links, or numbers.
If verification is required, put concrete claims in fact_check_focus.

Run the SAME Candidate Explorer hard gates and final sanity check from the
system prompt. Return SELECTED only if a candidate genuinely survives them.
Otherwise return REGENERATE. Return one JSON object only.
"""


def _run_candidate_supply_recovery(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    model=MODEL,
    original_reason="",
):
    execution_context = _build_candidate_supply_recovery_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        original_reason=original_reason,
    )

    call_number = authorize_call(model)
    print(f"💳 Candidate supply recovery API call authorized: #{call_number}")

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": CANDIDATE_EXPLORER_PROMPT,
            },
            {
                "role": "user",
                "content": execution_context,
            },
        ],
        temperature=0.55,
        response_format={"type": "json_object"},
    )

    usage = record_usage(model, response)
    print(f"💰 Candidate supply recovery call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Candidate supply recovery 응답이 비어 있습니다.")

    parsed = extract_json(content)
    return validate_explorer_output(parsed)


def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    model=MODEL,
):
    global _candidate_supply_recovery_used

    result = _original_explore_candidates_before_supply_recovery(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        model=model,
    )

    if not _candidate_supply_reason_is_zero_usable(result):
        return result

    if _candidate_supply_recovery_used:
        print("⏭️ Candidate supply recovery already spent for this generation run")
        return result

    _candidate_supply_recovery_used = True
    print("")
    print("=" * 64)
    print("🛟 CANDIDATE SUPPLY RECOVERY (1/1)")
    print("=" * 64)

    recovered = _run_candidate_supply_recovery(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        model=model,
        original_reason=result.get("reason", ""),
    )

    if recovered.get("status") == "SELECTED":
        print("✅ Candidate supply recovery produced a validated candidate")
    else:
        print("❌ Candidate supply recovery remained REGENERATE; fail closed")

    return recovered
'''


if MARKER in text:
    print("ℹ️ Candidate supply recovery hotfix already applied")
else:
    path.write_text(text + PATCH, encoding="utf-8")
    print("✅ Bounded Candidate Explorer supply recovery hotfix applied")

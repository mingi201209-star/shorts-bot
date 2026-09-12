from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "# GROUNDING_AWARE_CANDIDATE_SUPPLY_V1"


PATCH = r'''

# GROUNDING_AWARE_CANDIDATE_SUPPLY_V1
# Authority: production Run 33960845940 supplied 20 aviation candidates across
# seven attempts; host canonical grounding rejected every one. Run 34707653148
# then showed that prompt-only capability guidance can still exhaust automatic
# supply on unsupported physical identities. Expose the exact repo-owned
# grounding capability to the existing Explorer call and, only after automatic
# aviation model supply fails, offer a bounded repo-owned seed pool through the
# unchanged host handoff. No quality gate, retry, or budget is relaxed.
from quality.grounding_aware_candidate_supply import (
    grounded_seed_candidate_pool,
    grounding_capability_context,
    no_grounded_candidate_supply_result,
)

_grounding_aware_previous_explore_candidates = explore_candidates


def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
    model=MODEL,
):
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    if aviation_scope:
        empty = no_grounded_candidate_supply_result()
        if empty is not None:
            print(
                "[GROUNDING_AWARE_SUPPLY] "
                "status=NO_GROUNDED_CANDIDATE_SUPPLY capabilities=0 api_calls=0"
            )
            return empty

    result = _grounding_aware_previous_explore_candidates(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic=fixed_topic,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        model=model,
    )

    # Fixed-topic authority must never be replaced by an unrelated automatic
    # seed. This fallback exists only for automatic aviation topic discovery.
    fixed_topic_requested = bool(
        str(fixed_topic or "").strip()
        or os.environ.get("SHORTS_TOPIC", "").strip()
    )
    if (
        not aviation_scope
        or fixed_topic_requested
        or not isinstance(result, dict)
        or str(result.get("status") or "").strip().upper() == "SELECTED"
    ):
        return result

    seed_pool = grounded_seed_candidate_pool(
        recent_topics=recent_topics,
        rejected_topics=rejected_topics,
    )
    if str(seed_pool.get("status") or "").strip().upper() != "CANDIDATE_POOL":
        print(
            "[GROUNDING_SEED_FALLBACK] "
            f"status={seed_pool.get('status')} candidates=0 api_calls=0 "
            f"reason={seed_pool.get('reason', '')}"
        )
        return result

    # Candidate Pool Handoff remains the deterministic authority. Feeding the
    # repo-owned seed pool through validate_explorer_output means every seed is
    # revalidated for schema, aviation specificity, canonical grounding, and
    # visual proof before it can reach Candidate Gate.
    seed_result = validate_explorer_output(seed_pool)
    trace = (
        seed_result.get("_candidate_pool_handoff", {})
        if isinstance(seed_result, dict)
        else {}
    )
    seed_result["_grounding_seed_fallback"] = {
        "status": "USED",
        "upstream_status": str(result.get("status") or ""),
        "upstream_reason": str(result.get("reason") or ""),
        "supplied": len(seed_pool.get("candidates") or []),
        "survived": trace.get("survived", 0),
        "api_calls": 0,
    }
    print(
        "[GROUNDING_SEED_FALLBACK] "
        f"status={seed_result.get('status')} "
        f"supplied={len(seed_pool.get('candidates') or [])} "
        f"survived={trace.get('survived', 0)} api_calls=0"
    )
    return seed_result


# The capability list is derived at install/runtime import from the exact same
# repo-owned registries used by host validation. Keep it at SYSTEM authority so
# primary Explorer and the existing bounded recovery call inherit one contract
# without wrapping build_execution_context (which later compatibility installers
# inspect structurally).
CANDIDATE_EXPLORER_PROMPT += "\n\n" + grounding_capability_context() + "\n"
CANDIDATE_EXPLORER_PROMPT += """

============================================================
16. GROUNDING-AWARE AVIATION SUPPLY — RUN 33960845940 / 34707653148
============================================================
For aviation automatic supply, the SYSTEM prompt contains a compact
[GROUNDING-AWARE CANDIDATE SUPPLY] capability list derived from the exact
repo-owned trusted grounding registries used by host validation.

This is a hard generation-space constraint, not a list of required topic titles:
- generate reviewable aviation candidates only inside those evidence-supported
  canonical subject capabilities;
- use their observable/context hints to instantiate concrete #283 seeds;
- vary question, phenomenon, mechanism, and presentation when the trusted
  evidence actually supports that variation;
- respect recent/rejected-topic context and Audience Continuity when choosing
  among supported capabilities;
- never leave the supported capability space merely to gain novelty/diversity;
- never invent a new canonical identity, provenance, alias, causal mechanism, or
  evidence claim to make an unsupported candidate appear groundable.

The existing Candidate Pool Handoff and Canonical Subject Grounding remain the
final deterministic authorities. Every generated candidate must still survive
unchanged schema, aviation specificity, visual-proof, canonical grounding, FACT,
and downstream Candidate Gate checks.

If automatic aviation model supply still returns no host-usable Candidate, the
host may offer a bounded repo-owned seed pool from trusted identity records. That
seed pool is not pre-approved: it goes through the exact same Candidate Pool
Handoff, canonical grounding, Candidate Gate, FACT, visual, and quality gates.
It adds zero model calls and does not apply to fixed-topic mode.

If the capability context says NO_GROUNDED_CANDIDATE_SUPPLY, do not fabricate a
fallback candidate. Fail closed. This contract adds no model call and changes no
quality threshold, Candidate Gate, FACT gate, API ceiling, cost ceiling, or retry.
"""
'''


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ Grounding-aware Candidate Supply V1 already applied")
        return
    required = (
        "CANDIDATE_POOL_HANDOFF_V1",
        "AVIATION_SYSTEM_AUTHORITY_SUPPLY_V1",
        "AVIATION OBSERVABLE SEED SUPPLY CONTRACT",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(
            "Grounding-aware Candidate Supply requires existing contracts: "
            + ", ".join(missing)
        )
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print(
        "✅ Grounding-aware Candidate Supply V1 installed; "
        "trusted capability + bounded deterministic seed fallback active, "
        "host validation unchanged"
    )


main()

# Run 34708987774: deterministic repo-owned seeds can overlap multiple generic
# text descriptions even though the originating trusted record is already known.
# Install a fail-closed in-memory identity scope after the seed supplier exists.
import ci_run_34708987774_grounded_seed_identity_hotfix  # noqa: E402,F401

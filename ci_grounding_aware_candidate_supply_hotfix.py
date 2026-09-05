from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "# GROUNDING_AWARE_CANDIDATE_SUPPLY_V1"


PATCH = r'''

# GROUNDING_AWARE_CANDIDATE_SUPPLY_V1
# Authority: production Run 33960845940 supplied 20 aviation candidates across
# seven attempts; host canonical grounding rejected every one.  Expose the exact
# repo-owned grounding capability to the existing Explorer call without relaxing
# host validation or adding a model/network call.
from quality.grounding_aware_candidate_supply import (
    grounding_capability_context,
    grounding_candidate_capabilities,
    no_grounded_candidate_supply_result,
)

_grounding_aware_previous_build_execution_context = build_execution_context
_grounding_aware_previous_explore_candidates = explore_candidates


def build_execution_context(*args, **kwargs):
    context = _grounding_aware_previous_build_execution_context(*args, **kwargs)
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return context
    return context.rstrip() + "\n\n" + grounding_capability_context() + "\n"


def explore_candidates(*args, **kwargs):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() == "aviation":
        empty = no_grounded_candidate_supply_result()
        if empty is not None:
            print(
                "[GROUNDING_AWARE_SUPPLY] "
                "status=NO_GROUNDED_CANDIDATE_SUPPLY capabilities=0 api_calls=0"
            )
            return empty
    return _grounding_aware_previous_explore_candidates(*args, **kwargs)


CANDIDATE_EXPLORER_PROMPT += """

============================================================
16. GROUNDING-AWARE AVIATION SUPPLY — RUN 33960845940
============================================================
For aviation automatic supply, the execution context contains a compact
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
        "trusted capability constrains generation, host validation unchanged"
    )


main()

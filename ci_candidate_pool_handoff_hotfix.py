from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")
MARKER = "# CANDIDATE_POOL_HANDOFF_V1"


PATCH = r'''

# CANDIDATE_POOL_HANDOFF_V1
# Authority: Runs 33887547463 and 33893139846 both measured
# ZERO_SUPPLY=6/7 and EXPLORER_SELECTED=1/7. Move validation authority from
# model-side self-withholding to deterministic host validation without changing
# Candidate Gate or hard factual safety.
from quality.candidate_pool_handoff import handoff_candidate_pool
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)

_candidate_pool_previous_validate_explorer_output = validate_explorer_output


def _candidate_pool_host_hard_validate(candidate):
    # Existing deterministic aviation helpers only. Editorial broad/generic/
    # predictable-payoff checks intentionally remain Candidate Gate authority.
    if not aviation_scope_compatible(candidate):
        return False, "candidate drifted outside aviation scope"
    details = _aviation_detail_values(candidate)
    if not details:
        return False, "no concrete aviation specificity detail"
    if not _aviation_detail_is_referenced(candidate, details):
        return False, "concrete detail not carried by topic/question/reveal"
    if not candidate.get("visual_proof"):
        return False, "visual_proof missing"
    return True, "host hard validation PASS"


def validate_explorer_output(data):
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    status = (
        str((data or {}).get("status") or "").strip().upper()
        if isinstance(data, dict)
        else ""
    )
    if not aviation_scope or status != "CANDIDATE_POOL":
        return _candidate_pool_previous_validate_explorer_output(data)

    result = handoff_candidate_pool(
        data,
        scope="aviation",
        validate_candidate_fn=validate_candidate,
        hard_validate_fn=_candidate_pool_host_hard_validate,
        trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )
    trace = result.get("_candidate_pool_handoff") or {}
    print(
        "[CANDIDATE_POOL_HANDOFF] "
        f"status={trace.get('status')} "
        f"supplied={trace.get('supplied', len((data or {}).get('candidates') or []))} "
        f"survived={trace.get('survived', 0)}"
    )
    for item in trace.get("diagnostics") or []:
        print(
            "[CANDIDATE_POOL_ITEM] "
            f"index={item.get('index')} status={item.get('status')} "
            f"topic={item.get('topic', '')} reason={item.get('reason', '')}"
        )
    return result


CANDIDATE_EXPLORER_PROMPT += r"""

============================================================
15. AVIATION CANDIDATE POOL HANDOFF V1 — HOST AUTHORITY
============================================================
When SHORTS_CANDIDATE_SCOPE=aviation, this scoped block overrides only the
contradictory final-selection/output behavior above. #282 supply/editorial
separation and #283 observable-seed/recovery remain active.

RESPONSIBILITY:
- LLM = bounded Candidate supplier
- HOST = deterministic schema / aviation specificity / canonical grounding
- Candidate Gate = independent editorial authority

Use the existing Candidate Explorer call only. Do not request another call.
Instantiate #283 observable seeds, then return every reviewable concrete Candidate
that survives only obvious supply-time failure. Do not hide the whole pool merely
because one Candidate looks broad, generic, predictable, weak in novelty, or
editorially weak. Candidate Gate owns those editorial judgments.

SUPPLY-TIME terminal failure remains limited to:
- malformed Candidate / missing required fields
- obvious fabrication or impossible causal claim
- obvious non-aviation/off-scope Candidate

Host owns grounding sufficiency, canonical subject identity, deterministic
specificity/structure, visual-proof validation, and fail-close handling.

[POOL SIZE]
Reuse the existing shortlist ceiling: return 1..3 Candidates. Never add filler,
placeholder, fabricated provenance, or invented technical identity to reach 3.

[AVIATION PRIMARY OUTPUT]
If at least one reviewable Candidate exists, return exactly one JSON object:
{
  "status": "CANDIDATE_POOL",
  "candidates": [
    {
      "topic": "...",
      "angle": "...",
      "core_question": "...",
      "micro_narrative": {
        "hook": "...",
        "core_question": "...",
        "reveal": "...",
        "payoff": "..."
      },
      "fact_check_focus": [],
      "visual_proof": ["..."],
      "selection_reason": "...",
      "specific_observation": "...",
      "constraint": "...",
      "counterintuitive_result": "...",
      "tradeoff": "...",
      "concrete_condition": "...",
      "subject_kind": "physical_entity | non_physical_concept",
      "canonical_subject": "... | UNKNOWN | NOT_APPLICABLE",
      "subject_identity_confidence": 0.0,
      "grounding_evidence": []
    }
  ]
}
Use the existing Candidate schema and aviation specificity fields. At least one
specificity field must contain a concrete observation/constraint/result/trade-off/
condition already supported by the Candidate story.

Return REGENERATE only when reviewable supply is truly zero after the narrow
supply-time failures above. Structural/factual/grounding failures still fail
closed at host validation; no quality threshold is relaxed.
"""
'''


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("ℹ️ Candidate Pool Handoff V1 already applied")
        return
    required = (
        "AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V2",
        "AVIATION OBSERVABLE SEED SUPPLY CONTRACT",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(
            "Candidate Pool Handoff requires existing aviation contracts: "
            + ", ".join(missing)
        )
    EXPLORER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ Candidate Pool Handoff V1 installed; host validation authority active")


main()

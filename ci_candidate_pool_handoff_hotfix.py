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
    supply_trusted_subject_grounding,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
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


def _legacy_selected_supply_trusted_grounding(data):
    """Give legacy SELECTED the same repo-owned grounding supply as pool handoff.

    The legacy validator remains authoritative for schema/selection behavior. This
    helper only enriches an already validated winner from independently owned
    evidence. No model-authored evidence is promoted and no gate is relaxed.
    """
    result = _candidate_pool_previous_validate_explorer_output(data)
    if not isinstance(result, dict):
        return result
    if str(result.get("status") or "").strip().upper() != "SELECTED":
        return result
    winner = result.get("winner")
    if not isinstance(winner, dict):
        return result

    trusted_records = tuple(PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS) + tuple(
        CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    )
    supplied = supply_trusted_subject_grounding(
        winner,
        trusted_records=trusted_records,
    )
    enriched = dict(result)
    enriched["winner"] = supplied
    if supplied.get("_trusted_grounding_evidence"):
        print(
            "[LEGACY_SELECTED_GROUNDING_SUPPLY] "
            f"canonical_subject={supplied.get('canonical_subject', '')} "
            f"claims={len(supplied.get('_trusted_grounded_claims') or [])}"
        )
    return enriched


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
    if not aviation_scope:
        if status == "CANDIDATE_POOL":
            # Run 34459538824: an unrelated automatic dispatch (category=역사,
            # blank SHORTS_CANDIDATE_SCOPE) still received a CANDIDATE_POOL
            # response, because section 15 of CANDIDATE_EXPLORER_PROMPT is
            # always present regardless of runtime scope and the model does
            # not reliably gate its own output format on it. Candidate Pool
            # Handoff itself stays aviation-only exactly as before -- this
            # candidate content is never validated or accepted here, same as
            # before this fix. Only the failure mode changes: fail closed the
            # same way any other unusable Explorer response already does
            # (REGENERATE) instead of an unhandled ValueError that crashes
            # the whole production run on the very first Candidate attempt.
            return {
                "status": "REGENERATE",
                "reason": "CANDIDATE_POOL response received outside aviation scope",
            }
        return _candidate_pool_previous_validate_explorer_output(data)
    if status == "SELECTED":
        return _legacy_selected_supply_trusted_grounding(data)
    if status != "CANDIDATE_POOL":
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
        f"validated={trace.get('validated', len((data or {}).get('candidates') or []))} "
        f"survived={trace.get('survived', 0)}"
    )
    normalization = trace.get("normalization") or {}
    if normalization:
        print(
            "[CANDIDATE_POOL_NORMALIZE] "
            f"status={normalization.get('status')} "
            f"supplied={normalization.get('supplied')} "
            f"validated={normalization.get('validated')} "
            f"limit={normalization.get('limit')}"
        )
    for item in trace.get("diagnostics") or []:
        print(
            "[CANDIDATE_POOL_ITEM] "
            f"index={item.get('index')} status={item.get('status')} "
            f"topic={item.get('topic', '')} reason={item.get('reason', '')}"
        )
    return result


_AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX = r"""

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

[POOL SIZE — HARD OUTPUT CONTRACT]
The `candidates` array MUST contain 1, 2, or 3 items. This is an output contract,
not a preference. NEVER return 4 or more Candidates. Before emitting JSON, count
the array. If more than 3 reviewable Candidates exist, keep only the strongest
first 3 and delete every extra item. Do not add filler, placeholder, fabricated
provenance, or invented technical identity to reach 3.

[MICRO NARRATIVE PROGRESSION — HARD OUTPUT CONTRACT]
For every Candidate, `micro_narrative.hook` MUST be a concrete declarative first
beat already supported by that Candidate: an observable detail, concrete result,
constraint, contrast, or causal clue. It MUST NOT be a question. It MUST NOT
repeat, paraphrase, or merely restate either the top-level `core_question` or
`micro_narrative.core_question`. The first two beats must advance information:
HOOK = concrete observation/result/constraint; CORE QUESTION = ask why/how that
observation exists. Do not turn "왜 X인가?" into "X는 왜 그럴까?" and call it a
new Hook. Do not invent a new fact to satisfy this rule; if no grounded concrete
first beat exists, omit that Candidate from the supplied pool.

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
        "hook": "구체 관찰/결과/제약을 말하는 서술문. 질문 재진술 금지.",
        "core_question": "왜/어떻게를 묻는 하나의 중심 질문",
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

CANDIDATE_EXPLORER_PROMPT += _AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX


# RUN_34686824352_AVIATION_PROMPT_SCOPE_V1
# Run 34686824352 (automatic-topic mode, blank SHORTS_CANDIDATE_SCOPE) showed
# section 15 above is always present in the system prompt regardless of the
# runtime scope, and the model does not reliably gate its own output format on
# the in-prompt "When SHORTS_CANDIDATE_SCOPE=aviation" instruction alone -- 5 of
# 7 Candidate attempts returned a CANDIDATE_POOL envelope for ordinary
# non-aviation topics (desert ant navigation was one of only two attempts that
# reached a real topic at all), each one an automatic REGENERATE that spent a
# bounded attempt without ever reaching Candidate Gate. This does not touch
# CANDIDATE_POOL parsing/validation at all -- that stays aviation-only exactly
# as installed above, and a CANDIDATE_POOL envelope outside aviation scope still
# fails closed to REGENERATE if the model returns one anyway. It only stops
# teaching the model that output shape when the run cannot use it, by keeping
# section 15 out of the system prompt for that one call.
_candidate_pool_scope_previous_explore_candidates = explore_candidates


def explore_candidates(*args, **kwargs):
    global CANDIDATE_EXPLORER_PROMPT
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    if aviation_scope:
        return _candidate_pool_scope_previous_explore_candidates(*args, **kwargs)
    original_prompt = CANDIDATE_EXPLORER_PROMPT
    if _AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX in original_prompt:
        # Later hotfixes append more prompt text after section 15, so this
        # cannot assume the appendix is the current suffix -- remove exactly
        # that substring (first occurrence) wherever it now sits and leave
        # everything appended before/after it untouched.
        CANDIDATE_EXPLORER_PROMPT = original_prompt.replace(
            _AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX, "", 1
        )
    try:
        return _candidate_pool_scope_previous_explore_candidates(*args, **kwargs)
    finally:
        CANDIDATE_EXPLORER_PROMPT = original_prompt
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

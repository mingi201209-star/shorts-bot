from pathlib import Path


RUNNER = Path("content/script_engine_v2_runner.py")
MARKER = "# RUN_34753759233_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1"


runner = RUNNER.read_text(encoding="utf-8")
if MARKER not in runner:
    anchor = "def _owned_claim_keyword_terms(contract):"
    if anchor not in runner:
        raise RuntimeError(
            "Run 34753759233 scene-role grounded keyword: "
            "_owned_claim_keyword_terms anchor not found "
            "(ci_grounded_keyword_contract_hotfix.py must run first)"
        )

    runner = runner.rstrip() + "\n\n\n" + MARKER + r'''
# Run 34753759233 (fixed-topic "착륙 직후 날개 위로 솟는 스포일러", exact main
# 65f6f5e0815e5c24c858fb5ec659b69e662d83d3, immediately after #360/#361
# landed): PR #360/#361 fixed literal spoiler grounding at the Candidate
# Pool/pre-Writer boundary; this run then proved a *separate* bug exposed
# only once that fix worked. `owned_claim_id` values like
# "spoiler_weight_to_wheels" and "spoiler_braking_effectiveness" are
# causal-LINEAGE labels ("this result claim descends from the spoiler
# claim"), not a promise that this specific Scene's own narration/
# visual_goal shows the spoiler. `_owned_claim_keyword_terms` previously
# tokenized `owned_claim_id` unconditionally, so "spoiler" leaked into
# Scene 4/5's retrieval keyword even though neither Scene's narration nor
# visual_goal ever names it. The retrieval/proof layer
# (video_downloader.extract_query_anchors + concrete_visual_evidence) then
# treats any component word present in the query text as a hard 3/3
# visual-proof requirement, so Scene 4/5 rejected every real aircraft+wing
# "result" stock candidate as cross-domain and ultimately exhausted every
# fallback, crashing production.
#
# Fix: a concrete physical-component word (the same closed vocabulary the
# visual retrieval layer treats as a hard anchor) sourced only from
# `owned_claim_id` is no longer trusted as claim-specific keyword content
# unless the claim's own descriptive text (supporting_evidence_summary /
# allowed_paraphrase_scope / required_concepts) independently repeats it.
# Non-component id tokens (e.g. "weight", "wheel", "braking",
# "effectiveness") are unaffected and remain useful retrieval hints; a
# Scene whose own descriptive content genuinely discusses the component
# (e.g. Scene 3's spoiler/airflow-disruption mechanism) keeps it. This
# generalizes to any future component-named claim id (flap_*, chevron_*,
# landing_gear_*, ...): only descriptive Scene content can promote a
# physical component into the retrieval keyword, never a bookkeeping
# lineage label. No API/retry/budget/threshold change.
_RUN_34753759233_PHYSICAL_COMPONENT_TERMS = {
    "aircraft", "wing", "window", "cabin", "engine", "spinner",
    "bridge", "tunnel", "road", "building", "chevron", "flap",
    "spoiler", "speedbrake", "winglet", "wingtip",
}

_run_34753759233_previous_owned_claim_keyword_terms = _owned_claim_keyword_terms


def _owned_claim_keyword_terms(contract):
    contract = contract if isinstance(contract, dict) else {}
    id_terms = _grounded_keyword_terms(
        str(contract.get("owned_claim_id") or "").replace("_", " ")
    )
    content_values = [str(contract.get("supporting_evidence_summary") or "")]
    content_values.extend(
        str(item) for item in contract.get("allowed_paraphrase_scope") or [] if item
    )
    content_values.extend(
        str(item) for item in contract.get("required_concepts") or [] if item
    )
    content_terms = []
    for value in content_values:
        for term in _grounded_keyword_terms(value):
            if term not in content_terms:
                content_terms.append(term)

    result = []
    for term in id_terms:
        if term in _RUN_34753759233_PHYSICAL_COMPONENT_TERMS and term not in content_terms:
            continue
        if term not in result:
            result.append(term)
    for term in content_terms:
        if term not in result:
            result.append(term)
    return result
''' + "\n"
    RUNNER.write_text(runner, encoding="utf-8")
    print("✅ Run 34753759233 scene-role grounded keyword applied: claim-id component leakage closed")
else:
    print("✅ Run 34753759233 scene-role grounded keyword already installed")

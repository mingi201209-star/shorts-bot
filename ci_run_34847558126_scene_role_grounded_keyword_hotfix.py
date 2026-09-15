from pathlib import Path


RUNNER = Path("content/script_engine_v2_runner.py")
MARKER = "# RUN_34847558126_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1"


runner = RUNNER.read_text(encoding="utf-8")
if MARKER not in runner:
    anchor = "def _owned_claim_keyword_terms(contract):"
    if anchor not in runner:
        raise RuntimeError(
            "Run 34847558126 scene-role grounded keyword: "
            "_owned_claim_keyword_terms anchor not found "
            "(ci_grounded_keyword_contract_hotfix.py must run first)"
        )

    runner = runner.rstrip() + "\n\n\n" + MARKER + r'''
# Run 34847558126 (Shorts Generator on publish-stable, dispatched from
# Publish Stable Engine run 34847540739, exact main
# 91002ebcc24a8fe201f931f95def45c0a5014bf9) re-proved the exact
# 34753759233/PR#362 regression: this repository's grounded-keyword builder
# reverted to its pre-fix form (the PR #362 hotfix that wrapped
# `_owned_claim_keyword_terms` is no longer wired into main.yml), so
# `owned_claim_id` values like "spoiler_weight_to_wheels" leaked "spoiler"
# back into Scene 4's retrieval keyword ("aircraft wing spoiler weight
# wheel") even though neither its narration ("착륙 뒤 양력을 없애면 항공기
# 무게가 바퀴에 더 실립니다") nor its visual_goal ("무게가 바퀴에 실리는
# 모습") ever names it. Every real aircraft+wing candidate was rejected as
# cross-domain (GENERAL_VISUAL_REJECT anchors=aircraft+wing+spoiler), the
# still-generation budget exhausted, and the scene fell to a WINGLET_FLOW
# explanatory diagram -- the wrong component family for a weight-transfer
# result scene with no winglet/spoiler visual promise at all.
#
# owned_claim_id is a causal-LINEAGE label ("this result claim descends
# from the spoiler claim"), not a promise that this specific Scene's own
# narration/visual_goal shows the spoiler. Fix: a concrete physical-
# component word sourced only from owned_claim_id is no longer trusted as
# claim-specific keyword content unless the claim's own descriptive text
# (supporting_evidence_summary / allowed_paraphrase_scope /
# required_concepts) independently repeats it. Non-component id tokens
# (e.g. "weight", "wheel", "braking", "effectiveness") are unaffected and
# remain useful retrieval hints; a Scene whose own descriptive content
# genuinely discusses the component (a direct spoiler-deployment mechanism
# Scene) keeps it. Generalizes to any future component-named claim id
# (flap_*, chevron_*, landing_gear_*, ...). No API/retry/budget/threshold
# change.
_RUN_34847558126_PHYSICAL_COMPONENT_TERMS = {
    "aircraft", "wing", "window", "cabin", "engine", "spinner",
    "bridge", "tunnel", "road", "building", "chevron", "flap",
    "spoiler", "speedbrake", "winglet", "wingtip",
}

_run_34847558126_previous_owned_claim_keyword_terms = _owned_claim_keyword_terms


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
        if term in _RUN_34847558126_PHYSICAL_COMPONENT_TERMS and term not in content_terms:
            continue
        if term not in result:
            result.append(term)
    for term in content_terms:
        if term not in result:
            result.append(term)
    return result
''' + "\n"
    RUNNER.write_text(runner, encoding="utf-8")
    print("✅ Run 34847558126 scene-role grounded keyword applied: claim-id component leakage closed")
else:
    print("✅ Run 34847558126 scene-role grounded keyword already installed")

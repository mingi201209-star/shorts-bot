"""Regression for `quality/production_hotfix_execution_order.py`.

Authority: this session's investigation (2026-09-19) found that
`PRODUCTION_HOTFIX_CHAIN` (47 distinct files) is not the full set of
hotfixes the production chain executes. Several listed hotfixes pull in
further hotfixes as a side effect of running -- through plain `import`,
`runpy.run_path(...)`, and `exec(compile(Path(...).read_text(), ...))` --
and NONE of those were covered by
`production_hotfix_chain_structure_regression_test.py`'s "exactly 48
entries" check, which only ever looked at the list itself.

Verified against `main` HEAD `eab97f8598e1df24f6dc967a8607c41f835a7eac`:
the chain's 47 listed files actually execute 111 distinct files, 64 of
which are never named in `PRODUCTION_HOTFIX_CHAIN` at all.

CASE A pins the exact set (protects against silent drift the same way the
existing 48-entry test protects the list itself -- a hidden hotfix's
change is now something a reviewer can be shown, not something that stays
invisible). CASE B is a basic sanity check that every listed chain entry
is itself part of what gets executed. CASE C asserts every traced file
actually exists on disk.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.production_hotfix_chain import PRODUCTION_HOTFIX_CHAIN  # noqa: E402
from quality.production_hotfix_execution_order import distinct_files  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pinned 2026-09-19 against main HEAD eab97f8. Update this list (and the
# investigation note above) in the same PR that intentionally changes what
# the chain executes -- do not update it to silence an unexpected diff
# without first confirming the diff is intended.
EXPECTED_EXECUTION_ORDER = [
    'ci_hotfix.py',
    'ci_novelty_budget_hotfix.py',
    'ci_fact_critical_hotfix.py',
    'ci_speech_style_hotfix.py',
    'ci_hook_generation_hotfix.py',
    'ci_narrative_reveal_contract_hotfix.py',
    'ci_script_local_formal_repair_hotfix.py',
    'ci_hook_pool_guard_hotfix.py',
    'ci_hook_retry_repair_hotfix.py',
    'ci_hook_structure_guidance_hotfix.py',
    'ci_observable_statement_hook_hotfix.py',
    'ci_retention_hotfix.py',
    'ci_first5_retention_tts_hotfix.py',
    'ci_first5_visual_contract_hotfix.py',
    'ci_video_provider_hotfix.py',
    'ci_topic_input_hotfix.py',
    'ci_fixed_topic_gate_advisory_hotfix.py',
    'ci_aviation_candidate_context_hotfix.py',
    'ci_aviation_candidate_specificity_hotfix.py',
    'ci_aviation_context_signature_compat_hotfix.py',
    'ci_fixed_aviation_scope_contract_hotfix.py',
    'ci_run_34825745612_legacy_hook_repair_hotfix.py',
    'ci_fixed_topic_runtime_call_compat_hotfix.py',
    'ci_run_33691170895_term_visual_subject_hotfix.py',
    'ci_run_34682392892_human_visual_progression_hotfix.py',
    'ci_script_scene_local_recovery_hotfix.py',
    'ci_aviation_specificity_output_repair_hotfix.py',
    'ci_aviation_specificity_projection_hotfix.py',
    'ci_candidate_pool_handoff_hotfix.py',
    'ci_grounding_aware_candidate_supply_hotfix.py',
    'ci_run_34708987774_grounded_seed_identity_hotfix.py',
    'ci_candidate_grounded_recovery_hotfix.py',
    'ci_candidate_supply_recovery_hotfix.py',
    'ci_canonical_subject_grounding_hotfix.py',
    'ci_canonical_subject_grounding_supply_hotfix.py',
    'ci_flap_canonical_grounding_hotfix.py',
    'ci_prewriter_grounding_resupply_hotfix.py',
    'ci_static_wick_canonical_grounding_hotfix.py',
    'ci_growth_candidate_shadow_hotfix.py',
    'ci_run_35065228877_bounded_supply_authority_hotfix.py',
    'ci_final_render_content_integrity_hotfix.py',
    'ci_output_quality_hotfix.py',
    'ci_curiosity_retention_hotfix.py',
    'ci_visual_specificity_hotfix.py',
    'ci_design_causality_hotfix.py',
    'ci_query_semantic_integrity_hotfix.py',
    'ci_concrete_visual_evidence_hotfix.py',
    'ci_visible_evidence_provenance_hotfix.py',
    'ci_hook_production_parity_hotfix.py',
    'ci_hook_fallback_quality_floor_hotfix.py',
    'ci_ai_visual_fallback_hotfix.py',
    'ci_ai_visual_mechanism_fallback_hotfix.py',
    'ci_problem_solution_narrative_hotfix.py',
    'ci_causal_information_progression_hotfix.py',
    'ci_retention_structure_experiment_hotfix.py',
    'ci_subscriber_conversion_hotfix.py',
    'ci_script_production_parity_hotfix.py',
    'ci_script_production_parity_bridge_hotfix.py',
    'ci_adaptive_scene_count_hotfix.py',
    'ci_general_scene_visual_parity_hotfix.py',
    'ci_script_validation_recovery_hotfix.py',
    'ci_script_v2_visual_goal_hotfix.py',
    'ci_run_34847558126_fixed_topic_novelty_weak_domain_hotfix.py',
    'ci_script_v2_gunggeum_formal_ending_hotfix.py',
    'ci_writer_audience_comprehension_hotfix.py',
    'ci_final_visual_semantic_qa_hotfix.py',
    'ci_still_action_gate_hotfix.py',
    'ci_still_image_verifier_contract_hotfix.py',
    'ci_still_vision_evidence_groups_hotfix.py',
    'ci_still_vision_evidence_trace_hotfix.py',
    'ci_early_verified_asset_presentation_hotfix.py',
    'ci_run_33371268494_scene2_verified_subject_reuse_hotfix.py',
    'ci_run_33377519851_scene1_viewpoint_structure_hotfix.py',
    'ci_run_33506951642_still_generation_response_hotfix.py',
    'ci_still_parent_domain_propagation_hotfix.py',
    'ci_cross_process_video_dedupe_hotfix.py',
    'ci_candidate_competition_completion_hotfix.py',
    'ci_grounded_causal_contrast_hotfix.py',
    'ci_grounded_causal_role_hotfix.py',
    'ci_grounded_claim_plan_hotfix.py',
    'ci_grounded_explanatory_visual_supply_hotfix.py',
    'ci_visual_explanation_retrieval_v1_hotfix.py',
    'ci_grounded_keyword_contract_hotfix.py',
    'ci_live_script_blockers_hotfix.py',
    'ci_noise_reduction_result_visual_hotfix.py',
    'ci_run_33245676515_script_contract_hotfix.py',
    'ci_subtitle_director_completion_hotfix.py',
    'ci_visual_diversity_preflight_hotfix.py',
    'ci_visual_quality_v1_completion_hotfix.py',
    'ci_visual_quality_v1_hotfix.py',
    'ci_visual_subject_anchor_contract_v1_completion_hotfix.py',
    'ci_visual_subject_anchor_contract_v2_hotfix.py',
    'ci_canonical_visual_supply_contract_hotfix.py',
    'ci_visual_claim_semantic_fallback_hotfix.py',
    'ci_visual_subject_anchor_fallback_inheritance_hotfix.py',
    'ci_visual_subject_anchor_contract_v1_hotfix.py',
    'ci_writer_compliance_plan_hotfix.py',
    'ci_run_34847558126_scene_role_grounded_keyword_hotfix.py',
    'ci_writer_observable_opening_hotfix.py',
    'ci_run_33977099845_verified_still_rescue_hotfix.py',
    'ci_run_33981204957_flap_director_repair_hotfix.py',
    'ci_static_wick_fallback_provenance_hotfix.py',
    'ci_static_wick_local_visual_handoff_hotfix.py',
    'ci_static_wick_visual_explanation_hotfix.py',
    'ci_run_34645762458_candidate_feedback_hotfix.py',
    'ci_run_34663907508_human_qa_escape_hotfix.py',
    'ci_run_34671707523_opening_candidate_recovery_hotfix.py',
    'ci_run_34672661458_hook_floor_feedback_hotfix.py',
    'ci_good_enough_present_domains_hotfix.py',
    'ci_run_34676516725_fixed_topic_hook_body_reuse_hotfix.py',
    'ci_grounded_deterministic_explanation_hotfix.py',
]


def case_a_pinned_execution_order_unchanged():
    actual = distinct_files(PRODUCTION_HOTFIX_CHAIN)
    assert actual == EXPECTED_EXECUTION_ORDER, (
        "the chain's actual execution order changed -- if this is an "
        "intended change (a hotfix's chaining was added/removed/reordered), "
        "update EXPECTED_EXECUTION_ORDER above in the same PR; otherwise "
        "this is an unreviewed change to what production actually runs.\n"
        f"expected {len(EXPECTED_EXECUTION_ORDER)} files, got {len(actual)}.\n"
        f"added: {sorted(set(actual) - set(EXPECTED_EXECUTION_ORDER))}\n"
        f"removed: {sorted(set(EXPECTED_EXECUTION_ORDER) - set(actual))}"
    )
    print(
        f"CASE A pinned execution order ({len(EXPECTED_EXECUTION_ORDER)} "
        "files) unchanged: PASS"
    )


def case_b_every_listed_entry_is_executed():
    actual = set(distinct_files(PRODUCTION_HOTFIX_CHAIN))
    missing = [entry for entry in set(PRODUCTION_HOTFIX_CHAIN) if entry not in actual]
    assert not missing, (
        f"entries listed in PRODUCTION_HOTFIX_CHAIN were not found in their "
        f"own traced execution (should be impossible): {missing}"
    )
    print("CASE B every PRODUCTION_HOTFIX_CHAIN entry is part of its own execution: PASS")


def case_c_every_executed_file_exists():
    from pathlib import Path

    root = Path(ROOT)
    missing = [name for name in EXPECTED_EXECUTION_ORDER if not (root / name).is_file()]
    assert not missing, f"pinned execution order names files that don't exist: {missing}"
    print("CASE C every file in the pinned execution order exists on disk: PASS")


def main():
    case_a_pinned_execution_order_unchanged()
    case_b_every_listed_entry_is_executed()
    case_c_every_executed_file_exists()
    hidden = [f for f in EXPECTED_EXECUTION_ORDER if f not in PRODUCTION_HOTFIX_CHAIN]
    print(
        f"production hotfix execution order regression: PASS "
        f"({len(EXPECTED_EXECUTION_ORDER)} files executed, "
        f"{len(hidden)} not directly listed in PRODUCTION_HOTFIX_CHAIN)"
    )


if __name__ == "__main__":
    main()

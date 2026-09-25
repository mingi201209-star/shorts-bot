"""Single source of truth for the production hotfix apply order.

Authority: this session's Publish Engine Stabilization V1 investigation
found three mutually inconsistent copies of "the production hotfix chain"
already living in this repo at once -- `.github/workflows/main.yml`'s
"Apply production hotfixes" step (the one that actually runs in
production), `.github/workflows/production_hotfix_composition_gate.yml`'s
own hand-maintained copy (diverges from `main.yml` at index 46: it runs
`ci_run_33977099845_verified_still_rescue_hotfix.py` where `main.yml` runs
`ci_grounded_deterministic_explanation_hotfix.py` -- a different hotfix
entirely), and `quality/script_human_quality_v1_regression_test.py`'s
`_PRODUCTION_HOTFIX_CHAIN` (4 hotfixes short of the real chain, dropping two
different files than the composition gate's own divergence). None of the
three protected against the others drifting.

This list is verified directly against `main` HEAD
`b84a567382720909aee80131812495a822f2ff5b`
(`.github/workflows/main.yml`'s "Apply production hotfixes" step). It is now
the one place the chain is defined; `main.yml`,
`production_hotfix_composition_gate.yml`, and
`script_human_quality_v1_regression_test.py` all read this list (the two
workflows via `quality/apply_production_hotfix_chain.py`, the test via a
plain Python import) instead of each hard-coding their own copy.

All indices below are 0-based, matching this list's own indexing.

`ci_aviation_context_signature_compat_hotfix.py` is intentionally applied
TWICE -- once at index 13 and again as the final entry (index
`len(PRODUCTION_HOTFIX_CHAIN) - 1`) -- because later hotfixes in the chain
rewrite the `content/candidate_explorer.py` wrappers it patches, so it must
be re-applied against the final composed state. This is documented,
required behavior, not a bug; see the ordering comment inline below and
`quality/production_hotfix_chain_structure_regression_test.py`, which
asserts this exact shape.

IMPORTANT -- this "exactly 49 entries, exactly one intentional duplicate"
shape is a PRE-CONSOLIDATION invariant, not a permanent production
requirement. Publish Engine Stabilization V1's Phase 3 absorbs these
hotfixes into checked-in source, which shrinks this list by design. When
that happens, update (or retire) this module and its structural regression
test in the same cluster PR that does the absorbing -- do not let the old
structural test turn a successful consolidation into an apparent
regression.
"""

PRODUCTION_HOTFIX_CHAIN = [
    "ci_hotfix.py",
    "ci_novelty_budget_hotfix.py",
    "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py",
    "ci_first5_retention_tts_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_aviation_candidate_specificity_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",  # index 13: first application
    "ci_aviation_specificity_output_repair_hotfix.py",
    "ci_aviation_specificity_projection_hotfix.py",
    "ci_candidate_grounded_recovery_hotfix.py",
    "ci_growth_candidate_shadow_hotfix.py",
    "ci_final_render_content_integrity_hotfix.py",
    "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py",
    "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py",
    "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py",
    "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py",
    "ci_hook_fallback_quality_floor_hotfix.py",
    "ci_ai_visual_fallback_hotfix.py",
    "ci_ai_visual_mechanism_fallback_hotfix.py",
    "ci_problem_solution_narrative_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_retention_structure_experiment_hotfix.py",
    "ci_subscriber_conversion_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
    "ci_general_scene_visual_parity_hotfix.py",
    "ci_script_validation_recovery_hotfix.py",
    "ci_script_v2_visual_goal_hotfix.py",
    # Must run immediately after ci_script_v2_visual_goal_hotfix.py: it
    # patches build_consensus's return statement, which that hotfix's
    # _apply_fixed_topic_soft_judges leaves untouched, and it reads the
    # `fixed_topic` local variable that hotfix installs.
    "ci_run_34847558126_fixed_topic_novelty_weak_domain_hotfix.py",
    "ci_script_v2_gunggeum_formal_ending_hotfix.py",
    "ci_final_visual_semantic_qa_hotfix.py",
    "ci_visual_diversity_preflight_hotfix.py",
    "ci_cross_process_video_dedupe_hotfix.py",
    # Must run after ci_cross_process_video_dedupe_hotfix.py: it chains in
    # ci_grounded_keyword_contract_hotfix.py, and this hotfix wraps that
    # hotfix's _owned_claim_keyword_terms function.
    "ci_run_34847558126_scene_role_grounded_keyword_hotfix.py",
    "ci_writer_observable_opening_hotfix.py",
    # Must run after ci_writer_observable_opening_hotfix.py: it chains in
    # the last upstream video/visual_explanation.py wrapper layer
    # (STATIC_WICK_VISUAL_EXPLANATION_V1) that this hotfix wraps.
    "ci_grounded_deterministic_explanation_hotfix.py",
    # Some later production hotfixes rewrite candidate_explorer wrappers.
    # Re-apply the compatibility patch against the FINAL production state.
    "ci_aviation_context_signature_compat_hotfix.py",  # index 48 (last): second, intentional application
]

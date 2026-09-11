"""Authority regression for Run 34596419083, Scene 4 (topic "비행기 창문 모서리는
왜 둥글까", keyword "modern aircraft window rounded stress distribution").

RED authority (Run 34596419083, exact main f187a906cae782562a17c85dec6ae20940fb9e4f):

    [VISION_EVIDENCE_TRACE] pass=True required_subject_groups=aircraft+window
        visible_subject_groups={'aircraft': False, 'window': False}
        visible_components=aircraft window+clouds+sky
        parent_domain_satisfied=none missing=aircraft
        schema_parser_consistency=False result=REJECT
        reason=The rounded aircraft window is clearly visible, with stress
        distribution arrows effectively shown, matching the hook's promise.

    RuntimeError: 영상 후보가 없고 검증된 정지 이미지/설명 visual fallback도
    실패했습니다: modern aircraft window rounded stress distribution

Audit findings (all six required checks from the task):

1. Not a Vision model schema inconsistency: the model's own reason text and
   its own explicit visible_subject_groups dict were internally coherent
   with what it reported seeing ("aircraft window" clearly visible).
2. Root cause IS a parser/normalizer misinterpretation:
   _still_vision_component_matches_group() in this file's patch to
   video/hook_visual_dominance.py required an EXACT whole-string match
   between a visible_components entry and each required group name (with a
   pre-defined alias set for "engine"/"chevron" only -- never "aircraft" or
   "window"). The model returned "aircraft window" as ONE compound
   visible_components entry (a natural, reasonable description), so it
   matched neither "aircraft" nor "window" exactly, even though both exact
   required words are literally present as whitespace-delimited tokens.
3. No information was lost during generation or structured-groups
   construction: the same function already tokenizes visible_components
   into `visible_words` (used only as a fallback for anchors ABSENT from
   the structured dict) -- the tokens were computed, just never consulted
   for a required group that already has a (wrongly False) dict entry.
4. Scene 3's verified/cached still was correctly NOT reused for Scene 4:
   the real log's call=9 Vision re-verification of the reused cached image
   returned pass=False, reason="The window is visible but lacks the
   promised stress distribution action and is not dominant" -- Scene 4
   requires a materially different visual (stress-distribution arrows),
   so the cache miss is a legitimate, unrelated fail-close, not a caching
   bug.
5. Budget exhaustion is exactly as designed: STILL_IMAGE_MAX_PER_VIDEO=2 is
   a whole-VIDEO (not per-scene) cap. Scene 3 consumed slot 1 (succeeded).
   Scene 4's own new generation consumed slot 2 -- and was wrongly rejected
   by the bug in point 2, exhausting the budget with no code defect in the
   budget accounting itself.
6. VisualExplanation's "unsupported_or_fact_unsafe" is correct, unrelated
   by-design behavior: annotation_fact_safe() gates that fallback to
   winglet-vortex/airflow/fuel-efficiency scenes only (_winglet_subject());
   an aircraft-window-corner scene is legitimately out of its scope.

Fix (point 2 only): _still_vision_component_matches_group() now also
credits a group when its own exact word appears as a whitespace-delimited
token inside a multi-word component phrase. This is not new alias/
vocabulary leniency (no new words are treated as equivalent to a required
group) and does not touch schema_parser_consistency's own pass/fail rule,
the dominance/subject-visibility thresholds, retry counts, budget caps, or
any exception handling.
"""

from __future__ import annotations

import subprocess
import sys


def _apply_relevant_hotfixes():
    """Full exact main.yml chain through the entry point that reaches the
    still-vision structured-evidence layer, matching real production exactly."""
    chain = (
        "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
        "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py",
        "ci_hook_pool_guard_hotfix.py", "ci_retention_hotfix.py",
        "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
        "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py",
        "ci_aviation_candidate_context_hotfix.py",
        "ci_aviation_candidate_specificity_hotfix.py",
        "ci_aviation_context_signature_compat_hotfix.py",
        "ci_aviation_specificity_output_repair_hotfix.py",
        "ci_aviation_specificity_projection_hotfix.py",
        "ci_candidate_grounded_recovery_hotfix.py", "ci_growth_candidate_shadow_hotfix.py",
        "ci_final_render_content_integrity_hotfix.py", "ci_output_quality_hotfix.py",
        "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py",
        "ci_design_causality_hotfix.py", "ci_query_semantic_integrity_hotfix.py",
        "ci_concrete_visual_evidence_hotfix.py", "ci_visible_evidence_provenance_hotfix.py",
        "ci_hook_production_parity_hotfix.py", "ci_hook_fallback_quality_floor_hotfix.py",
        "ci_ai_visual_fallback_hotfix.py", "ci_ai_visual_mechanism_fallback_hotfix.py",
        "ci_problem_solution_narrative_hotfix.py",
        "ci_causal_information_progression_hotfix.py",
        "ci_retention_structure_experiment_hotfix.py", "ci_subscriber_conversion_hotfix.py",
        "ci_script_production_parity_hotfix.py",
        "ci_script_production_parity_bridge_hotfix.py", "ci_adaptive_scene_count_hotfix.py",
        "ci_general_scene_visual_parity_hotfix.py", "ci_script_validation_recovery_hotfix.py",
        "ci_script_v2_visual_goal_hotfix.py", "ci_script_v2_gunggeum_formal_ending_hotfix.py",
        "ci_final_visual_semantic_qa_hotfix.py", "ci_cross_process_video_dedupe_hotfix.py",
        "ci_writer_observable_opening_hotfix.py",
    )
    for script in chain:
        subprocess.run([sys.executable, script], check=True)


def main():
    _apply_relevant_hotfixes()

    import video.hook_visual_dominance as hvd

    required_groups = ["aircraft", "window"]

    # RED -> GREEN: exact Run 34596419083 Scene 4 counterexample.
    positive_payload = {
        "visible_components": ["aircraft window", "clouds", "sky"],
        "visible_subject_groups": {"aircraft": True, "window": True},
        "reason": (
            "The rounded aircraft window is clearly visible, with stress "
            "distribution arrows effectively shown, matching the hook's promise."
        ),
    }
    result = hvd._still_vision_apply_structured_evidence(
        {"pass": True}, positive_payload, required_groups
    )
    assert result["visible_subject_groups"] == {"aircraft": True, "window": True}, (
        result["visible_subject_groups"]
    )
    assert result["schema_parser_consistency"] is True, result["evidence_inconsistencies"]

    # Negative control: model explicitly denies a group; an unrelated
    # compound component sharing no token must not resurrect it.
    result = hvd._still_vision_apply_structured_evidence(
        {"pass": True},
        {
            "visible_components": ["car window", "road"],
            "visible_subject_groups": {"aircraft": False, "window": True},
            "reason": "A car window is visible but no aircraft is present.",
        },
        ["aircraft", "window"],
    )
    assert result["visible_subject_groups"]["aircraft"] is False, result["visible_subject_groups"]

    # Negative control: group word genuinely absent from every component,
    # even though the model's explicit dict wrongly claims it -- stays
    # unmatched and still flags the inconsistency (schema_parser_consistency
    # is not weakened).
    result = hvd._still_vision_apply_structured_evidence(
        {"pass": True},
        {
            "visible_components": ["car window", "road", "trees"],
            "visible_subject_groups": {"aircraft": True},
            "reason": "aircraft is somehow claimed but nothing shows it",
        },
        ["aircraft"],
    )
    assert result["visible_subject_groups"]["aircraft"] is False, result["visible_subject_groups"]
    assert result["schema_parser_consistency"] is False, result["evidence_inconsistencies"]

    # Regression: existing engine/chevron alias behavior is untouched.
    result = hvd._still_vision_apply_structured_evidence(
        {"pass": True},
        {
            "visible_components": ["jet engine", "wing"],
            "visible_subject_groups": {"engine": False},
            "reason": "a jet engine is visible",
        },
        ["engine"],
    )
    assert result["visible_subject_groups"]["engine"] is True, result["visible_subject_groups"]

    result = hvd._still_vision_apply_structured_evidence(
        {"pass": True},
        {
            "visible_components": ["wing", "engine"],
            "visible_subject_groups": {"chevron": False},
            "reason": "no chevron visible",
        },
        ["chevron"],
    )
    assert result["visible_subject_groups"]["chevron"] is False, (
        "wing/engine must never count as chevron evidence: " + str(result["visible_subject_groups"])
    )

    # Safety invariants: no threshold/budget/retry surface touched by this fix.
    hotfix_source = open(
        "ci_still_vision_evidence_groups_hotfix.py", encoding="utf-8"
    ).read()
    for forbidden in (
        "STILL_IMAGE_MAX_PER_VIDEO =",
        "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO =",
        "subject_visibility\", 0",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
        "except Exception",
    ):
        assert forbidden not in hotfix_source, forbidden

    print(
        "RUN 34596419083 STILL VISION COMPOUND COMPONENT REGRESSION: PASS "
        "(compound-phrase token credit fixed, no threshold/budget/retry change, "
        "no alias-table widening, no fail-open)"
    )


if __name__ == "__main__":
    main()

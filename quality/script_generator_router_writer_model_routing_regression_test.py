"""Authority regression for Run 34539602721: the production Script Writer
call silently used the cheap model instead of the premium production model.

RED authority (Run 34539602721, exact main ff932d911ede20ee8e2aa74f191899ccab44f7c6):
- [API_MODEL_ROUTE] call=5 model=gpt-4o-mini -- immediately followed by
  [GROUNDED_KEYWORD_TRACE]/[WRITER_COMPLIANCE_TRACE] confirming this was the
  Script Engine V2 Writer's first (and only) writer call for that run.
  Every one of the run's 9 API calls logged model=gpt-4o-mini; model=gpt-5.6-sol
  never appeared once.

Root cause: content/script_engine_v2_runner.py::_default_call() (the checked-in
version) correctly resolves `_model_for_mode(mode)` -> WRITER_MODEL for
"writer" / REPAIR_MODEL for "local_repair". But four production hotfixes --
ci_writer_compliance_plan_hotfix.py, ci_grounded_claim_plan_hotfix.py,
ci_grounded_causal_role_hotfix.py, ci_grounded_causal_contrast_hotfix.py
(all chain-imported by ci_cross_process_video_dedupe_hotfix.py, itself part
of the real .github/workflows/main.yml "Apply production hotfixes" step) --
each append their OWN _default_call() to that same file. Every one of those
overrides hardcodes the plain module-level MODEL constant (the cheap
default) directly in its openai.chat.completions.create(model=MODEL, ...)
call and its authorize_call(MODEL) call, for BOTH "writer" and
"local_repair" modes, whenever the payload carries a grounded_claim_plan /
grounded_claim_mode key -- which current production writer_payload() /
local_repair_payload() output always does. These four hotfixes predate the
#312 writer/repair model separation and were never updated to route through
_model_for_mode()/WRITER_MODEL/REPAIR_MODEL, so applying them (as every real
production run does) silently regressed the Writer call back to the cheap
model.

Why quality/production_model_routing_composition_regression_test.py missed
this: it re-checks only the WRITER_MODEL *constant* after the exact hotfix
chain (which does still correctly resolve to "gpt-5.6-sol" -- config.py's
env-gate is untouched by any of this) and the import wiring (main.py ->
router -> runner). It never exercises an actual writer-mode call through
the fully hotfix-composed _default_call(), so it could not see that none of
these hotfix overrides ever reads that constant in the first place.

Fix location: content/script_generator_router.py::_resilient_v2_call(),
NOT any of the four hotfix files or content/script_engine_v2_runner.py
itself. Every one of those hotfix overrides resolves `model=MODEL` as a
late-bound lookup of content.script_engine_v2_runner's own MODEL attribute
at call time; temporarily aliasing that attribute to WRITER_MODEL for the
exact duration of a "writer" call (restored in a finally block immediately
after) routes whichever hotfix-appended _default_call ends up executing
through the correct model -- current chain and any future hotfix following
the same model=MODEL pattern -- without touching any hotfix file or the
hotfix-mutated runner file. No extra API call, no threshold/budget/retry
change: the same single call now authorizes and requests the right model.
"""

from __future__ import annotations

import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

PRODUCTION_HOTFIX_CHAIN = (
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
    "ci_aviation_context_signature_compat_hotfix.py",
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
    "ci_script_v2_gunggeum_formal_ending_hotfix.py",
    "ci_final_visual_semantic_qa_hotfix.py",
    "ci_cross_process_video_dedupe_hotfix.py",
    "ci_writer_observable_opening_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
)


def _apply_production_hotfix_chain():
    """Apply the exact .github/workflows/main.yml hotfix chain so
    content/script_engine_v2_runner.py carries the same _default_call
    override stack a real production run does -- required to reproduce
    this bug at all; the checked-in (un-hotfixed) _default_call is
    already correct.
    """
    for script in PRODUCTION_HOTFIX_CHAIN:
        subprocess.run([sys.executable, script], check=True)


def _fake_response():
    content = (
        '{"title": "t", "scenes": [{"text": "x", "visual_goal": "y", "keyword": "z"}]}'
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0, cache_write_tokens=0),
        ),
    )


def main():
    os.environ["V3_SCRIPT_WRITER_MODEL"] = "gpt-5.6-sol"
    os.environ["V3_SCRIPT_MODEL"] = "gpt-4o-mini"
    os.environ.pop("V3_SCRIPT_REPAIR_MODEL", None)

    _apply_production_hotfix_chain()

    import content.script_engine_v2_runner as runner
    import content.script_generator_router as router

    assert runner.WRITER_MODEL == "gpt-5.6-sol", runner.WRITER_MODEL
    assert runner.MODEL == "gpt-4o-mini", runner.MODEL

    captured_models = []

    def fake_create(**kwargs):
        captured_models.append(kwargs.get("model"))
        return _fake_response()

    grounded_writer_payload = {
        "target_scene_count": 1,
        "scene_contracts": [{"index": 1, "role": "phenomenon"}],
        "grounded_claim_plan": [{"claim_id": "x", "owner_scene_index": 1}],
    }
    grounded_repair_payload = {
        "targets": [],
        "grounded_claim_plan": [{"claim_id": "x", "owner_scene_index": 1}],
    }

    with patch(
        "content.script_engine_v2_runner.authorize_call", return_value=1
    ) as mock_authorize, patch(
        "openai.chat.completions.create", side_effect=fake_create
    ), patch(
        "content.script_engine_v2_runner.record_usage",
        return_value={"cost_usd": 0.0, "over_budget": False},
    ):
        # RED -> GREEN: the actual production entry point is
        # content.script_generator_router._resilient_v2_call (what
        # generate_script_v2(..., call_fn=_resilient_v2_call) invokes),
        # going through whichever hotfix-appended _default_call wins.
        router._resilient_v2_call(grounded_writer_payload, mode="writer")
        writer_model = captured_models[-1]
        writer_authorize_model = mock_authorize.call_args.args[0]

        router._resilient_v2_call(grounded_repair_payload, mode="local_repair")
        repair_model = captured_models[-1]
        repair_authorize_model = mock_authorize.call_args.args[0]

        # A second writer call right after a repair call proves MODEL is
        # restored/reapplied each time, not left stuck from a prior call.
        router._resilient_v2_call(grounded_writer_payload, mode="writer")
        writer_model_again = captured_models[-1]

    assert writer_model == "gpt-5.6-sol", (
        "production Writer call must authorize+request the premium model "
        f"through the exact hotfix-composed _default_call; got {writer_model!r}"
    )
    assert writer_authorize_model == "gpt-5.6-sol", writer_authorize_model
    assert writer_model_again == "gpt-5.6-sol", writer_model_again

    # Control: repair/cheap path must NOT be promoted to the premium model.
    assert repair_model == "gpt-4o-mini", (
        "local_repair must keep the existing cheap model; "
        f"got {repair_model!r}"
    )
    assert repair_authorize_model == "gpt-4o-mini", repair_authorize_model

    # Control: MODEL itself must be left exactly as it started -- no
    # permanent mutation leaking into any other caller of this module.
    assert runner.MODEL == "gpt-4o-mini", runner.MODEL

    print(
        "PASS: production Script Writer call routes through the premium "
        "model across the exact hotfix-composed _default_call chain "
        "(Run 34539602721 counterexample fixed); repair/cheap path and "
        "MODEL attribute are unaffected"
    )


if __name__ == "__main__":
    main()

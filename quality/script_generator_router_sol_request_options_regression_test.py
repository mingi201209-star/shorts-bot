"""Authority regression for Run 34570864208: production Writer routing to
GPT-5.6 Sol (PR #319) worked, but the very same hotfix-appended writer call
still sent an OpenAI-request option Sol rejects outright.

RED authority (Run 34570864208, exact main 795e2d11a87182e243ada9fc12e70186a95c7cb8):
[API_MODEL_ROUTE] call=1 model=gpt-4o-mini    (Candidate)
[API_MODEL_ROUTE] call=2 model=gpt-4o-mini    (Candidate Gate / Grounding path)
[API_MODEL_ROUTE] call=3 model=gpt-5.6-sol    (Script Writer -- PR #319's fix
                                                confirmed working in real
                                                production)
Error code: 400 - {'error': {'message': "Unsupported value: 'temperature'
does not support 0.2 with this model. Only the default (1) value is
supported.", 'type': 'invalid_request_error', 'param': 'temperature',
'code': 'unsupported_value'}}

Root cause: content/script_engine_v2_runner.py's checked-in _default_call()
correctly builds its openai.chat.completions.create(...) kwargs via
**_model_request_options(model) (reasoning_effort="none" for any gpt-5.6*
model, temperature=0.2 otherwise). But all four production hotfixes that
append their own _default_call() to that same file --
ci_writer_compliance_plan_hotfix.py, ci_grounded_claim_plan_hotfix.py,
ci_grounded_causal_role_hotfix.py, ci_grounded_causal_contrast_hotfix.py
(chain-imported by ci_cross_process_video_dedupe_hotfix.py, part of the
real .github/workflows/main.yml chain; the last of the four,
ci_grounded_causal_contrast_hotfix.py's GROUNDED_CAUSAL_CONTRAST_PROMPT_V2,
is the one that actually executes in the final composition) hardcode
`temperature=0.2` as a literal directly in their own
openai.chat.completions.create(...) call -- never calling
_model_request_options() at all. PR #319 already fixed which `model` these
overrides request (aliasing content.script_engine_v2_runner.MODEL to
WRITER_MODEL for the duration of a writer call), but that fix could not
also correct this hardcoded temperature literal -- it isn't a variable
lookup PR #319's technique can intercept.

Why quality/script_generator_router_writer_model_routing_regression_test.py
(PR #319) missed this: it captures and asserts only the `model` kwarg (and
the authorize_call() argument). By the time that regression ran, `model`
was already correct, so it never inspected the rest of the request kwargs
and had no reason to catch an incompatible `temperature` riding alongside
the now-correct model.

Fix location: content/script_generator_router.py::_resilient_v2_call(), NOT
any hotfix file or the hotfix-mutated runner file. `temperature=0.2` is a
literal baked into each hotfix override's source, so it cannot be corrected
by aliasing a module attribute the way MODEL is. Instead, for the exact
duration of one _default_call() invocation, openai.chat.completions.create
is wrapped to re-derive the correct options for whatever model is actually
being requested via the same authoritative, hotfix-untouched
_model_request_options(model) helper the checked-in _default_call() already
uses -- dropping an incompatible temperature and applying the right option
set -- then restored in a finally block. This reuses the single source of
truth for model-aware request options rather than duplicating that policy.
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
    """Apply the exact .github/workflows/main.yml hotfix chain -- required
    to reproduce this bug at all; the checked-in _default_call already
    builds correct request options via _model_request_options().
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

    captured_calls = []

    def fake_create(**kwargs):
        captured_calls.append(kwargs)
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
    ), patch(
        "openai.chat.completions.create", side_effect=fake_create
    ), patch(
        "content.script_engine_v2_runner.record_usage",
        return_value={"cost_usd": 0.0, "over_budget": False},
    ):
        # A. production Writer: model=gpt-5.6-sol, no temperature, reasoning_effort=none.
        router._resilient_v2_call(grounded_writer_payload, mode="writer")
        writer_call = captured_calls[-1]

        # B. local repair: cheap model, temperature=0.2, never promoted to Sol.
        router._resilient_v2_call(grounded_repair_payload, mode="local_repair")
        repair_call = captured_calls[-1]

        # C. repair immediately after a writer call: still fully reverted to
        # cheap-model options (covered by B occurring right after A above).

        # D. a second writer call right after a repair call: Sol options
        # re-applied cleanly, proving per-call independence in both directions.
        router._resilient_v2_call(grounded_writer_payload, mode="writer")
        writer_call_again = captured_calls[-1]

    # RED -> GREEN: production Writer call to Sol must never carry an
    # unsupported temperature, and must carry the model's own reasoning_effort.
    assert writer_call.get("model") == "gpt-5.6-sol", writer_call
    assert "temperature" not in writer_call, (
        "Writer call to gpt-5.6-sol must not send temperature "
        f"(Run 34570864208 counterexample): {writer_call}"
    )
    assert writer_call.get("reasoning_effort") == "none", writer_call

    # Control: local_repair keeps the existing cheap-model sampling policy
    # and is never promoted to the premium model.
    assert repair_call.get("model") == "gpt-4o-mini", repair_call
    assert repair_call.get("temperature") == 0.2, repair_call
    assert "reasoning_effort" not in repair_call, repair_call

    # Control: a second writer call after a repair call gets the Sol options
    # again -- proves per-call reapplication, not a one-shot side effect.
    assert writer_call_again.get("model") == "gpt-5.6-sol", writer_call_again
    assert "temperature" not in writer_call_again, writer_call_again
    assert writer_call_again.get("reasoning_effort") == "none", writer_call_again

    # Control: no permanent mutation of shared state.
    assert runner.MODEL == "gpt-4o-mini", runner.MODEL
    import openai

    assert openai.chat.completions.create is not fake_create, (
        "openai.chat.completions.create must be restored, not left patched"
    )

    print(
        "PASS: production Writer requests gpt-5.6-sol with Sol-compatible "
        "request options (no temperature, reasoning_effort=none); "
        "local_repair keeps cheap-model temperature=0.2; both recover "
        "correctly across consecutive calls (Run 34570864208 counterexample "
        "fixed)"
    )


if __name__ == "__main__":
    main()

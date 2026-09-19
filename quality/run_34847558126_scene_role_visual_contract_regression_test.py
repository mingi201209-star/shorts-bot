"""Run 34847558126 Scene-role-aware Visual Contract regression (re-fix).

Authority: production Run 34847558126 (Shorts Generator on `publish-stable`,
dispatched by Publish Stable Engine run 34847540739 with
`youtube_upload=true`, exact stable SHA
`91002ebcc24a8fe201f931f95def45c0a5014bf9`, immediately after PR #371) proved
the exact Run 34753759233 / PR #362 regression recurred: PR #362's hotfix
(`ci_run_34753759233_scene_role_grounded_keyword_hotfix.py`) was no longer
wired into main.yml's production hotfix chain, so
`content.script_engine_v2_runner._owned_claim_keyword_terms` had reverted to
tokenizing `owned_claim_id` unconditionally again. Scene 4's own
`owned_claim_id` ("spoiler_weight_to_wheels") leaked "spoiler" back into its
retrieval keyword ("aircraft wing spoiler weight wheel") even though neither
its narration ("착륙 뒤 양력을 없애면 항공기 무게가 바퀴에 더 실립니다")
nor its visual_goal ("무게가 바퀴에 실리는 모습") ever names it. Every real
aircraft+wing candidate was rejected as cross-domain
(`GENERAL_VISUAL_REJECT anchors=aircraft+wing+spoiler`), the still-generation
budget exhausted, and the scene fell to a `WINGLET_FLOW` explanatory diagram
-- the wrong component family, with no winglet/spoiler visual promise in
this Scene at all.

This run also proved a second-order effect: even after the keyword leak is
closed (so the retrieval query itself no longer contains "spoiler"),
`video.visual_explanation._winglet_subject`'s bare "aircraft wing" match
would still misclassify this same weight-transfer Scene into the winglet
family *if* it ever reached the explanatory fallback (e.g. on a transient
stock-retrieval miss), because the Scene's own narration/visual_goal/keyword
combination still contains the substring "aircraft wing" with no spoiler
word left to trigger the existing spoiler/flap exclusion. Both fixes are
required together.

This regression composes the real production hotfix chain in a scratch copy
and proves the fix end to end.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

_CHAIN = [
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_aviation_candidate_specificity_hotfix.py", "ci_aviation_context_signature_compat_hotfix.py",
    "ci_aviation_specificity_output_repair_hotfix.py", "ci_aviation_specificity_projection_hotfix.py",
    "ci_candidate_grounded_recovery_hotfix.py", "ci_growth_candidate_shadow_hotfix.py",
    "ci_final_render_content_integrity_hotfix.py", "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py", "ci_design_causality_hotfix.py",
    "ci_query_semantic_integrity_hotfix.py", "ci_concrete_visual_evidence_hotfix.py",
    "ci_visible_evidence_provenance_hotfix.py", "ci_hook_production_parity_hotfix.py",
    "ci_hook_fallback_quality_floor_hotfix.py", "ci_ai_visual_fallback_hotfix.py",
    "ci_ai_visual_mechanism_fallback_hotfix.py", "ci_problem_solution_narrative_hotfix.py",
    "ci_causal_information_progression_hotfix.py", "ci_retention_structure_experiment_hotfix.py",
    "ci_subscriber_conversion_hotfix.py", "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py", "ci_adaptive_scene_count_hotfix.py",
    "ci_general_scene_visual_parity_hotfix.py", "ci_script_validation_recovery_hotfix.py",
    "ci_script_v2_visual_goal_hotfix.py", "ci_script_v2_gunggeum_formal_ending_hotfix.py",
    "ci_final_visual_semantic_qa_hotfix.py", "ci_cross_process_video_dedupe_hotfix.py",
    "ci_run_34847558126_scene_role_grounded_keyword_hotfix.py",
    "ci_writer_observable_opening_hotfix.py",
    "ci_grounded_deterministic_explanation_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
]

_STOCK_AIRCRAFT_WING = {
    "title": "commercial aircraft wing in flight aviation",
    "tags": "aircraft wing airplane",
    "description": "", "metadata": "", "source_url": "", "url": "",
}

SCENE4_NARRATION = "착륙 뒤 양력을 없애면 항공기 무게가 바퀴에 더 실립니다."
SCENE4_GOAL = "무게가 바퀴에 실리는 모습"


def _prepare_repo() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="run_34847558126_"))
    repo = scratch / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    for script in _CHAIN:
        result = subprocess.run([sys.executable, script], cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(
                f"production composition failed at {script}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
    return repo


def main():
    repo = _prepare_repo()
    try:
        runner_source = (repo / "content/script_engine_v2_runner.py").read_text(encoding="utf-8")
        assert "RUN_34847558126_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1" in runner_source
        ve_source = (repo / "video/visual_explanation.py").read_text(encoding="utf-8")
        assert "RUN_34847558126_WINGLET_FAMILY_CONTAMINATION_FIX_V1" in ve_source

        sys.path.insert(0, str(repo))
        try:
            for name in list(sys.modules):
                if name in ("video", "content", "quality") or name.startswith(
                    ("video.", "content.", "quality.")
                ):
                    del sys.modules[name]

            vd = __import__("video.video_downloader", fromlist=["*"])
            runner = __import__("content.script_engine_v2_runner", fromlist=["*"])
            ve = __import__("video.visual_explanation", fromlist=["*"])

            # CASE A: exact Run 34847558126 Scene 4 claim -- keyword leak closed.
            plan_ctx = {"canonical_subject": "aircraft wing spoilers"}
            contract4 = {
                "owned_claim_id": "spoiler_weight_to_wheels",
                "supporting_evidence_summary": (
                    "Lift loss transfers aircraft weight onto the landing gear wheels."
                ),
                "grounding_provenance_present": True,
            }
            keyword4 = runner._grounded_claim_aware_keyword(contract4, plan_ctx)
            assert "spoiler" not in keyword4.split(), keyword4
            print(f"CASE A Scene 4 keyword no longer carries spoiler: {keyword4!r}: PASS")

            # CASE B: the resulting query is accepted as ordinary result-scene
            # stock instead of being rejected as cross-domain.
            effective4 = vd.enforce_visual_subject_anchor_query(
                narration=SCENE4_NARRATION, visual_goal=SCENE4_GOAL, query=keyword4,
            )
            tier4, label4 = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, effective4)
            assert tier4 <= 4, (tier4, label4)
            print(f"CASE B Scene 4 result-scene stock accepted tier={tier4}({label4}): PASS")

            # CASE C: even if the explanatory fallback were still reached for
            # this exact Scene shape, it must fail closed (no WINGLET_FLOW
            # misfire) instead of drawing the wrong component family.
            scene4 = {"text": SCENE4_NARRATION, "visual_goal": SCENE4_GOAL, "keyword": keyword4}
            plan4 = ve.plan_explanation(scene4)
            assert plan4 is None, plan4
            print("CASE C Scene 4 explanatory fallback no longer misfires as WINGLET_FLOW: PASS")

            # CASE D: Scene 3 (direct mechanism, genuinely discusses spoiler)
            # must KEEP its spoiler requirement -- no over-correction.
            contract3 = {
                "owned_claim_id": "spoiler_destroy_lift",
                "supporting_evidence_summary": (
                    "The deployed spoiler disrupts airflow over the wing and destroys lift."
                ),
                "grounding_provenance_present": True,
            }
            keyword3 = runner._grounded_claim_aware_keyword(contract3, plan_ctx)
            assert "spoiler" in keyword3.split(), keyword3
            print(f"CASE D Scene 3 keeps spoiler requirement: {keyword3!r}: PASS")

            # CASE E: genuine winglet Scene still gets WINGLET_FLOW.
            winglet_scene = {
                "text": "윙렛이 공기 흐름을 바꿉니다",
                "visual_goal": "winglet redirecting airflow",
                "keyword": "aircraft wing winglet airflow",
            }
            wplan = ve.plan_explanation(winglet_scene)
            assert wplan is not None and wplan["template"] == "WINGLET_FLOW", wplan
            print("CASE E genuine winglet Scene unaffected: PASS")

            # CASE F: bare "aircraft wing" alone (no winglet/wingtip token) is
            # not winglet family.
            bare_scene = {"text": "항공기 날개", "visual_goal": "aircraft wing in flight", "keyword": "aircraft wing"}
            assert ve._winglet_subject(bare_scene) is False
            print("CASE F bare aircraft+wing -> winglet family false: PASS")

            # CASE G: the wing-flex payoff claim must retrieve observable
            # flex/bending-under-load evidence, not literal claim-id prose such
            # as "not rigid plate" that produces static generic wing shots.
            flex_plan = {
                "canonical_subject": "aircraft wing structure under aerodynamic load",
            }
            flex_contract = {
                "owned_claim_id": "wing_flex_not_rigid_plate",
                "supporting_evidence_summary": (
                    "항공기 날개는 완전히 움직이지 않는 판이 아니라 "
                    "하중 아래에서 탄성 변형하는 구조입니다."
                ),
                "grounding_provenance_present": True,
            }
            flex_keyword = runner._grounded_claim_aware_keyword(
                flex_contract, flex_plan
            )
            flex_words = set(flex_keyword.split())
            assert {"aircraft", "wing", "flex", "bending", "load"} <= flex_words, flex_keyword
            assert not ({"not", "rigid", "plate"} & flex_words), flex_keyword
            print(
                f"CASE G wing-flex payoff uses observable retrieval terms: "
                f"{flex_keyword!r}: PASS"
            )

            # CASE H: "flapwise" is an aerodynamic bending-mode word,
            # not evidence that a physical trailing-edge flap is present.
            flapwise_required = vd._required_scene_subject_anchors(
                "NASA flexible-wing model uses flapwise bending and torsion on an aircraft wing.",
                "날개의 휨과 비틀림을 보여줍니다.",
            )
            assert "aircraft" in flapwise_required, flapwise_required
            assert "wing" in flapwise_required, flapwise_required
            assert "flap" not in flapwise_required, flapwise_required

            actual_flap_required = vd._required_scene_subject_anchors(
                "The aircraft wing flap moves at the trailing edge.",
                "실제 날개 플랩을 보여줍니다.",
            )
            assert "flap" in actual_flap_required, actual_flap_required
            print(
                "CASE H ASCII alias boundaries: flapwise!=flap while real flap stays required: PASS"
            )

        finally:
            sys.path.remove(str(repo))

        # No budget/floor/retry/API/model-routing constant touched.
        own_marker = "RUN_34847558126_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1"
        own_block = runner_source[runner_source.index(own_marker):]
        ve_own_block = ve_source[ve_source.index("RUN_34847558126_WINGLET_FAMILY_CONTAMINATION_FIX_V1"):]
        combined_own = own_block + ve_own_block
        for forbidden in (
            "V3_MAX_COST_USD =", "V3_MAX_API_CALLS =", "MAX_TOPIC_REGENERATIONS =",
            "HOOK_MIN_SCORE =", "AI_MAX_GENERATIONS_PER_VIDEO", "IDENTITY_CONFIDENCE_MIN =",
            "temperature=0.", "authorize_call(", "openai.",
        ):
            assert forbidden not in combined_own, forbidden
        print("CASE (budget invariant) budgets/floors/retries/model routing unchanged: PASS")

        print("RUN 34847558126 SCENE ROLE VISUAL CONTRACT REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()

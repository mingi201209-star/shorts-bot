"""Run 34753759233 Scene-role-aware Visual Contract regression.

Authority: production Run 34753759233 (fixed-topic "착륙 직후 날개 위로 솟는
스포일러", exact main `65f6f5e0815e5c24c858fb5ec659b69e662d83d3`, immediately
after PR #360/#361 landed) proved #360/#361's literal spoiler grounding works
-- Scene 1/2 both got a verified aircraft+wing+spoiler still and PASSED -- but
then failed on two *separate*, newly-exposed root causes:

1. `owned_claim_id` values like "spoiler_weight_to_wheels" and
   "spoiler_braking_effectiveness" are causal-LINEAGE labels ("this result
   claim descends from the spoiler claim"), not a promise that Scene 4/5's
   own narration/visual_goal shows the spoiler. The grounded-keyword builder
   tokenized `owned_claim_id` unconditionally, so "spoiler" leaked into Scene
   4/5's retrieval keyword even though neither Scene names it. Every
   downstream anchor/proof check (extract_query_anchors,
   concrete_visual_evidence, candidate_anchor_compatibility) reads that query
   TEXT directly, so a real aircraft+wing "result" stock candidate was
   rejected as cross-domain for both Scenes, exhausting retrieval.

2. `video.visual_explanation._winglet_subject` classified any Scene whose
   text merely contained the substring "aircraft wing" into the winglet
   family -- including the spoiler Scene 3 mechanism explanation ("aircraft
   wing spoiler destroy lift"). It drew a winglet silhouette for a spoiler
   Scene, and then Scene 4 (also matching "aircraft wing") repeat-rejected
   the same WINGLET_FLOW template, leaving Scene 5 with no visual fallback at
   all and crashing production.

This regression composes the real production hotfix chain in a scratch copy
and proves cases A-I.
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
    "ci_run_34753759233_scene_role_grounded_keyword_hotfix.py",
    "ci_writer_observable_opening_hotfix.py",
    "ci_grounded_deterministic_explanation_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
]

_STOCK_AIRCRAFT_WING = {
    "title": "commercial aircraft wing in flight aviation",
    "tags": "aircraft wing airplane",
    "description": "", "metadata": "", "source_url": "", "url": "",
}
_STOCK_AIRCRAFT_WING_SPOILER = {
    "title": "commercial aircraft wing spoiler deployed in flight",
    "tags": "aircraft wing spoiler airplane",
    "description": "", "metadata": "", "source_url": "", "url": "",
}

SCENE1_NARRATION = "착륙 직후 날개 위로 스포일러가 솟아오릅니다."
SCENE1_GOAL = "착륙 후 날개 위 스포일러 전개를 보여줍니다."
SCENE3_NARRATION = "스포일러가 날개 위로 펼쳐지며 공기 흐름을 방해하고 양력을 파괴합니다."
SCENE3_GOAL = "날개 위 스포일러가 펼쳐져 공기 흐름을 방해하는 모습을 보여줍니다."
SCENE4_NARRATION = "양력을 없애면 항공기 무게가 바퀴에 더 실리게 됩니다."
SCENE4_GOAL = "항공기 무게가 착륙 장치의 바퀴로 전달되는 모습을 표현합니다."
SCENE5_NARRATION = "이로 인해 바퀴 제동이 더 잘 작동해 착륙 후 지상 활주 거리가 줄어듭니다."
SCENE5_GOAL = "활주로에서 감속하는 항공기와 짧아지는 지상 활주 거리를 보여줍니다."


def _prepare_repo() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="run_34753759233_"))
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
        assert "RUN_34753759233_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1" in runner_source
        ve_source = (repo / "video/visual_explanation.py").read_text(encoding="utf-8")
        assert "RUN_34753759233_WINGLET_FAMILY_CONTAMINATION_FIX_V1" in ve_source
        assert "RUN_34753759233_SPOILER_FAMILY_V1" in ve_source

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

            # CASE A: #547-style bad opening blocked. Scene 1's narration and
            # visual_goal both directly promise a visible spoiler; a
            # generic aircraft+wing candidate (no spoiler visible) must stay
            # rejected as incomplete/cross-domain.
            effective = vd.enforce_visual_subject_anchor_query(
                narration=SCENE1_NARRATION, visual_goal=SCENE1_GOAL,
                query="aircraft wing spoiler in flight",
            )
            tier, label = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, effective)
            assert tier >= 5, (tier, label)
            evidence = vd.concrete_visual_evidence(_STOCK_AIRCRAFT_WING, effective)
            assert evidence["complete"] is False, evidence
            print("CASE A #547 bad opening (generic aircraft+wing, no spoiler) blocked: PASS")

            # CASE B: direct spoiler 3/3 (aircraft+wing+spoiler visible) passes.
            evidence_b = vd.concrete_visual_evidence(_STOCK_AIRCRAFT_WING_SPOILER, effective)
            assert evidence_b["complete"] is True, evidence_b
            print("CASE B direct spoiler 3/3 visible candidate passes: PASS")

            # CASE C: Scene 4 result -- spoiler keyword-only provenance must
            # not force a hard spoiler anchor. Simulate the grounded-keyword
            # builder's real output for this exact claim shape.
            plan = {"canonical_subject": "aircraft wing spoilers"}
            contract4 = {
                "owned_claim_id": "spoiler_weight_to_wheels",
                "supporting_evidence_summary": (
                    "Lift loss transfers aircraft weight onto the landing gear wheels."
                ),
                "grounding_provenance_present": True,
            }
            keyword4 = runner._grounded_claim_aware_keyword(contract4, plan)
            assert "spoiler" not in keyword4.split(), keyword4
            effective4 = vd.enforce_visual_subject_anchor_query(
                narration=SCENE4_NARRATION, visual_goal=SCENE4_GOAL, query=keyword4,
            )
            tier4, label4 = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, effective4)
            assert tier4 <= 4, (tier4, label4, keyword4, effective4)
            evidence4 = vd.concrete_visual_evidence(_STOCK_AIRCRAFT_WING, effective4)
            assert evidence4["complete"] is True, evidence4
            print(f"CASE C Scene 4 result scene keyword={keyword4!r} tier={tier4}({label4}): PASS")

            # CASE D: Scene 5 result -- same contract, different claim.
            contract5 = {
                "owned_claim_id": "spoiler_braking_effectiveness",
                "supporting_evidence_summary": (
                    "Reduced lift improves wheel braking effectiveness during landing rollout."
                ),
                "grounding_provenance_present": True,
            }
            keyword5 = runner._grounded_claim_aware_keyword(contract5, plan)
            assert "spoiler" not in keyword5.split(), keyword5
            effective5 = vd.enforce_visual_subject_anchor_query(
                narration=SCENE5_NARRATION, visual_goal=SCENE5_GOAL, query=keyword5,
            )
            tier5, label5 = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, effective5)
            assert tier5 <= 4, (tier5, label5, keyword5, effective5)
            evidence5 = vd.concrete_visual_evidence(_STOCK_AIRCRAFT_WING, effective5)
            assert evidence5["complete"] is True, evidence5
            print(f"CASE D Scene 5 result scene keyword={keyword5!r} tier={tier5}({label5}): PASS")

            # Scene 3 (direct mechanism, genuinely discusses spoiler in its
            # own evidence) must KEEP the spoiler requirement -- claim-id
            # stripping must not blind a Scene that legitimately needs it.
            contract3 = {
                "owned_claim_id": "spoiler_destroy_lift",
                "supporting_evidence_summary": (
                    "The deployed spoiler disrupts airflow over the wing and destroys lift."
                ),
                "grounding_provenance_present": True,
            }
            keyword3 = runner._grounded_claim_aware_keyword(contract3, plan)
            assert "spoiler" in keyword3.split(), keyword3
            effective3 = vd.enforce_visual_subject_anchor_query(
                narration=SCENE3_NARRATION, visual_goal=SCENE3_GOAL, query=keyword3,
            )
            tier3, label3 = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, effective3)
            assert tier3 >= 5, (tier3, label3, keyword3, effective3)
            print(f"CASE (Scene 3 no-regression) direct mechanism keeps spoiler requirement: PASS")

            def scene(text="", visual_goal="", keyword=""):
                return {"text": text, "visual_goal": visual_goal, "keyword": keyword}

            # CASE E: winglet contamination must not occur for a spoiler Scene.
            s_e = scene(
                keyword="aircraft wing spoiler airflow",
                visual_goal="disrupting airflow over the wing",
                text="스포일러가 공기 흐름을 방해합니다",
            )
            plan_e = ve.plan_explanation(s_e)
            assert plan_e is not None and plan_e["template"] != "WINGLET_FLOW", plan_e
            assert plan_e["template"] == "SPOILER_DEPLOY", plan_e
            print("CASE E winglet contamination excluded for spoiler Scene: PASS")

            # CASE F: bare "aircraft wing" -> winglet family false.
            s_f = scene(keyword="aircraft wing", visual_goal="aircraft wing in flight", text="항공기 날개")
            assert ve._winglet_subject(s_f) is False
            assert ve.plan_explanation(s_f) is None
            print("CASE F bare aircraft+wing -> winglet family false: PASS")

            # CASE G: explicit winglet identity -> winglet family true.
            s_g = scene(
                keyword="aircraft wing winglet airflow",
                visual_goal="winglet redirecting airflow",
                text="윙렛이 공기 흐름을 바꿉니다",
            )
            assert ve._winglet_subject(s_g) is True
            plan_g = ve.plan_explanation(s_g)
            assert plan_g is not None and plan_g["template"] == "WINGLET_FLOW", plan_g
            assert ve.annotation_fact_safe(s_g, plan_g) is True
            print("CASE G explicit winglet identity -> winglet family true: PASS")

            # CASE H: fallback inheritance -- a direct spoiler Scene whose
            # query is relaxed to a broader fallback query still carries the
            # original required spoiler proof (fallback cannot loosen it).
            fallback_query = "airplane wing detail"
            tier_fb, label_fb = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, fallback_query)
            # authority_query resolves to the still-active Scene-3 contract's
            # effective_query (set above), not the raw fallback text, so the
            # spoiler requirement survives even though the fallback query
            # itself never repeats "spoiler".
            assert tier_fb >= 5, (tier_fb, label_fb)
            print("CASE H fallback inheritance keeps direct-scene spoiler proof required: PASS")

            # CASE I: result-scene contract must not be strengthened back to a
            # hard anchor merely because a fallback query still carries the
            # original (pre-fix-irrelevant) causal keyword text. Re-assert
            # the Scene 4 contract, then check a broader fallback query.
            vd.enforce_visual_subject_anchor_query(
                narration=SCENE4_NARRATION, visual_goal=SCENE4_GOAL, query=keyword4,
            )
            tier_i, label_i = vd.general_scene_unknown_safe_tier(_STOCK_AIRCRAFT_WING, "airplane wing detail")
            assert tier_i <= 4, (tier_i, label_i)
            print("CASE I result-scene fallback query stays governed by visual promise, not hard contract: PASS")

        finally:
            sys.path.remove(str(repo))

        # No budget/floor/retry/API/model-routing constant touched. Scope the
        # check to this fix's own inserted regions, not the whole
        # already-hotfixed file (which legitimately contains unrelated
        # temperature=/threshold constants from other, pre-existing hotfixes).
        own_marker = "RUN_34753759233_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1"
        own_block = runner_source[runner_source.index(own_marker):]
        ve_own_markers = (
            "RUN_34753759233_WINGLET_FAMILY_CONTAMINATION_FIX_V1",
            "RUN_34753759233_SPOILER_FAMILY_V1",
        )
        ve_own_start = min(ve_source.index(marker) for marker in ve_own_markers)
        ve_own_block = ve_source[ve_own_start:]
        combined_own = own_block + ve_own_block
        for forbidden in (
            "V3_MAX_COST_USD =", "V3_MAX_API_CALLS =", "MAX_TOPIC_REGENERATIONS =",
            "HOOK_MIN_SCORE =", "AI_MAX_GENERATIONS_PER_VIDEO", "IDENTITY_CONFIDENCE_MIN =",
            "temperature=0.", "authorize_call(", "openai.",
        ):
            assert forbidden not in combined_own, forbidden
        # The pre-existing budget constant must keep its original definition
        # (read from env, default "3") -- untouched, not merely absent.
        assert (
            'MAX_EXPLANATION_TRANSFORMS_PER_VIDEO = int(\n'
            '    os.environ.get("MAX_EXPLANATION_TRANSFORMS_PER_VIDEO", "3")\n'
            ')' in ve_source
        )
        print("CASE (budget invariant) budgets/floors/retries/model routing unchanged: PASS")

        print("RUN 34753759233 SCENE ROLE VISUAL CONTRACT REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()

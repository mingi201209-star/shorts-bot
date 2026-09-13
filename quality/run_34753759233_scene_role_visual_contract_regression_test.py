"""Run 34753759233 / 34781319743 scene-role visual contract regression.

#549 proved direct spoiler identity had become fail-closed, then exposed claim-id
component leakage and winglet-family contamination. PR #362 fixed those two.
#550 then mechanically PASSed but HUMAN-QA failed: Scene 4 selected the old
night-vision aircraft while promising weight-on-wheels, and Scene 5 selected
generic wing/cloud footage while promising braking / landing rollout.
"""
from __future__ import annotations

import json
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
    "ci_writer_observable_opening_hotfix.py", "ci_grounded_deterministic_explanation_hotfix.py",
    "ci_aviation_context_signature_compat_hotfix.py",
]

BAD_WING = {
    "provider": "pixabay", "source_id": "142647",
    "title": "airplane wing flying sky clouds flight",
    "tags": "airplane wing flying sky clouds flight",
    "description": "", "metadata": "", "source_url": "", "url": "",
}
BAD_NIGHT = {
    "provider": "pixabay", "source_id": "15270",
    "title": "aircraft flight plane airplane air transport aviation fly sky cloud wing weather binoculars",
    "tags": "aircraft flight plane airplane air transport aviation fly sky cloud wing weather binoculars",
    "description": "", "metadata": "", "source_url": "", "url": "",
}
GOOD_SPOILER = {
    "provider": "test", "source_id": "spoiler-visible",
    "title": "commercial aircraft wing spoiler deployed in flight",
    "tags": "aircraft wing spoiler airplane",
    "description": "", "metadata": "", "source_url": "", "url": "",
}
GOOD_GEAR = {
    "provider": "test", "source_id": "landing-gear-visible",
    "title": "aircraft landing gear wheels touchdown closeup",
    "tags": "aircraft landing gear wheel wheels touchdown",
    "description": "", "metadata": "", "source_url": "", "url": "",
}
GOOD_RUNWAY = {
    "provider": "test", "source_id": "runway-rollout-visible",
    "title": "aircraft runway rollout braking after touchdown",
    "tags": "aircraft runway rollout braking touchdown",
    "description": "", "metadata": "", "source_url": "", "url": "",
}

S1_TEXT = "착륙 직후 날개 위로 스포일러가 솟아오릅니다."
S1_GOAL = "착륙 후 날개 위 스포일러 전개를 보여줍니다."
S3_TEXT = "스포일러가 날개 위로 펼쳐지며 공기 흐름을 방해하고 양력을 파괴합니다."
S3_GOAL = "날개 위 스포일러가 펼쳐져 공기 흐름을 방해하는 모습을 보여줍니다."
S4_TEXT = "양력을 없애면 항공기 무게가 바퀴에 더 실리게 됩니다."
S4_GOAL = "항공기 무게가 착륙 장치의 바퀴로 전달되는 모습을 표현합니다."
S5_TEXT = "이로 인해 바퀴 제동이 더 잘 작동해 착륙 후 지상 활주 거리가 줄어듭니다."
S5_GOAL = "활주로에서 감속하는 항공기와 짧아지는 지상 활주 거리를 보여줍니다."


def prepare_repo() -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="run_34781319743_"))
    repo = scratch / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    for script in _CHAIN:
        result = subprocess.run([sys.executable, script], cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(
                f"production composition failed at {script}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
    return repo


def selection(candidate, matched=2, total=2):
    metadata = " ".join(str(candidate.get(k) or "") for k in (
        "title", "tags", "description", "metadata", "source_url", "url"
    ))
    return {
        "accepted": True, "mode": "SAME_DOMAIN_CONTEXTUAL_UNKNOWN", "tier": 4,
        "visual_state": "UNKNOWN", "anchor_matched": matched, "anchor_total": total,
        "provider": candidate.get("provider", "test"), "source_id": candidate.get("source_id", ""),
        "metadata": metadata,
    }


def main():
    repo = prepare_repo()
    try:
        runner_source = (repo / "content/script_engine_v2_runner.py").read_text(encoding="utf-8")
        downloader_source = (repo / "video/video_downloader.py").read_text(encoding="utf-8")
        ve_source = (repo / "video/visual_explanation.py").read_text(encoding="utf-8")
        qa_source = (repo / "quality/final_visual_semantic_qa.py").read_text(encoding="utf-8")
        assert "RUN_34753759233_CLAIM_ID_LINEAGE_LABEL_NOT_VISUAL_PROMISE_V1" in runner_source
        assert "RUN_34781319743_RESULT_VISUAL_PROMISE_V1" in downloader_source
        assert "RUN_34781319743_RESULT_VISUAL_FINAL_QA_V1" in qa_source
        assert "RUN_34753759233_WINGLET_FAMILY_CONTAMINATION_FIX_V1" in ve_source
        assert "RUN_34753759233_SPOILER_FAMILY_V1" in ve_source

        sys.path.insert(0, str(repo))
        try:
            for name in list(sys.modules):
                if name in ("video", "content", "quality") or name.startswith(("video.", "content.", "quality.")):
                    del sys.modules[name]
            vd = __import__("video.video_downloader", fromlist=["*"])
            runner = __import__("content.script_engine_v2_runner", fromlist=["*"])
            ve = __import__("video.visual_explanation", fromlist=["*"])
            qa = __import__("quality.final_visual_semantic_qa", fromlist=["*"])

            # A/B: direct spoiler identity remains 3/3 fail-closed.
            q1 = vd.enforce_visual_subject_anchor_query(
                narration=S1_TEXT, visual_goal=S1_GOAL, query="aircraft wing spoiler in flight"
            )
            tier, label = vd.general_scene_unknown_safe_tier(BAD_WING, q1)
            assert tier >= 5, (tier, label)
            assert vd.concrete_visual_evidence(BAD_WING, q1)["complete"] is False
            assert vd.concrete_visual_evidence(GOOD_SPOILER, q1)["complete"] is True
            print("CASE A/B direct spoiler proof preserved: PASS")

            plan = {"canonical_subject": "aircraft wing spoilers"}

            # C: exact #550 Scene 4 must target landing gear/wheels, not generic aircraft.
            c4 = {
                "owned_claim_id": "spoiler_weight_to_wheels",
                "supporting_evidence_summary": "Lift loss transfers aircraft weight onto the landing gear wheels.",
                "grounding_provenance_present": True,
            }
            k4 = runner._grounded_claim_aware_keyword(c4, plan)
            assert "spoiler" not in k4.split(), k4
            q4 = vd.enforce_visual_subject_anchor_query(narration=S4_TEXT, visual_goal=S4_GOAL, query=k4)
            w4 = set(q4.split())
            assert {"aircraft", "landing", "gear", "wheel"} <= w4, q4
            assert "wing" not in w4, q4
            assert vd.get_current_result_visual_contract()["group"] == "landing_gear_wheel"
            for bad in (BAD_WING, BAD_NIGHT):
                tier, label = vd.general_scene_unknown_safe_tier(bad, q4)
                assert tier >= 5, (bad["source_id"], tier, label)
                assert not vd._run_34781319743_result_candidate_matches(bad)
            tier, label = vd.general_scene_unknown_safe_tier(GOOD_GEAR, q4)
            assert tier <= 4, (tier, label)
            assert vd._run_34781319743_result_candidate_matches(GOOD_GEAR)
            print("CASE C #550 night-vision Scene 4 blocked; landing-gear result accepted: PASS")

            # D: exact #550 Scene 5 must target runway/rollout, not wing/cloud footage.
            c5 = {
                "owned_claim_id": "spoiler_braking_effectiveness",
                "supporting_evidence_summary": "Reduced lift improves wheel braking effectiveness during landing rollout.",
                "grounding_provenance_present": True,
            }
            k5 = runner._grounded_claim_aware_keyword(c5, plan)
            assert "spoiler" not in k5.split(), k5
            q5 = vd.enforce_visual_subject_anchor_query(narration=S5_TEXT, visual_goal=S5_GOAL, query=k5)
            w5 = set(q5.split())
            assert {"aircraft", "runway", "braking", "rollout"} <= w5, q5
            assert "wing" not in w5, q5
            assert vd.get_current_result_visual_contract()["group"] == "runway_rollout"
            tier, label = vd.general_scene_unknown_safe_tier(BAD_WING, q5)
            assert tier >= 5, (tier, label)
            assert not vd._run_34781319743_result_candidate_matches(BAD_WING)
            tier, label = vd.general_scene_unknown_safe_tier(GOOD_RUNWAY, q5)
            assert tier <= 4, (tier, label)
            assert vd._run_34781319743_result_candidate_matches(GOOD_RUNWAY)
            print("CASE D #550 wing/cloud Scene 5 blocked; runway rollout accepted: PASS")

            # Direct mechanism no-regression.
            c3 = {
                "owned_claim_id": "spoiler_destroy_lift",
                "supporting_evidence_summary": "The deployed spoiler disrupts airflow over the wing and destroys lift.",
                "grounding_provenance_present": True,
            }
            k3 = runner._grounded_claim_aware_keyword(c3, plan)
            assert "spoiler" in k3.split(), k3
            q3 = vd.enforce_visual_subject_anchor_query(narration=S3_TEXT, visual_goal=S3_GOAL, query=k3)
            tier, label = vd.general_scene_unknown_safe_tier(BAD_WING, q3)
            assert tier >= 5, (tier, label)
            assert not vd.get_current_result_visual_contract()["required"]
            print("CASE direct mechanism spoiler requirement preserved: PASS")

            # E/F/G: spoiler is not winglet; explicit winglet still works.
            scene = lambda text="", visual_goal="", keyword="": {
                "text": text, "visual_goal": visual_goal, "keyword": keyword
            }
            p = ve.plan_explanation(scene(
                keyword="aircraft wing spoiler airflow",
                visual_goal="disrupting airflow over the wing",
                text="스포일러가 공기 흐름을 방해합니다",
            ))
            assert p is not None and p["template"] == "SPOILER_DEPLOY", p
            bare = scene(keyword="aircraft wing", visual_goal="aircraft wing in flight", text="항공기 날개")
            assert ve._winglet_subject(bare) is False and ve.plan_explanation(bare) is None
            winglet = scene(
                keyword="aircraft wing winglet airflow",
                visual_goal="winglet redirecting airflow",
                text="윙렛이 공기 흐름을 바꿉니다",
            )
            assert ve._winglet_subject(winglet) is True
            assert ve.plan_explanation(winglet)["template"] == "WINGLET_FLOW"
            print("CASE E/F/G winglet contamination remains closed: PASS")

            # H: direct fallback cannot loosen spoiler proof.
            vd.enforce_visual_subject_anchor_query(narration=S3_TEXT, visual_goal=S3_GOAL, query=k3)
            tier, label = vd.general_scene_unknown_safe_tier(BAD_WING, "airplane wing detail")
            assert tier >= 5, (tier, label)
            print("CASE H direct fallback keeps spoiler proof: PASS")

            # I: result fallback cannot resurrect generic aircraft.
            vd.enforce_visual_subject_anchor_query(narration=S4_TEXT, visual_goal=S4_GOAL, query=k4)
            tier, label = vd.general_scene_unknown_safe_tier(BAD_NIGHT, "airplane wing detail")
            assert tier >= 5, (tier, label)
            assert vd._run_34781319743_result_candidate_matches(GOOD_GEAR)
            print("CASE I result fallback keeps goal-result evidence: PASS")

            # J: Final QA blocks the exact #550 false-positive pair.
            qa.reset_final_visual_semantic_report()
            qa.record_final_visual_scene(0, q4, selection(BAD_NIGHT))
            qa.record_final_visual_scene(1, q5, selection(BAD_WING))
            try:
                qa.validate_final_visual_semantic_qa([{}, {}])
            except RuntimeError as exc:
                assert "RESULT_EVIDENCE_FAILED" in str(exc), str(exc)
            else:
                raise AssertionError("Final QA accepted #550 night-vision/wing-cloud result footage")
            bad_payload = json.loads((repo / "final_visual_semantic_qa.json").read_text(encoding="utf-8"))
            assert bad_payload["status"] == "FAIL" and len(bad_payload["failed_scenes"]) == 2
            print("CASE J exact #550 Final QA false-PASS blocked: PASS")

            # K: positive result lineage stays valid.
            qa.reset_final_visual_semantic_report()
            qa.record_final_visual_scene(0, q4, selection(GOOD_GEAR))
            qa.record_final_visual_scene(1, q5, selection(GOOD_RUNWAY))
            good_payload = qa.validate_final_visual_semantic_qa([{}, {}])
            assert good_payload["status"] == "PASS", good_payload
            print("CASE K positive landing-gear/runway result path: PASS")

        finally:
            sys.path.remove(str(repo))

        own = downloader_source[downloader_source.index("RUN_34781319743_RESULT_VISUAL_PROMISE_V1"):] + qa_source[
            qa_source.index("RUN_34781319743_RESULT_VISUAL_FINAL_QA_V1"):
        ]
        for forbidden in (
            "V3_MAX_COST_USD =", "V3_MAX_API_CALLS =", "MAX_TOPIC_REGENERATIONS =",
            "HOOK_MIN_SCORE =", "AI_MAX_GENERATIONS_PER_VIDEO", "IDENTITY_CONFIDENCE_MIN =",
            "authorize_call(", "openai.",
        ):
            assert forbidden not in own, forbidden
        print("CASE budget invariant: quality floors/calls/retries/budgets unchanged: PASS")
        print("RUN 34753759233 + 34781319743 SCENE ROLE VISUAL CONTRACT REGRESSION: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()

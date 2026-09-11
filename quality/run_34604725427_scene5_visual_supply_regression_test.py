"""Run 34604725427 Scene 5 visual supply regression (PHASE 8 counterexample).

Authority: Run 34604725427, main 9931cabf71ec70067c08d4e0c884679f7706dbcd,
topic "비행기 창문 모서리는 왜 둥글까". Already VERIFIED in this run: #321
grounding, #322 compound Vision component parser, #323 observable Scene 1
opening, GPT-5.6 Sol Writer routing. Scene 5 (keyword "modern aircraft window
squarish fatigue rupture comet", claim=squarish_window_fatigue_rupture) then
failed:

    [STILL_IMAGE_FALLBACK] scene=unknown status=budget_exhausted count=2 trigger=no_semantically_safe_stock
    [VisualExplanation] status=unsupported_or_fact_unsafe
    RuntimeError: 영상 후보가 없고 검증된 정지 이미지/설명 visual fallback도 실패했습니다: modern aircraft window squarish fatigue rupture comet

Zero network/LLM/Vision/AI-image calls in this test. video._render_clip's
actual .mp4 write is stubbed (ffmpeg is not installed in this sandbox,
confirmed pre-existing and unrelated -- matching PR #322's documented
precedent) so the full generate_visual_explanation_fallback() decision path
(budget, dedup signature, result fields) is exercised without needing a real
encode.
"""
from __future__ import annotations

import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    "ci_writer_observable_opening_hotfix.py",
]

_FAA_SOURCE = "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"
_CANONICAL = "modern aircraft passenger window with rounded/oval corners"


def _scene5():
    # Reconstructed from the real Run 34604725427 [GROUNDED_KEYWORD_TRACE] and
    # [VISION_EVIDENCE_TRACE]-adjacent log lines: scene=5,
    # claim=squarish_window_fatigue_rupture, keyword text verbatim.
    return {
        "scene_id": 5,
        "role": "payoff",
        "text": "각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 빠르게 이어질 수 있었습니다.",
        "visual_goal": "각진 창문 모서리의 응력 집중이 재료 피로와 파열로 이어지는 결과를 보여준다.",
        "keyword": "modern aircraft window squarish fatigue rupture comet",
        "_canonical_visual_supply": {
            "canonical_subject": _CANONICAL,
            "identity_confidence": 0.97,
            "grounding_source": _FAA_SOURCE,
        },
    }


def _prepare_repo(*, apply_new_hotfix):
    scratch = Path(tempfile.mkdtemp(prefix="run_34604725427_"))
    repo = scratch / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    chain = list(_CHAIN)
    if apply_new_hotfix:
        chain.append("ci_grounded_deterministic_explanation_hotfix.py")
    for script in chain:
        subprocess.run([sys.executable, script], check=True, cwd=repo, capture_output=True)
    return repo


def _load_vx(repo):
    for mod in list(sys.modules):
        if mod.startswith("video.") or mod == "video":
            del sys.modules[mod]
    sys.path.insert(0, str(repo))
    try:
        module = runpy.run_path(str(repo / "video" / "visual_explanation.py"), run_name="video.visual_explanation")
    finally:
        sys.path.remove(str(repo))
    return module


def red():
    """Baseline (this fix's own hotfix NOT applied): reproduces the exact
    Run 34604725427 failure -- stock/reuse already exhausted upstream (not
    reproduced here, that is #321/#322/#323's own already-verified territory);
    this isolates the specific link in the chain this task targets:
    VisualExplanation itself has no template for this subject and must
    correctly refuse."""
    repo = _prepare_repo(apply_new_hotfix=False)
    try:
        vx = _load_vx(repo)
        scene = _scene5()
        plan = vx["plan_explanation"](scene)
        assert plan is None, "RED setup invalid: baseline unexpectedly has a plan for this scene"
        assert vx["annotation_fact_safe"](scene, plan) is False
        print("RUN 34604725427 SCENE5 VISUAL SUPPLY RED: PASS (reproduces unsupported_or_fact_unsafe)")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


def green():
    repo = _prepare_repo(apply_new_hotfix=True)
    try:
        vx = _load_vx(repo)
        scene = _scene5()

        plan = vx["plan_explanation"](scene)
        assert plan is not None
        assert plan["template"] == "AIRCRAFT_WINDOW_STRESS_V1"
        assert plan["evidence_source"] == "TRUSTED_GROUNDING"
        assert vx["annotation_fact_safe"](scene, plan) is True
        assert plan["_comparison_segment"] is not None
        segment = plan["_comparison_segment"]["comparison_segments"][0]
        assert segment["presentation"] == "SPLIT_SCREEN"
        assert {b["slot"] for b in segment["bindings"]} == {"LEFT", "RIGHT"}

        # Exercise the full production entrypoint with _render_clip stubbed
        # (no ffmpeg in this sandbox -- see module docstring).
        rendered = {}

        def _stub_render_clip(base_image, output_path, duration, render_plan):
            Path(output_path).write_bytes(b"stub-mp4")
            rendered["plan"] = render_plan

        # generate_visual_explanation_fallback resolves _render_clip via its
        # own __globals__ at call time; patch that exact dict (runpy's
        # returned namespace is not guaranteed to be the identical object).
        vx["generate_visual_explanation_fallback"].__globals__["_render_clip"] = _stub_render_clip

        out_dir = Path(tempfile.mkdtemp(prefix="run_34604725427_out_"))
        output_path = out_dir / "scene5.mp4"
        result = vx["generate_visual_explanation_fallback"](
            scene, output_path=output_path, duration=5.0, trigger_reason="still_budget_exhausted",
        )
        assert result is not None, "GREEN: generate_visual_explanation_fallback must not return None"
        assert result["template_type"] == "AIRCRAFT_WINDOW_STRESS_V1"
        assert result["additional_llm_calls"] == 0
        assert result["additional_vision_calls"] == 0
        assert output_path.is_file()
        shutil.rmtree(out_dir, ignore_errors=True)

        print("RUN 34604725427 SCENE5 VISUAL SUPPLY GREEN: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


def negative_e2e_controls():
    repo = _prepare_repo(apply_new_hotfix=True)
    try:
        vx = _load_vx(repo)
        cases = {
            "building_window": {
                **_scene5(),
                "keyword": "modern building window frame corner stress",
                "_canonical_visual_supply": {
                    "canonical_subject": "modern office building window with square corners",
                    "grounding_source": _FAA_SOURCE,
                },
            },
            "car_window": {
                **_scene5(),
                "keyword": "car window rounded corner glass",
                "_canonical_visual_supply": {
                    "canonical_subject": "passenger car side window with rounded corners",
                    "grounding_source": _FAA_SOURCE,
                },
            },
            "generic_window": {
                **_scene5(),
                "keyword": "generic window corner shape",
                "_canonical_visual_supply": {
                    "canonical_subject": "a window with corners",
                    "grounding_source": _FAA_SOURCE,
                },
            },
            "cockpit_windshield": {
                **_scene5(),
                "keyword": "aircraft cockpit windshield frame",
                "_canonical_visual_supply": {
                    "canonical_subject": "aircraft cockpit windshield with flat panels",
                    "grounding_source": _FAA_SOURCE,
                },
            },
            "unrelated_why_small": {
                **_scene5(),
                "text": "이 창문은 왜 작을까?",
                "keyword": "aircraft window why small",
            },
            "no_grounding": (lambda s: (s.pop("_canonical_visual_supply", None), s)[1])(_scene5()),
            "wrong_owned_claim": {**_scene5(), "owned_claim_id": "flap_low_landing_speed"},
            "contradicted_grounding": {**_scene5(), "_canonical_visual_supply": {}},
            "vision_only_verified": (lambda s: (
                s.pop("_canonical_visual_supply", None),
                s.__setitem__("_vision_evidence", {"pass": True, "state": "VERIFIED"}),
                s,
            )[-1])(_scene5()),
        }
        for label, scene in cases.items():
            plan = vx["plan_explanation"](scene)
            assert plan is None or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1", (
                f"{label} must not select AIRCRAFT_WINDOW_STRESS_V1"
            )
        print("RUN 34604725427 NEGATIVE E2E CONTROLS: PASS")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


def main():
    red()
    green()
    negative_e2e_controls()


if __name__ == "__main__":
    main()

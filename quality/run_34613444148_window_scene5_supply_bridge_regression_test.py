"""Run 34613444148: trusted window record must reach deterministic Scene 5 supply.

Authority: production Run 34613444148 on main
c64297673169068ec7a6a1d0b4e42f08221072a1. Scene 3 and Scene 4 consumed the
bounded still budget. Scene 5 then had no safe stock/reuse and logged
``[VisualExplanation] status=unsupported_or_fact_unsafe`` even though the
trusted FAA window claims and AIRCRAFT_WINDOW_STRESS_V1 renderer were present.

Root cause: the repo-owned window identity record carried trusted claims but no
``visual_discriminators``. The existing Canonical Visual Supply Contract only
builds ``_canonical_visual_supply`` from evidence-owned
``_trusted_visual_discriminators``. Consequently the real production scene did
not receive the private trusted supply profile that the deterministic
eligibility adapter requires. Earlier fixture tests manually injected that
profile and therefore missed the bridge gap.

This test executes the production hotfix composition in an isolated checkout,
then proves the real chain:
trusted record -> trusted subject grounding -> trusted visual discriminators ->
canonical visual supply profile -> production-shaped Scene 5 ->
AIRCRAFT_WINDOW_STRESS_V1 plan. No network, LLM, Vision, or image generation.
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
    "ci_writer_observable_opening_hotfix.py", "ci_grounded_deterministic_explanation_hotfix.py",
]

CANONICAL = "modern aircraft passenger window with rounded/oval corners"
EXPECTED_DISCRIMINATORS = {"window", "rounded", "oval", "curved"}


def _prepare_repo():
    scratch = Path(tempfile.mkdtemp(prefix="run_34613444148_"))
    repo = scratch / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    for script in _CHAIN:
        subprocess.run([sys.executable, script], check=True, cwd=repo, capture_output=True)
    return repo


def _run_child(repo: Path):
    code = r'''
from copy import deepcopy

from quality.candidate_pool_grounding_records import CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
from quality.canonical_subject_grounding_supply import supply_trusted_subject_grounding
from video.video_downloader import build_canonical_visual_supply_profile
from video.visual_explanation import plan_explanation, annotation_fact_safe

canonical = "modern aircraft passenger window with rounded/oval corners"
expected_discriminators = {"window", "rounded", "oval", "curved"}
window_records = [
    record for record in CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    if record.get("canonical_subject") == canonical
]
assert len(window_records) == 1, "window trusted identity record must remain unique"
record = window_records[0]
assert set(record.get("visual_discriminators") or []) == expected_discriminators

candidate = {
    "topic": "비행기 창문 모서리는 왜 둥글까",
    "angle": "비행기 창문은 모서리가 둥글게 디자인",
    "core_question": "비행기 창문 모서리가 둥글게 설계된 이유는 무엇인가?",
    "specific_observation": "현대 여객기 동체의 승객용 창문 가장자리는 둥글거나 타원형입니다.",
    "micro_narrative": {
        "hook": "비행기 창문은 모서리가 둥글게 디자인됩니다.",
        "core_question": "왜 둥글게 설계됐을까요?",
        "reveal": "둥근 모서리는 응력이 곡선 가장자리를 따라 흐르게 합니다.",
        "payoff": "각진 창문 모서리의 응력 집중은 재료 피로와 파열 위험을 키웠습니다.",
    },
}

supplied = supply_trusted_subject_grounding(candidate, trusted_records=[record])
assert supplied.get("canonical_subject") == canonical
assert set(supplied.get("_trusted_visual_discriminators") or []) == expected_discriminators, supplied
assert supplied.get("_trusted_grounding_evidence"), supplied
assert len(supplied.get("_trusted_grounded_claims") or []) == 3, supplied

profile = build_canonical_visual_supply_profile(supplied)
assert profile.get("canonical_subject") == canonical, profile
assert set(profile.get("visual_discriminators") or []) == expected_discriminators, profile
assert profile.get("grounding_source"), profile

# Production-shaped Scene 5 from Run 34613444148. The private profile is not
# hand-authored: it is the exact output of the existing canonical supply bridge.
scene5 = {
    "scene_id": 5,
    "role": "payoff",
    "causal_role": "primary_result",
    "text": "각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 이어질 수 있었습니다.",
    "visual_goal": "각진 창문 모서리에서 재료 피로가 시작되어 동체 균열로 이어지는 과정을 보여줍니다.",
    "keyword": "modern aircraft window squarish fatigue rupture comet",
    "_canonical_visual_supply": profile,
}
plan = plan_explanation(scene5)
assert plan is not None, "real trusted supply profile must unlock deterministic Scene 5"
assert plan.get("template") == "AIRCRAFT_WINDOW_STRESS_V1", plan
assert plan.get("owned_claim_id") == "squarish_window_fatigue_rupture", plan
assert plan.get("evidence_source") == "TRUSTED_GROUNDING", plan
assert annotation_fact_safe(scene5, plan) is True

# Negative: same trusted identity/claims without evidence-owned visual
# discriminators must not produce a canonical visual supply profile. This is
# the exact pre-fix bridge gap, not a threshold relaxation.
legacy_record = deepcopy(record)
legacy_record.pop("visual_discriminators", None)
legacy_supplied = supply_trusted_subject_grounding(candidate, trusted_records=[legacy_record])
assert legacy_supplied.get("canonical_subject") == canonical
assert not legacy_supplied.get("_trusted_visual_discriminators")
assert build_canonical_visual_supply_profile(legacy_supplied) == {}

# Negative: Vision-only evidence never substitutes for trusted grounding.
vision_only_scene = dict(scene5)
vision_only_scene.pop("_canonical_visual_supply", None)
vision_only_scene["_vision_evidence"] = {"pass": True, "state": "VERIFIED"}
assert plan_explanation(vision_only_scene) is None

print("RUN 34613444148 WINDOW SCENE5 SUPPLY BRIDGE REGRESSION: PASS")
'''
    subprocess.run([sys.executable, "-c", code], check=True, cwd=repo)


def main():
    repo = _prepare_repo()
    try:
        _run_child(repo)
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    main()

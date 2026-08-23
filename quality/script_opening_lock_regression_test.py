from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Reproduce the production Apply production hotfixes order. This regression
# exists specifically to catch marker/order drift between independently layered
# hotfixes before a production run does.
HOTFIXES = (
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
    # Production re-applies this compatibility patch after later wrappers.
    "ci_aviation_context_signature_compat_hotfix.py",
)

for hotfix in HOTFIXES:
    subprocess.run([sys.executable, hotfix], cwd=ROOT, check=True)

from content import script_generator as sg
legacy = getattr(sg, "_LEGACY", sg)


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾여 있는 이유",
        "angle": "winglet causal explanation",
        "core_question": "그런데 왜 이렇게 꺾여 있을까요?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "그런데 왜 이렇게 꺾여 있을까요?",
            "reveal": "날개 끝 공기 흐름을 줄이는 구조다",
            "payoff": "와류와 유도항력을 줄이는 데 도움이 된다",
        },
        "fact_check_focus": ["wingtip vortex", "induced drag"],
        "visual_proof": ["airplane winglet close up"],
    }


def scene(text, goal="항공기 날개 끝 구조", keyword="airplane winglet close up"):
    return {"text": text, "visual_goal": goal, "keyword": keyword}


payload = {
    "title": "fixture",
    "scenes": [
        scene("LLM이 첫 문장을 질문으로 바꿨나요?"),
        scene("왜 필요한지 지금 알려드려요."),
        scene("날개 끝에서는 소용돌이가 생기는데요."),
        scene("그 흐름 때문에 저항이 생기죠."),
        scene("직접 보세요."),
    ],
}

cleaned_candidate = legacy.validate_candidate(candidate())
locked = legacy._script_opening_lock_apply(payload, cleaned_candidate)

assert locked["scenes"][0]["text"] == "비행기 날개 끝이 위로 꺾여 있습니다."
assert locked["scenes"][1]["text"] == "그런데 왜 이렇게 꺾여 있을까요?"
assert locked["scenes"][0]["visual_goal"] == "항공기 날개 끝 구조"
assert locked["scenes"][0]["keyword"] == "airplane winglet close up"
assert locked["scenes"][2]["text"] == "날개 끝에서는 소용돌이가 생깁니다."
assert locked["scenes"][3]["text"] == "그 흐름 때문에 저항이 생깁니다."
assert locked["scenes"][4]["text"] == "직접 볼 수 있습니다."

unrepairable = {
    "title": "fixture",
    "scenes": [scene("x"), scene("y"), scene("정말 놀라워요.")],
}
result = legacy._script_opening_lock_apply(unrepairable, cleaned_candidate)
assert result["scenes"][2]["text"] == "정말 놀라워요."

print("✅ Script opening lock production-order regression PASS")

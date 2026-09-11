"""Regression for Script Human Quality V1.

Authority: Run 34625637738 was machine-green but human review rejected the
narration. Its opening restated the same rounded-window proposition as a
statement and then a question; Scene 3 also received the deterministic
"원인의 첫 단서는" filler despite already containing the concrete stress clue.

This test installs the same final production writer hotfix and proves the
quality contract without making network/LLM calls or changing any budget.
"""
from __future__ import annotations

import importlib
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Exact .github/workflows/main.yml "Apply production hotfixes" order, through
# ci_writer_observable_opening_hotfix.py (the last hotfix this PR extends).
# ci_writer_observable_opening_hotfix.py's own anchors depend on several
# earlier hotfixes having already run in this exact order (Run 34601308285 /
# PR #323 established this precedent) -- most relevantly here,
# ci_script_v2_gunggeum_formal_ending_hotfix.py (chain-imports
# ci_writer_audience_comprehension_hotfix.py, which rewrites the Writer
# instruction text this PR's own anchor depends on) and
# ci_cross_process_video_dedupe_hotfix.py (chain-imports the grounded claim
# plan layer that installs _grounded_opening in content/script_engine_v2.py).
_PRODUCTION_HOTFIX_CHAIN = [
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


def _install_production_final_hotfix() -> None:
    for script in _PRODUCTION_HOTFIX_CHAIN:
        subprocess.run([sys.executable, script], cwd=ROOT, check=True)
    importlib.invalidate_caches()


def _explorer_namespace() -> dict:
    # Final-composition installers may preload a wrapper/module under the
    # content.candidate_explorer name. Execute the patched production source
    # directly so this regression cannot accidentally inspect a stale module.
    return runpy.run_path(str(ROOT / "content" / "candidate_explorer.py"))


def _candidate(*, hook: str, question: str) -> dict:
    return {
        "status": "SELECTED",
        "winner": {
            "topic": "비행기 창문 모서리는 왜 둥글까",
            "angle": "창문 모서리 형상이 응력 분포에 미치는 차이",
            "core_question": question,
            "micro_narrative": {
                "hook": hook,
                "core_question": question,
                "reveal": "둥근 모서리는 응력이 한 지점에 집중되는 정도를 줄입니다.",
                "payoff": "모서리 형상은 반복 하중을 받는 창문 주변 구조의 피로 위험과 연결됩니다.",
            },
            "fact_check_focus": [
                "초기 Comet의 각진 창문 모서리에서 높은 응력 집중이 발생했다.",
                "둥근·타원형 창문은 모서리의 응력 집중을 줄인다.",
            ],
            "visual_proof": ["각진 창문과 둥근 창문의 모서리 비교"],
            "selection_reason": "익숙한 창문 형상에 숨은 구조적 이유가 있다.",
        },
        "runner_up": None,
    }


def test_candidate_prompt_is_lock_aware() -> None:
    explorer = _explorer_namespace()
    prompt = explorer["CANDIDATE_EXPLORER_PROMPT"]
    assert "SCRIPT_HUMAN_QUALITY_V1" in prompt
    assert "Hook 다음 Core Question이 Hook과 같은 명제를 다시 묻는 구조는 금지" in prompt
    assert "그대로 읽어도 자연스러운 짧은 한 문장" in prompt
    assert "인과 범위를 넘어 더 큰 재난이나 결과로 확대하지 마라" in prompt


def test_run_346256_opening_counterexample_fails_closed() -> None:
    explorer = _explorer_namespace()
    bad = _candidate(
        hook="비행기 창문 모서리는 둥급니다.",
        question="비행기 창문 모서리가 둥글게 디자인된 이유는 무엇일까요?",
    )
    try:
        explorer["validate_explorer_output"](bad)
    except ValueError as exc:
        assert "같은 내용을 반복" in str(exc)
        return
    raise AssertionError("Run 34625637738 hook/question restatement must fail closed")


def test_progressive_opening_is_accepted() -> None:
    explorer = _explorer_namespace()
    good = _candidate(
        hook="작은 모서리 형상 차이가 반복 하중을 받는 구조의 응력 분포를 바꿉니다.",
        question="비행기 창문 모서리가 둥근 이유는 무엇일까요?",
    )
    result = explorer["validate_explorer_output"](good)
    assert result["status"] == "SELECTED"
    assert result["winner"]["micro_narrative"]["hook"].startswith("작은 모서리")


def test_stress_is_already_a_causal_clue() -> None:
    engine = runpy.run_path(str(ROOT / "content" / "script_engine_v2.py"))
    assert "응력" in engine["CAUSAL_CLUE_TOKENS"]
    repair = engine["deterministic_scene_repair"]
    text = "초기 코멧의 각진 창문 모서리에는 높은 응력이 집중됐습니다."
    repaired = repair(text, "causal_clue")
    assert repaired == text
    assert not repaired.startswith("원인의 첫 단서는")


def test_writer_and_rewrite_prompts_carry_human_quality_contract() -> None:
    runner = (ROOT / "content" / "script_engine_v2_runner.py").read_text(encoding="utf-8")
    rewrite = (ROOT / "quality" / "rewrite_engine.py").read_text(encoding="utf-8")
    assert "SCRIPT_HUMAN_QUALITY_WRITER_V1" in runner
    assert "one short sentence and one new idea" in runner
    assert "Do not strengthen causal claims beyond the supplied facts" in runner
    assert "SCRIPT_HUMAN_QUALITY_REWRITE_V1" in rewrite
    assert "Scene 1과 Scene 2가 같은 명제를" in rewrite
    assert "인과 표현은 Candidate/Fact 근거보다 강하게 키우지 않는다" in rewrite


def main() -> None:
    _install_production_final_hotfix()
    test_candidate_prompt_is_lock_aware()
    test_run_346256_opening_counterexample_fails_closed()
    test_progressive_opening_is_accepted()
    test_stress_is_already_a_causal_clue()
    test_writer_and_rewrite_prompts_carry_human_quality_contract()
    print("SCRIPT HUMAN QUALITY V1 REGRESSION: PASS")


if __name__ == "__main__":
    main()

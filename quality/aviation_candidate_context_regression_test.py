from pathlib import Path
import subprocess
import sys

subprocess.run([sys.executable, "ci_topic_input_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_aviation_candidate_context_hotfix.py"], check=True)

explorer = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
supply_recovery = Path("ci_candidate_supply_recovery_hotfix.py").read_text(encoding="utf-8")
production_hotfix = Path("ci_hotfix.py").read_text(encoding="utf-8")
candidate_gate = Path("content/candidate_gate.py").read_text(encoding="utf-8")

required = (
    "SHORTS_CANDIDATE_SCOPE",
    "[THIS RUN ONLY - AVIATION CANDIDATE SUPPLY CONTEXT]",
    "최소 10개의 서로 다른 grounded seed",
    "[SEPARATION OF RESPONSIBILITIES]",
    "[SUPPLY SHORTAGE IS NOT A TERMINAL RESULT]",
    "[DO NOT SELF-WITHHOLD]",
    "[BOUNDED RETRY DISCIPLINE]",
    "Gate 기준을 낮추지 마라",
)
for item in required:
    assert item in explorer, item

# Production Run 32646061801 exhausted attempts after Explorer began returning
# REGENERATE only because it could not supply enough distinct candidates.
# A single viable grounded candidate must still reach the independent Gate.
for item in (
    "위 최소 10개는 탐색 목표이지 SELECTED를 반환하기 위한 최소 통과 숫자가 아니다",
    "grounded하고 구체적이며 필수 필드가 완성된 Candidate가 1개라도 남아 있다면 후보 수가 목표보다 적다는 이유만으로 REGENERATE를 반환하지 마라",
    "runner_up은 null이어도 된다",
    "REGENERATE는 usable grounded Candidate가 0개인 경우",
    "후보 공급 부족",
    "이 규칙은 Candidate Gate를 우회하지 않는다",
):
    assert item in explorer, item

# Generation must not self-withhold candidates for downstream editorial reasons.
for item in (
    "predictable payoff, weak payoff, novelty 부족 같은 편집적 판단 때문에 후보를 생성 단계에서 숨기거나 0개로 만들지 마라",
    "실제 탈락 여부는 기존 Gate가 결정한다",
    "후보가 Gate에서 약할 것 같다는 이유로 전체 Candidate pool을 비우고 재시도하지 마라",
):
    assert item in explorer, item

# Authority Run 33878093224 showed the previous context contradicted the supply
# separation contract later in the same prompt: after saying predictable / weak
# payoff must reach the independent Candidate Gate, it re-required the Explorer's
# editorial final-sanity/novelty filters as terminal selection gates. Six distinct
# aviation directions then self-returned zero usable grounded supply. The aviation
# scope must explicitly make editorial final-sanity criteria ranking-only at the
# supply boundary while keeping structural/factual hard gates fail-closed.
for item in (
    "[AVIATION SUPPLY PRECEDENCE — RUN 33878093224]",
    "편집적 final sanity와 novelty 판단은 후보 간 순위를 정하는 데만 사용",
    "BROAD / GENERIC QUESTION",
    "GENERIC REVEAL",
    "PREDICTABLE PAYOFF",
    "Candidate pool을 0개로 만들거나 REGENERATE를 반환하는 근거로 사용하지 마라",
    "구조·사실성 Hard Gate는 그대로 fail-close",
    "독립 Candidate Gate가 최종 편집성 PASS/REGENERATE authority",
):
    assert item in explorer, item

# The old contradictory terminal instruction must no longer exist in aviation
# supply context. It made the supply layer re-enforce the downstream Gate's job.
assert (
    "후보 비교와 최종 Winner 선택에서는 기존 Candidate Explorer의 Hard Gate, scoring, shortlist, final sanity, novelty/중복 회피 기준을 그대로 적용하라."
    not in explorer
)

# The one bounded zero-supply recovery call must preserve the same aviation
# separation instead of re-imposing the generic terminal final-sanity wording.
for item in (
    "[AVIATION SUPPLY RECOVERY PRECEDENCE — RUN 33878093224]",
    "BROAD / GENERIC QUESTION, GENERIC REVEAL, PREDICTABLE PAYOFF",
    "editorial signals only to rank surviving supply candidates",
    "unchanged independent Candidate Gate",
    "For non-aviation scopes, run the normal Candidate Explorer hard gates and final",
):
    assert item in supply_recovery, item
assert (
    "Run the SAME Candidate Explorer hard gates and final sanity check from the"
    not in supply_recovery
)

# Hard structural / grounding exclusions remain explicit.
for item in (
    "placeholder / 빈 필드 / 추상적인 시스템명만 있는 항목",
    "같은 질문·reveal·mechanism의 사실상 중복",
    "실제 존재나 인과관계가 의심스러워 이야기를 발명해야 하는 항목",
):
    assert item in explorer, item

# Run 33883590214: the #281 aviation separation lived only in user execution
# context, while the same call's system prompt retained terminal editorial rules.
# The correction must exist at SYSTEM authority and explicitly scope the override
# to aviation supply only, after the legacy Final Sanity language it overrides.
system_marker = "[AVIATION SYSTEM-AUTHORITY SUPPLY CONTRACT — RUN 33883590214]"
assert system_marker in explorer
assert explorer.index(system_marker) > explorer.index("12. FINAL SANITY CHECK")
for item in (
    "same SYSTEM-prompt authority",
    "PREDICTABLE PAYOFF",
    "WEAK PAYOFF / SO WHAT?",
    "GENERIC EXPLANATION / BROAD THEME",
    "weak novelty",
    "ranking/preference signals only",
    "must not be the sole reason to return REGENERATE",
    "structural/factual supply failures remain terminal",
    "independent Candidate Gate remains the editorial authority",
    "For non-aviation scopes, keep Sections 7 and 12 unchanged",
):
    assert item in explorer, item

# A: editorially weak but grounded/structural aviation supply survives to Gate.
assert "return SELECTED with the strongest surviving Candidate" in explorer
# B/C: factual/grounding and aviation-scope failures remain fail-closed.
for item in (
    "fabricated or unsupported causal claim",
    "grounding/evidence insufficient",
    "aviation scope violation",
    "visual-proof requirement failure",
):
    assert item in explorer, item
# D: malformed schema remains host-side invalid; no schema relaxation is installed.
assert "Candidate Explorer status는" in explorer
assert "winner.visual_proof" in explorer
# E: independent Candidate Gate is untouched and remains capable of REGENERATE.
assert "def evaluate_candidate" in candidate_gate
assert '"REGENERATE"' in candidate_gate
# F: bounded recovery stays exactly 1/1 and uses the same system prompt object.
assert "CANDIDATE SUPPLY RECOVERY (1/1)" in supply_recovery
assert '"content": CANDIDATE_EXPLORER_PROMPT' in supply_recovery
# G: non-aviation semantics are explicitly preserved by the new system contract.
assert "For non-aviation scopes, keep Sections 7 and 12 unchanged" in explorer

# Deterministic host-side observability: do not fabricate model-internal counts.
for item in (
    "CANDIDATE_SUPPLY_OBSERVABILITY_V1",
    "final_zero_stage=model_output_pre_host_candidate_validation",
    "discard_reason_code=ZERO_USABLE_GROUNDED",
    "model_internal_candidate_counts=unavailable",
):
    assert item in explorer, item
assert "candidate_count_before_filter=" not in explorer

# Fixed topic mode returns before the optional automatic run scope is read.
assert explorer.index("if fixed_topic:") < explorer.index("SHORTS_CANDIDATE_SCOPE")
assert "winner.topic은 반드시 아래 문자열과" in explorer
assert "result[\"runner_up\"] = None" in explorer

# Production chain remains intact; aviation context is appended after topic-input support.
chain = (
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
)
positions = [workflow.index(name) for name in chain]
assert positions == sorted(positions)
assert "SHORTS_TOPIC: ${{ inputs.topic }}" in workflow
assert "SHORTS_CANDIDATE_SCOPE: ${{ inputs.candidate_scope }}" in workflow

# Authority safety invariants: no retry or budget expansion is part of this fix.
assert '"MAX_TOPIC_REGENERATIONS = 6"' in production_hotfix
assert 'V3_MAX_API_CALLS: "60"' in workflow
assert 'V3_MAX_COST_USD: "0.05"' in workflow

print("PASS: Run 33883590214 aviation system/user authority conflict removed without Gate relaxation")

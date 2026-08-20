from pathlib import Path
import subprocess
import sys

subprocess.run([sys.executable, "ci_topic_input_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_aviation_candidate_context_hotfix.py"], check=True)

explorer = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")

required = (
    "SHORTS_CANDIDATE_SCOPE",
    "[THIS RUN ONLY - AVIATION EXPLORATION CONTEXT]",
    "서로 실질적으로 다른 후보를 최소 10개",
    "Pexels/Pixabay",
    "기존 novelty/중복 회피 기준은 그대로 적용한다",
)
for item in required:
    assert item in explorer, item

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

print("PASS: aviation run scope, >=10 exploration instruction, fixed topic preservation, hotfix chain")

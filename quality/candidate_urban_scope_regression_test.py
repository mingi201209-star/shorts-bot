from pathlib import Path
import subprocess
import sys


subprocess.run([sys.executable, "ci_topic_input_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_candidate_urban_scope_hotfix.py"], check=True)

explorer = Path("content/candidate_explorer.py").read_text(encoding="utf-8")
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")

required_scope = (
    "[AUTOMATIC TOPIC SCOPE]",
    "- 도시",
    "- 건축",
    "- 초고층 건물",
    "- 도시 인프라",
    "- 도로, 교량, 터널",
    "- 지하 공간",
    "- 도시 설계",
    "- 건축에 숨겨진 기능",
)
for item in required_scope:
    assert item in explorer, item

# Fixed topic mode must return before the automatic-scope execution context.
fixed_index = explorer.index("[EXECUTION CONTEXT - FIXED PRODUCTION TOPIC]")
auto_index = explorer.index("[AUTOMATIC TOPIC SCOPE]")
assert fixed_index < auto_index
assert "winner.topic은 반드시 아래 문자열과" in explorer
assert "result[\"runner_up\"] = None" in explorer

# Preserve the existing production hotfix chain and append only this scope patch.
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
    "ci_candidate_urban_scope_hotfix.py",
)
positions = [workflow.index(name) for name in chain]
assert positions == sorted(positions)

print("PASS: automatic urban scope, fixed topic preservation, production hotfix chain")

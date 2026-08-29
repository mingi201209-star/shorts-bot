import importlib
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for hotfix in (
    "ci_design_causality_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
):
    runpy.run_path(str(ROOT / hotfix), run_name="__main__")

sg = importlib.reload(importlib.import_module("content.script_generator"))
runtime = getattr(sg, "_SCRIPT_PARITY_RUNTIME", None) or getattr(sg, "_LEGACY", None)
assert runtime is not None

context = {
    "topic": "비행기 날개 뒤쪽 플랩은 왜 이착륙 때 펼쳐질까",
    "angle": "플랩이 낮은 속도에서 필요한 양력을 만드는 이유",
    "core_question": "왜 이착륙 때만 플랩을 펼치는가",
}
runtime._SCRIPT_PARITY_ACTIVE_CONTEXT = context

scene_contract = runtime._adaptive_scene_count_instruction(context)
duration_contract = runtime._adaptive_duration_instruction(context)
length_contract = runtime._adaptive_length_instruction(context)

assert "Scene 수는 목표가 아니라 상한/가이드" in scene_contract
assert "보통 6~7 Scene" in scene_contract
assert "hard minimum이 아니다" in scene_contract
assert "5 Scene 이하도 허용" in scene_contract
assert "8 Scene 이상" in scene_contract
assert "Scene 수를 채우기 위한 mechanism_n" in scene_contract

for phrase in (
    "새 사실",
    "새 원인 또는 메커니즘",
    "새 의문",
    "반전 또는 대조",
    "payoff 진전",
    "의미 있는 visual 변화",
    "무엇이 새 정보인지 답할 수 없으면 그 Scene을 만들지 마라",
):
    assert phrase in scene_contract, phrase

for phrase in ("중요합니다", "핵심 역할을 합니다", "성능을 높입니다", "도움이 됩니다"):
    assert phrase in scene_contract
assert "새 정보 없이 앞 내용을 요약할 뿐이면" in scene_contract

assert "20~35초" in duration_contract
assert "18~20초" in duration_contract
assert "목표 시간을 채우려고 내용을 늘리지 말고" in duration_contract
assert "목표 시간을 채우기 위해 문장이나 Scene을 추가하지 마라" in length_contract
assert "설명이 끝났다면 즉시 종료" in length_contract
assert "하나의 자연스러운 인과" in length_contract

source = (ROOT / "content" / "script_generator.py").read_text(encoding="utf-8")
assert "{_adaptive_scene_count_instruction(candidate)}" in source
assert "{_adaptive_duration_instruction(candidate)}" in source
assert "[LENGTH]\n{_adaptive_length_instruction(candidate)}\n\n[OUTPUT]" in source

assert hasattr(runtime, "retention_story_compress_scenes")

print("PASS: Retention Story V2 Writer contract is stop-when-complete and scene-value driven")

from pathlib import Path

hotfix = Path("ci_script_validation_recovery_hotfix.py").read_text(encoding="utf-8")
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")

required = [
    "SCRIPT_VALIDATION_RECOVERY_V2_GROUNDED_SPECIFICITY",
    "specific_observation",
    "constraint",
    "counterintuitive_result",
    "tradeoff",
    "concrete_condition",
    "같은 mechanism/result를 어휘만 바꿔 반복하지 마라",
    "설계형 최소 장면 수를 먼저 확보하되 filler를 추가하지 마라",
]
for needle in required:
    assert needle in hotfix, needle

assert "python ci_script_validation_recovery_hotfix.py" in workflow
assert "V3_MAX_API_CALLS: 60" in workflow or "V3_MAX_API_CALLS: \"60\"" in workflow
assert "V3_MAX_COST_USD: 0.05" in workflow or "V3_MAX_COST_USD: \"0.05\"" in workflow
assert "AI_VISUAL_FALLBACK_ENABLED: false" in workflow or "AI_VISUAL_FALLBACK_ENABLED: \"false\"" in workflow

print("SCRIPT CAUSAL RETRY GROUNDING REGRESSION: PASS")
print("CASE A grounded specificity preserved: PASS")
print("CASE B causal paraphrase retry guidance: PASS")
print("CASE C adaptive scene-count recovery without filler: PASS")
print("CASE D API/cost/Sora policy unchanged: PASS")

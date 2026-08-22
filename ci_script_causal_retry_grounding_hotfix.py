from pathlib import Path

src = Path("ci_script_validation_recovery_hotfix.py").read_text(encoding="utf-8")
assert "SCRIPT_VALIDATION_RECOVERY_V2_GROUNDED_SPECIFICITY" in src
assert "specific_observation" in src
assert "설계형 주제의 최소 장면 수를 먼저 확보하되 filler를 추가하지 마라" in src
print("SCRIPT CAUSAL RETRY GROUNDING HOTFIX PROBE: PASS")

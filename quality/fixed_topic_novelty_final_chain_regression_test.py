from pathlib import Path
import re

text = Path("ci_script_v2_visual_goal_hotfix.py").read_text(encoding="utf-8")
assert "final-chain branch not found; skipping lock without blocking production" in text
assert "re.MULTILINE" in text
assert 'status\\s*==\\s*["\\\']REGENERATE_TOPIC["\\\']' in text
assert 'raise RuntimeError(f"fixed-topic Novelty final-chain marker mismatch' not in text
print("PASS: final-chain fixed-topic Novelty installer cannot block production on marker drift")

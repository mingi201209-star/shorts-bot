import importlib
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

main_before = (ROOT / "main.py").read_text(encoding="utf-8")
gate_before = (ROOT / "content" / "candidate_gate.py").read_text(encoding="utf-8")

assert "NOVELTY_HARD_REGENERATE_SCORE = 5.0" in main_before
assert "CANDIDATE_NOVELTY_PARITY_V1" not in gate_before

runpy.run_path(str(ROOT / "ci_novelty_budget_hotfix.py"), run_name="__main__")

main_after = (ROOT / "main.py").read_text(encoding="utf-8")
gate_after = (ROOT / "content" / "candidate_gate.py").read_text(encoding="utf-8")

# Existing downstream threshold and bounded rewrite contract remain unchanged.
assert "NOVELTY_HARD_REGENERATE_SCORE = 5.0" in main_after
assert "MAX_REWRITES = 1" in main_after

# Production Candidate Gate now carries the same novelty intent before Script/Judges.
assert "CANDIDATE_NOVELTY_PARITY_V1" in gate_after
assert "후단 Novelty Judge와 같은 방향" in gate_after
assert "구체적이지만 예상 가능한 Candidate" in gate_after
assert "비행 중 기내에서 중력이 느껴지는 방식" in gate_after
assert "후단 Rewrite로 해결할 문제가 아니라 Candidate 자체가 약한 것" in gate_after

# Familiar subjects are not banned: the contract explicitly preserves surprising reveals.
assert "익숙한 비행기 소재라도" in gate_after
assert "숨은 설계 제약" in gate_after

# Patch must stay idempotent, because production hotfix chains can be re-applied in tests.
runpy.run_path(str(ROOT / "ci_novelty_budget_hotfix.py"), run_name="__main__")
gate_twice = (ROOT / "content" / "candidate_gate.py").read_text(encoding="utf-8")
assert gate_twice.count("CANDIDATE_NOVELTY_PARITY_V1") == 1

# Importability after the production mutation is the minimum runtime parity check.
sys.modules.pop("content.candidate_gate", None)
gate = importlib.import_module("content.candidate_gate")
assert "CANDIDATE_NOVELTY_PARITY_V1" in gate.GATE_SYSTEM_PROMPT
assert "구체적이지만 예상 가능한 Candidate" in gate.GATE_SYSTEM_PROMPT

print("PASS: Candidate Gate novelty parity; no threshold relaxation or extra API call")

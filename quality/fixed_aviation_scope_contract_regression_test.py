from pathlib import Path
import os
import runpy
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

subprocess.run([sys.executable, "ci_aviation_candidate_context_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_aviation_candidate_specificity_hotfix.py"], check=True)
subprocess.run([sys.executable, "ci_aviation_context_signature_compat_hotfix.py"], check=True)

source = (ROOT / "content" / "candidate_explorer.py").read_text(encoding="utf-8")
assert "FIXED_AVIATION_SCOPE_CONTRACT_V1" in source

# This regression never makes an API call; candidate_explorer only needs the
# module to exist while its functions are loaded.
sys.modules.setdefault("openai", types.SimpleNamespace())
namespace = runpy.run_path(
    str(ROOT / "content" / "candidate_explorer.py"),
    run_name="fixed_aviation_scope_regression_runtime",
)
ce = types.SimpleNamespace(**namespace)

# Exact production shape: fixed topic, candidate_scope intentionally blank.
os.environ["SHORTS_CANDIDATE_SCOPE"] = ""
context = ce.build_execution_context(
    {"category": "항공", "topic": "윙렛"},
    fixed_topic="비행기 날개 끝의 윙렛은 왜 위로 꺾여 있을까",
    fixed_topic_gate_feedback="질문이 지나치게 넓고 Reveal이 일반적이다.",
)
assert "FIXED AVIATION TOPIC — CONCRETE MECHANISM CONTRACT" in context
assert "날개 끝 와류" in context
assert "압력 차" in context
assert "유도항력" in context
assert "질문이 지나치게 넓고 Reveal이 일반적이다." in context

# A non-aviation fixed topic with blank scope must not receive aviation guidance.
other = ce.build_execution_context(
    {"category": "일반", "topic": "건축"},
    fixed_topic="로마 콘크리트는 왜 오래 버틸까",
)
assert "FIXED AVIATION TOPIC — CONCRETE MECHANISM CONTRACT" not in other

print("PASS: blank-scope fixed aviation topic receives concrete mechanism contract; no API/Sora calls")

from pathlib import Path

path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

marker = '''[MECHANISM DEPTH — REQUIRED]\n영상의 가장 중요한 주장 1~2개는 단순 사실 나열에서 멈추지 않는다.\n'''
replacement = '''[PROBLEM → SOLUTION NARRATIVE — EVIDENCE GATED]\n단순 백과사전식 사실 나열보다 시청자가 "왜 이런 형태/기능이 필요해졌는가"를 따라갈 수 있는 작은 서사를 우선한다.\nCandidate의 fact_check_focus, micro_narrative, visual_proof 안에 실제 문제·위험·제약·실패·불편과 그에 대응하는 설계/해결책이 근거로 존재한다면 본문에 다음 흐름을 반드시 만든다:\n관찰/Hook → 문제 또는 제약 → 왜 그것이 문제가 되는가 → 해결/설계 변화 → 작동 원리 → 결과/Payoff.\n문제와 해결은 서로 직접 연결되어야 하며, 해결책이 무엇을 줄이거나 막거나 가능하게 하는지 명시한다.\n예를 들어 특정 구조가 응력 집중을 줄이기 위한 것이라는 근거가 Candidate에 있다면, 단순히 "안전하다"고 끝내지 말고 문제였던 집중 → 구조 변화 → 힘이 분산되는 결과까지 연결한다.\n단, Candidate에 문제·사고·역사적 실패·설계 변경의 근거가 없다면 절대로 극적인 문제나 사고 사례를 만들어내지 않는다. 이 경우에는 현상 → 의문 → 원인 → mechanism → 결과 구조를 사용한다.\n역사적 사건, 사망자, 사고명, 연도, 최초 설계 같은 정보는 Candidate에 명시되어 있을 때만 사용한다.\n목표는 모든 소재에 억지 갈등을 넣는 것이 아니라, 검증 가능한 문제-해결 관계가 있는 소재에서 설명을 이야기로 바꾸는 것이다.\n\n[MECHANISM DEPTH — REQUIRED]\n영상의 가장 중요한 주장 1~2개는 단순 사실 나열에서 멈추지 않는다.\n'''

if replacement in text:
    print("ℹ️ Problem-solution narrative guidance already applied")
elif text.count(marker) != 1:
    raise RuntimeError(f"Problem-solution marker mismatch: {text.count(marker)}")
else:
    text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")
    print("✅ Evidence-gated problem-solution narrative guidance applied")

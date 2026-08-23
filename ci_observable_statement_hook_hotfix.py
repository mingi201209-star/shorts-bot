from pathlib import Path

path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")
marker = "OBSERVABLE_STATEMENT_HOOK_V2"

# Prompt contract: Scene 1 is not merely preferred to be an observation.  The
# downstream retention contract requires it, so Hook selection must enforce the
# same contract upstream before a Hook can ever become approved/locked.
if marker not in text:
    anchor = '- 첫 구절에 구체적 대상 이름을 바로 넣는다.\n'
    addition = '''- OBSERVABLE_STATEMENT_HOOK_V2: 모든 Hook 후보는 첫 화면에서 즉시 확인 가능한 외형/움직임/배치 특징을 말하는 관찰형 평서문이어야 한다.\n- Hook 후보 자체에 질문을 넣지 않는다. 물음표(?)와 ~까요?/~나요?/~어요?/~예요? 질문형은 Hook 후보에서 금지한다.\n- 예: "비행기 날개 끝이 위로 꺾여 있습니다."처럼 시청자가 첫 화면에서 바로 확인할 수 있는 사실을 격식체로 먼저 말한다.\n- 질문은 Hook Selector가 만들지 않는다. 다음 Script Scene 2가 "그런데 왜 이렇게 꺾여 있을까요?"처럼 별도로 질문한다.\n- 관찰형 진술은 Candidate의 visual_proof/micro_narrative에서 직접 뒷받침되는 사실만 사용하고 새 사실을 만들지 않는다.\n'''
    if anchor not in text:
        raise RuntimeError("hook prompt anchor not found")
    text = text.replace(anchor, anchor + addition, 1)

# Deterministic gate: a question-shaped candidate must never enter the scoring
# pool, regardless of model self-score.  This prevents a selected question Hook
# from being locked into Scene 1 and then failing the retention validator on every
# Script retry.
gate_marker = '''        diagnostics["shape_valid_count"] += 1

        speech_valid, _ = validate_korean_speech_text(
'''
gate_replacement = '''        # OBSERVABLE_STATEMENT_HOOK_V2_GATE
        if "?" in text or text.rstrip().endswith(("까요", "나요", "어요", "예요")):
            diagnostics["rejected"]["question_hook_not_allowed"] += 1
            continue

        diagnostics["shape_valid_count"] += 1

        speech_valid, _ = validate_korean_speech_text(
'''
if "OBSERVABLE_STATEMENT_HOOK_V2_GATE" not in text:
    if text.count(gate_marker) != 1:
        raise RuntimeError(
            "observable Hook deterministic gate marker mismatch: "
            f"{text.count(gate_marker)}"
        )
    text = text.replace(gate_marker, gate_replacement, 1)

# Make bounded retry feedback actionable if a model still emits question Hooks.
feedback_anchor = '''이전 탈락 사유가 있으면 가장 많이 발생한 사유부터 이번 출력에서 직접 고친다.\n'''
feedback_addition = '''question_hook_not_allowed가 있으면 질문을 제거하고, 화면에서 보이는 현상을 ~습니다/~있습니다 평서문으로 다시 쓴다. 질문은 다음 Script Scene 2의 역할이다.\n'''
if feedback_addition not in text and feedback_anchor in text:
    text = text.replace(feedback_anchor, feedback_anchor + feedback_addition, 1)

path.write_text(text, encoding="utf-8")
print("✅ Observable statement Hook V2 upstream contract enforced")

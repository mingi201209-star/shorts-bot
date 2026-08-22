from pathlib import Path

path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")
marker = "OBSERVABLE_STATEMENT_HOOK_V1"
if marker not in text:
    anchor = '- 첫 구절에 구체적 대상 이름을 바로 넣는다.\n'
    addition = '''- OBSERVABLE_STATEMENT_HOOK_V1: 화면에서 즉시 확인 가능한 외형/움직임/배치 특징이 있으면 첫 Hook은 질문형보다 관찰형 진술을 우선한다.\n- 예: "비행기의 날개 끝은 위로 꺾여 있습니다."처럼 시청자가 첫 화면에서 바로 확인할 수 있는 사실을 먼저 말한다.\n- "왜 ~일까요?"로 바로 시작하지 말고, 가능한 경우 관찰을 먼저 말한 뒤 다음 대본 문장에서 궁금증/이유 질문으로 이어지게 한다.\n- 관찰형 진술은 Candidate의 visual_proof/micro_narrative에서 직접 뒷받침되는 사실만 사용하고 새 사실을 만들지 않는다.\n'''
    if anchor not in text:
        raise RuntimeError("hook prompt anchor not found")
    text = text.replace(anchor, anchor + addition, 1)
path.write_text(text, encoding="utf-8")
print("✅ Observable statement Hook preference applied")

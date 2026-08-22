from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

length_marker = '''- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다.
'''
length_replacement = '''- 안정적으로 하한을 넘기되 상한 초과를 피하도록 14~15자를 목표로 쓴다. 16자는 허용 상한이지 생성 목표가 아니다.
- 숫자 글자 수만 맞추려 하지 말고 text를 4~5개의 짧은 한국어 어절로 구성한다.
- 각 text에는 반드시 (1) 구체적 대상명, (2) 구체적 부위/구조/관찰 단서, (3) 눈으로 확인 가능한 동작/결과가 모두 들어간다.
- 관찰형 Hook도 설명을 덧붙여 17자 이상으로 늘리지 않는다. 첫 문장은 한 가지 보이는 사실만 말하고 이유/메커니즘은 다음 대사로 넘긴다.
- "드론이 균열을 찾아요"처럼 너무 짧은 문장은 구체 단서 1개만 추가하되, 수식어를 겹쳐 상한을 넘기지 않는다.
'''

feedback_marker = '''길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.
'''
feedback_replacement = '''길이 탈락이면 14~15자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.
too_short가 발생했다면 구체적인 부위/구조/관찰 단서 1개만 추가한다.
too_long이 발생했다면 핵심 대상+관찰은 유지하고 이유, 배경, 수식어를 삭제해 14~15자로 다시 쓴다. 관찰과 이유를 한 Hook에 합치지 않는다.
'''

for name, marker, replacement in (
    ("length structure", length_marker, length_replacement),
    ("retry structure", feedback_marker, feedback_replacement),
):
    if replacement in text:
        continue
    if text.count(marker) != 1:
        raise RuntimeError(
            f"Hook {name} marker mismatch: {text.count(marker)}"
        )
    text = text.replace(marker, replacement, 1)

path.write_text(text, encoding="utf-8")
print("✅ Hook bounded 14-15-char observable guidance applied")

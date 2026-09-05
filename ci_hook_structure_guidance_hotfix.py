from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

length_marker = '''- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다.\n'''
length_replacement = '''- Hook text는 공백 제외 실제 한글 글자 수 기준 14~15자를 목표로 쓴다. 13자 이하는 절대 출력하지 않는다.\n- 출력하기 직전에 각 후보의 text 글자 수를 직접 세고, 13자 이하면 구체 단서를 추가해 14~15자로 고친 뒤 JSON에 넣는다.\n- 숫자 글자 수만 맞추려 하지 말고 text를 4~5개의 짧은 한국어 어절로 구성한다.\n- 각 text에는 반드시 (1) 구체적 대상명, (2) 구체적 부위/구조/관찰 단서, (3) 눈으로 확인 가능한 동작/결과가 모두 들어간다.\n- 모든 Hook은 설명형 평서문 '~다/~이다' 문체로 끝낸다. '~요/~습니다/~입니다/~죠/~세요' 같은 존댓말 종결은 사용하지 않는다.\n- 관찰형 Hook도 설명을 덧붙여 17자 이상으로 늘리지 않는다. 첫 문장은 한 가지 보이는 사실만 말하고 이유/메커니즘은 다음 대사로 넘긴다.\n- "드론이 균열을 찾는다"처럼 너무 짧은 문장은 구체 단서 1개만 추가하되, 수식어를 겹쳐 상한을 넘기지 않는다.\n'''

feedback_marker = '''길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.\n'''
feedback_replacement = '''길이 탈락이면 공백 제외 14~15자 목표를 우선하고, speech_style_failure면 반드시 '~다/~이다' 평서문 종결을 사용한다. '~요/~습니다/~입니다/~죠/~세요' 종결은 재생성한다.\ntoo_short가 발생했다면 기존 문장을 그대로 반복하지 말고 구체적인 부위/구조/관찰 단서 1개를 추가한 뒤, 출력 전 글자 수를 다시 세어 최소 14자인지 확인한다.\ntoo_long이 발생했다면 핵심 대상+관찰은 유지하고 이유, 배경, 수식어를 삭제해 14~15자로 다시 쓴다. 관찰과 이유를 한 Hook에 합치지 않는다.\n'''

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
print("✅ Hook bounded 14-15-char observable plain-da guidance applied")

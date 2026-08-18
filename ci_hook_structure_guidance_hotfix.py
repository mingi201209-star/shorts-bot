from pathlib import Path


path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")

length_marker = '''- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다.
'''
length_replacement = '''- 안정적으로 하한을 넘기도록 15~16자를 목표로 쓴다.
- 숫자 글자 수만 맞추려 하지 말고 text를 5~6개의 짧은 한국어 어절로 구성한다.
- 각 text에는 반드시 (1) 구체적 대상명, (2) 구체적 부위/구조/관찰 단서, (3) 눈으로 확인 가능한 동작/결과가 모두 들어간다.
- "드론이 균열을 찾아요"처럼 대상+동작만 있는 3~4어절 문장은 너무 짧으므로 출력하지 않는다.
'''

feedback_marker = '''길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.
'''
feedback_replacement = '''길이 탈락이면 15~16자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.
too_short가 발생했다면 기존 짧은 문장에 구체적인 부위/구조/관찰 단서를 1~2어절 추가해 5~6어절 문장으로 만든다.
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
print("✅ Hook concrete 5-6-eojeol generation guidance applied")

from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label} marker count mismatch: {count}")
    return text.replace(marker, replacement, 1)


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")

    marker = '''    return f"""
[EXECUTION CONTEXT]

이번 탐색의 넓은 분야:
{category}
'''

    replacement = '''    run_scope = os.environ.get(
        "SHORTS_CANDIDATE_SCOPE",
        "",
    ).strip().lower()

    scope_context = ""
    if run_scope == "aviation":
        scope_context = """
[THIS RUN ONLY - AVIATION EXPLORATION CONTEXT]

이번 자동 탐색은 비행기/항공 범위 안에서만 수행하라.
특정 세부 소재를 미리 정하지 말고, 서로 실질적으로 다른 후보를 최소 10개 먼저 탐색한 뒤 기존 Candidate Explorer의 Hard Gate, scoring, shortlist, final sanity 규칙으로 경쟁시켜라.

탐색 방향 예시:
- 여객기의 숨겨진 기능
- 기내에서 사람들이 자주 궁금해하는 것
- 비행 중 일어나는 현상
- 조종석/객실의 특이한 설계
- 비행기 안전장치
- 공항/활주로의 숨겨진 시스템
- 사람들이 흔히 잘못 알고 있는 항공 상식
- 비행기를 타면서 한 번쯤 궁금했을 법한 질문

위 항목은 방향 예시일 뿐 특정 소재를 hard-code한 목록이 아니다.

[AVIATION NOVELTY SEARCH CONTRACT]

항공 분야에서 가장 먼저 떠오르는 교과서식 질문을 Candidate로 제출하지 마라.
대상의 대표 기능이나 현상의 기본 원리를 설명하는 것만으로 끝나는 질문은 탐색용 seed일 뿐 최종 후보가 아니다.

각 seed마다 한 단계 더 파고들어 다음 중 하나가 실제로 존재하는 경우에만 Candidate로 승격하라:
- 눈에 보이는 작은 구조의 예상 밖의 구체적 목적
- 서로 충돌하는 두 설계 요구 사이의 trade-off
- 공간·무게·압력·속도·소음·열·안전 같은 제약 때문에 생긴 우회 설계
- 정상 상황보다 예외/고장/비상 조건에서 진짜 목적이 드러나는 장치
- 승객의 직관과 실제 작동 방식이 반대인 mechanism
- 한 부품의 형태나 위치가 다른 시스템의 요구 때문에 결정된 연결
- 흔히 알려진 설명만으로는 설명되지 않는 두 번째 인과 단계

Candidate를 제출하기 전에 스스로 다음 테스트를 수행하라.

1. Core Question만 읽고 일반 시청자가 Reveal의 핵심을 한 문장으로 쉽게 맞힐 수 있는가?
2. Reveal이 사실상 "안전하려고", "압력을 맞추려고", "소음을 줄이려고", "공기를 공급하려고", "효율을 높이려고" 같은 목적어 하나로 끝나는가?
3. 학교/백과사전의 첫 문단 수준의 기본 원리 설명만으로 이야기가 끝나는가?

하나라도 YES라면 그 Candidate를 그대로 제출하지 말고 더 구체적인 구조·제약·trade-off·두 번째 causal step을 찾아라. 실제로 그런 deeper layer가 확실하지 않으면 후보를 버려라. 흥미를 위해 deeper layer를 발명해서는 안 된다.

좋은 항공 Candidate는 "왜 X일까? → X의 대표 기능"이 아니라, 익숙한 비행기 장면을 본 뒤에도 시청자가 쉽게 예상하지 못할 구체적인 설계 이유나 작동 연결을 가져야 한다.

후보 비교에서는 기존 점수와 gate를 변경하지 않은 채 다음 특성이 강한 후보를 우선 탐색하라:
- 대중적 호기심과 강한 curiosity gap
- 첫 1~3초 안에 즉시 이해 가능한 Hook 가능성
- 정답을 초반에 전부 공개하지 않고 payoff까지 retention을 만들 수 있음
- Pexels/Pixabay 무료 영상으로 의미가 맞는 시각 자료를 확보할 가능성이 높음
- 핵심 사실을 신뢰할 수 있는 자료로 검증 가능함

너무 전문적인 항공공학 설명이나 화면으로 표현하기 어려운 소재는 피하라.
흔하게 소비된 소재도 답이 너무 뻔하지 않고 강한 Hook/Payoff를 만들 수 있다면 허용한다.
기존 novelty/중복 회피 기준은 그대로 적용한다.
"""

    return f"""
[EXECUTION CONTEXT]
{scope_context}

이번 탐색의 넓은 분야:
{category}
'''

    text = replace_once(text, marker, replacement, "aviation execution context")
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ aviation candidate run context hotfix applied")


if __name__ == "__main__":
    main()

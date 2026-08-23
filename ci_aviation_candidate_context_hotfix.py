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
[THIS RUN ONLY - AVIATION CANDIDATE SUPPLY CONTEXT]

이번 자동 탐색은 비행기/항공 범위 안에서만 수행하라.
초기 채널의 핵심 관심군은 '승객이 실제로 봤지만 이유는 몰랐던 것'이다.

[SEPARATION OF RESPONSIBILITIES]
이 단계에서 너의 첫 임무는 완벽한 Winner 하나를 스스로 검열해 제출하는 것이 아니다.
먼저 기존 Candidate Gate가 실제로 비교할 수 있도록 서로 실질적으로 다른 구체적이고 사실 기반인 Story Candidate를 충분히 공급하라.

중요:
- predictable payoff, weak payoff, novelty 부족 같은 편집적 판단 때문에 후보를 생성 단계에서 숨기거나 0개로 만들지 마라.
- 그런 편집적 품질 판단은 아래 기존 Hard Gate / scoring / shortlist 단계의 책임이다.
- 생성 단계에서는 '이 후보가 Gate에서 질 수도 있다'는 이유만으로 버리지 마라.
- 단, 존재 자체가 의심스럽거나 인과를 발명해야 하는 후보, 도시전설, placeholder, 명백한 허구는 생성 단계에서도 금지한다.

[AVIATION SUPPLY TARGET]
최종 평가 전에 내부적으로 최소 10개의 서로 다른 grounded seed를 먼저 탐색하라.
그중 가능한 한 여러 개를 실제 Candidate record로 유지하여 기존 Gate가 비교하게 하라.
모든 후보가 완벽할 필요는 없다. Gate가 경쟁시킬 수 있을 정도로 구체적이고 사실 기반이면 된다.

각 Candidate는 다음을 갖춰야 한다:
1. 승객이 좌석/창문/객실/탑승/이륙/비행/착륙 과정에서 직접 보고·듣고·느낄 수 있는 단일 관찰 대상 또는 행동
2. 그 대상을 직접 묻는 구체적인 core_question
3. '안전/효율/편의 때문'만으로 끝나지 않는 실제 mechanism, constraint, trade-off 또는 causal step
4. 첫 화면에서 무엇을 보여줄지 설명 가능한 visual_proof
5. 후단 Fact Judge가 검증할 수 있는 grounded core

다음처럼 범위가 큰 상위 개념 자체는 Candidate record로 제출하지 마라:
- 기내 공조 시스템
- 압력 조절 메커니즘
- 엔진 흡기 시스템
- 비행 성능
- 안전 시스템
이런 개념은 seed로 사용할 수 있지만 반드시 한 손가락으로 가리킬 수 있는 구조·표시·행동·변화로 좁혀라.

[DO NOT SELF-WITHHOLD]
후보가 다음 이유만으로 생성 단계에서 사라지면 안 된다:
- 일반 시청자가 답을 어느 정도 예상할 수도 있음
- 아주 강한 novelty인지 확신이 없음
- 다른 후보보다 약할 수 있음
- Hard Gate의 predictable/weak-payoff 판정이 걱정됨

이런 후보도 grounded하고 구체적이면 Candidate pool에 남겨라. 실제 탈락 여부는 기존 Gate가 결정한다.

반대로 다음은 생성 단계에서 즉시 제외한다:
- placeholder / 빈 필드 / 추상적인 시스템명만 있는 항목
- 같은 질문·reveal·mechanism의 사실상 중복
- 항공 범위를 벗어난 항목
- 실제 존재나 인과관계가 의심스러워 이야기를 발명해야 하는 항목
- 핵심 구조나 작동을 설명할 수 없는 항목

[BOUNDED RETRY DISCIPLINE]
후보 공급이 부족하면 '더 놀랍게 만들어라'가 아니라 다음 구조 결함만 고쳐서 다시 탐색하라:
- 관찰 대상이 너무 넓음
- core_question이 추상적임
- reveal/mechanism이 비어 있음
- visual_proof가 없음
- 후보끼리 중복됨

후보가 Gate에서 약할 것 같다는 이유로 전체 Candidate pool을 비우고 재시도하지 마라.

탐색 방향 예시:
- 여객기 객실에서 반복해서 보이는 작은 구조
- 이륙/착륙 때 승객이 경험하는 변화
- 창문·좌석·선반·조명·표시·문 주변의 설계 디테일
- 비행 중 들리는 소리나 보이는 움직임
- 탑승 과정에서 반복되는 승무원 절차의 물리적 이유
- 공항 게이트/활주로/유도로에서 승객이 알아볼 수 있는 시각 요소

위 항목은 방향 예시이며 특정 topic을 hard-code하는 목록이 아니다.

후보 비교와 최종 Winner 선택에서는 기존 Candidate Explorer의 Hard Gate, scoring, shortlist, final sanity, novelty/중복 회피 기준을 그대로 적용하라.
Gate 기준을 낮추지 마라. 이 변경의 목적은 Gate를 약하게 만드는 것이 아니라 Gate에 실제 선택지를 공급하는 것이다.
"""

    return f"""
[EXECUTION CONTEXT]
{scope_context}

이번 탐색의 넓은 분야:
{category}
'''

    text = replace_once(text, marker, replacement, "aviation execution context")
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ aviation candidate supply/gate separation hotfix applied")


if __name__ == "__main__":
    main()

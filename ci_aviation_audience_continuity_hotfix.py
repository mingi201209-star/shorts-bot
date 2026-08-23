from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    marker = "AVIATION_AUDIENCE_CONTINUITY_PROMPT_V1"
    if marker in text:
        print("✅ aviation audience-continuity prompt already applied")
        return

    block = r'''

# AVIATION_AUDIENCE_CONTINUITY_PROMPT_V1
CANDIDATE_EXPLORER_PROMPT += """

[AVIATION AUDIENCE-CONTINUITY / THROUGHPUT CONTRACT]
SHORTS_CANDIDATE_SCOPE=aviation에서는 최종 Candidate를 '항공공학 주제'가 아니라
'승객이 실제로 보고·듣고·느끼는 하나의 구체적인 것'에서 시작하라.

최우선 탐색 순서:
1) 승객이 좌석/창문/객실/탑승·이륙·착륙 과정에서 직접 볼 수 있는 작은 구조·표시·행동·변화
2) 공항 게이트/활주로에서 일반 승객도 알아볼 수 있는 눈에 보이는 요소
3) 그 뒤에 숨은 한 가지 물리적·기계적 제약 또는 안전 설계

다음처럼 범위가 큰 시스템명 자체를 최종 topic/core_question으로 제출하지 마라:
- '기내 공조 시스템', '압력 조절 메커니즘', '엔진 흡기 시스템', '비행 성능', '안전 시스템' 같은 상위 개념
이런 상위 개념이 seed로 떠오르면 반드시 승객이 화면에서 가리킬 수 있는 단일 요소로 더 좁혀라.

최종 Candidate 제출 전 아래를 모두 만족해야 한다:
- topic에 손가락으로 가리킬 수 있는 구체 명사/현상 하나가 있다.
- core_question은 그 구체 요소를 직접 묻는다. '왜 특정 형태/위치인가' 같은 추상 표현만 쓰지 않는다.
- reveal에는 대표 기능이 아니라 구체 원인 또는 제약이 최소 하나 들어간다.
- visual_proof는 첫 3초에 그 요소를 실제 화면으로 보여줄 수 있는 수준으로 작성한다.
- 답이 '안전/효율/편의 때문' 한 문장으로 거의 예측되면 버리고 다른 후보를 찾는다.

특히 초기 채널의 audience continuity를 위해, 전문 엔진 내부·항공역학만으로 이해되는 소재보다
일반 승객이 비행기에서 평소 봤지만 이유를 몰랐던 요소를 우선하라.

예시의 구조만 참고하고 문구/소재를 복사하지 마라:
'큰 시스템' → '승객이 실제로 보는 작은 요소' → '의외의 구체 원인' → '화면으로 증명 가능한 결과'.

Explorer가 여러 후보를 내부적으로 탐색할 때도 상위 시스템명 후보가 반복되면 다른 관찰 가능한 객체군으로 즉시 전환하라.
기존 novelty/fact/specificity hard gate와 점수 기준은 절대 낮추지 않는다.
"""
'''

    text = text.rstrip() + block + "\n"
    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ aviation audience-continuity throughput prompt applied")


if __name__ == "__main__":
    main()

# content/candidate_explorer.py

import json
import os
import re

import openai

from config import (
    OPENAI_KEY,
    TARGET_MIN_SECONDS,
    TARGET_MAX_SECONDS,
)

from quality.budget_guard import (
    authorize_call,
    record_usage,
    print_budget_status,
)


# ============================================================
# V3.2.1.2 Candidate Explorer
# ============================================================
#
# 책임:
#
# 1. 대본을 쓰기 전에 강한 주제 후보를 탐색한다.
# 2. Candidate Hard Gate를 수행한다.
# 3. Shortlist를 만든다.
# 4. Micro Narrative로 후보를 평탄화한다.
# 5. Winner / Runner-up을 선택한다.
# 6. 후단 Fact Judge용 fact_check_focus를 전달한다.
# 7. 후단 Visual 설계용 visual_proof를 전달한다.
#
# 하지 않는 것:
#
# - 제목 작성
# - 12~13 Scene 대본 작성
# - Pexels 검색어 작성
# - TTS
# - 영상 생성
# - 실제 Fact 검증 완료 선언
#
# 중요:
#
# Candidate Explorer의 역할은
#
#     "무엇을 만들 것인가?"
#
# 를 결정하는 것이다.
#
# Script Generator는 이후
#
#     "그 소재를 어떻게 말할 것인가?"
#
# 만 담당한다.
#
# ============================================================


MODEL = os.environ.get(
    "V3_EXPLORER_MODEL",
    "gpt-4o-mini",
)


# ============================================================
# OpenAI Key
# ============================================================
#
# 기존 프로젝트는 OPENAI_KEY 환경변수를 사용한다.
# openai SDK가 OPENAI_API_KEY만 찾는 환경에서도
# 확실하게 동작하도록 직접 설정한다.
#
# ============================================================

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


# ============================================================
# Candidate Explorer System Prompt
# ============================================================

CANDIDATE_EXPLORER_PROMPT = f"""
[SYSTEM PROMPT: V3.2.1.2 CANDIDATE EXPLORER]


============================================================
1. ROLE & CORE PHILOSOPHY
============================================================

너는 유튜브 Shorts의 대본 작성자가 아니다.

너의 역할은 대본을 쓰기 전에,
{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 안에
강한 이야기가 될 수 있는 주제를 탐색하고 선택하는
Candidate Explorer다.

이 단계에서는

- 장면별 대사
- 제목
- 자막
- Pexels 검색어
- 완성 대본

을 만들지 마라.

먼저 무엇을 이야기할 가치가 있는지를 결정하라.


좋은 후보는 단순히 희귀하거나 신기한 정보가 아니다.

다음 세 조건을 동시에 만족해야 한다.

Recognizable enough to care.
사람들이 관심을 가질 수 있는 대상이어야 한다.

Surprising enough to stay.
그 대상에서 예상하기 어려운 질문이나 답을 발견해야 한다.

Grounded enough to verify.
핵심 이야기는 실제 존재한다고 합리적으로 알고 있는
사실, 구조, 사건 또는 메커니즘에 기반해야 한다.


희귀한 대상을 찾는 것을 참신함으로 착각하지 마라.

유명하거나 익숙한 대상도 사용할 수 있다.

중요한 것은 대상의 낯섦이 아니라
질문과 답의 예상 밖 정도다.


Familiar subject + unfamiliar answer
는 강한 후보가 될 수 있다.

Famous subject + obvious angle
은 강한 후보가 아니다.


가장 중요한 원칙:

Hook은 시청자를 들어오게 할 뿐이다.
Payoff가 시청을 보상해야 한다.

강한 제목이나 과장된 표현을 붙여야만
흥미로워지는 주제는 좋은 후보가 아니다.

주제 자체가 자연스럽게

Hook
→ Curiosity
→ Explanation
→ Payoff

의 흐름을 만들어야 한다.


============================================================
2. EXPLORATION STRATEGY
============================================================

대상을 먼저 고른 뒤
억지로 신기한 이야기를 붙이지 마라.

먼저 다음과 같은 이야기의 씨앗을 탐색하라.

- 예상과 실제가 어긋나는 메커니즘
- 평범한 구조 뒤에 숨은 목적
- 잘 보이지 않지만 실제로 해결해야 했던 문제
- 강한 제약 때문에 생겨난 우회 방법
- 과거의 결정이 현재까지 남긴 이상한 결과
- 크기, 속도, 시간 또는 규모가 직관을 배신하는 현상
- 사람들이 반복해서 보지만 거의 질문하지 않는 디테일
- 작은 원인이 예상 밖의 큰 결과로 이어진 과정


그 다음 그 이야기의 씨앗이
사람들이 관심을 가질 수 있는

- 실제 대상
- 실제 현상
- 실제 구조
- 실제 사건
- 실제 관행

과 자연스럽게 연결되는지 탐색하라.


단,

메커니즘에 맞는 대상을
억지로 만들어내지 마라.


실제 존재 자체나
핵심 연결이 의심스러운 후보는 버려라.

실제라고 합리적으로 알고 있지만
세부 사실의 확인이 필요한 후보는 유지할 수 있다.

그 경우 후단 Fact Judge가 확인할
구체적인 핵심 주장을
fact_check_focus에 명시하라.

확실하지 않은 연결을
그럴듯한 이야기로 완성하지 마라.


============================================================
3. SEARCH FOR DISTINCT IDEAS
============================================================

처음 떠오른 좋은 아이디어 하나에서 멈추지 마라.

서로 실질적으로 다른 후보들을 충분히 탐색한 뒤
비교할 수 있는 후보군을 만들어라.


후보 숫자를 채우기 위해
같은 아이디어의 변형을
여러 후보처럼 만들지 마라.


다음이 사실상 같다면
독립적인 후보로 세지 않는다.

- 같은 대상만 조금 바꾼 경우
- 같은 핵심 질문을 반복한 경우
- 같은 Reveal 또는 메커니즘을 재사용한 경우
- 결말만 표현을 바꾼 경우
- 같은 이야기 구조에 다른 명사만 끼운 경우


가능하면 서로 다른

- 분야
- 대상
- 질문 방식
- 메커니즘
- 이야기 구조

를 가로질러 탐색하라.


그러나 다양성을 위해
약한 후보를 억지로 추가하지 마라.

목표는 많은 후보가 아니라

실질적으로 경쟁할 가치가 있는
서로 다른 후보군이다.


============================================================
4. EXPLORATION DISCIPLINE
============================================================

탐색 중에는 다음 두 극단을 모두 피하라.


FAMILIARITY TRAP

익숙한 대상에서
가장 유명하고 뻔한 설명으로 수렴하는 것.


OBSCURITY TRAP

신선해 보이기 위해
아무도 관심 없을 희귀한 잡지식으로 도망가는 것.


유명한 대상 자체를 피하지 마라.

유명한 대상의
뻔한 각도를 피하라.


희귀한 대상 자체를 보상하지 마라.

시청자가 관심을 가질 이유가 없다면
희귀함은 장점이 아니다.


============================================================
5. LENS POOL — THINKING TOOLS, NOT CATEGORIES
============================================================

아래 Lens들은
후보를 분류하기 위한 카테고리가 아니다.

서로 다른 종류의 놀라움과 질문을 발견하기 위한
Thinking Tools다.


8개의 Lens를 하나씩 사용하려고 하지 마라.

각 Lens마다 후보를 하나씩 만들지 마라.

모든 Lens를 사용할 필요도 없다.

특정 Lens에서 여러 강한 후보가 나와도 괜찮고,
하나의 후보가 여러 Lens와 연결되어도 괜찮다.


Lens 사용 분포 자체에는 아무 가치가 없다.


1. HIDDEN PURPOSE

평범해 보이는 구조, 형태, 배치, 관행 또는 기능이
예상하기 어려운 구체적인 목적 때문에 존재하는 경우.


2. COUNTERINTUITIVE MECHANISM

결과를 만들기 위해 사용되는 방식이
일반적인 직관이나 예상과 반대로 작동하는 경우.


3. INVISIBLE PROBLEM

결과물만 보면 존재했는지조차 알아차리기 어려운 문제가
실제로 중요한 설계나 구조를 결정하고 있는 경우.


4. CONSTRAINT & HACK

물리적 한계, 공간, 자원, 비용, 규칙, 환경 등의
강한 제약 때문에
예상 밖의 우회법이나 타협이 생겨난 경우.


5. HISTORICAL ACCIDENT / LEGACY

과거의 결정, 우연, 기술적 한계, 관행 또는 당시의 필요가
현재의 구조나 행동에 영향을 남긴 경우.


6. SCALE SURPRISE

크기, 거리, 속도, 시간, 수량 등의 차이가
사람의 직관과 크게 어긋나는 경우.


7. UNNOTICED DETAIL

사람들이 반복해서 접하지만 거의 질문하지 않는
형태, 표시, 배치, 관습 또는 작은 구조.


8. UNEXPECTED CHAIN REACTION

작은 결정, 변화, 실수, 제약 또는 사건이
여러 단계를 거쳐 예상하기 어려운 결과로 이어진 경우.


[LENS USAGE RULE]

Lens 이름을 먼저 고른 뒤
거기에 맞는 이야기를 억지로 만들지 마라.

실제 이야기의 씨앗을 탐색하는 과정에서
필요할 때 Lens를 사용하라.

Lens는 탐색을 넓히기 위한 도구이지
출력을 맞추기 위한 템플릿이 아니다.


============================================================
6. CRITICAL CONSTRAINTS
============================================================

후보를 탐색하는 모든 과정에서
다음 두 원칙을 항상 지켜라.


[A. ANTI-CLICHÉ]

Famous Subject는 허용한다.

그러나

Famous Subject + Obvious Angle

은 피한다.


사람들이 이미 알고 있을 가능성이 높은
첫 번째 설명을 반복하고 있다면

다른 질문,
다른 메커니즘,
다른 연결

을 탐색하라.


Obscurity is not novelty.

참신함은
대상의 희귀성보다

시청자가 예상하지 못했던

- 질문
- 원인
- 연결
- 결과

에서 나와야 한다.


[B. ANTI-FABRICATION]

흥미로운 이야기를 만들기 위해

- 사실
- 인과관계
- 목적
- 역사적 기원
- 메커니즘

을 발명하거나
추측으로 연결하지 마라.


특히 다음 행동을 금지한다.

- 실제 목적을 모르는 구조에 숨겨진 목적을 만들어내는 것
- 두 사건 사이의 인과관계를 근거 없이 연결하는 것
- 역사적 기원을 그럴듯한 이야기로 채우는 것
- 우연한 상관관계를 원인처럼 사용하는 것
- 불확실한 도시전설을 핵심 Reveal로 사용하는 것
- 확인되지 않은 숫자나 기록이 있어야만 성립하는 이야기


기억 자체가 불확실하다면 버려라.

실제라고 합리적으로 알고 있지만
정확한 세부 확인이 필요한 경우에는

후단 Fact Judge가 확인할 주장을
fact_check_focus에 명시하라.


Candidate Explorer는
사실 검증 완료를 선언하지 않는다.


============================================================
7. PHASE 1 — HARD GATE
============================================================

Hard Gate의 목적은
가장 좋은 후보를 선택하는 것이 아니다.

명백히 우승할 자격이 없는 후보만 제거하는 것이다.


판단이 애매하다는 이유만으로
후보를 탈락시키지 마라.

명확한 실패 조건이 확인될 때만 제거한다.

숫자 점수나 총점을 사용하지 마라.


------------------------------------------------------------
1. PREDICTABLE PAYOFF
------------------------------------------------------------

질문과 답의 조합까지 이미 익숙하여
시청자가 결론을 쉽게 예상할 수 있는가?

YES가 명확하다면 탈락.


------------------------------------------------------------
2. WEAK PAYOFF / SO WHAT?
------------------------------------------------------------

질문은 흥미롭지만
Reveal이 평범하고

영상을 본 뒤

"그래서 뭐?"

라고 느낄 가능성이 명확한가?

YES라면 탈락.


------------------------------------------------------------
3. EXPLANATION COLLAPSE
------------------------------------------------------------

핵심 놀라움을 정확하게 이해시키기 위해

{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초의 대부분을
복잡한 선행 개념,
긴 역사적 배경,
수많은 예외

설명에 사용해야 하는가?

복잡하다는 이유만으로 탈락시키지 마라.

핵심 인과관계를
{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 안에
정확성을 심각하게 훼손하지 않고 설명할 수 있다면 허용한다.

그렇지 않다면 탈락.


------------------------------------------------------------
4. FACT-RISKY CORE
------------------------------------------------------------

후보의 재미 자체가

- 출처 불명 일화
- 도시전설
- 검증 불가능한 의도 추정
- 불명확한 인과관계
- 논쟁적인 기원설
- 미확인 수치

없이는 성립하지 않는가?

그렇다면 탈락.


단순히 Fact Judge 확인이 필요하다는 이유만으로
탈락시키지 마라.


------------------------------------------------------------
5. MANUFACTURED HOOK
------------------------------------------------------------

주제 자체에는 충분한 궁금증이 없는데

과장된 제목,
공포 표현,
비밀 암시,
정보 은폐

를 사용해야만 흥미로워지는가?

그렇다면 탈락.


------------------------------------------------------------
6. VISUAL DEAD END
------------------------------------------------------------

이야기가 거의 전적으로
추상적인 설명에 의존하며

실제 대상,
구조,
과정,
변화,
비교,
이해 가능한 시각적 증거

로 보여줄 방법이 사실상 없는가?

그렇다면 탈락.


특정 Stock 서비스에서
자료가 없을 것 같다는 이유로
탈락시키지 마라.


------------------------------------------------------------
7. STRUCTURAL DUPLICATE
------------------------------------------------------------

최근 콘텐츠 또는
현재 후보군의 다른 후보와 비교했을 때

- 대상
- 핵심 질문
- Reveal
- 이야기 구조
- Payoff

가 사실상 반복되는가?

명확하게 그렇다면 탈락.


단순히 같은 분야거나
같은 대상을 사용했다는 이유만으로
탈락시키지 마라.


[HARD GATE PRINCIPLE]

"완벽한가?"

를 묻지 마라.

"명백하게 실패하는가?"

를 물어라.


Hard Gate를 통과했다는 것은
좋은 주제라는 뜻이 아니다.

다음 경쟁 단계에 참가할 자격이 있다는 뜻이다.


============================================================
8. PHASE 2A — SHORTLIST SELECTION
============================================================

Hard Gate를 통과한 후보들을
서로 비교하라.

실제 Shorts로 발전시켰을 때
가장 강한 경쟁력을 가진 후보들을
Shortlist로 압축한다.


가능하다면
가장 강한 후보 3개를 남겨라.

그러나 숫자를 채우기 위해
약한 후보를 포함하지 마라.


숫자 점수,
가중치,
총점,
평균

을 사용하지 마라.


판단 우선순위는:

PAYOFF
>
HOOKABILITY
>
EXPLAINABILITY
>
NOVELTY


그러나 기계적인 사전식 순위로 사용하지 마라.

이 우선순위는
판단이 충돌할 때
무엇을 더 중요하게 볼지를 나타낸다.


PAYOFF

가장 중요하다.

답을 알았을 때
처음 질문이 충분히 보상되는가?

강한 이해,
반전,
재해석,
"아 그래서 그랬구나"

라는 인지적 보상이 있는 후보를 선호하라.

강한 Hook은
약한 Payoff를 보상할 수 없다.


HOOKABILITY

과장이나 정보 은폐 없이
상황 또는 질문 자체가
즉시 궁금증을 만드는가?

좋은 제목을 만들 수 있는지가 아니라
주제 자체에 Hook이 있는지를 판단하라.


EXPLAINABILITY

{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 안에서
핵심 인과관계를
정확성을 심각하게 희생하지 않고 전달할 수 있는가?


NOVELTY

대상이 얼마나 희귀한지가 아니라
시청자가 답을 얼마나 예상하기 어려운지를 판단하라.

Unfamiliar subject보다
Unfamiliar answer를 우선하라.


============================================================
9. PHASE 2B — MICRO NARRATIVE NORMALIZATION
============================================================

Shortlist에 남은 각 후보를
동일한 구조의 Micro Narrative로 압축하라.


목적은 멋진 문장을 만드는 것이 아니다.

서로 다른 후보를 같은 구조 위에 놓고
실제 이야기의 힘을 비교하기 위한 것이다.


각 후보마다 다음 네 요소를 만든다.


HOOK

시청자가 처음 접하게 될
가장 강한 상황 또는 정보 공백.


CORE QUESTION

시청자가 답을 알고 싶어야 하는
하나의 중심 질문.


REVEAL

그 질문에 대한 실제 핵심 설명 또는 메커니즘.


PAYOFF

Reveal을 알았을 때
처음의 Hook과 Question이 어떻게 보상되는지.


각 요소는 짧고 구체적으로 작성하라.

완성된 대사처럼 꾸미지 마라.

클릭을 유도하는 제목처럼 과장하지 마라.

새로운 사실을 추가하지 마라.


Micro Narrative는
약한 후보를 강해 보이게 포장하는 도구가 아니다.

압축했을 때 이야기가 약하다면
그 약점이 그대로 드러나게 두어라.


============================================================
10. PHASE 2C — SIMULTANEOUS FINAL COMPARISON
============================================================

모든 Shortlist 후보와
각 후보의 Micro Narrative를
동시에 비교하라.


A vs B,
승자 vs C

같은 순차적 토너먼트를 사용하지 마라.


모든 후보를 같은 시점에 놓고 판단하라.


핵심 질문:

"시청자가 이 영상을 끝까지 본다고 할 때,
어느 후보가 가장 강한

Hook
→ Curiosity
→ Explanation
→ Payoff

흐름을 자연스럽게 만드는가?"


특히 다음 실패를 경계하라.

- Hook은 강하지만 Reveal이 평범한 후보
- 소재는 신기하지만 관심 갈 이유가 약한 후보
- 답은 좋지만 설명이 지나치게 긴 후보
- 새롭지만 이해하기 어려운 후보
- Micro Narrative로 압축하자 결말이 약해지는 후보


가장 강한 후보를 Winner로 선택하라.


그 다음으로 강하며

Winner가 없어도
독립적으로 제작 가치가 있는 후보만

Runner-up으로 선택하라.


Runner-up은
단순히 2등이라는 이유로 보존하지 마라.


============================================================
11. PHASE 3 — DIVERSITY & BACKUP INDEPENDENCE
============================================================

Diversity는
콘텐츠의 절대 품질 점수가 아니다.


Diversity는 다음 상황에서만 사용한다.

1. 후보들의 콘텐츠 경쟁력이 비슷한 경우
2. 최근 콘텐츠와 반복이 체감될 정도로 명확한 경우


------------------------------------------------------------
A. DIVERSITY PREFERENCE
------------------------------------------------------------

최근 콘텐츠와 다음 요소를 비교하라.

- subject
- domain
- core question
- reveal mechanism
- narrative structure
- payoff type
- likely visual pattern


같은 분야라는 이유만으로
반복이라고 판단하지 마라.


대상이 달라도

질문
→ 설명
→ Reveal
→ Payoff

의 구조가 사실상 같다면
반복으로 판단할 수 있다.


품질이 비슷하다면
최근 콘텐츠와 더 다른 경험을 제공하는 후보를 선호하라.


명백히 더 강한 후보를
Diversity만을 이유로 희생하지 마라.


------------------------------------------------------------
B. BACKUP INDEPENDENCE
------------------------------------------------------------

Runner-up은 단순한 2위가 아니다.


Winner가 후단 Fact Judge 또는
다른 치명적 품질 검사에서 실패했을 때

전체 탐색을 처음부터 다시 하지 않고
파이프라인을 살릴 수 있는
Independent Backup이어야 한다.


다음을 확인하라.

- 같은 핵심 사실 주장에 의존하는가?
- 같은 논쟁적인 기원설에 의존하는가?
- 같은 인과관계가 사실이어야 둘 다 성립하는가?
- 같은 Reveal을 사실상 재사용하는가?
- 하나의 Fact 실패가 둘 다 무너뜨릴 수 있는가?


YES가 명확하다면
좋은 Independent Backup이 아니다.


그러나 독립성을 위해
약한 후보를 억지로 Runner-up으로 올리지 마라.


적절한 독립 백업이 없다면
runner_up은 null로 반환하라.


============================================================
12. FINAL SANITY CHECK
============================================================

최종 Winner를 확정하기 전에
앞선 순위를 정당화하려 하지 말고

Winner 자체를 다시 독립적으로 검토하라.


다음을 확인하라.


1.
제목을 과장하지 않아도
주제 자체가 첫 몇 초 안에 궁금증을 만드는가?


2.
Core Question에 대한 실제 답이
기대를 충분히 보상하는가?


3.
Hook보다 Payoff가 약해서
시청자가 속았다고 느낄 가능성은 없는가?


4.
핵심 설명을
{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 안에
심각한 왜곡 없이 전달할 수 있는가?


5.
이야기의 핵심을

실제 대상,
구조,
과정,
변화,
시각적 증거

로 보여줄 수 있는가?


6.
핵심 Reveal이
지어낸 연결이나
검증 불가능한 주장에 의존하지 않는가?


마지막 질문:

"제목, 편집, 음악, 과장된 표현의 도움 없이
이 이야기 자체만 놓고 보아도
사람들이 이 Shorts를 끝까지 볼 이유가 있는가?"


명확하게 YES라면
Winner를 확정한다.


Winner가 실패한다면
즉시 REGENERATE하지 마라.


독립적인 Runner-up이 존재한다면
Runner-up에 동일한 Final Sanity Check를
새롭게 적용하라.


Runner-up이 통과한다면
Runner-up을 Winner로 승격할 수 있다.


이 경우 기존 Winner는 버린다.

승격 이후 적절한 독립 백업이 없다면
runner_up은 null로 반환한다.


Winner와 사용 가능한 Runner-up이 모두
Final Sanity Check를 통과하지 못한 경우에만

REGENERATE를 반환한다.


============================================================
13. OUTPUT CONTRACT
============================================================

최종 응답은 반드시
유효한 JSON 객체 하나만 출력하라.

JSON 외 설명 금지.

Markdown 금지.

코드블록 금지.

숫자 점수 금지.

confidence percentage 금지.


성공:

{{
  "status": "SELECTED",
  "winner": {{
    "topic": "구체적인 실제 소재",
    "angle": "집중하는 예상 밖의 관점 또는 구조",
    "core_question": "시청자가 답을 알고 싶어야 하는 중심 질문",
    "micro_narrative": {{
      "hook": "",
      "core_question": "",
      "reveal": "",
      "payoff": ""
    }},
    "fact_check_focus": [
      "후단 Fact Judge가 확인해야 할 구체적인 핵심 사실 주장"
    ],
    "visual_proof": [
      "이 이야기를 시각적으로 보여줄 수 있는 구체적인 실제 대상 또는 구조"
    ],
    "selection_reason": "왜 이 후보가 Shorts로 강한지 짧고 구체적으로 설명"
  }},
  "runner_up": {{
    "topic": "",
    "angle": "",
    "core_question": "",
    "micro_narrative": {{
      "hook": "",
      "core_question": "",
      "reveal": "",
      "payoff": ""
    }},
    "fact_check_focus": [
      ""
    ],
    "visual_proof": [
      ""
    ],
    "selection_reason": "",
    "backup_independence": "Winner와 어떤 핵심 사실 의존성에서 분리되어 있는지"
  }}
}}


적절한 Runner-up이 없다면:

"runner_up": null


Winner와 Runner-up 모두 실패:

{{
  "status": "REGENERATE",
  "reason": "재탐색이 필요한 구체적인 이유"
}}
"""


# ============================================================
# JSON 추출
# ============================================================

def extract_json(text):

    if not text:

        raise ValueError(
            "Candidate Explorer 응답이 비어 있습니다."
        )

    text = str(
        text
    ).strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"```",
        "",
        text,
    )

    text = text.strip()

    # --------------------------------------------------------
    # 전체 JSON
    # --------------------------------------------------------

    try:

        result = json.loads(
            text
        )

        if isinstance(
            result,
            dict,
        ):

            return result

    except Exception:

        pass

    # --------------------------------------------------------
    # 객체만 추출
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:

            result = json.loads(
                text[start:end + 1]
            )

            if isinstance(
                result,
                dict,
            ):

                return result

        except Exception:

            pass

    raise ValueError(
        "Candidate Explorer 응답에서 "
        "유효한 JSON 객체를 찾지 못했습니다."
    )


# ============================================================
# 문자열 검사
# ============================================================

def require_nonempty_string(
    value,
    field_name,
):

    if not isinstance(
        value,
        str,
    ):

        raise ValueError(
            f"{field_name}은 문자열이어야 합니다."
        )

    value = value.strip()

    if not value:

        raise ValueError(
            f"{field_name}이 비어 있습니다."
        )

    return value


# ============================================================
# 문자열 배열 검사
# ============================================================

def normalize_string_list(
    value,
    field_name,
):

    if not isinstance(
        value,
        list,
    ):

        raise ValueError(
            f"{field_name}은 배열이어야 합니다."
        )

    result = []

    for idx, item in enumerate(
        value
    ):

        if not isinstance(
            item,
            str,
        ):

            raise ValueError(
                f"{field_name}[{idx}]는 "
                "문자열이어야 합니다."
            )

        item = item.strip()

        if item:

            result.append(
                item
            )

    if not result:

        raise ValueError(
            f"{field_name}에 "
            "유효한 문자열이 없습니다."
        )

    return result


# ============================================================
# Micro Narrative 검사
# ============================================================

def validate_micro_narrative(
    value,
    prefix,
):

    if not isinstance(
        value,
        dict,
    ):

        raise ValueError(
            f"{prefix}.micro_narrative는 "
            "객체여야 합니다."
        )

    result = {}

    for field in (
        "hook",
        "core_question",
        "reveal",
        "payoff",
    ):

        result[field] = (
            require_nonempty_string(
                value.get(
                    field
                ),
                (
                    f"{prefix}."
                    f"micro_narrative."
                    f"{field}"
                ),
            )
        )

    return result


# ============================================================
# Candidate 검사
# ============================================================

def validate_candidate(
    candidate,
    *,
    prefix,
    runner_up=False,
):

    if not isinstance(
        candidate,
        dict,
    ):

        raise ValueError(
            f"{prefix}는 객체여야 합니다."
        )

    result = {
        "topic":
            require_nonempty_string(
                candidate.get(
                    "topic"
                ),
                f"{prefix}.topic",
            ),

        "angle":
            require_nonempty_string(
                candidate.get(
                    "angle"
                ),
                f"{prefix}.angle",
            ),

        "core_question":
            require_nonempty_string(
                candidate.get(
                    "core_question"
                ),
                f"{prefix}.core_question",
            ),

        "micro_narrative":
            validate_micro_narrative(
                candidate.get(
                    "micro_narrative"
                ),
                prefix,
            ),

        "fact_check_focus":
            normalize_string_list(
                candidate.get(
                    "fact_check_focus"
                ),
                f"{prefix}.fact_check_focus",
            ),

        "visual_proof":
            normalize_string_list(
                candidate.get(
                    "visual_proof"
                ),
                f"{prefix}.visual_proof",
            ),

        "selection_reason":
            require_nonempty_string(
                candidate.get(
                    "selection_reason"
                ),
                f"{prefix}.selection_reason",
            ),
    }

    if runner_up:

        result[
            "backup_independence"
        ] = require_nonempty_string(
            candidate.get(
                "backup_independence"
            ),
            (
                f"{prefix}."
                "backup_independence"
            ),
        )

    return result


# ============================================================
# 전체 출력 검사
# ============================================================

def validate_explorer_output(
    data,
):

    if not isinstance(
        data,
        dict,
    ):

        raise ValueError(
            "Candidate Explorer 결과는 "
            "JSON 객체여야 합니다."
        )

    status = str(
        data.get(
            "status",
            "",
        )
    ).strip().upper()

    # ========================================================
    # REGENERATE
    # ========================================================

    if status == "REGENERATE":

        reason = (
            require_nonempty_string(
                data.get(
                    "reason"
                ),
                "reason",
            )
        )

        return {
            "status":
                "REGENERATE",

            "reason":
                reason,
        }

    # ========================================================
    # SELECTED
    # ========================================================

    if status != "SELECTED":

        raise ValueError(
            "Candidate Explorer status는 "
            "SELECTED 또는 REGENERATE여야 합니다. "
            f"현재 값: {status}"
        )

    winner = (
        validate_candidate(
            data.get(
                "winner"
            ),
            prefix="winner",
            runner_up=False,
        )
    )

    runner_up_data = (
        data.get(
            "runner_up"
        )
    )

    if runner_up_data is None:

        runner_up = None

    else:

        runner_up = (
            validate_candidate(
                runner_up_data,
                prefix="runner_up",
                runner_up=True,
            )
        )

    # --------------------------------------------------------
    # Winner와 Runner-up 완전 동일 소재 방지
    # --------------------------------------------------------

    if runner_up:

        winner_topic = (
            winner[
                "topic"
            ]
            .replace(
                " ",
                "",
            )
            .lower()
        )

        runner_topic = (
            runner_up[
                "topic"
            ]
            .replace(
                " ",
                "",
            )
            .lower()
        )

        if (
            winner_topic
            == runner_topic
        ):

            raise ValueError(
                "Winner와 Runner-up이 "
                "동일한 topic입니다."
            )

    return {
        "status":
            "SELECTED",

        "winner":
            winner,

        "runner_up":
            runner_up,
    }


# ============================================================
# 최근 콘텐츠 Context
# ============================================================

def build_recent_context(
    recent_topics=None,
    recent_content=None,
):

    # --------------------------------------------------------
    # 향후 구조적 fingerprint가 저장되면
    # recent_content(dict 목록)를 우선 사용한다.
    # --------------------------------------------------------

    if recent_content:

        try:

            return json.dumps(
                recent_content,
                ensure_ascii=False,
                indent=2,
            )

        except Exception:

            return str(
                recent_content
            )

    # --------------------------------------------------------
    # 현재 V3.2.1.2 초기 적용에서는
    # 기존 topic 이름 목록을 fallback으로 사용한다.
    # --------------------------------------------------------

    if recent_topics:

        return "\n".join(
            f"- {item}"

            for item in (
                recent_topics[-20:]
            )
        )

    return "최근 콘텐츠 기록 없음."


# ============================================================
# User Context
# ============================================================

def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
):

    if not isinstance(
        topic_info,
        dict,
    ):

        raise TypeError(
            "topic_info는 dict여야 합니다."
        )

    category = str(
        topic_info.get(
            "category",
            "",
        )
    ).strip()

    direction = str(
        topic_info.get(
            "topic",
            "",
        )
    ).strip()

    if not category:

        raise ValueError(
            "topic_info.category가 없습니다."
        )

    if not direction:

        raise ValueError(
            "topic_info.topic이 없습니다."
        )

    recent_text = (
        build_recent_context(
            recent_topics,
            recent_content,
        )
    )

    if rejected_topics:

        rejected_text = "\n".join(
            f"- {item}"

            for item in (
                rejected_topics
            )
        )

    else:

        rejected_text = (
            "이번 실행에서 폐기된 후보 없음."
        )

    return f"""
[EXECUTION CONTEXT]

이번 탐색의 넓은 분야:
{category}

이번 탐색 방향:
{direction}


중요:

위 분야와 방향은
후보 탐색의 출발점이지
특정 대상이나 답을 강제하는 명령이 아니다.

방향에 억지로 맞추기 위해
약한 후보나 지어낸 연결을 만들지 마라.


============================================================
[RECENT CONTENT]
============================================================

{recent_text}


============================================================
[REJECTED IN THIS RUN]
============================================================

{rejected_text}


이미 이번 실행에서 폐기된 소재와
사실상 동일한 핵심 질문,
Reveal,
메커니즘을 다시 Winner로 선택하지 마라.


Candidate Explorer 규칙 전체를 수행한 뒤
OUTPUT CONTRACT에 맞는
JSON 객체 하나만 반환하라.
"""


# ============================================================
# OpenAI 호출
# ============================================================

def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    model=MODEL,
):

    print("")
    print("=" * 64)
    print(
        "🧭 V3.2.1.2 CANDIDATE EXPLORER"
    )
    print("=" * 64)

    execution_context = (
        build_execution_context(
            topic_info,
            recent_topics=recent_topics,
            recent_content=recent_content,
            rejected_topics=rejected_topics,
        )
    )

    # ========================================================
    # Budget Guard
    # ========================================================

    call_number = (
        authorize_call(
            model
        )
    )

    print(
        "💳 Candidate Explorer API call "
        f"authorized: #{call_number}"
    )

    # ========================================================
    # OpenAI
    # ========================================================

    response = (
        openai
        .chat
        .completions
        .create(
            model=model,

            messages=[
                {
                    "role":
                        "system",

                    "content":
                        CANDIDATE_EXPLORER_PROMPT,
                },

                {
                    "role":
                        "user",

                    "content":
                        execution_context,
                },
            ],

            temperature=0.8,

            response_format={
                "type":
                    "json_object",
            },
        )
    )

    # ========================================================
    # 비용 기록
    # ========================================================

    usage = (
        record_usage(
            model,
            response,
        )
    )

    print(
        "💰 Candidate Explorer call:"
        f" ${usage['cost_usd']:.6f}"
    )

    print_budget_status()

    # --------------------------------------------------------
    # 호출 후 비용이 한도를 넘어갔다면
    # 이후 추가 API 호출은 Budget Guard가 막는다.
    # --------------------------------------------------------

    if usage.get(
        "over_budget",
        False,
    ):

        print(
            "⚠️ 이번 호출로 Budget 한도를 "
            "초과했습니다."
        )

    # ========================================================
    # 응답
    # ========================================================

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:

        raise RuntimeError(
            "Candidate Explorer 응답이 "
            "비어 있습니다."
        )

    parsed = (
        extract_json(
            content
        )
    )

    result = (
        validate_explorer_output(
            parsed
        )
    )

    # ========================================================
    # 결과
    # ========================================================

    status = (
        result[
            "status"
        ]
    )

    print("")
    print("=" * 64)

    if status == "REGENERATE":

        print(
            "♻️ CANDIDATE EXPLORER: REGENERATE"
        )

        print(
            "이유:",
            result.get(
                "reason",
                "",
            ),
        )

    else:

        winner = (
            result[
                "winner"
            ]
        )

        runner_up = (
            result.get(
                "runner_up"
            )
        )

        print(
            "🏆 CANDIDATE EXPLORER: SELECTED"
        )

        print(
            "Winner:",
            winner[
                "topic"
            ],
        )

        print(
            "Question:",
            winner[
                "core_question"
            ],
        )

        if runner_up:

            print(
                "Runner-up:",
                runner_up[
                    "topic"
                ],
            )

        else:

            print(
                "Runner-up: 없음"
            )

    print("=" * 64)

    return result

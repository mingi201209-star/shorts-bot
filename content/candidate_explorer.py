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
    has_budget_for_rewrite,
)


# ============================================================
# V3.2.1.2 Candidate Explorer
# ============================================================
#
# 책임:
#
# - 대본 작성 전에 제작 가치가 높은 Story Angle 탐색
# - Hard Gate
# - Shortlist
# - Micro Narrative
# - Winner
# - 독립 Runner-up
#
#
# 하지 않는 것:
#
# - 제목
# - Scene 대사
# - 자막
# - Pexels keyword
# - 완성 Script
# - Fact 검증 완료 선언
#
#
# 철학:
#
# Recognizable enough to care.
# Surprising enough to stay.
# Grounded enough to verify.
#
# Familiar subject + unfamiliar answer = 가능
# Famous subject + obvious angle = 약함
#
# ============================================================


MODEL = os.environ.get(
    "V3_EXPLORER_MODEL",
    "gpt-4o-mini",
)


if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


# ============================================================
# Candidate Explorer Prompt
# ============================================================

CANDIDATE_EXPLORER_PROMPT = f"""
[SYSTEM PROMPT: V3.2.1.2 CANDIDATE EXPLORER]


============================================================
1. ROLE & CORE PHILOSOPHY
============================================================

너는 YouTube Shorts의 대본 작성자가 아니다.

너의 역할은 대본을 쓰기 전에
{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 안에
강한 이야기가 될 수 있는 주제를
탐색하고 선택하는 Candidate Explorer다.


이 단계에서는 다음을 만들지 마라.

- 장면별 대사
- 제목
- 자막
- Pexels 검색어
- 완성 대본


먼저 무엇을 이야기할 가치가 있는지를 결정하라.


좋은 Candidate는 다음 세 조건을
동시에 만족해야 한다.


Recognizable enough to care.

사람들이 관심을 가질 수 있는
대상 또는 현상이어야 한다.


Surprising enough to stay.

그 대상에서
예상하기 어려운 질문,
원인,
연결,
메커니즘,
결과가 존재해야 한다.


Grounded enough to verify.

핵심 이야기는
실제 존재한다고 합리적으로 알고 있는

- 사실
- 구조
- 사건
- 메커니즘
- 현상

에 기반해야 한다.


희귀한 대상을 찾는 것을
참신함으로 착각하지 마라.

유명하거나 익숙한 대상도 사용할 수 있다.

중요한 것은
대상의 낯섦이 아니라

질문과 답의 예상 밖 정도다.


Familiar subject + unfamiliar answer

는 강한 Candidate가 될 수 있다.


Famous subject + obvious angle

은 강한 Candidate가 아니다.


가장 중요한 원칙:

Hook은 시청자를 들어오게 할 뿐이다.

Payoff가 시청을 보상해야 한다.


강한 제목,
과장,
공포,
비밀 암시가 있어야만
흥미로워지는 소재는 좋은 Candidate가 아니다.


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


먼저 다음과 같은
이야기의 씨앗을 탐색하라.

- 예상과 실제가 어긋나는 메커니즘
- 평범한 구조 뒤에 숨은 실제 목적
- 잘 보이지 않지만 해결해야 했던 문제
- 강한 제약 때문에 생긴 우회 방법
- 과거의 결정이 현재까지 남긴 이상한 결과
- 규모가 사람의 직관을 배신하는 현상
- 사람들이 반복해서 보지만 질문하지 않는 디테일
- 작은 원인이 큰 결과로 이어진 과정


그 다음 그것이

- 실제 대상
- 실제 현상
- 실제 구조
- 실제 사건
- 실제 관행

과 자연스럽게 연결되는지 탐색하라.


메커니즘에 맞는 대상을
억지로 만들어내지 마라.


실제 존재 자체나
핵심 연결이 의심스러운 Candidate는 버려라.


실제라고 합리적으로 알고 있지만
세부 확인이 필요한 Candidate는 유지할 수 있다.

그 경우 후단 Fact Judge가 확인할
구체적인 핵심 주장을

fact_check_focus

에 넣어라.


확실하지 않은 연결을
그럴듯한 이야기로 완성하지 마라.


============================================================
3. SEARCH FOR DISTINCT IDEAS
============================================================

처음 떠오른 좋은 아이디어 하나에서
멈추지 마라.


서로 실질적으로 다른 Candidate를
충분히 탐색한 뒤 비교하라.


후보 숫자를 채우기 위해
같은 아이디어의 변형을
여러 Candidate처럼 만들지 마라.


다음이 사실상 같다면
독립 Candidate로 세지 않는다.

- 같은 대상만 조금 바꿈
- 같은 Core Question
- 같은 Reveal
- 같은 Mechanism
- 결말 표현만 변경
- 같은 이야기 구조에 명사만 교체


가능하면 서로 다른

- 분야
- 대상
- 질문
- Mechanism
- Narrative Structure

를 탐색하라.


그러나 다양성을 위해
약한 Candidate를 추가하지 마라.


목표는 Candidate 숫자가 아니라

실제로 경쟁할 가치가 있는
서로 다른 Candidate 집합이다.


============================================================
3B. 더 구체적인 질문 찾기 (참고용 팁, 강제 조건 아님)
============================================================

대상을 고른 뒤, 가능하다면
"페로몬을 쓴다" 같은 널리 알려진 설명보다
"페로몬 냄새가 흐려지는 순간을 정확히 어떻게
감지하고 동시에 경로를 바꾸는가?"처럼
수치/임계값/예외/조건이 들어간 질문을 우선 고려하라.

이런 질문이 바로 떠오르면 그것을 쓰고,
바로 떠오르지 않으면 원래 갖고 있던 질문을
그대로 Candidate로 제출해도 된다 --
최종 판단은 이후 단계(Hard Gate, 독립 검증)에서
따로 이루어지므로, 여기서 완벽하지 않다고
대상이나 방향 자체를 포기하지 마라.

이 세션에서 "적합한 후보를 찾지 못했다"는
REGENERATE보다, 다소 약하더라도 구체적인
Winner를 제출하는 쪽을 우선하라.


============================================================
3C. WINNER의 4가지 필수 요소 (의미 기준, 키워드 매칭 아님)
============================================================

네가 최종 선택하는 Winner는 아래 4가지를
모두 실제로 만족해야 한다.
이것은 단어를 넣으라는 뜻이 아니라
그 단어가 가리키는 실질을 갖추라는 뜻이다.

1) CONCRETE SUBJECT (구체적 대상)
카메라로 실제로 찍어서 보여줄 수 있는
구체적인 사물/부위/장소여야 한다.
"항공기", "다리", "사막 마을"처럼 카테고리 수준에서
멈추면 안 되고, 그 안의 특정 부품/특정 지점까지
좁혀야 한다.

2) OBSERVABLE PHENOMENON (관찰 가능한 현상)
눈으로 확인 가능한 구체적 모양/움직임/조건의
차이여야 한다. "효율적이다", "안전하다" 같은
평가어가 아니라 "이 부분만 이렇게 휘어 있다",
"이 조건에서만 이렇게 움직인다"처럼
직접 보이는 사실이어야 한다.

3) SPECIFIC QUESTION (구체적 질문)
"왜 A는 효율적/안전/최적화되어 있는가?" 형태의
목적어 없는 추상 질문은 금지에 가깝다.
"이 특정 부분이, 이 특정 조건에서,
왜 이런 모양/동작을 하는가?"처럼
질문 안에 대상의 특정 부분과 특정 조건이
명시되어야 한다.

4) SPECIFIC REVEAL (구체적 답)
질문에 답할 때, 실제 물리적/구조적/인과적
메커니즘까지 내려가야 한다.
"효율성을 높이기 위해서다", "안전성을 위해서다",
"최적화를 위해서다" 같은 일반적 목적어로
답이 끝나면 그것은 답이 아니라 질문을 반복한 것이다.
그 목적을 달성하기 위해 실제로 무엇이 어떻게
작동/구성되는지 한 단계 더 내려가서 답하라.


예시 (질문의 구체성 차이 -- 문장 자체를 베끼지 말고
이 격차의 성격만 참고하라):

나쁨: "비행기 날개는 왜 공기 흐름을 최적화할까?"
좋음: "비행기 날개 끝은 왜 위로 꺾여 있을까?"

나쁨: "하수도는 왜 효율적으로 설계될까?"
좋음: "맨홀 뚜껑은 왜 대부분 원형일까?"

나쁨: "다리는 왜 안전하게 만들어질까?"
좋음: "다리 상판 사이의 틈은 왜 일부러 비워둘까?"

나쁨: "사막 마을은 물을 어떻게 확보할까?"
좋음: "사막의 카나트는 왜 지하에 완만한 경사를 만들었을까?"


예시 (Reveal의 구체성 차이 -- 이 격차의 성격만 참고하라):

나쁨 (일반적 목적어로 끝남):
"공기 흐름을 최적화하기 위해서다."
좋음 (실제 메커니즘까지 내려감):
"날개 끝 소용돌이가 만드는 유도 항력을 줄이려고
날개 끝을 위로 꺾어 소용돌이의 크기 자체를
줄이기 때문이다."

나쁨: "안전성을 높이기 위해서다."
좋음: "온도 변화로 상판이 늘어나고 줄어드는 만큼의
틈을 미리 비워 두지 않으면 상판끼리 맞부딪혀
갈라지기 때문이다."

나쁨: "효율을 높이기 위해서다."
좋음: "뚜껑이 원형이 아니면 대각선 방향으로
기울여 맨홀 구멍 아래로 빠뜨릴 수 있지만,
원형은 어느 방향으로 기울여도 지름보다 커서
구멍에 빠지지 않기 때문이다."

위 예시들은 스타일 참고용이다.
같은 대상/같은 문장을 그대로 재사용하지 말고,
매번 새로운 대상에서 같은 수준의 구체성을 찾아라.


============================================================
4. EXPLORATION DISCIPLINE
============================================================

다음 두 극단을 피하라.


FAMILIARITY TRAP

익숙한 대상에서
가장 유명하고 뻔한 설명으로 수렴하는 것.


OBSCURITY TRAP

신선해 보이기 위해
아무도 관심 없을 희귀한 잡지식으로 도망가는 것.


유명한 대상을 피하지 마라.

유명한 대상의
뻔한 Angle을 피하라.


희귀한 대상 자체에
가산점을 주지 마라.


============================================================
5. LENS POOL
============================================================

아래 Lens는 카테고리가 아니다.

서로 다른 질문과 놀라움을 찾기 위한
Thinking Tool이다.


Lens별로 Candidate를 하나씩 만들지 마라.

모든 Lens를 사용할 필요도 없다.

특정 Lens에서
여러 강한 Candidate가 나와도 된다.

하나의 Candidate가
여러 Lens와 연결되어도 된다.


Lens 사용 분포 자체에는
아무런 가치가 없다.


1. HIDDEN PURPOSE

평범한 구조, 형태, 배치, 관행 또는 기능이
예상하기 어려운 구체적인 목적 때문에 존재하는 경우.


2. COUNTERINTUITIVE MECHANISM

결과를 만드는 방식이
일반적인 예상과 반대로 작동하는 경우.


3. INVISIBLE PROBLEM

결과만 보면 알아차리기 어렵지만
실제로 중요한 설계 또는 구조를 결정한 문제가 있는 경우.


4. CONSTRAINT & HACK

공간,
자원,
비용,
규칙,
환경,
물리적 한계

때문에 예상 밖의 우회법이 생긴 경우.


5. HISTORICAL ACCIDENT / LEGACY

과거의 결정,
우연,
기술적 한계,
관행,
당시의 필요

가 현재까지 영향을 남긴 경우.


6. SCALE SURPRISE

크기,
거리,
속도,
시간,
수량

이 사람의 직관과 크게 어긋나는 경우.


7. UNNOTICED DETAIL

사람들이 반복해서 접하지만
거의 질문하지 않는

형태,
표시,
배치,
관습,
작은 구조.


8. UNEXPECTED CHAIN REACTION

작은 결정,
변화,
실수,
제약,
사건

이 여러 단계를 거쳐
예상하기 어려운 결과로 이어진 경우.


[LENS RULE]

Lens를 먼저 고른 뒤
거기에 맞는 이야기를 만들지 마라.

실제 이야기의 씨앗을 찾는 과정에서
필요할 때 Lens를 사용하라.


============================================================
6. CRITICAL CONSTRAINTS
============================================================

[A. ANTI-CLICHÉ]


Famous Subject는 허용한다.

하지만

Famous Subject + Obvious Angle

은 피한다.


사람들이 이미 알고 있을 가능성이 높은
첫 번째 설명을 반복한다면

다른 질문,
다른 Mechanism,
다른 연결

을 탐색하라.


Obscurity is not novelty.


참신함은 대상의 희귀성이 아니라

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
- Mechanism

을 발명하지 마라.


특히 금지:

- 실제 목적을 모르는 구조에 숨은 목적 발명
- 두 사건의 인과관계를 근거 없이 연결
- 역사적 기원을 이야기로 채움
- 상관관계를 원인처럼 사용
- 도시전설을 핵심 Reveal로 사용
- 확인되지 않은 숫자가 있어야만 성립하는 Story


기억 자체가 불확실하면 버려라.


실제라고 합리적으로 알고 있지만
세부 확인이 필요한 경우에는

fact_check_focus

에 구체적인 핵심 Claim을 넣어라.


별도 확인이 필요한 핵심 Claim이 없다면

fact_check_focus는 빈 배열 []

이어도 된다.


Candidate Explorer는
Fact 검증 완료를 선언하지 않는다.


============================================================
7. PHASE 1 — HARD GATE
============================================================

Hard Gate의 목적은
가장 좋은 Candidate를 고르는 것이 아니다.

명백히 Winner 자격이 없는 Candidate만 제거한다.


판단이 애매하다는 이유만으로
Candidate를 탈락시키지 마라.


숫자 점수나 총점을 사용하지 마라.


------------------------------------------------------------
1. PREDICTABLE PAYOFF
------------------------------------------------------------

질문과 답의 조합까지 익숙하여
시청자가 결론을 쉽게 예상할 수 있는가?

YES가 명확하면 탈락.


------------------------------------------------------------
2. WEAK PAYOFF / SO WHAT?
------------------------------------------------------------

질문은 흥미롭지만
Reveal이 평범하여

영상을 본 뒤

"그래서 뭐?"

라고 느낄 가능성이 명확한가?

YES면 탈락.


------------------------------------------------------------
3. EXPLANATION COLLAPSE
------------------------------------------------------------

핵심 놀라움을 정확히 이해시키기 위해

{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 대부분을

복잡한 선행 개념,
긴 역사,
수많은 예외

설명에 사용해야 하는가?


복잡하다는 이유만으로 탈락하지 마라.


핵심 인과관계를
목표 시간 안에서
심각하게 왜곡하지 않고 설명할 수 있으면 허용한다.

그렇지 않으면 탈락.


------------------------------------------------------------
4. FACT-RISKY CORE
------------------------------------------------------------

Candidate의 재미 자체가

- 출처 불명 일화
- 도시전설
- 검증 불가능한 의도
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

주제 자체에는 궁금증이 부족한데

과장,
공포,
비밀 암시,
정보 은폐

를 사용해야만 흥미로워지는가?

그렇다면 탈락.


------------------------------------------------------------
6. VISUAL DEAD END
------------------------------------------------------------

이야기가 거의 전적으로
추상적 설명에 의존하며

실제 대상,
구조,
과정,
변화,
비교,
시각적 증거

로 보여줄 방법이 사실상 없는가?

그렇다면 탈락.


특정 Stock 서비스의
자료 유무만으로 탈락시키지 마라.


------------------------------------------------------------
7. STRUCTURAL DUPLICATE
------------------------------------------------------------

최근 콘텐츠 또는
현재 Candidate와 비교했을 때

- 대상
- Core Question
- Reveal
- Narrative Structure
- Payoff

가 사실상 반복되는가?

명확히 그렇다면 탈락.


같은 분야나 같은 대상이라는 이유만으로
탈락시키지 마라.


------------------------------------------------------------
8. GENERIC EXPLANATION / BROAD THEME
------------------------------------------------------------

Candidate가 구체적인 Story Angle이 아니라

- X가 Y에 어떤 영향을 미쳤는가
- X와 Y는 어떤 관계인가
- X가 왜 중요한가
- X가 미래를 어떻게 바꿀까
- X의 장점과 단점은 무엇인가

같은 넓은 설명 주제에 머물러 있는가?


그리고 Reveal도

- 영향을 준다
- 중요하다
- 도움이 된다
- 삶의 질을 높일 수 있다
- 여러 요인이 작용한다
- 미래에 중요할 수 있다

처럼 일반적인 결론으로 끝나는가?


그렇다면 탈락.


좋은 Candidate는
넓은 주제를 설명하는 것이 아니라

하나의 구체적인 질문
→ 하나의 예상 밖 Mechanism 또는 연결
→ 하나의 명확한 Payoff

로 압축될 수 있어야 한다.


대상이 넓거나 유명한 것은 허용한다.

Story Angle 자체가 넓어서는 안 된다.


나쁜 예 (탈락):
대상: "인간이 만든 계단식 농장"
Core Question: "왜 산속에 계단식 농장이 만들어졌을까요?"
Reveal (예상): "경사진 지형에 적응하기 위해 만들었다."
(질문의 답이 질문만 읽고도 예상된다. Reveal도 "지형에 적응했다"는
일반 상식 수준에서 끝난다 -- 하나의 구체적 Mechanism이 없다.)

대상: "개미의 비밀스러운 의사소통 방식"
Core Question: "어떻게 개미는 화학물질로 서로의 위치와 상태를 알릴 수 있을까?"
Reveal (예상): "페로몬이라는 화학물질을 사용한다."
("페로몬을 쓴다"는 이미 널리 알려진 답이라 예상 밖의 정보가 없다.
 "화학물질로 소통한다"는 넓은 주제이지, 하나의 구체적 질문이 아니다.)

좋은 예 (통과 가능):
대상: "개미"
Core Question: "개미는 페로몬 냄새가 사라지기 전, 정확히 얼마나 지나야
길이 틀렸다는 것을 알아채고 새 길을 만들까?"
Reveal (가상): "페로몬이 옅어지는 특정 농도 임계값을 넘는 순간, 개미들이
동시에 그 경로를 버리고 다른 경로로 갈아탄다 -- 마치 투표하듯."
(같은 "개미 페로몬" 소재라도, 질문이 하나의 구체적 순간/수치/전환점을
겨냥하고 있고, Reveal이 "화학물질을 쓴다"를 넘어 하나의 놀라운
메커니즘(임계값에서의 집단적 전환)까지 도달한다.)

Explorer 자체 판단으로 "구체적이다"라고 느껴도, 위 나쁜 예처럼
Core Question의 답을 질문만 보고 예상할 수 있거나, Reveal이 상식
수준에서 끝난다면 여전히 탈락 대상이다. Hard Gate를 통과시키기 전에
"이 Reveal의 답을 시청자가 질문만 읽고 이미 알고 있는가?"를 반드시
자문하라. "그렇다"이면 같은 대상이라도 질문/Reveal을 더 좁고
구체적인 지점(수치, 조건, 전환의 순간, 반례)으로 다시 잡아라.


[HARD GATE PRINCIPLE]

"완벽한가?"

를 묻지 마라.


"명백하게 실패하는가?"

를 물어라.


Hard Gate 통과는
좋은 Candidate라는 의미가 아니다.

경쟁 단계에 참가할 자격이 있다는 의미다.


============================================================
8. PHASE 2A — SHORTLIST
============================================================

Hard Gate를 통과한 Candidate를
서로 비교하라.


가능하면 가장 강한 Candidate
최대 3개만 남겨라.

숫자를 채우기 위해
약한 Candidate를 포함하지 마라.


숫자 점수,
가중치,
총점,
평균

을 사용하지 마라.


판단 우선순위:

PAYOFF
>
HOOKABILITY
>
EXPLAINABILITY
>
NOVELTY


기계적인 사전식 순위로 사용하지 마라.


PAYOFF

답을 알았을 때
처음 질문이 충분히 보상되는가?

강한 이해,
재해석,
반전,
"아 그래서 그랬구나"

를 만드는 Candidate를 선호하라.


강한 Hook은
약한 Payoff를 보상할 수 없다.


HOOKABILITY

과장 없이도
상황이나 질문 자체가
즉시 궁금증을 만드는가?


EXPLAINABILITY

목표 시간 안에
핵심 인과관계를
심각하게 왜곡하지 않고 전달할 수 있는가?


NOVELTY

대상이 희귀한지가 아니라

답을 얼마나 예상하기 어려운지 판단하라.


Unfamiliar subject보다
Unfamiliar answer를 우선하라.


============================================================
9. PHASE 2B — MICRO NARRATIVE
============================================================

Shortlist Candidate를
동일한 Micro Narrative 구조로 압축하라.


HOOK

시청자가 처음 접할
가장 강한 상황 또는 정보 공백.


CORE QUESTION

시청자가 답을 알고 싶어야 하는
하나의 중심 질문.


HOOK와 CORE QUESTION의 관계 (중요, 필수 규칙):

HOOK이 대상을 단순히 서술만 하고
CORE QUESTION이 그 서술에 "왜"만 붙인 질문이면
두 요소가 같은 명제를 반복하는 것이다.
이런 Candidate는 자동으로 REGENERATE된다.
CORE QUESTION은 거의 항상 "왜/이유/무엇/어떻게/어째서/?" 중
하나를 포함하므로, 이 검사는 사실상 모든 Candidate에 적용된다.

나쁜 예:
HOOK: "비행기 창문 모서리는 둥급니다."
CORE QUESTION: "왜 비행기 창문 모서리는 둥글까요?"
(HOOK이 관찰만 하고, QUESTION이 그 관찰에 "왜"만 붙였다.)

좋은 예:
HOOK: "비행기 창문 모서리는 일부러 둥글게 만듭니다."
CORE QUESTION: "각진 부분에는 힘이 한곳에 몰릴 수 있기 때문일까요?"
(HOOK이 이미 "일부러"라는 의도/반전을 담아 하나의 주장을 하고,
 QUESTION은 그 주장의 구체적인 이유를 다르게 묻는다.)

필수 규칙 (예외 없음):
HOOK 문장에는 다음 마커 중 반드시 하나 이상을 포함해야 한다.
- 의도: "일부러", "의도적으로", "고의로"
- 부정/반전: "아니다", "아닙니다", "아니라", "않습니다", "않는다"
- 재확인/대비: "사실은", "실제로는", "오히려", "대신"

이 마커가 하나도 없는 HOOK은 주제와 상관없이
거의 항상 REGENERATE된다. 소재의 자연스러운 표현이
"왜 ~ 까"로 시작하는 질문이더라도 예외는 없다 --
그런 소재일수록 HOOK에 마커를 넣는 것이 더 중요하다.

HOOK을 쓰기 전에 스스로 확인하라: 이 문장에 위 마커 중
하나가 들어있는가? 들어있지 않다면 반드시 추가하라.
단, 마커만 붙이고 주어만 반복하는 것으로는 부족하다
(예: "비행기 창문 모서리는 사실은 둥급니다"처럼 마커 앞뒤가
전부 QUESTION과 겹치는 단어뿐이면 여전히 REGENERATE될 수 있다).
마커와 함께 QUESTION에는 없는 구체적인 정보나 주장을 더하라.

CORE QUESTION은 HOOK이 이미 암시한 답을 다시 묻지 말고
더 구체적인 원인/조건을 물어라.


REVEAL

그 질문에 대한
실제 핵심 설명 또는 Mechanism.


PAYOFF

Reveal을 알았을 때
처음 Hook과 Question이 어떻게 보상되는지.


각 요소는 짧고 구체적으로 작성한다.

완성 대사처럼 꾸미지 마라.

Clickbait 제목처럼 만들지 마라.

새로운 사실을 추가하지 마라.


Micro Narrative는
약한 Candidate를 강해 보이게 포장하는 도구가 아니다.


============================================================
10. PHASE 2C — SIMULTANEOUS COMPARISON
============================================================

모든 Shortlist Candidate와
Micro Narrative를 동시에 비교하라.


A vs B,
Winner vs C

형태의 순차 토너먼트를 하지 마라.


핵심 질문:

"시청자가 영상을 끝까지 본다고 할 때
어느 Candidate가 가장 강한

Hook
→ Curiosity
→ Explanation
→ Payoff

흐름을 자연스럽게 만드는가?"


특히 경계:

- Hook은 강하지만 Reveal이 평범함
- 소재는 신기하지만 관심 이유가 약함
- 답은 좋지만 설명이 지나치게 김
- 새롭지만 이해하기 어려움
- Micro Narrative로 압축하자 Payoff가 약해짐


가장 강한 Candidate를 Winner로 선택한다.


그 다음으로 강하고
Winner 없이도 독립 제작 가치가 있는 Candidate만
Runner-up으로 선택한다.


Runner-up은
단순한 2등이 아니다.


============================================================
11. DIVERSITY & BACKUP INDEPENDENCE
============================================================

Diversity는
절대 품질 점수가 아니다.


다음 상황에서만 사용한다.

1. Candidate들의 품질이 비슷함
2. 최근 콘텐츠와 반복이 체감될 정도로 명확함


최근 콘텐츠와 비교할 요소:

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

구조가 사실상 같다면
반복으로 볼 수 있다.


품질이 비슷하면
최근 콘텐츠와 다른 경험을 주는 Candidate를 선호한다.


명백하게 더 강한 Candidate를
Diversity만으로 희생하지 마라.


------------------------------------------------------------
BACKUP INDEPENDENCE
------------------------------------------------------------

Runner-up은
Winner가 후단 Fact 검사에서 죽었을 때

전체 탐색을 처음부터 하지 않고
Pipeline을 살릴 수 있는

Independent Backup

이어야 한다.


확인:

- 같은 핵심 사실 Claim에 의존하는가?
- 같은 논쟁적 기원설에 의존하는가?
- 같은 인과관계가 사실이어야 둘 다 성립하는가?
- 같은 Reveal을 재사용하는가?
- 하나의 Fact 실패가 둘 다 무너뜨릴 수 있는가?


YES가 명확하면
Independent Backup이 아니다.


독립성을 위해
약한 Candidate를 Runner-up으로 올리지 마라.


적절한 Backup이 없다면

runner_up = null

로 반환한다.


============================================================
12. FINAL SANITY CHECK
============================================================

최종 Winner를 확정하기 전에
앞선 순위를 정당화하지 말고

Winner 자체를 독립적으로 다시 검토하라.


1.

제목을 과장하지 않아도
주제 자체가 첫 몇 초 안에 궁금증을 만드는가?


2.

Core Question의 실제 답이
기대를 충분히 보상하는가?


3.

Hook보다 Payoff가 약해서
시청자가 속았다고 느낄 가능성이 없는가?


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
검증 불가능한 Claim에 의존하지 않는가?


7.

Core Question이 단순히

"X가 Y에 어떤 영향을 미쳤는가?"

같은 넓은 설명 질문은 아닌가?


질문만 읽어도
하나의 구체적인 Reveal을 기대할 수 있어야 한다.


8.

Reveal을 한 문장으로 말했을 때

구체적인

- Mechanism
- 구조
- 제약
- 사건
- 원인
- 예상 밖 연결

중 적어도 하나가 존재하는가?


Reveal이 단순히

"영향을 준다"
"중요하다"
"도움이 된다"
"여러 요인이 작용한다"

수준이라면 실패다.


9.

Payoff가 넓은 주제를 요약하는 것이 아니라

시청자가 보기 전에는
쉽게 예상하지 못했을

하나의 명확한 이해 또는 재해석을 주는가?


그렇지 않다면 Winner로 확정하지 마라.


마지막 질문:

"제목, 편집, 음악, 과장 표현의 도움 없이
이 Story 자체만 놓고도
사람들이 Shorts를 끝까지 볼 이유가 있는가?"


명확하게 YES라면
Winner를 확정한다.


Winner가 실패했다고
즉시 REGENERATE하지 마라.


독립 Runner-up이 있다면
동일한 Final Sanity Check를
새롭게 적용한다.


Runner-up이 통과하면
Runner-up을 Winner로 승격할 수 있다.


기존 Winner는 버린다.


승격 뒤 적절한 Backup이 없다면
runner_up은 null로 반환한다.


Winner와 Runner-up 모두
Final Sanity를 통과하지 못한 경우에만

REGENERATE

를 반환한다.


============================================================
13. OUTPUT CONTRACT
============================================================

반드시 유효한 JSON 객체 하나만 출력한다.

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
    "angle": "집중하는 예상 밖의 Story Angle",
    "core_question": "하나의 구체적인 중심 질문",
    "micro_narrative": {{
      "hook": "",
      "core_question": "",
      "reveal": "",
      "payoff": ""
    }},
    "fact_check_focus": [],
    "visual_proof": [
      "실제로 보여줄 수 있는 대상 또는 구조"
    ],
    "selection_reason": "왜 Shorts로 강한지 짧게 설명"
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
    "fact_check_focus": [],
    "visual_proof": [
      ""
    ],
    "selection_reason": "",
    "backup_independence": "Winner와 어떤 핵심 Fact 의존성에서 분리되는지"
  }}
}}


fact_check_focus 규칙:

후단 Fact Judge가 별도로 확인할
구체적인 핵심 Claim이 있다면 배열에 넣는다.

특별히 확인할 Claim이 없다면
빈 배열 []을 반환한다.


적절한 Runner-up이 없다면:

"runner_up": null


Winner와 Runner-up 모두 실패:

{{
  "status": "REGENERATE",
  "reason": "<여기에 이번 탐색에서 구체적으로 무엇이 부족했는지 실제로 작성. 아래는 형식 예시일 뿐 그대로 복사하지 말 것: '수도관 부식 후보의 Reveal이 일반 상식 수준(녹이 슨다)에서 끝나 예상 밖의 메커니즘이 없었음'>"
}}

주의: 위 "reason" 값은 형식을 보여주는 예시 문장이다.
절대 저 예시 문장을 그대로 복사해서 반환하지 마라.
이번 탐색에서 실제로 어떤 대상을, 어떤 이유로 왜 버렸는지
구체적으로 새로 작성해야 한다.
"""


# ============================================================
# JSON
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError(
            "Candidate Explorer 응답이 비어 있습니다."
        )

    text = str(text).strip()

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
    ).strip()

    try:

        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except Exception:
        pass

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

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    raise ValueError(
        "Candidate Explorer 응답에서 "
        "유효한 JSON 객체를 찾지 못했습니다."
    )


# ============================================================
# Validators
# ============================================================

def require_nonempty_string(
    value,
    field_name,
):

    if not isinstance(value, str):

        raise ValueError(
            f"{field_name}은 문자열이어야 합니다."
        )

    value = value.strip()

    if not value:

        raise ValueError(
            f"{field_name}이 비어 있습니다."
        )

    return value


def normalize_string_list(
    value,
    field_name,
    *,
    require_nonempty=False,
):

    if not isinstance(value, list):

        raise ValueError(
            f"{field_name}은 배열이어야 합니다."
        )

    result = []

    for idx, item in enumerate(value):

        if not isinstance(item, str):

            raise ValueError(
                f"{field_name}[{idx}]는 "
                "문자열이어야 합니다."
            )

        item = item.strip()

        if item:
            result.append(item)

    if require_nonempty and not result:

        raise ValueError(
            f"{field_name}에 "
            "유효한 문자열이 없습니다."
        )

    return result


def validate_micro_narrative(
    value,
    prefix,
):

    if not isinstance(value, dict):

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
                value.get(field),
                (
                    f"{prefix}."
                    f"micro_narrative."
                    f"{field}"
                ),
            )
        )

    return result


def validate_candidate(
    candidate,
    *,
    prefix,
    runner_up=False,
):

    if not isinstance(candidate, dict):

        raise ValueError(
            f"{prefix}는 객체여야 합니다."
        )

    result = {
        "topic":
            require_nonempty_string(
                candidate.get("topic"),
                f"{prefix}.topic",
            ),

        "angle":
            require_nonempty_string(
                candidate.get("angle"),
                f"{prefix}.angle",
            ),

        "core_question":
            require_nonempty_string(
                candidate.get("core_question"),
                f"{prefix}.core_question",
            ),

        "micro_narrative":
            validate_micro_narrative(
                candidate.get(
                    "micro_narrative"
                ),
                prefix,
            ),

        # 비어 있어도 정상.
        "fact_check_focus":
            normalize_string_list(
                candidate.get(
                    "fact_check_focus"
                ),
                f"{prefix}.fact_check_focus",
                require_nonempty=False,
            ),

        # Visual Proof는 실제 제작을 위해 최소 하나 필요.
        "visual_proof":
            normalize_string_list(
                candidate.get(
                    "visual_proof"
                ),
                f"{prefix}.visual_proof",
                require_nonempty=True,
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


def validate_explorer_output(data):

    if not isinstance(data, dict):

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

    if status == "REGENERATE":

        return {
            "status":
                "REGENERATE",

            "reason":
                require_nonempty_string(
                    data.get("reason"),
                    "reason",
                ),
        }

    if status != "SELECTED":

        raise ValueError(
            "Candidate Explorer status는 "
            "SELECTED 또는 REGENERATE여야 합니다. "
            f"현재 값: {status}"
        )

    winner = validate_candidate(
        data.get("winner"),
        prefix="winner",
        runner_up=False,
    )

    runner_up_data = (
        data.get("runner_up")
    )

    if runner_up_data is None:

        runner_up = None

    else:

        runner_up = validate_candidate(
            runner_up_data,
            prefix="runner_up",
            runner_up=True,
        )

    if runner_up:

        winner_topic = (
            winner["topic"]
            .replace(" ", "")
            .lower()
        )

        runner_topic = (
            runner_up["topic"]
            .replace(" ", "")
            .lower()
        )

        if winner_topic == runner_topic:

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
# Recent Context
# ============================================================

def build_recent_context(
    recent_topics=None,
    recent_content=None,
):

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

    if recent_topics:

        return "\n".join(
            f"- {item}"
            for item in recent_topics[-20:]
        )

    return "최근 콘텐츠 기록 없음."


# ============================================================
# Execution Context
# ============================================================

def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
):

    if not isinstance(topic_info, dict):

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

    recent_text = build_recent_context(
        recent_topics,
        recent_content,
    )

    if rejected_topics:

        rejected_text = "\n".join(
            f"- {item}"
            for item in rejected_topics
        )

    else:

        rejected_text = (
            "이번 실행에서 폐기된 후보 없음."
        )

    fixed_topic = str(
        fixed_topic or ""
    ).strip()

    if fixed_topic:

        fixed_topic_gate_feedback = str(
            fixed_topic_gate_feedback or ""
        ).strip()

        feedback_section = ""

        if fixed_topic_gate_feedback:
            feedback_section = f"""
============================================================
[PREVIOUS CANDIDATE GATE FEEDBACK]
============================================================

직전 fixed-topic Candidate가 아래 이유로 거절되었다.

{fixed_topic_gate_feedback}

주제 문자열은 그대로 유지하되 같은 Core Question,
Reveal, Mechanism을 반복하지 마라.
거절 이유를 직접 해결하도록 Story Angle을 더 좁히고,
눈에 보이는 구체 관찰, 실제 제약, trade-off,
counterintuitive result 중 근거 있는 요소를 질문과 Reveal에
직접 반영하라.

Candidate Gate와 기존 품질 규칙은 그대로 적용한다.
사실을 발명하거나 약한 Candidate를 억지로 통과시키지 마라.
"""

        return f"""
[EXECUTION CONTEXT - FIXED PRODUCTION TOPIC]

지정 production 주제:
{fixed_topic}


중요:

이번 실행은 지정 주제 모드다.
주제를 다른 대상으로 바꾸거나 넓히지 마라.

winner.topic은 반드시 아래 문자열과
정확히 동일해야 한다.

{fixed_topic}

이 지정 주제 안에서만
가장 강한 Story Angle,
Core Question,
Reveal,
Payoff를 탐색하라.

Runner-up으로 다른 주제를 제안하지 마라.
runner_up은 null로 반환하라.

기존 Candidate Explorer의
Hard Gate, Fact safety, visual proof,
Final Sanity 규칙은 그대로 적용한다.

최근 콘텐츠는 참고하되
지정 주제를 다른 주제로 교체하지 마라.

{feedback_section}

Candidate Explorer 전체 규칙을 수행한 뒤
OUTPUT CONTRACT에 맞는
JSON 객체 하나만 반환하라.
"""

    run_scope = os.environ.get(
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

[AVIATION OBSERVABLE SEED SUPPLY CONTRACT — RUN 33887547463]
The broad direction is an exploration axis, never the Candidate itself.
Before evaluating Candidate quality, instantiate several materially distinct concrete observable seeds inside the assigned aviation direction.
Do not evaluate the broad direction itself as a Candidate.

Each internal seed must bind all of these meanings before Hard Gate evaluation:
- observable_object_or_feature: one real object, part, action, indication, movement, or visible change a viewer can point to
- specific_observation: exactly what the passenger/viewer sees, hears, feels, or notices
- viewer_question: a direct question about why that concrete observation exists, moves, changes, or is placed there
- candidate_mechanism_or_constraint: at least one grounded physical mechanism, operational constraint, trade-off, or causal step that could explain it
- direct_result: the immediate result of that mechanism/constraint, not a generic benefit label
- visual_proof_target: the concrete subject/process the final Short could actually show

Map those meanings into the existing Candidate JSON instead of inventing a parallel schema: topic/angle/core_question/micro_narrative, visual_proof, fact_check_focus, and the existing aviation specificity extension fields.
A broad category name such as a cabin system, safety system, engine/intake area, flight performance, or pressure/air-conditioning domain may be a search axis only; narrow it to one concrete observable object/feature/action/change before Candidate evaluation.
Do not hard-code or prefer any named answer or component. The concrete seeds must be discovered inside the current direction from grounded knowledge.
This staged seed instantiation happens inside the existing Candidate Explorer call; it requires no additional API call.

[SUPPLY SHORTAGE IS NOT A TERMINAL RESULT]
위 최소 10개는 탐색 목표이지 SELECTED를 반환하기 위한 최소 통과 숫자가 아니다.
grounded하고 구체적이며 필수 필드가 완성된 Candidate가 1개라도 남아 있다면 후보 수가 목표보다 적다는 이유만으로 REGENERATE를 반환하지 마라.
그 경우 구조·사실성 Hard Gate를 통과한 남은 Candidate 중 가장 강한 하나를 Winner로 SELECTED하라.
독립적인 두 번째 후보가 없으면 runner_up은 null이어도 된다.
REGENERATE는 usable grounded Candidate가 0개인 경우, 또는 남은 모든 후보가 구조·사실성 Hard Gate를 통과하지 못한 경우에만 사용하라.
"후보 공급 부족", "후보 숫자 부족", "충분한 후보를 탐색하지 못함" 자체는 Candidate가 1개 이상 살아 있는 상황의 REGENERATE 이유가 될 수 없다.
이 규칙은 Candidate Gate를 우회하지 않는다. SELECTED된 Winner는 기존 독립 Candidate Gate에서 똑같이 심사받고 약하면 그대로 탈락해야 한다.

[AVIATION SUPPLY PRECEDENCE — RUN 33878093224]
이 aviation 자동 공급 모드에서는 공급 단계와 독립 Candidate Gate의 책임을 섞지 마라.
기존 Candidate Explorer의 편집적 final sanity와 novelty 판단은 후보 간 순위를 정하는 데만 사용한다.
특히 다음 Candidate Gate 성격의 편집 판단만으로 grounded Candidate를 공급 단계에서 제거하지 마라:
- BROAD / GENERIC QUESTION
- GENERIC REVEAL
- PREDICTABLE PAYOFF
- weak payoff / novelty concern

위 편집적 판단만으로 Candidate pool을 0개로 만들거나 REGENERATE를 반환하는 근거로 사용하지 마라.
구조·사실성 Hard Gate는 그대로 fail-close한다. 즉 placeholder, 항공 범위 이탈, 실제 존재/인과가 의심되는 내용, 필수 구조 누락, visual proof 부재는 계속 제거한다.
독립 Candidate Gate가 최종 편집성 PASS/REGENERATE authority다.
이 scoped precedence는 뒤에 나오는 일반적인 final sanity 지시보다 우선한다.

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

후보 비교와 Winner 선택에서는 기존 scoring/shortlist/novelty 신호를 강한 후보의 순위를 정하는 데 사용하라.
단, aviation 공급 모드에서는 위 [AVIATION SUPPLY PRECEDENCE — RUN 33878093224]에 따라 편집적 broad/generic/predictable 판단만으로 공급을 0으로 만들지 마라.
Gate 기준을 낮추지 마라. 구조·사실성 Hard Gate와 downstream Candidate Gate 기준은 그대로 유지한다.
"""

    return f"""
[EXECUTION CONTEXT]
{scope_context}

이번 탐색의 넓은 분야:
{category}

이번 탐색 방향:
{direction}


중요:

위 분야와 방향은
탐색의 출발점이지
특정 대상이나 답을 강제하는 명령이 아니다.

방향에 억지로 맞추기 위해
약한 Candidate나
지어낸 연결을 만들지 마라.


============================================================
[RECENT CONTENT]
============================================================

{recent_text}


============================================================
[REJECTED IN THIS RUN]
============================================================

{rejected_text}


이번 실행에서 폐기된 Candidate와

- 사실상 동일한 Core Question
- 동일한 Reveal
- 동일한 Mechanism

을 다시 Winner로 선택하지 마라.


Candidate Explorer 전체 규칙을 수행한 뒤
OUTPUT CONTRACT에 맞는

JSON 객체 하나만 반환하라.
"""


_SELF_CRITIQUE_PROMPT = """
[SYSTEM PROMPT: NARROWNESS SELF-CRITIQUE]

너는 Candidate Explorer가 방금 고른 Winner 하나를
제출 직전에 검사하는 엄격한 자기 비평가다.

새 Candidate를 만들지 마라.
대본을 쓰지 마라.

딱 하나만 판단하라:

이 Core Question의 답을,
시청자가 질문 문장만 읽고도
이미 예상할 수 있는가?

또는 Reveal이

- 영향을 준다
- 적응했다
- 화학물질/메커니즘을 사용한다
- 방법을 찾았다

같은 일반 상식 수준의 설명으로 끝나는가?

둘 중 하나라도 그렇다면 NARROW하지 않다.

아래 JSON 하나만 반환하라:

{
  "verdict": "NARROW_ENOUGH" | "TOO_BROAD",
  "reason": "판단 이유를 한 문장으로"
}
"""


# NARROWNESS_BOUNDED_RECOVERY_V1
# Run 618: the Narrowness self-critique gate above correctly rejected every
# SELECTED Winner it saw (generic Reveals with no specific mechanism), but
# once rejected, Explorer discarded the whole subject and moved to a brand
# new, unrelated topic direction. Across 20 attempts this meant every
# TOO_BROAD verdict cost the Explorer its remaining attempt budget instead
# of being fixed. This does NOT change the self-critique's own pass/fail
# logic or threshold in any way -- a recovered candidate goes back through
# the exact same, unmodified _self_critique_narrowness() a normal candidate
# would. It only gives a rejected candidate a small, bounded number of
# chances to become narrower on the SAME subject before Explorer gives up
# on it and moves to a new direction, same as before.
MAX_NARROWNESS_REWRITES = 2


_NARROWNESS_REWRITE_PROMPT = """
[SYSTEM PROMPT: NARROWNESS TARGETED REWRITE]

너는 Candidate Explorer가 이미 고른 Winner 하나를
같은 소재, 같은 대상 안에서
더 좁고 구체적인 버전으로 다시 쓰는 역할이다.

새로운 대상이나 다른 방향으로 바꾸지 마라.
반드시 같은 대상(subject)을 그대로 유지하라 --
subject 필드(topic/angle에 들어간 핵심 대상)를
다른 사물/장소/현상으로 바꾸면 안 된다.

같은 대상 안에서, 아래 [REJECTION REASON]에서
지적된 일반적인/예상 가능한 설명 대신
다음 중 하나의 축을 명확히 좁혀라
("더 구체적으로 써라" 같은 막연한 지시가 아니라
반드시 아래 중 하나를 실제로 선택해서 좁혀야 한다):

- 특정 부품/부위 (전체가 아닌 그 안의 한 부분)
- 특정 위치 (전체가 아닌 특정 지점)
- 특정 조건 (특정 상황/환경에서만)
- 특정 수치/임계값
- 특정 예외 (일반 규칙이 깨지는 경우)
- 특정 전후 차이 (달라지기 전/후의 비교)
- 특정 관찰 가능한 모양 (눈에 보이는 구체적 형태)

Reveal을 다시 쓸 때 특히 주의하라:
"효율성", "안전성", "최적화", "성능 향상",
"압력 감소", "안정성 향상" 같은 일반적 목적어
하나로 문장이 끝나면 그것은 답이 아니라
질문을 반복한 것으로 간주된다.
그 목적을 실제로 달성하는 물리적/구조적/인과적
메커니즘이나 조건/수치를 한 단계 더 추가해서
Reveal을 완성하라 (이런 단어 자체를 쓰지 말라는
뜻이 아니라, 그 단어에서 답을 멈추지 말라는 뜻이다).

예:
넓음: "비행기 날개는 왜 공기 흐름을 최적화할까?"
좁음: "비행기 날개 끝은 왜 위로 꺾여 있을까?"
(위 예시는 축의 성격 참고용 -- 실제 대상은
반드시 원래 Winner의 subject를 그대로 유지하라)

OUTPUT CONTRACT의 winner 객체와
동일한 형식의 JSON 객체 하나만 반환하라
(status 필드 없이 winner 필드 내용만):

{
  "topic": "",
  "angle": "",
  "core_question": "",
  "micro_narrative": {
    "hook": "",
    "core_question": "",
    "reveal": "",
    "payoff": ""
  },
  "fact_check_focus": [],
  "visual_proof": [""],
  "selection_reason": ""
}
"""


def _rewrite_narrower_candidate(winner, reason, *, model=MODEL):
    """Targeted, same-subject rewrite of a Winner the narrowness self-critique
    rejected as TOO_BROAD.

    Feeds the critique's own rejection reason back in and asks for a
    narrower version of the SAME subject (never a new topic direction).
    The rewritten candidate is validated with the same
    ``validate_candidate`` schema check every normal Winner goes through,
    and it is NOT treated as accepted here -- the caller must still run it
    back through the unmodified ``_self_critique_narrowness`` gate.

    Returns the rewritten winner dict, or ``None`` if the rewrite call
    failed or produced an unusable/malformed candidate (in which case the
    caller should treat this rewrite attempt as spent and move on).
    """

    micro = winner.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    original_summary = (
        f"Topic: {winner.get('topic', '')}\n"
        f"Angle: {winner.get('angle', '')}\n"
        f"Core Question: {winner.get('core_question', '')}\n"
        f"Hook: {micro.get('hook', '')}\n"
        f"Reveal: {micro.get('reveal', '')}\n"
        f"Payoff: {micro.get('payoff', '')}\n"
        f"\n[REJECTION REASON]\n{reason}"
    )

    call_number = authorize_call(model)
    print(f"💳 Narrowness rewrite API call authorized: #{call_number}")

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _NARROWNESS_REWRITE_PROMPT},
                {"role": "user", "content": original_summary},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
    except Exception:
        return None

    usage = record_usage(model, response)
    print(f"💰 Narrowness rewrite call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        return None

    try:
        parsed = extract_json(content)
    except Exception:
        return None

    try:
        return validate_candidate(parsed, prefix="winner", runner_up=False)
    except Exception:
        return None


# Conservative, deterministic pre-check run BEFORE the expensive LLM
# narrowness self-critique call. It only exists to catch the cheapest,
# most obviously-generic shape of question -- "why is X efficient/safe/
# optimized" with literally nothing else concrete in the sentence -- so
# that shape never burns an LLM call on the full critique. It is
# intentionally narrow: it must NEVER flag a question that names any
# concrete part/location/condition/number, even if it also contains one
# of the generic adjectives below. This is a supplement to, never a
# replacement for, the real (LLM) Narrowness self-critique and Candidate
# Gate, which remain unmodified and are still the actual gates.
_GENERIC_BARE_QUESTION_RE = re.compile(
    r"^[가-힣A-Za-z0-9 ]{1,12}(은|는|이|가)\s*"
    r"왜\s*"
    r"(효율적(?:이|인가|일까)?|"
    r"안전(?:한가|할까|하다)?|"
    r"최적화(?:되어|된|되는가|될까)?|"
    r"성능이?\s*(?:좋|향상)(?:는가|되는가|될까|한가)?|"
    r"안정적(?:인가|일까)?)\??$"
)


def _is_trivially_generic_question(core_question):
    """True only for a bare "왜 효율적인가/안전한가/최적화되는가" style
    question with no other concrete content -- see module note above the
    regex for why this must stay conservative. Anything with extra words
    describing a part, location, condition or number falls outside the
    fixed-width pattern and is correctly left to the real LLM gates.
    """

    if not isinstance(core_question, str):
        return False

    text = core_question.strip()
    if not text:
        return False

    return bool(_GENERIC_BARE_QUESTION_RE.match(text))


def _self_critique_narrowness(winner, *, model=MODEL):
    """Cheap pre-filter before the independent, more expensive Winner Gate.

    Prompt examples alone (worked bad/good cases in section 8) were not
    enough to stop gpt-4o-mini from repeatedly submitting broad-question /
    generic-reveal candidates that the Winner Gate then rejects after a
    full round-trip (run 607, run 608 -- same failure mode both times even
    after the examples were added). This adds a second, narrowly-scoped
    self-critique call that asks the model to judge ONLY narrowness on its
    own already-selected Winner, separate from the generative act of
    picking one. Judging a fixed candidate is an easier task than
    generating a good one, so this catches some cases the single-pass
    generation missed -- it is a cheap supplement to the Explorer's own
    Hard Gate, not a replacement for the independent Winner Gate.
    """

    micro = winner.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    if _is_trivially_generic_question(winner.get("core_question", "")):
        print(
            "🪫 Narrowness pre-check: bare generic question pattern "
            "detected -- skipping LLM self-critique call"
        )
        return {
            "verdict": "TOO_BROAD",
            "reason": (
                "결정론적 사전 검사: Core Question이 다른 구체적 내용 "
                "없이 '왜 효율적/안전/최적화되는가' 형태로만 되어 있습니다."
            ),
        }

    summary = (
        f"Topic: {winner.get('topic', '')}\n"
        f"Core Question: {winner.get('core_question', '')}\n"
        f"Hook: {micro.get('hook', '')}\n"
        f"Reveal: {micro.get('reveal', '')}\n"
        f"Payoff: {micro.get('payoff', '')}"
    )

    call_number = authorize_call(model)
    print(f"💳 Narrowness self-critique API call authorized: #{call_number}")

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SELF_CRITIQUE_PROMPT},
            {"role": "user", "content": summary},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    usage = record_usage(model, response)
    print(f"💰 Narrowness self-critique call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        # Fail open: an empty self-critique response should not block a
        # candidate the Explorer already selected. The independent Winner
        # Gate remains the real backstop either way.
        return {"verdict": "NARROW_ENOUGH", "reason": "self-critique response empty"}

    try:
        parsed = extract_json(content)
    except Exception:
        return {"verdict": "NARROW_ENOUGH", "reason": "self-critique response unparsable"}

    if not isinstance(parsed, dict) or parsed.get("verdict") not in (
        "NARROW_ENOUGH",
        "TOO_BROAD",
    ):
        return {"verdict": "NARROW_ENOUGH", "reason": "self-critique response malformed"}

    return parsed


# ============================================================
# Explorer
# ============================================================

def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
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
            fixed_topic=fixed_topic,
            fixed_topic_gate_feedback=(
                fixed_topic_gate_feedback
            ),
        )
    )

    call_number = (
        authorize_call(
            model
        )
    )

    print(
        "💳 Candidate Explorer API call "
        f"authorized: #{call_number}"
    )

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

    if usage.get(
        "over_budget",
        False,
    ):

        print(
            "⚠️ 이번 호출로 Budget 한도를 "
            "초과했습니다."
        )

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

    parsed = _repair_aviation_specificity_output_if_needed(
        parsed,
        model=model,
    )

    result = (
        validate_explorer_output(
            parsed
        )
    )

    fixed_topic = str(
        fixed_topic or ""
    ).strip()

    if (
        fixed_topic
        and result.get("status") == "SELECTED"
    ):

        winner_topic = str(
            result.get(
                "winner",
                {},
            ).get(
                "topic",
                "",
            )
        ).strip()

        if winner_topic != fixed_topic:

            raise ValueError(
                "Candidate Explorer가 지정 production 주제를 "
                "변경했습니다."
            )

        result["runner_up"] = None

    status = result[
        "status"
    ]

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
            result["winner"]
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
            winner["topic"],
        )

        print(
            "Question:",
            winner[
                "core_question"
            ],
        )

        # Observability: the first-generation Reveal is the element run 621's
        # rejections overwhelmingly named ("Reveal이 일반 상식 수준의 설명으로
        # 끝나고 있어"), but it was never printed, so first-generation reveal
        # quality could not be measured from the log at all.
        _selected_micro = winner.get("micro_narrative")
        if not isinstance(_selected_micro, dict):
            _selected_micro = {}

        print(
            "Reveal:",
            _selected_micro.get("reveal", ""),
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

        critique = _self_critique_narrowness(winner, model=model)

        rewrite_attempts = 0

        while (
            critique.get("verdict") == "TOO_BROAD"
            and rewrite_attempts < MAX_NARROWNESS_REWRITES
        ):

            if not has_budget_for_rewrite():
                print("")
                print("=" * 64)
                print(
                    "⚠️  NARROWNESS BOUNDED RECOVERY: skipped "
                    "(API budget reserve too low) -- discarding candidate"
                )
                print("=" * 64)
                break

            print("")
            print("=" * 64)
            print(
                "🔧 NARROWNESS BOUNDED RECOVERY: "
                f"rewrite {rewrite_attempts + 1}/{MAX_NARROWNESS_REWRITES}"
            )
            print("=" * 64)
            print("이유:", critique.get("reason", ""))
            print("=" * 64)

            rewritten = _rewrite_narrower_candidate(
                winner,
                critique.get("reason", ""),
                model=model,
            )

            rewrite_attempts += 1

            if rewritten is None:
                # Rewrite itself failed or was unusable -- this attempt is
                # spent. Keep the original (still TOO_BROAD) winner/critique
                # so the loop condition above can still try again if
                # attempts remain, and so the final REGENERATE below (if
                # attempts run out) reports the real last critique reason.
                continue

            winner = rewritten

            # Observability: run 621's log printed only the ORIGINAL Winner,
            # so a rewrite that stayed generic was indistinguishable from one
            # that narrowed correctly and was rejected for another reason.
            # Printing the rewritten subject/question/reveal makes the
            # generation-quality effect of this fix measurable from the log.
            _rewritten_micro = winner.get("micro_narrative")
            if not isinstance(_rewritten_micro, dict):
                _rewritten_micro = {}
            print("🔁 Rewritten Winner:", winner.get("topic", ""))
            print("🔁 Rewritten Question:", winner.get("core_question", ""))
            print("🔁 Rewritten Reveal:", _rewritten_micro.get("reveal", ""))

            critique = _self_critique_narrowness(winner, model=model)

        if critique.get("verdict") == "TOO_BROAD":

            print("")
            print("=" * 64)
            print("🔎 NARROWNESS SELF-CRITIQUE: TOO_BROAD")
            print("=" * 64)
            print("이유:", critique.get("reason", ""))
            print("=" * 64)

            return {
                "status": "REGENERATE",
                "reason": (
                    "Narrowness self-critique: "
                    f"{critique.get('reason', '')}"
                ),
            }

        result["winner"] = winner

        return result

    print("=" * 64)

    return result


# AVIATION_SYSTEM_AUTHORITY_SUPPLY_V1
# Run 33883590214 proved that the aviation ranking-only instruction in the user
# execution context could conflict with older terminal editorial rules in the
# system prompt. Install the scope-aware precedence at the same SYSTEM authority.
CANDIDATE_EXPLORER_PROMPT += """

[AVIATION SYSTEM-AUTHORITY SUPPLY CONTRACT — RUN 33883590214]
This block is part of the same SYSTEM-prompt authority as Sections 7 and 12.
When the execution context declares SHORTS_CANDIDATE_SCOPE=aviation, this scoped
contract overrides only contradictory editorial terminal semantics in those
sections. It does not weaken structural, factual, grounding, scope, visual-proof,
or schema requirements.

AVIATION SUPPLY RESPONSIBILITY:
Candidate Explorer is the grounded + structurally usable Candidate supplier.
The independent Candidate Gate remains the editorial authority for final
publish-worthiness.

For aviation supply, the following are ranking/preference signals only and must
not be the sole reason to return REGENERATE or reduce an otherwise grounded,
structurally complete Candidate pool to zero:
- PREDICTABLE PAYOFF
- WEAK PAYOFF / SO WHAT?
- GENERIC EXPLANATION / BROAD THEME or broad question
- weak novelty
- generic reveal when the Candidate still has a real grounded mechanism or
  constraint that can be evaluated downstream

If at least one Candidate remains grounded, structurally complete, inside the
aviation scope, supported by a concrete visual proof, and valid under the output
schema, return SELECTED with the strongest surviving Candidate even when it has
one or more of the editorial weaknesses above. Those weaknesses may lower its
rank; they do not by themselves erase supply. The independent Candidate Gate may
then return REGENERATE for those same editorial weaknesses.

Aviation structural/factual supply failures remain terminal. Continue to reject
or return REGENERATE when no Candidate survives because of any of these:
- fabricated or unsupported causal claim
- placeholder or required structure missing
- factual contradiction or grounding/evidence insufficient
- canonical subject is unclear or unsupported
- aviation scope violation
- visual-proof requirement failure
- malformed schema/output

Final Sanity in aviation supply must apply the same separation: factual,
structural, grounding, scope and visual-proof failures can be terminal; purely
editorial broad/generic/predictable/weak-novelty findings are ranking signals and
belong to the independent Candidate Gate for terminal editorial judgment.

For non-aviation scopes, keep Sections 7 and 12 unchanged and preserve their
existing terminal semantics.

[AVIATION OBSERVABLE SEED SUPPLY CONTRACT — RUN 33887547463]
For aviation supply, the assigned broad direction is an exploration axis, never
the Candidate itself. Before applying Hard Gate or Final Sanity, instantiate
several materially distinct concrete observable seeds inside that direction.
Do not evaluate the broad direction itself as a Candidate.

Each seed must bind these meanings before Candidate evaluation:
- observable_object_or_feature
- specific_observation
- viewer_question
- candidate_mechanism_or_constraint
- direct_result
- visual_proof_target

A seed is eligible for supply only when its physical/observable subject is clear,
its mechanism/constraint is grounded enough to state without invention, and its
visual proof target is concrete. Map those meanings into the existing Candidate
schema and aviation specificity fields; do not add a second output schema.
Broad category labels may guide search but must be narrowed to one concrete
object, feature, action, indication, movement, or visible change before Hard Gate.
Do not hard-code any particular aircraft component or answer. This staged
instantiation happens inside the current Candidate Explorer call and makes no
additional API call.

Apply the existing aviation editorial separation only after concrete seed
instantiation: editorial weakness may rank surviving seeds but cannot erase an
otherwise grounded/structurally valid seed. Fabrication, factual contradiction,
grounding insufficiency, aviation-scope violation, missing visual proof, missing
required structure, and malformed output remain terminal fail-close conditions.
"""

# CANDIDATE_SUPPLY_OBSERVABILITY_V1
# Host-observable telemetry only. The model does not expose its internal seed or
# discard counts, so never fabricate them. Log only the boundary and reason code
# deterministically visible from the returned JSON.
_aviation_supply_observability_previous_validate = validate_explorer_output


def validate_explorer_output(data):
    result = _aviation_supply_observability_previous_validate(data)
    if (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() == "aviation"
        and isinstance(result, dict)
        and str(result.get("status", "")).strip().upper() == "REGENERATE"
    ):
        reason = str(result.get("reason", "")).strip().lower()
        if "usable grounded candidate" in reason and (
            "0개" in reason or "zero" in reason or "없" in reason
        ):
            reason_code = "ZERO_USABLE_GROUNDED"
            zero_stage = "model_output_pre_host_candidate_validation"
        else:
            reason_code = "MODEL_REGENERATE_OTHER"
            zero_stage = "model_output_pre_host_candidate_validation"
        print(
            "[CANDIDATE_SUPPLY_DIAG] "
            f"final_zero_stage={zero_stage} "
            f"discard_reason_code={reason_code} "
            "model_internal_candidate_counts=unavailable"
        )
    return result

# AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V1
# AVIATION_CANDIDATE_SPECIFICITY_CONTRACT_V2
# Candidate Gate is unchanged. This layer makes the Explorer produce candidates
# at the level the Gate already expects, including fixed-topic retries.
_AVIATION_SPECIFICITY_FIELDS = (
    "specific_observation",
    "constraint",
    "counterintuitive_result",
    "tradeoff",
    "concrete_condition",
)
_AVIATION_DOMAIN_TERMS = {
    "비행기", "항공", "여객기", "기내", "객실", "조종석", "활주로", "공항",
    "엔진", "흡입구", "흡기", "날개", "윙렛", "착륙장치", "랜딩기어", "좌석",
    "aircraft", "airplane", "aviation", "airliner", "cabin", "cockpit", "runway",
    "engine", "wing", "winglet", "landing gear",
}
_AVIATION_GENERIC_REVEAL_TERMS = (
    "안전을 높", "안전성을 높", "안전을 위해", "효율을 높", "효율을 위해",
    "편의성을 높", "편의를 위해", "공기 흐름을 개선", "승객 경험을 개선",
    "승객 경험을 높", "소음을 줄", "성능을 높", "도움이 된다", "도움을 준다",
    "연료 효율", "비행 효율", "비행 안정", "비행 성능", "이점",
)
_AVIATION_GENERIC_QUESTION_FRAGMENTS = (
    "왜 특정하게 설계", "왜 이런 구조", "왜 이렇게 생", "왜 이런 배열",
    "왜 특정 배열", "왜 특정 위치", "왜 특정한 형태", "왜 존재할까",
    "어떤 영향을", "어떤 이점", "왜 효율", "성능에", "효율에",
)
_AVIATION_STOP_TOKENS = {
    "비행기", "항공", "여객기", "왜", "이유", "설계", "구조", "특정", "장치",
    "시스템", "기능", "있다", "하는", "위해", "때문", "일반", "실제",
    "효율", "성능", "안전", "이점", "영향", "도움",
}
_AVIATION_MECHANISM_HINTS = (
    "와류", "유도항력", "압력차", "압력 차", "양력", "항력", "난류", "소용돌이",
    "vortex", "induced drag", "pressure", "lift", "drag", "turbulence",
)


def _aviation_norm(value):
    return re.sub(r"[^0-9a-zA-Z가-힣]+", " ", str(value or "").lower()).strip()


def _aviation_detail_values(candidate):
    return [
        str(candidate.get(field) or "").strip()
        for field in _AVIATION_SPECIFICITY_FIELDS
        if str(candidate.get(field) or "").strip()
    ]


def _aviation_detail_tokens(value):
    return {
        token
        for token in _aviation_norm(value).split()
        if len(token) >= 2 and token not in _AVIATION_STOP_TOKENS
    }


def aviation_scope_compatible(candidate):
    combined = " ".join(
        [
            str(candidate.get("topic") or ""),
            str(candidate.get("angle") or ""),
            str(candidate.get("core_question") or ""),
            str((candidate.get("micro_narrative") or {}).get("reveal") or ""),
        ]
    ).lower()
    return any(term in combined for term in _AVIATION_DOMAIN_TERMS)


def _aviation_detail_is_referenced(candidate, details):
    micro = candidate.get("micro_narrative") or {}
    combined = _aviation_norm(
        " ".join(
            [
                str(candidate.get("topic") or ""),
                str(candidate.get("core_question") or ""),
                str(micro.get("reveal") or ""),
            ]
        )
    )
    combined_tokens = set(combined.split())
    for detail in details:
        normalized = _aviation_norm(detail)
        if normalized and normalized in combined:
            return True
        detail_tokens = _aviation_detail_tokens(detail)
        if detail_tokens and combined_tokens & detail_tokens:
            return True
    return False


def _aviation_generic_reveal(candidate, details):
    reveal = _aviation_norm((candidate.get("micro_narrative") or {}).get("reveal"))
    if not reveal:
        return True
    if not any(term in reveal for term in _AVIATION_GENERIC_REVEAL_TERMS):
        return False
    reveal_tokens = set(reveal.split())
    for detail in details:
        if reveal_tokens & _aviation_detail_tokens(detail):
            return False
    return True


def aviation_candidate_quality_check(candidate):
    if not isinstance(candidate, dict):
        return False, "aviation candidate is not an object"
    if not aviation_scope_compatible(candidate):
        return False, "aviation candidate drifted outside aviation scope"
    details = _aviation_detail_values(candidate)
    if not details:
        return False, "generic aviation topic: no concrete observation/constraint/result/trade-off/condition"
    core = _aviation_norm(candidate.get("core_question"))
    if (
        any(fragment in core for fragment in _AVIATION_GENERIC_QUESTION_FRAGMENTS)
        and not _aviation_detail_is_referenced(candidate, details)
    ):
        return False, "generic why-design question without a concrete element"
    if not _aviation_detail_is_referenced(candidate, details):
        return False, "topic/core question/reveal does not directly carry the concrete element"
    if _aviation_generic_reveal(candidate, details):
        return False, "generic benefit reveal without a concrete mechanism/constraint/trade-off"
    return True, "aviation candidate has concrete Shorts-level specificity"


_aviation_specificity_previous_validate_candidate = validate_candidate


def validate_candidate(candidate, *, prefix, runner_up=False):
    result = _aviation_specificity_previous_validate_candidate(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )
    for field in _AVIATION_SPECIFICITY_FIELDS:
        value = candidate.get(field) if isinstance(candidate, dict) else None
        if isinstance(value, str) and value.strip():
            result[field] = value.strip()
    return result


_aviation_specificity_previous_validate_output = validate_explorer_output


def validate_explorer_output(data):
    result = _aviation_specificity_previous_validate_output(data)
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return result
    if result.get("status") != "SELECTED":
        return result
    winner = result.get("winner") or {}
    winner_ok, winner_reason = aviation_candidate_quality_check(winner)
    if winner_ok:
        return result
    runner = result.get("runner_up")
    if runner:
        runner_ok, _ = aviation_candidate_quality_check(runner)
        if runner_ok:
            promoted = dict(runner)
            promoted.pop("backup_independence", None)
            return {"status": "SELECTED", "winner": promoted, "runner_up": None}
    return {
        "status": "REGENERATE",
        "reason": f"Aviation Explorer quality check: {winner_reason}",
    }


_aviation_specificity_previous_build_context = build_execution_context


def build_execution_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
):
    try:
        context = _aviation_specificity_previous_build_context(
            topic_info,
            recent_topics=recent_topics,
            recent_content=recent_content,
            rejected_topics=rejected_topics,
            fixed_topic=fixed_topic,
            fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        )
    except TypeError as exc:
        message = str(exc)
        if not (
            "unexpected keyword argument 'fixed_topic'" in message
            or "unexpected keyword argument 'fixed_topic_gate_feedback'" in message
        ):
            raise
        context = _aviation_specificity_previous_build_context(
            topic_info,
            recent_topics=recent_topics,
            recent_content=recent_content,
            rejected_topics=rejected_topics,
        )

    # FIXED_AVIATION_SCOPE_CONTRACT_V1
    # A fixed aviation topic is aviation even when candidate_scope is intentionally
    # blank. Production fixed-topic runs must still receive the specificity/mechanism
    # contract instead of silently falling back to the generic Explorer prompt.
    fixed = str(fixed_topic or "").strip()
    scope_is_aviation = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() == "aviation"
    )
    fixed_is_aviation = bool(fixed) and any(
        term in fixed.lower() for term in _AVIATION_DOMAIN_TERMS
    )
    if not (scope_is_aviation or fixed_is_aviation):
        return context

    rejected = [str(item).strip() for item in (rejected_topics or []) if str(item).strip()]
    rejected_feedback = "\n".join(f"- {item}" for item in rejected) or "- 없음"
    fixed = str(fixed_topic or "").strip()
    gate_feedback = str(fixed_topic_gate_feedback or "").strip()
    fixed_contract = ""
    if fixed:
        fixed_contract = f"""
[FIXED AVIATION TOPIC — CONCRETE MECHANISM CONTRACT]
고정 주제: {fixed}

고정 주제의 명사는 유지하되 질문을 '효율/성능/안전에 어떤 영향?' 같은 추상적 benefit 질문으로 바꾸지 마라.
반드시 다음 구조로 좁혀라:
1) 사람이 화면에서 바로 확인할 수 있는 구체 관찰 하나
2) 그 관찰을 만든 물리적/기계적 원인 또는 설계 제약 하나
3) 그 원인이 만드는 직접 결과 하나

core_question은 1)의 관찰을 직접 물어야 하고, micro_narrative.reveal은 2)와 3)을 명시해야 한다.
'효율이 좋아진다', '안정성이 높아진다', '성능에 도움이 된다'만으로 Reveal을 끝내면 실패다.

예시 형식(문구 복사 금지):
- 관찰: 날개 끝이 위로 꺾여 있다
- 질문: 왜 날개 끝을 위로 꺾어 놓았을까?
- 메커니즘: 날개 위아래 압력 차가 끝단에서 강한 소용돌이를 만들고, 끝단 형상이 그 흐름을 약화시킨다
- 직접 결과: 유도항력이 줄어든다

윙렛/날개끝 주제라면 사실 근거가 있을 때 '날개 끝 와류', '압력 차', '유도항력'처럼 실제 메커니즘 단위를 우선 검토하라. 근거 없는 수치나 효과 크기는 만들지 마라.
이전 Gate 피드백: {gate_feedback or '없음'}
"""

    return context + f"""

============================================================
[AVIATION SHORTS SPECIFICITY CONTRACT]
============================================================
{fixed_contract}
이번 aviation 탐색에서는 generic why-design topic을 최종 Candidate로 제출하지 마라.
각 Candidate는 사실 근거가 있는 경우 specific_observation / constraint / counterintuitive_result / tradeoff / concrete_condition 중 적용 가능한 필드를 사용하라.
최종 topic, core_question, micro_narrative.reveal에는 최소 하나의 구체 요소가 직접 드러나야 한다.

[DOWNSTREAM REJECTION FEEDBACK]
{rejected_feedback}

같은 명사만 바꾸거나 '왜 X인가? → 안전/효율/편의' 패턴을 반복하지 마라. retry/API budget은 늘리지 않는다.

[AVIATION OUTPUT EXTENSION]
기존 JSON contract를 유지하고 적용 가능한 경우에만 선택 specificity 필드를 추가하라.
"""


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION OUTPUT NOTE]
SHORTS_CANDIDATE_SCOPE=aviation에서는 execution context의 specificity contract를 최우선으로 지켜라.
특히 fixed_topic이 있으면 추상적 benefit 질문이 아니라 관찰 → 메커니즘 → 직접 결과 구조로 좁혀라.
근거 없는 내용을 만들지 마라.
"""


# AVIATION_SPECIFICITY_OUTPUT_REPAIR_V1
# Production-safe schema repair for aviation Candidate Explorer output.
# This does not weaken Candidate Gate or specificity quality checks. It only gives
# a SELECTED aviation output that omitted all structured specificity fields one
# bounded chance to copy an already-stated concrete element into the proper field.
# If the original candidate contains no safely reusable concrete element, repair
# must return REGENERATE rather than inventing a fact.

def _aviation_specificity_output_missing(candidate):
    if not isinstance(candidate, dict):
        return True
    return not any(
        isinstance(candidate.get(field), str) and candidate.get(field).strip()
        for field in _AVIATION_SPECIFICITY_FIELDS
    )


def _aviation_specificity_repair_needed(data):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return False
    if not isinstance(data, dict):
        return False
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return False
    return _aviation_specificity_output_missing(data.get("winner"))


def _repair_aviation_specificity_output_if_needed(data, *, model=MODEL):
    if not _aviation_specificity_repair_needed(data):
        return data

    call_number = authorize_call(model)
    print(
        "🩹 Aviation specificity schema repair API call authorized: "
        f"#{call_number}"
    )

    original_json = json.dumps(data, ensure_ascii=False, indent=2)
    repair_prompt = f"""
[AVIATION CANDIDATE SCHEMA REPAIR — ONE BOUNDED PASS]

아래 Candidate Explorer JSON은 SELECTED이지만 winner가 aviation specificity 구조화 필드를 모두 누락했다.
이 호출은 새 Candidate 생성이나 내용 개선이 아니라 출력 스키마 복구만 수행한다.

절대 규칙:
1. topic, angle, core_question, micro_narrative, fact_check_focus, visual_proof, selection_reason의 의미를 바꾸지 마라.
2. 새 사실, 새 숫자, 새 인과관계, 새 설계 의도, 새 역사적 원인을 추가하지 마라.
3. 아래 기존 JSON에 이미 명시적으로 표현된 구체 요소만 그대로 요약/복사하여 적절한 필드에 넣어라.
4. winner에는 다음 중 사실상 맞는 필드를 최소 1개 포함해야 한다:
   specific_observation, constraint, counterintuitive_result, tradeoff, concrete_condition
5. 모든 필드를 억지로 채우지 마라. 근거가 있는 필드만 사용한다.
6. 기존 JSON에 안전하게 옮길 수 있는 구체 요소가 하나도 없다면 내용을 발명하지 말고
   {{"status":"REGENERATE","reason":"aviation specificity repair could not recover a grounded concrete field"}}
   만 반환하라.
7. runner_up이 null이면 그대로 null. runner_up이 있더라도 근거 없는 필드를 만들지 마라.
8. JSON 객체 하나만 반환하라. 설명/Markdown 금지.

원본 JSON:
{original_json}
"""

    response = (
        openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You repair a JSON schema without adding facts. "
                        "Preserve candidate meaning exactly; if a grounded field cannot be copied "
                        "from the original JSON, return REGENERATE."
                    ),
                },
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    )

    usage = record_usage(model, response)
    print(f"💰 Aviation specificity repair call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        return {
            "status": "REGENERATE",
            "reason": "aviation specificity repair returned empty output",
        }

    repaired = extract_json(content)
    if str(repaired.get("status") or "").strip().upper() == "SELECTED":
        original_winner = data.get("winner") or {}
        repaired_winner = repaired.get("winner") or {}
        protected_fields = (
            "topic",
            "angle",
            "core_question",
            "micro_narrative",
            "fact_check_focus",
            "visual_proof",
            "selection_reason",
        )
        for field in protected_fields:
            if repaired_winner.get(field) != original_winner.get(field):
                return {
                    "status": "REGENERATE",
                    "reason": f"aviation specificity repair changed protected field: {field}",
                }

    return repaired


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION OUTPUT CONTRACT OVERRIDE — SPECIFICITY REQUIRED]
SHORTS_CANDIDATE_SCOPE=aviation에서 status=SELECTED를 반환할 때 winner에는 아래 5개 중
실제 근거가 있는 필드를 최소 1개 반드시 포함하라:
specific_observation, constraint, counterintuitive_result, tradeoff, concrete_condition.
이전의 '선택 필드' 표현은 '모든 필드를 강제하지 않는다'는 뜻일 뿐이며,
winner가 5개를 전부 생략해도 된다는 뜻이 아니다.
근거 없는 값을 만들어 필드 수를 채우는 것은 금지한다.
안전하게 넣을 수 있는 구체 필드가 하나도 없다면 SELECTED가 아니라 REGENERATE를 반환하라.
"""


# AVIATION_SPECIFICITY_PROJECTION_V3
# Preserve the V1 schema-repair function, then deterministically copy an already
# grounded structured detail into Gate-visible narration. The projection itself
# makes zero API calls and cannot invent a new fact.
_aviation_specificity_schema_repair_v1 = _repair_aviation_specificity_output_if_needed


def _aviation_projection_failure_reason(candidate):
    if not isinstance(candidate, dict):
        return "candidate is not an object"
    ok, reason = aviation_candidate_quality_check(candidate)
    return "" if ok else str(reason or "")


def _aviation_projection_needed(candidate):
    if not isinstance(candidate, dict):
        return False
    reason = _aviation_projection_failure_reason(candidate)
    return bool(reason) and (
        "does not directly carry the concrete element" in reason
        or "generic why-design question without a concrete element" in reason
        or "generic benefit reveal without a concrete mechanism/constraint/trade-off" in reason
    )


def _aviation_first_grounded_detail(candidate):
    for field in _AVIATION_SPECIFICITY_FIELDS:
        value = str((candidate or {}).get(field) or "").strip()
        if value:
            return field, value
    return None, ""


def _aviation_project_existing_detail(data):
    if not isinstance(data, dict):
        return data
    winner = data.get("winner")
    if not isinstance(winner, dict):
        return data

    detail_field, detail = _aviation_first_grounded_detail(winner)
    if not detail:
        return data

    projected = dict(data)
    projected_winner = dict(winner)
    micro = dict(projected_winner.get("micro_narrative") or {})

    reveal = str(micro.get("reveal") or "").strip()
    reveal_norm = _aviation_norm(reveal)
    detail_norm = _aviation_norm(detail)
    if detail_norm and detail_norm not in reveal_norm:
        separator = " " if not reveal or reveal.endswith((".", "!", "?", "다.", "요.")) else ". "
        micro["reveal"] = f"{reveal}{separator}구체적으로는 {detail}.".strip()
    else:
        micro["reveal"] = reveal

    # Keep topic/core_question and all structured specificity fields byte-for-byte.
    # Only the reveal receives an exact copy of an existing grounded detail.
    projected_winner["micro_narrative"] = micro
    projected["winner"] = projected_winner
    print(
        "🧷 Aviation specificity deterministic projection: "
        f"field={detail_field} api_calls=0"
    )
    return projected


def _aviation_specificity_repair_needed(data):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return False
    if not isinstance(data, dict):
        return False
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return False
    winner = data.get("winner")
    return _aviation_specificity_output_missing(winner) or _aviation_projection_needed(winner)


def _repair_aviation_specificity_output_if_needed(data, *, model=MODEL):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return data
    if not isinstance(data, dict):
        return data
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return data

    working = data
    winner = working.get("winner")

    # Missing structured specificity belongs to V1. Let that single bounded schema
    # repair run first; V3 never replaces it or spends a second LLM call.
    if _aviation_specificity_output_missing(winner):
        working = _aviation_specificity_schema_repair_v1(working, model=model)
        if not isinstance(working, dict):
            return working
        if str(working.get("status") or "").strip().upper() != "SELECTED":
            return working
        winner = working.get("winner")
        if _aviation_specificity_output_missing(winner):
            return {
                "status": "REGENERATE",
                "reason": "aviation specificity schema repair left no grounded detail",
            }

    ok, _ = aviation_candidate_quality_check(winner)
    if ok:
        return working

    if not _aviation_projection_needed(winner):
        return working

    projected = _aviation_project_existing_detail(working)
    projected_winner = projected.get("winner") or {}

    # Projection must not mutate any source-of-truth field. Only reveal may change.
    original_winner = working.get("winner") or {}
    for field in (
        "topic",
        "angle",
        "core_question",
        "fact_check_focus",
        "visual_proof",
        "selection_reason",
        *_AVIATION_SPECIFICITY_FIELDS,
    ):
        if projected_winner.get(field) != original_winner.get(field):
            return {
                "status": "REGENERATE",
                "reason": f"aviation deterministic projection changed protected field: {field}",
            }

    ok, reason = aviation_candidate_quality_check(projected_winner)
    if not ok:
        return {
            "status": "REGENERATE",
            "reason": f"aviation deterministic projection still weak: {reason}",
        }

    return projected


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION SPECIFICITY PROJECTION — GATE-VISIBLE CONTRACT V3]
aviation Candidate에서 concrete detail을 별도 필드에만 숨기지 마라.
Candidate Gate가 직접 읽는 topic, core_question, micro_narrative.reveal에도 같은 구체 요소를 명시하라.
'왜 특정 형태인가 → 안전을 위해' 같은 일반론은 금지한다.
구체 관찰/제약/trade-off/조건/직관과 반대되는 결과가 질문 또는 Reveal 자체에 직접 보여야 한다.
새 사실을 만들어 구체적으로 보이게 하는 것은 금지한다.
"""

# CANDIDATE_POOL_HANDOFF_V1
# Authority: Runs 33887547463 and 33893139846 both measured
# ZERO_SUPPLY=6/7 and EXPLORER_SELECTED=1/7. Move validation authority from
# model-side self-withholding to deterministic host validation without changing
# Candidate Gate or hard factual safety.
from quality.candidate_pool_handoff import handoff_candidate_pool
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)
from quality.candidate_pool_grounding_records import (
    CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS,
)

_candidate_pool_previous_validate_explorer_output = validate_explorer_output


def _candidate_pool_host_hard_validate(candidate):
    # Existing deterministic aviation helpers only. Editorial broad/generic/
    # predictable-payoff checks intentionally remain Candidate Gate authority.
    if not aviation_scope_compatible(candidate):
        return False, "candidate drifted outside aviation scope"
    details = _aviation_detail_values(candidate)
    if not details:
        return False, "no concrete aviation specificity detail"
    if not _aviation_detail_is_referenced(candidate, details):
        return False, "concrete detail not carried by topic/question/reveal"
    if not candidate.get("visual_proof"):
        return False, "visual_proof missing"
    return True, "host hard validation PASS"


def _legacy_selected_supply_trusted_grounding(data):
    """Give legacy SELECTED the same repo-owned grounding supply as pool handoff.

    The legacy validator remains authoritative for schema/selection behavior. This
    helper only enriches an already validated winner from independently owned
    evidence. No model-authored evidence is promoted and no gate is relaxed.
    """
    result = _candidate_pool_previous_validate_explorer_output(data)
    if not isinstance(result, dict):
        return result
    if str(result.get("status") or "").strip().upper() != "SELECTED":
        return result
    winner = result.get("winner")
    if not isinstance(winner, dict):
        return result

    trusted_records = tuple(PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS) + tuple(
        CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
    )
    supplied = supply_trusted_subject_grounding(
        winner,
        trusted_records=trusted_records,
    )
    enriched = dict(result)
    enriched["winner"] = supplied
    if supplied.get("_trusted_grounding_evidence"):
        print(
            "[LEGACY_SELECTED_GROUNDING_SUPPLY] "
            f"canonical_subject={supplied.get('canonical_subject', '')} "
            f"claims={len(supplied.get('_trusted_grounded_claims') or [])}"
        )
    return enriched


def validate_explorer_output(data):
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    status = (
        str((data or {}).get("status") or "").strip().upper()
        if isinstance(data, dict)
        else ""
    )
    if not aviation_scope:
        if status == "CANDIDATE_POOL":
            # Run 34459538824: an unrelated automatic dispatch (category=역사,
            # blank SHORTS_CANDIDATE_SCOPE) still received a CANDIDATE_POOL
            # response, because section 15 of CANDIDATE_EXPLORER_PROMPT is
            # always present regardless of runtime scope and the model does
            # not reliably gate its own output format on it. Candidate Pool
            # Handoff itself stays aviation-only exactly as before -- this
            # candidate content is never validated or accepted here, same as
            # before this fix. Only the failure mode changes: fail closed the
            # same way any other unusable Explorer response already does
            # (REGENERATE) instead of an unhandled ValueError that crashes
            # the whole production run on the very first Candidate attempt.
            return {
                "status": "REGENERATE",
                "reason": "CANDIDATE_POOL response received outside aviation scope",
            }
        return _candidate_pool_previous_validate_explorer_output(data)
    if status == "SELECTED":
        return _legacy_selected_supply_trusted_grounding(data)
    if status != "CANDIDATE_POOL":
        return _candidate_pool_previous_validate_explorer_output(data)

    result = handoff_candidate_pool(
        data,
        scope="aviation",
        validate_candidate_fn=validate_candidate,
        hard_validate_fn=_candidate_pool_host_hard_validate,
        trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    )
    trace = result.get("_candidate_pool_handoff") or {}
    print(
        "[CANDIDATE_POOL_HANDOFF] "
        f"status={trace.get('status')} "
        f"supplied={trace.get('supplied', len((data or {}).get('candidates') or []))} "
        f"validated={trace.get('validated', len((data or {}).get('candidates') or []))} "
        f"survived={trace.get('survived', 0)}"
    )
    normalization = trace.get("normalization") or {}
    if normalization:
        print(
            "[CANDIDATE_POOL_NORMALIZE] "
            f"status={normalization.get('status')} "
            f"supplied={normalization.get('supplied')} "
            f"validated={normalization.get('validated')} "
            f"limit={normalization.get('limit')}"
        )
    for item in trace.get("diagnostics") or []:
        print(
            "[CANDIDATE_POOL_ITEM] "
            f"index={item.get('index')} status={item.get('status')} "
            f"topic={item.get('topic', '')} reason={item.get('reason', '')}"
        )
        item_normalization = item.get("normalization") or {}
        if item_normalization:
            print(
                "[CANDIDATE_POOL_ITEM_NORMALIZE] "
                f"index={item.get('index')} "
                f"status={item_normalization.get('status')} "
                f"source_field={item_normalization.get('source_field', '')}"
            )
    return result


_AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX = r"""

============================================================
15. AVIATION CANDIDATE POOL HANDOFF V1 — HOST AUTHORITY
============================================================
When SHORTS_CANDIDATE_SCOPE=aviation, this scoped block overrides only the
contradictory final-selection/output behavior above. #282 supply/editorial
separation and #283 observable-seed/recovery remain active.

RESPONSIBILITY:
- LLM = bounded Candidate supplier
- HOST = deterministic schema / aviation specificity / canonical grounding
- Candidate Gate = independent editorial authority

Use the existing Candidate Explorer call only. Do not request another call.
Instantiate #283 observable seeds, then return every reviewable concrete Candidate
that survives only obvious supply-time failure. Do not hide the whole pool merely
because one Candidate looks broad, generic, predictable, weak in novelty, or
editorially weak. Candidate Gate owns those editorial judgments.

SUPPLY-TIME terminal failure remains limited to:
- malformed Candidate / missing required fields
- obvious fabrication or impossible causal claim
- obvious non-aviation/off-scope Candidate

Host owns grounding sufficiency, canonical subject identity, deterministic
specificity/structure, visual-proof validation, and fail-close handling.

[POOL SIZE — HARD OUTPUT CONTRACT]
The `candidates` array MUST contain 1, 2, or 3 items. This is an output contract,
not a preference. NEVER return 4 or more Candidates. Before emitting JSON, count
the array. If more than 3 reviewable Candidates exist, keep only the strongest
first 3 and delete every extra item. Do not add filler, placeholder, fabricated
provenance, or invented technical identity to reach 3.

[MICRO NARRATIVE PROGRESSION — HARD OUTPUT CONTRACT]
For every Candidate, `micro_narrative.hook` MUST be a concrete declarative first
beat already supported by that Candidate: an observable detail, concrete result,
constraint, contrast, or causal clue. It MUST NOT be a question. It MUST NOT
repeat, paraphrase, or merely restate either the top-level `core_question` or
`micro_narrative.core_question`. The first two beats must advance information:
HOOK = concrete observation/result/constraint; CORE QUESTION = ask why/how that
observation exists. Do not turn "왜 X인가?" into "X는 왜 그럴까?" and call it a
new Hook. Do not invent a new fact to satisfy this rule; if no grounded concrete
first beat exists, omit that Candidate from the supplied pool.

[AVIATION PRIMARY OUTPUT]
If at least one reviewable Candidate exists, return exactly one JSON object:
{
  "status": "CANDIDATE_POOL",
  "candidates": [
    {
      "topic": "...",
      "angle": "...",
      "core_question": "...",
      "micro_narrative": {
        "hook": "구체 관찰/결과/제약을 말하는 서술문. 질문 재진술 금지.",
        "core_question": "왜/어떻게를 묻는 하나의 중심 질문",
        "reveal": "...",
        "payoff": "..."
      },
      "fact_check_focus": [],
      "visual_proof": ["..."],
      "selection_reason": "...",
      "specific_observation": "...",
      "constraint": "...",
      "counterintuitive_result": "...",
      "tradeoff": "...",
      "concrete_condition": "...",
      "subject_kind": "physical_entity | non_physical_concept",
      "canonical_subject": "... | UNKNOWN | NOT_APPLICABLE",
      "subject_identity_confidence": 0.0,
      "grounding_evidence": []
    }
  ]
}
Use the existing Candidate schema and aviation specificity fields. At least one
specificity field must contain a concrete observation/constraint/result/trade-off/
condition already supported by the Candidate story.

Return REGENERATE only when reviewable supply is truly zero after the narrow
supply-time failures above. Structural/factual/grounding failures still fail
closed at host validation; no quality threshold is relaxed.
"""

CANDIDATE_EXPLORER_PROMPT += _AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX


# RUN_34686824352_AVIATION_PROMPT_SCOPE_V1
# Run 34686824352 (automatic-topic mode, blank SHORTS_CANDIDATE_SCOPE) showed
# section 15 above is always present in the system prompt regardless of the
# runtime scope, and the model does not reliably gate its own output format on
# the in-prompt "When SHORTS_CANDIDATE_SCOPE=aviation" instruction alone -- 5 of
# 7 Candidate attempts returned a CANDIDATE_POOL envelope for ordinary
# non-aviation topics (desert ant navigation was one of only two attempts that
# reached a real topic at all), each one an automatic REGENERATE that spent a
# bounded attempt without ever reaching Candidate Gate. This does not touch
# CANDIDATE_POOL parsing/validation at all -- that stays aviation-only exactly
# as installed above, and a CANDIDATE_POOL envelope outside aviation scope still
# fails closed to REGENERATE if the model returns one anyway. It only stops
# teaching the model that output shape when the run cannot use it, by keeping
# section 15 out of the system prompt for that one call.
_candidate_pool_scope_previous_explore_candidates = explore_candidates


def explore_candidates(*args, **kwargs):
    global CANDIDATE_EXPLORER_PROMPT
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    if aviation_scope:
        return _candidate_pool_scope_previous_explore_candidates(*args, **kwargs)
    original_prompt = CANDIDATE_EXPLORER_PROMPT
    if _AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX in original_prompt:
        # Later hotfixes append more prompt text after section 15, so this
        # cannot assume the appendix is the current suffix -- remove exactly
        # that substring (first occurrence) wherever it now sits and leave
        # everything appended before/after it untouched.
        CANDIDATE_EXPLORER_PROMPT = original_prompt.replace(
            _AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX, "", 1
        )
    try:
        return _candidate_pool_scope_previous_explore_candidates(*args, **kwargs)
    finally:
        CANDIDATE_EXPLORER_PROMPT = original_prompt

# GROUNDING_AWARE_CANDIDATE_SUPPLY_V1
# Authority: production Run 33960845940 supplied 20 aviation candidates across
# seven attempts; host canonical grounding rejected every one. Run 34707653148
# then showed that prompt-only capability guidance can still exhaust automatic
# supply on unsupported physical identities. Expose the exact repo-owned
# grounding capability to the existing Explorer call and, only after automatic
# aviation model supply fails, offer a bounded repo-owned seed pool through the
# unchanged host handoff. No quality gate, retry, or budget is relaxed.
from quality.grounding_aware_candidate_supply import (
    grounded_seed_candidate_pool,
    grounding_capability_context,
    no_grounded_candidate_supply_result,
)

_grounding_aware_previous_explore_candidates = explore_candidates


def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
    model=MODEL,
):
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    if aviation_scope:
        empty = no_grounded_candidate_supply_result()
        if empty is not None:
            print(
                "[GROUNDING_AWARE_SUPPLY] "
                "status=NO_GROUNDED_CANDIDATE_SUPPLY capabilities=0 api_calls=0"
            )
            return empty

    result = _grounding_aware_previous_explore_candidates(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic=fixed_topic,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        model=model,
    )

    # Fixed-topic authority must never be replaced by an unrelated automatic
    # seed. This fallback exists only for automatic aviation topic discovery.
    fixed_topic_requested = bool(
        str(fixed_topic or "").strip()
        or os.environ.get("SHORTS_TOPIC", "").strip()
    )
    if (
        not aviation_scope
        or fixed_topic_requested
        or not isinstance(result, dict)
        or str(result.get("status") or "").strip().upper() == "SELECTED"
    ):
        return result

    seed_pool = grounded_seed_candidate_pool(
        recent_topics=recent_topics,
        rejected_topics=rejected_topics,
    )
    if str(seed_pool.get("status") or "").strip().upper() != "CANDIDATE_POOL":
        print(
            "[GROUNDING_SEED_FALLBACK] "
            f"status={seed_pool.get('status')} candidates=0 api_calls=0 "
            f"reason={seed_pool.get('reason', '')}"
        )
        return result

    # Candidate Pool Handoff remains the deterministic authority. Feeding the
    # repo-owned seed pool through validate_explorer_output means every seed is
    # revalidated for schema, aviation specificity, canonical grounding, and
    # visual proof before it can reach Candidate Gate.
    seed_result = validate_explorer_output(seed_pool)
    trace = (
        seed_result.get("_candidate_pool_handoff", {})
        if isinstance(seed_result, dict)
        else {}
    )
    seed_result["_grounding_seed_fallback"] = {
        "status": "USED",
        "upstream_status": str(result.get("status") or ""),
        "upstream_reason": str(result.get("reason") or ""),
        "supplied": len(seed_pool.get("candidates") or []),
        "survived": trace.get("survived", 0),
        "api_calls": 0,
    }
    print(
        "[GROUNDING_SEED_FALLBACK] "
        f"status={seed_result.get('status')} "
        f"supplied={len(seed_pool.get('candidates') or [])} "
        f"survived={trace.get('survived', 0)} api_calls=0"
    )
    return seed_result


# The capability list is derived at install/runtime import from the exact same
# repo-owned registries used by host validation. Keep it at SYSTEM authority so
# primary Explorer and the existing bounded recovery call inherit one contract
# without wrapping build_execution_context (which later compatibility installers
# inspect structurally).
CANDIDATE_EXPLORER_PROMPT += "\n\n" + grounding_capability_context() + "\n"
CANDIDATE_EXPLORER_PROMPT += """

============================================================
16. GROUNDING-AWARE AVIATION SUPPLY — RUN 33960845940 / 34707653148
============================================================
For aviation automatic supply, the SYSTEM prompt contains a compact
[GROUNDING-AWARE CANDIDATE SUPPLY] capability list derived from the exact
repo-owned trusted grounding registries used by host validation.

This is a hard generation-space constraint, not a list of required topic titles:
- generate reviewable aviation candidates only inside those evidence-supported
  canonical subject capabilities;
- use their observable/context hints to instantiate concrete #283 seeds;
- vary question, phenomenon, mechanism, and presentation when the trusted
  evidence actually supports that variation;
- respect recent/rejected-topic context and Audience Continuity when choosing
  among supported capabilities;
- never leave the supported capability space merely to gain novelty/diversity;
- never invent a new canonical identity, provenance, alias, causal mechanism, or
  evidence claim to make an unsupported candidate appear groundable.

The existing Candidate Pool Handoff and Canonical Subject Grounding remain the
final deterministic authorities. Every generated candidate must still survive
unchanged schema, aviation specificity, visual-proof, canonical grounding, FACT,
and downstream Candidate Gate checks.

If automatic aviation model supply still returns no host-usable Candidate, the
host may offer a bounded repo-owned seed pool from trusted identity records. That
seed pool is not pre-approved: it goes through the exact same Candidate Pool
Handoff, canonical grounding, Candidate Gate, FACT, visual, and quality gates.
It adds zero model calls and does not apply to fixed-topic mode.

If the capability context says NO_GROUNDED_CANDIDATE_SUPPLY, do not fabricate a
fallback candidate. Fail closed. This contract adds no model call and changes no
quality threshold, Candidate Gate, FACT gate, API ceiling, cost ceiling, or retry.
"""



# CANDIDATE_SUPPLY_RECOVERY_V1
# A production generation process may spend at most one extra Explorer call
# when the normal Explorer returns REGENERATE specifically because it found
# zero usable grounded candidates. This is supply recovery only: the recovered
# payload must still satisfy the normal Explorer output validator and all
# downstream Candidate Gate / fact / quality checks remain unchanged.
_candidate_supply_recovery_used = False
_original_explore_candidates_before_supply_recovery = explore_candidates


def _candidate_supply_reason_is_zero_usable(result):
    if not isinstance(result, dict):
        return False
    if str(result.get("status", "")).strip().upper() != "REGENERATE":
        return False

    reason = str(result.get("reason", "")).strip().lower()
    normalized = " ".join(reason.split())

    # Run 33887547463 showed that the model can express the same supply
    # exhaustion without the literal phrase "usable grounded candidate".
    # Keep this deterministic and narrow: only explicit no-supply / all-hard-
    # gate-failed semantics spend the single bounded recovery. Pure editorial
    # weakness (predictable/generic/weak payoff) must not trigger recovery.
    zero_supply_markers = (
        "candidate supply shortage",
        "concrete candidate shortage",
        "zero usable candidate",
        "zero usable grounded candidate",
        "no usable candidate",
        "no grounded candidate",
        "후보 공급 부족",
        "구체적인 후보 부족",
        "구체적인 후보가 부족",
    )
    if any(marker in normalized for marker in zero_supply_markers):
        return True

    literal_zero = (
        "usable grounded candidate" in normalized
        and (
            "0개" in normalized
            or "zero" in normalized
            or "없" in normalized
        )
    )
    if literal_zero:
        return True

    hard_gate_exhaustion = (
        "구조·사실성 hard gate" in normalized
        and "모든 후보" in normalized
        and (
            "통과하지 못" in normalized
            or "실패" in normalized
        )
    )
    return hard_gate_exhaustion


def _reset_candidate_supply_recovery_for_tests():
    global _candidate_supply_recovery_used
    _candidate_supply_recovery_used = False


def _build_candidate_supply_recovery_context(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic_gate_feedback="",
    original_reason="",
):
    base = build_execution_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
    )

    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    aviation_precedence = ""
    if aviation_scope:
        aviation_precedence = """
[AVIATION SUPPLY RECOVERY PRECEDENCE — RUN 33878093224]
This recovery call is still a Candidate SUPPLY step, not the independent
Candidate Gate. Preserve the aviation execution-context separation of
responsibilities. BROAD / GENERIC QUESTION, GENERIC REVEAL, PREDICTABLE PAYOFF,
weak payoff, or novelty concern alone must not make a grounded, structurally
complete aviation Candidate disappear or turn the whole supply into zero.
Use those editorial signals only to rank surviving supply candidates. Keep
structural/factual hard gates fail-closed. The unchanged independent Candidate
Gate remains authoritative for editorial PASS/REGENERATE.

[AVIATION OBSERVABLE SEED RECOVERY — RUN 33887547463]
Stay inside the SAME assigned broad direction, but do not retry the broad
category as a Candidate. First instantiate several materially distinct concrete
observable seeds, each binding an observable object/feature, specific
observation, direct viewer question, grounded mechanism/constraint, direct
result, and visual proof target. Then apply the SAME structural/factual hard
gates. This is the same observable-seed contract as primary aviation supply and
adds no new call beyond this already-bounded recovery opportunity.
"""

    return base + f"""

============================================================
[BOUNDED SUPPLY RECOVERY]
============================================================

The normal Candidate Explorer returned REGENERATE because it found zero usable
grounded candidates.

Original reason:
{original_reason}

This is the only supply-recovery opportunity for this generation run.
Do NOT relax any Candidate Explorer structural/factual hard gate,
anti-fabrication rule, or fact-safety rule.
{aviation_precedence}
Before deciding REGENERATE, silently explore at least 6 materially distinct
concrete observations or mechanisms inside the assigned direction. Do not emit
that scratch list. Evaluate each against the SAME hard gates for structural/factual safety.
A weak first idea is not evidence that the direction has zero supply.

Prefer candidates whose observation, mechanism/constraint, direct result, and
visual proof can all be named concretely from established knowledge. For
aviation, avoid generic benefit-only ideas such as merely "safer", "more
efficient", or "better performance"; the concrete observable element and the
mechanism or constraint must carry the story.

Search again for at least one concrete candidate that is:
- a real, recognizable subject or observable detail,
- driven by a specific mechanism, purpose, constraint, or effect,
- independently verifiable,
- visually provable enough for a Short,
- explainable within the normal target duration.

Do not invent hidden purposes, historical accidents, causal links, or numbers.
If verification is required, put concrete claims in fact_check_focus.

For non-aviation scopes, run the normal Candidate Explorer hard gates and final
sanity check from the system prompt unchanged. For aviation scope, the scoped
supply-precedence block above controls editorial self-withholding: return
SELECTED when at least one grounded, structurally complete Candidate survives
supply hard gates, and let the unchanged independent Candidate Gate decide
broad/generic/predictable editorial quality. Return REGENERATE only after the silent breadth search still yields no Candidate permitted by the applicable
supply contract. Return one JSON object only.
"""


def _run_candidate_supply_recovery(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
    model=MODEL,
    original_reason="",
):
    execution_context = _build_candidate_supply_recovery_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        original_reason=original_reason,
    )

    call_number = authorize_call(model)
    print(f"💳 Candidate supply recovery API call authorized: #{call_number}")

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": CANDIDATE_EXPLORER_PROMPT,
            },
            {
                "role": "user",
                "content": execution_context,
            },
        ],
        temperature=0.55,
        response_format={"type": "json_object"},
    )

    usage = record_usage(model, response)
    print(f"💰 Candidate supply recovery call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Candidate supply recovery 응답이 비어 있습니다.")

    parsed = extract_json(content)
    return validate_explorer_output(parsed)


def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
    model=MODEL,
):
    global _candidate_supply_recovery_used

    result = _original_explore_candidates_before_supply_recovery(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic=fixed_topic,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        model=model,
    )

    if not _candidate_supply_reason_is_zero_usable(result):
        return result

    if _candidate_supply_recovery_used:
        print("⏭️ Candidate supply recovery already spent for this generation run")
        return result

    _candidate_supply_recovery_used = True
    print("")
    print("=" * 64)
    print("🛟 CANDIDATE SUPPLY RECOVERY (1/1)")
    print("=" * 64)

    recovered = _run_candidate_supply_recovery(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic=fixed_topic,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        model=model,
        original_reason=result.get("reason", ""),
    )

    if recovered.get("status") == "SELECTED":
        print("✅ Candidate supply recovery produced a validated candidate")
    else:
        print("❌ Candidate supply recovery remained REGENERATE; fail closed")

    return recovered


# CANONICAL_SUBJECT_GROUNDING_GATE_V1
# Structured identity metadata is produced by Candidate Explorer but validated
# independently. The Explorer is never allowed to turn an ambiguous surface
# description into a technical entity merely to complete a story.
from quality.canonical_subject_grounding import normalize_candidate_subject_metadata

CANDIDATE_EXPLORER_PROMPT += r"""

============================================================
14. CANONICAL SUBJECT GROUNDING GATE V1
============================================================

Before a Candidate can hand a physical object/part to the Writer, explicitly
separate object identity from the object's proposed function or mechanism.

For BOTH winner and runner_up add these fields:

"subject_kind": "physical_entity" | "non_physical_concept"
"canonical_subject": "..."
"subject_identity_confidence": 0.0~1.0
"grounding_evidence": []

Rules:

1. physical_entity
A concrete object, component, visible part, hole, mark, protrusion, plate, pin,
rod, structure, device, etc. whose function/purpose/mechanism is part of the
story. This also includes a living organism, animal, insect, plant,
microorganism, organ, or other biological structure -- a species or organism
is just as concrete an entity as a manufactured part.

A living organism or its biological structure IS a physical_entity even when
the mechanism being explained is a biological or chemical process internal to
it (e.g. digestion, an enzyme reaction, a gut microbiome). Use the organism's
common name as canonical_subject (e.g. "흰개미" for termite, "대장균" for E.
coli). Do NOT return UNKNOWN or leave subject_kind unresolved merely because
the mechanism is biological/chemical rather than mechanical -- the organism
itself is still a concrete, nameable subject.

physical_entity ALSO includes large-scale built/civil infrastructure and
engineered structures -- a sewer/drainage system, aqueduct, road, bridge,
canal, tunnel, dam, building, or other constructed system is just as concrete
and nameable as a small manufactured part, even though it is large, made of
many components, or built long ago. Use the specific named structure as
canonical_subject (e.g. "고대 로마의 하수도 시스템" for Ancient Rome's sewer
system). Do NOT return UNKNOWN merely because the object is large-scale
infrastructure rather than a single small part.

physical_entity ALSO includes a specific geometric/design feature of a
manufactured object -- e.g. the rounded corner of an airplane window, the
curvature of a blade, the taper of a pin -- when that shape/feature is itself
the concrete, identifiable subject whose design rationale is being explained.
Use the object plus the specific feature as canonical_subject (e.g. "비행기
창문의 둥근 모서리" for an airplane window's rounded corner). Do NOT return
UNKNOWN merely because the subject is a design feature/shape of an object
rather than the whole object.

Do NOT infer its canonical identity from its appearance or from a plausible
mechanism. Appearance-only descriptions are not identities.

If the Candidate itself explicitly names the established object, use that name
as canonical_subject and include evidence like:
{
  "evidence_type": "explicit_candidate_identity",
  "supports_subject": "same canonical name",
  "source": "candidate_text",
  "detail": "where the explicit identity appears"
}

If a real upstream source/evidence record identifies an otherwise ambiguous
object, preserve it as:
{
  "evidence_type": "source_backed_identity",
  "supports_subject": "canonical name",
  "source": "actual source handle",
  "detail": "identity-specific support"
}

Never invent a source, citation, technical name, or identity evidence. If the
physical object's identity is not actually established, return:

"canonical_subject": "UNKNOWN"
"subject_identity_confidence": 0.0
"grounding_evidence": []

Do not attach a function/mechanism to UNKNOWN merely because that mechanism is
true for some other object in the same location or category.

2. non_physical_concept
Use only when the Candidate's subject is genuinely a process, transition,
policy, historical sequence, abstract relation, or other non-physical concept.
Use:
"canonical_subject": "NOT_APPLICABLE"
"subject_identity_confidence": 1.0
"grounding_evidence": []

Do not classify a physical detail as non_physical_concept to bypass grounding.

The three identity fields are not FACT verification. They only establish what
the subject is before function/mechanism reasoning begins.
"""

_original_validate_candidate_before_subject_grounding = validate_candidate


def validate_candidate(candidate, *, prefix, runner_up=False):
    result = _original_validate_candidate_before_subject_grounding(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )

    metadata = normalize_candidate_subject_metadata(candidate)
    kind = metadata["subject_kind"]

    # Compatibility is deliberately fail-closed at the later boundary: old
    # fixtures/payloads can still parse, but missing identity metadata becomes
    # unresolved rather than silently treated as grounded.
    if kind not in ("physical_entity", "non_physical_concept"):
        metadata = {
            "subject_kind": "unresolved",
            "canonical_subject": "UNKNOWN",
            "subject_identity_confidence": 0.0,
            "grounding_evidence": [],
        }

    result.update(metadata)
    return result

# CANONICAL_SUBJECT_GROUNDING_SUPPLY_V1
# Deterministic trusted provenance supplier. Runs after all model/schema repair
# output and before Candidate Gate evaluation. No API call or retry.
from quality.canonical_subject_grounding_supply import (
    PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    supply_trusted_subject_grounding,
)

_original_validate_explorer_output_before_grounding_supply = validate_explorer_output


def validate_explorer_output(data):
    result = _original_validate_explorer_output_before_grounding_supply(data)
    if not isinstance(result, dict) or str(result.get("status", "")).strip().upper() != "SELECTED":
        return result
    winner = result.get("winner")
    if isinstance(winner, dict):
        result["winner"] = supply_trusted_subject_grounding(
            winner, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
    runner_up = result.get("runner_up")
    if isinstance(runner_up, dict):
        result["runner_up"] = supply_trusted_subject_grounding(
            runner_up, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        )
    return result

# RUN_35063499913_SUPPLY_GROUNDING_V1

# Make the grounding fields visibly mandatory at the final prompt boundary.
# This is output-shape guidance only; canonical identity still fails closed when
# it is unknown or unsupported.
CANDIDATE_EXPLORER_PROMPT += r"""

============================================================
RUN 35063499913 — REQUIRED GROUNDING OUTPUT CONTRACT
============================================================
For every SELECTED winner and runner_up, the following four fields are
MANDATORY and must not be omitted:
- subject_kind
- canonical_subject
- subject_identity_confidence
- grounding_evidence

If the subject is a named physical entity already explicit in the Candidate
story, preserve that exact explicit name as canonical_subject and use only
explicit_candidate_identity evidence that points back to the Candidate text.
If physical identity is genuinely unresolved, return canonical_subject=UNKNOWN
with confidence 0.0 and empty grounding_evidence. Never invent an identity,
source, or mechanism merely to fill these fields.
"""


def _candidate_supply_recovery_system_prompt():
    """Return the same scope-correct prompt shape used by normal exploration."""
    prompt = CANDIDATE_EXPLORER_PROMPT
    aviation_scope = (
        os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower()
        == "aviation"
    )
    if aviation_scope:
        return prompt

    appendix = globals().get("_AVIATION_CANDIDATE_POOL_HANDOFF_APPENDIX", "")
    if isinstance(appendix, str) and appendix and appendix in prompt:
        prompt = prompt.replace(appendix, "", 1)
    return prompt


def _run_candidate_supply_recovery(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    fixed_topic_gate_feedback="",
    model=MODEL,
    original_reason="",
):
    execution_context = _build_candidate_supply_recovery_context(
        topic_info,
        recent_topics=recent_topics,
        recent_content=recent_content,
        rejected_topics=rejected_topics,
        fixed_topic_gate_feedback=fixed_topic_gate_feedback,
        original_reason=original_reason,
    )

    call_number = authorize_call(model)
    print(f"💳 Candidate supply recovery API call authorized: #{call_number}")

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": _candidate_supply_recovery_system_prompt(),
            },
            {
                "role": "user",
                "content": execution_context,
            },
        ],
        temperature=0.55,
        response_format={"type": "json_object"},
    )

    usage = record_usage(model, response)
    print(f"💰 Candidate supply recovery call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Candidate supply recovery 응답이 비어 있습니다.")

    parsed = extract_json(content)
    return validate_explorer_output(parsed)


_run_35063499913_previous_validate_candidate = validate_candidate


def _run_35063499913_candidate_text(candidate):
    if not isinstance(candidate, dict):
        return ""
    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}
    values = (
        candidate.get("topic"),
        candidate.get("angle"),
        candidate.get("core_question"),
        micro.get("hook"),
        micro.get("core_question"),
        micro.get("reveal"),
        micro.get("payoff"),
    )
    return " ".join(str(value or "").strip() for value in values).lower()


def validate_candidate(candidate, *, prefix, runner_up=False):
    result = _run_35063499913_previous_validate_candidate(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )
    if result.get("subject_kind") in (
        "physical_entity",
        "non_physical_concept",
    ):
        return result

    # Recover ONLY a missing kind from model-authored metadata that already
    # carries an explicit canonical identity. We do not invent a canonical name.
    # The existing canonical evaluator below still rechecks confidence and
    # explicit evidence against literal Candidate text before allowing Writer.
    raw = normalize_candidate_subject_metadata(candidate)
    canonical = str(raw.get("canonical_subject") or "").strip()
    canonical_key = " ".join(canonical.lower().split())
    confidence = float(raw.get("subject_identity_confidence") or 0.0)
    evidence = raw.get("grounding_evidence") or []

    if canonical_key == "not_applicable" and confidence >= 1.0:
        raw["subject_kind"] = "non_physical_concept"
        result.update(raw)
        return result

    unknown = {"", "unknown", "unresolved", "none", "null", "n/a"}
    candidate_text = _run_35063499913_candidate_text(candidate)
    explicit_support = any(
        isinstance(item, dict)
        and str(item.get("evidence_type") or "").strip().lower()
            == "explicit_candidate_identity"
        and " ".join(str(item.get("supports_subject") or "").strip().lower().split())
            == canonical_key
        for item in evidence
    )

    if (
        canonical_key not in unknown
        and canonical_key in candidate_text
        and explicit_support
    ):
        raw["subject_kind"] = "physical_entity"
        result.update(raw)
        print(
            "🧭 CANONICAL_SUBJECT_KIND normalized from explicit Candidate identity "
            f"canonical={canonical}"
        )

    return result


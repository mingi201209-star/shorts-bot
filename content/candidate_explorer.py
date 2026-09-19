# content/candidate_explorer.py

import json
import os
import re
from copy import deepcopy

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

    return f"""
[EXECUTION CONTEXT]

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
같은 대상(subject)을 유지한 채,
아래 [REJECTION REASON]에서 지적된
일반적인/예상 가능한 설명 대신

- 구체적인 구조/부품
- 힘이나 변화가 전달되는 경로
- 위치/방향의 차이
- 조건
- 순서
- 예외
- 관찰 가능한 변화
- 이미 근거에 있는 구체적인 메커니즘

중 하나 이상을 사용해
더 좁은 Core Question과 Reveal로 다시 써라.

아래 [FACT CHECK FOCUS]와 [VISUAL PROOF], 그리고 기존 Candidate에
이미 들어 있는 사실·관찰·메커니즘을 최우선으로 사용하라.
이 단계는 Fact discovery가 아니다.

수치·퍼센트·각도·힘·질량·거리·시간 같은 정량 정보는
기존 Candidate 또는 근거에 같은 값이 이미 있을 때만 사용할 수 있다.
없는 숫자를 만들어 구체적으로 보이게 하지 마라.
근거가 비어 있거나 불충분하면 숫자를 만들지 말고
구조/위치/조건/순서/관찰 포인트를 더 좁혀라.

예:
넓음: "비행기 날개는 왜 공기 흐름을 최적화할까?"
좁음: "비행기 날개 끝은 왜 위로 꺾여 있을까?"

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


_REWRITE_AUTHORITY_FIELDS = (
    "fact_check_focus",
    "visual_proof",
    "specific_observation",
    "mechanism",
    "constraint",
    "concrete_condition",
    "counterintuitive_result",
    "tradeoff",
    "subject_kind",
    "canonical_subject",
    "subject_identity_confidence",
    "grounding_evidence",
    "_trusted_grounding_evidence",
    "_trusted_grounded_claims",
)


def _rewrite_candidate_text(candidate):
    if not isinstance(candidate, dict):
        return ""

    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        micro = {}

    chunks = [
        candidate.get("topic"),
        candidate.get("angle"),
        candidate.get("core_question"),
        candidate.get("specific_observation"),
        candidate.get("mechanism"),
        candidate.get("constraint"),
        candidate.get("concrete_condition"),
        candidate.get("counterintuitive_result"),
        candidate.get("tradeoff"),
        micro.get("hook"),
        micro.get("core_question"),
        micro.get("reveal"),
        micro.get("payoff"),
    ]

    for field in ("fact_check_focus", "visual_proof"):
        values = candidate.get(field)
        if isinstance(values, list):
            chunks.extend(values)

    return " ".join(str(value or "").strip() for value in chunks if str(value or "").strip())


def _numeric_claim_tokens(text):
    return set(re.findall(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?:\s*(?:%|°|도|배|초|분|시간|km|m|cm|mm|kg|g|N|kN))?", str(text or "")))


def _preserve_rewrite_authority(original, rewritten):
    """Keep a bounded rewrite on the exact same subject/evidence authority.

    The rewrite call is editorial recovery, not a fact-discovery or grounding
    step. It may rephrase the question/reveal, but it cannot replace the
    Candidate's evidence lists, trusted grounding metadata, or introduce a new
    numeric claim that was absent from the original Candidate/evidence.
    """

    if not isinstance(original, dict) or not isinstance(rewritten, dict):
        return None

    original_topic = str(original.get("topic") or "").strip()
    rewritten_topic = str(rewritten.get("topic") or "").strip()
    if not original_topic or rewritten_topic != original_topic:
        print("🚫 Narrowness rewrite rejected: subject/topic changed")
        return None

    allowed_numbers = _numeric_claim_tokens(_rewrite_candidate_text(original))
    rewritten_numbers = _numeric_claim_tokens(_rewrite_candidate_text(rewritten))
    unsupported_numbers = rewritten_numbers - allowed_numbers
    if unsupported_numbers:
        print(
            "🚫 Narrowness rewrite rejected: unsupported numeric detail "
            + ",".join(sorted(unsupported_numbers))
        )
        return None

    for field in _REWRITE_AUTHORITY_FIELDS:
        if field in original:
            rewritten[field] = deepcopy(original[field])

    for field, value in original.items():
        if field.startswith("_repo_owned_") or field.startswith("_trusted_"):
            rewritten[field] = deepcopy(value)

    return rewritten


_NARROWNESS_FIXED_TOPIC_LLM_BLOCKED = set()


def _exact_fixed_topic_for_candidate(candidate):
    fixed_topic = str(os.environ.get("SHORTS_TOPIC") or "").strip()
    candidate_topic = str((candidate or {}).get("topic") or "").strip()
    if fixed_topic and candidate_topic == fixed_topic:
        return fixed_topic
    return ""


def _deterministic_grounded_narrowness_rewrite(winner):
    """One no-API narrowing attempt using only evidence already on Winner.

    This is deliberately conservative: it never changes topic/identity and it
    never invents a mechanism.  It only promotes an already-present mechanism
    or fact-check claim into the Reveal, then lets the normal narrowness
    self-critique decide whether that is specific enough.
    """

    if not isinstance(winner, dict):
        return None

    micro = winner.get("micro_narrative")
    if not isinstance(micro, dict):
        return None

    evidence = []

    for field in (
        "mechanism",
        "constraint",
        "concrete_condition",
        "specific_observation",
        "counterintuitive_result",
        "tradeoff",
    ):
        value = str(winner.get(field) or "").strip()
        if value and value not in evidence:
            evidence.append(value)

    for field in ("fact_check_focus", "visual_proof"):
        values = winner.get(field)
        if isinstance(values, list):
            for value in values:
                text = str(value or "").strip()
                if text and text not in evidence:
                    evidence.append(text)

    # A deterministic rewrite is only useful when there is real grounded
    # specificity to promote.  Otherwise return None and preserve fail-close.
    if not evidence:
        return None

    rewritten = deepcopy(winner)
    rewritten_micro = deepcopy(micro)

    # If this exact fixed topic is owned by exactly one repo-trusted seed,
    # prefer that seed's already-grounded editorial question/reveal before
    # asking a model to invent specificity.  The normal narrowness
    # self-critique still decides PASS/TOO_BROAD afterwards, so this is supply,
    # not a gate bypass.
    fixed_topic = _exact_fixed_topic_for_candidate(winner)
    if fixed_topic:
        try:
            from quality.grounding_aware_candidate_supply import (
                all_trusted_candidate_records,
            )

            exact_seed_records = []
            for record in all_trusted_candidate_records():
                if not isinstance(record, dict):
                    continue
                seed = record.get("seed_candidate")
                if not isinstance(seed, dict):
                    continue
                if str(seed.get("topic") or "").strip() == fixed_topic:
                    exact_seed_records.append(record)

            if len(exact_seed_records) == 1:
                seed = exact_seed_records[0].get("seed_candidate") or {}
                seed_micro = seed.get("micro_narrative")
                if isinstance(seed_micro, dict):
                    seed_question = str(seed.get("core_question") or "").strip()
                    seed_reveal = str(seed_micro.get("reveal") or "").strip()
                    if seed_question and seed_reveal:
                        rewritten["angle"] = str(
                            seed.get("angle") or rewritten.get("angle") or ""
                        ).strip()
                        rewritten["core_question"] = seed_question
                        rewritten_micro = deepcopy(seed_micro)
                        rewritten["micro_narrative"] = rewritten_micro
                        preserved = _preserve_rewrite_authority(
                            winner,
                            rewritten,
                        )
                        if preserved is not None:
                            print(
                                "🧭 NARROWNESS DETERMINISTIC GROUNDED REWRITE: "
                                "used exact repo-owned fixed-topic seed"
                            )
                            return preserved
        except Exception:
            # Exact-seed assistance is optional. Any lookup/composition problem
            # falls back to the existing winner-owned evidence path below.
            pass

    # Prefer mechanism/fact authority over a generic generated Reveal.
    grounded_reveal = ""
    for field in ("mechanism",):
        value = str(winner.get(field) or "").strip()
        if value:
            grounded_reveal = value
            break

    if not grounded_reveal:
        fact_focus = winner.get("fact_check_focus")
        if isinstance(fact_focus, list):
            grounded_reveal = next(
                (str(item).strip() for item in fact_focus if str(item or "").strip()),
                "",
            )

    if not grounded_reveal:
        grounded_reveal = evidence[0]

    if not grounded_reveal:
        return None

    rewritten_micro["reveal"] = grounded_reveal
    rewritten["micro_narrative"] = rewritten_micro

    preserved = _preserve_rewrite_authority(winner, rewritten)
    if preserved is None:
        return None

    print(
        "🧭 NARROWNESS DETERMINISTIC GROUNDED REWRITE: "
        "promoted existing evidence without API call"
    )
    return preserved


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

    fact_check_focus = winner.get("fact_check_focus")
    if not isinstance(fact_check_focus, list):
        fact_check_focus = []

    visual_proof = winner.get("visual_proof")
    if not isinstance(visual_proof, list):
        visual_proof = []

    fact_focus_text = "\n".join(
        f"- {str(item).strip()}"
        for item in fact_check_focus
        if str(item).strip()
    ) or "- 없음"

    visual_proof_text = "\n".join(
        f"- {str(item).strip()}"
        for item in visual_proof
        if str(item).strip()
    ) or "- 없음"

    original_summary = (
        f"Topic: {winner.get('topic', '')}\n"
        f"Angle: {winner.get('angle', '')}\n"
        f"Core Question: {winner.get('core_question', '')}\n"
        f"Hook: {micro.get('hook', '')}\n"
        f"Reveal: {micro.get('reveal', '')}\n"
        f"Payoff: {micro.get('payoff', '')}\n"
        f"\n[FACT CHECK FOCUS]\n{fact_focus_text}\n"
        f"\n[VISUAL PROOF]\n{visual_proof_text}\n"
        f"\n[REJECTION REASON]\n{reason}"
    )

    call_number = authorize_call(model)
    print(f"💳 Narrowness rewrite API call authorized: #{call_number}")

    try:
        allowed_numbers = sorted(
            _numeric_claim_tokens(_rewrite_candidate_text(winner))
        )
        if allowed_numbers:
            numeric_policy = (
                "\n\n[NUMERIC AUTHORITY]\n"
                "사용 가능한 기존 정량 토큰은 다음뿐이다: "
                + ", ".join(allowed_numbers)
                + "\n이 목록에 없는 새 숫자/단위/퍼센트/각도는 절대 추가하지 마라."
            )
        else:
            numeric_policy = (
                "\n\n[NUMERIC AUTHORITY]\n"
                "기존 Candidate와 근거에는 승인된 정량 값이 없다. "
                "숫자, 퍼센트, 각도, 힘, 질량, 거리, 시간 값을 새로 만들지 마라."
            )

        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": _NARROWNESS_REWRITE_PROMPT + numeric_policy,
                },
                {"role": "user", "content": original_summary},
            ],
            temperature=0.2,
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
        rewritten = validate_candidate(parsed, prefix="winner", runner_up=False)
    except Exception:
        return None

    return _preserve_rewrite_authority(winner, rewritten)


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

    result = (
        validate_explorer_output(
            parsed
        )
    )

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

        fixed_topic_key = _exact_fixed_topic_for_candidate(winner)

        # Run 35415019612: before spending another model rewrite call, make one
        # deterministic attempt that can only promote evidence already present
        # on the Winner.  Acceptance still requires the unchanged narrowness
        # self-critique to return NARROW_ENOUGH.
        if (
            critique.get("verdict") == "TOO_BROAD"
            and fixed_topic_key
            and fixed_topic_key not in _NARROWNESS_FIXED_TOPIC_LLM_BLOCKED
        ):
            deterministic_rewrite = _deterministic_grounded_narrowness_rewrite(
                winner
            )
            if deterministic_rewrite is not None:
                deterministic_critique = _self_critique_narrowness(
                    deterministic_rewrite,
                    model=model,
                )
                winner = deterministic_rewrite
                critique = deterministic_critique

        rewrite_attempts = 0

        while (
            critique.get("verdict") == "TOO_BROAD"
            and rewrite_attempts < MAX_NARROWNESS_REWRITES
        ):

            if (
                fixed_topic_key
                and fixed_topic_key in _NARROWNESS_FIXED_TOPIC_LLM_BLOCKED
            ):
                print(
                    "🛑 NARROWNESS LLM REWRITE SKIPPED: "
                    "exact fixed topic already produced an unusable rewrite "
                    "in this process"
                )
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
                # For an exact fixed topic, repeating a model rewrite after an
                # unusable result recreated the same unsupported-precision loop
                # across production attempts.  Remember that one failure for
                # this process and let later raw Explorer candidates try to
                # pass the real gate without spending more rewrite calls.
                if fixed_topic_key:
                    _NARROWNESS_FIXED_TOPIC_LLM_BLOCKED.add(fixed_topic_key)
                    print(
                        "🛑 NARROWNESS FIXED-TOPIC REWRITE BLOCKED: "
                        "later attempts must pass without another LLM rewrite"
                    )
                    break

                # Automatic-topic paths retain the original bounded retry
                # behavior.  No threshold or retry limit is relaxed.
                continue

            winner = rewritten

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

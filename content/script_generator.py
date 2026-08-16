# content/script_generator.py

import json
import re

import openai

from config import (
    MIN_SCENES,
    MAX_SCENES,
    MIN_NOVELTY_SCORE,
    MAX_SCRIPT_ATTEMPTS,
)

from content.topic_selector import (
    get_recent_topic_names,
)

from quality.budget_guard import (
    authorize_call,
    record_usage,
    print_budget_status,
)


# ============================================================
# V3.2 Shorts Script Generator
# ============================================================
#
# 책임:
#
# 1. 구체적인 소재 발굴
# 2. 소재 신선도 검사
# 3. 대중성 / 감정 자극 검사
# 4. 기본적인 첫 장면 구조 검사
# 5. 대본 생성
# 6. 장면 구조 검사
# 7. Pexels 검색어 검사
# 8. API Budget Guard 연동
#
# 중요:
#
# 실제 Hook 품질은 quality/judge.py의
# Hook Judge가 최종 평가한다.
#
# Script Generator의 하드 Validator는
# 명백한 구조 오류만 차단한다.
#
# 하지 않는 것:
#
# - 영상 다운로드
# - TTS
# - 자막 렌더링
# - 영상 합성
# - Telegram
#
# ============================================================


MODEL = "gpt-4o-mini"


# ============================================================
# V3 후킹 기준
# ============================================================

HOOK_MIN_SCORE = 8


# ============================================================
# 명백한 설명형 오프닝 패턴
#
# 이 패턴들은 하드 차단.
# ============================================================

HOOK_BANNED_PATTERNS = [
    "있는 모습",
    "하는 장면",
    "보이는 모습",
    "보이고 있습니다",
    "놓여 있는",
    "놓여있는",
    "단순히",
    "오늘은",
    "이번 영상에서는",
    "알아보겠습니다",
]


# ============================================================
# Hook 참고 신호
#
# 중요:
# 더 이상 validate_hook()의 필수조건이 아니다.
#
# Prompt에서 AI에게 좋은 후킹 방향을
# 알려주기 위한 참고 신호로만 사용한다.
# ============================================================

HOOK_REQUIRED_SIGNALS = [
    "왜",
    "진짜 이유",
    "사실",
    "몰랐",
    "위험",
    "비밀",
    "이상",
    "반전",
    "의외",
    "그런데",
]


# ============================================================
# 대중성 필터
# ============================================================

TRAFFIC_REQUIRED_SIGNALS = [
    "공포",
    "위험",
    "충격",
    "의외",
    "궁금",
    "비밀",
    "반전",
    "놀라",
    "믿기",
    "몰랐",
]


# ============================================================
# 명백한 상식 소재
# ============================================================

COMMON_KNOWLEDGE_KEYWORDS = [
    "지구는 둥글",
    "태양은 동쪽",
    "물은 100도",
    "물은 섭씨 100도",
    "하늘은 파란",
    "중력 때문에 떨어",
    "심장은 피",
    "지구가 태양",
    "달은 지구",
    "식물은 광합성",
    "사람은 산소",
    "얼음은 물",
    "비는 구름",
    "무지개는 빛",
    "번개는 전기",
    "겨울에는 춥",
    "여름에는 덥",
]


# ============================================================
# JSON 추출
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError(
            "AI 응답이 비어 있습니다."
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
        return json.loads(
            text
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # 배열 추출
    # --------------------------------------------------------

    start = text.find("[")
    end = text.rfind("]")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:
            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # 객체 추출
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:
            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    raise ValueError(
        "AI 응답에서 JSON을 찾지 못했습니다."
    )


# ============================================================
# 너무 흔한 소재 검사
# ============================================================

def looks_too_common(topic):

    if not topic:
        return True

    normalized = (
        topic
        .replace(" ", "")
        .lower()
    )

    for keyword in (
        COMMON_KNOWLEDGE_KEYWORDS
    ):

        normalized_keyword = (
            keyword
            .replace(" ", "")
            .lower()
        )

        if (
            normalized_keyword
            in normalized
        ):

            return True

    return False


# ============================================================
# 후킹 하드 검사 V3.2
# ============================================================
#
# 과거:
#
#   "왜", "비밀", "위험" 등의 특정 단어가
#   없으면 바로 FAIL.
#
# 문제:
#
#   실제로 좋은 후킹도 키워드가 없다는 이유만으로
#   Script Generator에서 폐기될 수 있었다.
#
# V3.2:
#
#   - 빈 대사
#   - 빈 검색어
#   - 명백한 설명형 오프닝
#   - 지나치게 짧은 대사
#
# 이런 객관적 문제만 하드 차단.
#
# 실제 Hook 품질은 Hook Judge가 평가한다.
#
# ============================================================

def validate_hook(scene):

    if not isinstance(
        scene,
        dict,
    ):

        return (
            False,
            "첫 장면 데이터가 없음",
        )

    text = str(
        scene.get(
            "text",
            "",
        )
    ).strip()

    keyword = str(
        scene.get(
            "keyword",
            "",
        )
    ).strip()

    # --------------------------------------------------------
    # 빈 대사
    # --------------------------------------------------------

    if not text:

        return (
            False,
            "첫 장면 대사가 없음",
        )

    # --------------------------------------------------------
    # 빈 검색어
    # --------------------------------------------------------

    if not keyword:

        return (
            False,
            "첫 장면 검색어가 없음",
        )

    # --------------------------------------------------------
    # 명백한 설명조 오프닝 차단
    # --------------------------------------------------------

    for banned in (
        HOOK_BANNED_PATTERNS
    ):

        if banned in text:

            return (
                False,
                (
                    "설명조 오프닝 금지 표현: "
                    f"{banned}"
                ),
            )

    # --------------------------------------------------------
    # 지나치게 짧은 대사 차단
    # --------------------------------------------------------

    if len(text) < 12:

        return (
            False,
            "첫 장면 대사가 지나치게 짧음",
        )

    # --------------------------------------------------------
    # 중요:
    #
    # 특정 호기심 단어 존재 여부로
    # 더 이상 FAIL시키지 않는다.
    #
    # 실제 Hook 품질은 AI Hook Judge가 판단.
    # --------------------------------------------------------

    return (
        True,
        "하드 후킹 검사 통과",
    )


# ============================================================
# 대중성 검사
# ============================================================

def validate_traffic_potential(
    title,
    topic,
    scenes,
):

    combined_text = " ".join([
        str(title),
        str(topic),
    ])

    signal_count = sum(
        1

        for signal in (
            TRAFFIC_REQUIRED_SIGNALS
        )

        if signal in combined_text
    )

    # --------------------------------------------------------
    # 첫 장면까지 포함
    # --------------------------------------------------------

    if scenes:

        first_text = str(
            scenes[0].get(
                "text",
                "",
            )
        )

        signal_count += sum(
            1

            for signal in (
                TRAFFIC_REQUIRED_SIGNALS
            )

            if signal in first_text
        )

    if signal_count <= 0:

        return (
            False,
            (
                "대중적 관심을 유발하는 "
                "감정/호기심 신호 부족"
            ),
        )

    return (
        True,
        "통과",
    )


# ============================================================
# 장면 구조 검사
# ============================================================

def validate_scenes(scenes):

    if not isinstance(
        scenes,
        list,
    ):

        return (
            False,
            "scenes가 배열이 아님",
        )

    if len(scenes) < MIN_SCENES:

        return (
            False,
            (
                f"장면 수 부족: "
                f"{len(scenes)}"
            ),
        )

    if len(scenes) > MAX_SCENES:

        return (
            False,
            (
                f"장면 수 초과: "
                f"{len(scenes)}"
            ),
        )

    for idx, scene in enumerate(
        scenes
    ):

        if not isinstance(
            scene,
            dict,
        ):

            return (
                False,
                (
                    f"{idx + 1}번 "
                    "장면이 객체가 아님"
                ),
            )

        text = str(
            scene.get(
                "text",
                "",
            )
        ).strip()

        keyword = str(
            scene.get(
                "keyword",
                "",
            )
        ).strip()

        if not text:

            return (
                False,
                (
                    f"{idx + 1}번 "
                    "장면 대사가 없음"
                ),
            )

        if not keyword:

            return (
                False,
                (
                    f"{idx + 1}번 "
                    "장면 검색어가 없음"
                ),
            )

        # ----------------------------------------------------
        # keyword는 영어 검색어 기대
        # ----------------------------------------------------

        if not re.search(
            r"[A-Za-z]",
            keyword,
        ):

            return (
                False,
                (
                    f"{idx + 1}번 "
                    "검색어가 영어가 아님: "
                    f"{keyword}"
                ),
            )

        # ----------------------------------------------------
        # 지나치게 추상적인 검색어
        # ----------------------------------------------------

        normalized = (
            keyword.lower()
        )

        bad_keywords = [
            "science",
            "technology",
            "nature",
            "interesting",
            "amazing",
            "documentary",
            "random",
            "background",
        ]

        if normalized in bad_keywords:

            return (
                False,
                (
                    f"{idx + 1}번 "
                    "검색어가 너무 추상적임: "
                    f"{keyword}"
                ),
            )

    return (
        True,
        "통과",
    )


# ============================================================
# 검색어 다양성 검사
# ============================================================

def validate_keyword_variety(
    scenes,
):

    keywords = [
        str(
            scene.get(
                "keyword",
                "",
            )
        ).lower()

        for scene in scenes
    ]

    if not keywords:

        return (
            False,
            "검색어 없음",
        )

    unique_count = len(
        set(
            keywords
        )
    )

    # --------------------------------------------------------
    # 최소 절반 이상은 서로 달라야 함
    # --------------------------------------------------------

    required = max(
        6,
        len(keywords) // 2,
    )

    if unique_count < required:

        return (
            False,
            "검색어 반복이 지나치게 많음",
        )

    return (
        True,
        "통과",
    )


# ============================================================
# V3.2 전체 Script 하드 검사
# ============================================================

def validate_script(result):

    if not isinstance(
        result,
        dict,
    ):

        return (
            False,
            "AI 결과가 JSON 객체가 아님",
        )

    title = str(
        result.get(
            "title",
            "",
        )
    ).strip()

    topic = str(
        result.get(
            "topic",
            "",
        )
    ).strip()

    scenes = result.get(
        "scenes",
        [],
    )

    novelty_score = result.get(
        "novelty_score",
        0,
    )

    try:

        novelty_score = int(
            novelty_score
        )

    except Exception:

        novelty_score = 0

    # --------------------------------------------------------
    # 기본값
    # --------------------------------------------------------

    if not title:

        return (
            False,
            "제목 없음",
        )

    if not topic:

        return (
            False,
            "소재 없음",
        )

    # --------------------------------------------------------
    # 명백한 상식 소재
    # --------------------------------------------------------

    if looks_too_common(
        topic
    ):

        return (
            False,
            "너무 흔한 상식 소재",
        )

    # --------------------------------------------------------
    # 생성 AI 자체 신선도 기준
    #
    # 이후 Novelty Judge가 다시 독립 평가한다.
    # --------------------------------------------------------

    if (
        novelty_score
        < MIN_NOVELTY_SCORE
    ):

        return (
            False,
            (
                f"신선도 부족: "
                f"{novelty_score}/10"
            ),
        )

    # --------------------------------------------------------
    # 장면 구조
    # --------------------------------------------------------

    valid, reason = (
        validate_scenes(
            scenes
        )
    )

    if not valid:

        return (
            False,
            reason,
        )

    # --------------------------------------------------------
    # 첫 장면 하드 검사
    # --------------------------------------------------------

    valid, reason = (
        validate_hook(
            scenes[0]
        )
    )

    if not valid:

        return (
            False,
            (
                f"후킹 구조 실패: "
                f"{reason}"
            ),
        )

    # --------------------------------------------------------
    # 대중성 기본 필터
    # --------------------------------------------------------

    valid, reason = (
        validate_traffic_potential(
            title,
            topic,
            scenes,
        )
    )

    if not valid:

        return (
            False,
            (
                f"트래픽 필터 실패: "
                f"{reason}"
            ),
        )

    # --------------------------------------------------------
    # 검색어 다양성
    # --------------------------------------------------------

    valid, reason = (
        validate_keyword_variety(
            scenes
        )
    )

    if not valid:

        return (
            False,
            reason,
        )

    return (
        True,
        "V3.2 하드 검사 통과",
    )


# ============================================================
# AI 대본 생성
# ============================================================

def generate_script(
    topic_info,
):

    if not isinstance(
        topic_info,
        dict,
    ):

        raise TypeError(
            "topic_info는 dict여야 합니다."
        )

    category = (
        topic_info["category"]
    )

    direction = (
        topic_info["topic"]
    )

    recent_topics = (
        get_recent_topic_names()
    )

    recent_text = "\n".join(
        f"- {item}"

        for item in (
            recent_topics[-20:]
        )
    )

    print("")
    print("=" * 58)
    print(
        "🧠 V3.2 AI 소재 + 대본 생성 시작"
    )
    print("=" * 58)

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1,
    ):

        print("")
        print(
            f"🔎 V3.2 소재 탐색 "
            f"{attempt}/"
            f"{MAX_SCRIPT_ATTEMPTS}"
        )

        prompt = f"""
너는 유튜브 Shorts 전문 콘텐츠 디렉터다.

이번 콘텐츠 방향:
{direction}

분야:
{category}


============================================================
V3.2 핵심 목표
============================================================

절대로 평범한 정보 영상을 만들지 마라.

시청자가 첫 1~3초에

"어? 왜?"
"저게 왜 저렇게 되지?"
"처음 보는데?"
"설마 저런 이유였어?"

라고 느껴야 한다.

단순히 대상을 보여주고 설명하는 영상은 실패다.


============================================================
[첫 장면]
============================================================

첫 장면은 반드시 강한 정보 공백이나
의외성을 만들어야 한다.

좋은 첫 장면은 반드시
'왜', '비밀', '위험' 같은 단어를
직접 포함할 필요는 없다.

예:

"사막에서 물 한 방울 없이 몇 달을 버티는 동물이 있습니다."

"이 거대한 건물은 강풍이 불면 일부러 움직입니다."

"이 배는 바닥에 구멍이 있는데도 가라앉지 않습니다."

이런 식으로 문장 자체가
시청자의 궁금증을 만들면 된다.


============================================================
[절대 금지 오프닝]
============================================================

첫 장면에서 다음과 같은
평범한 설명을 금지한다.

"전선이 놓여 있습니다."

"기차가 달리고 있습니다."

"어떤 장면입니다."

"오늘은 ~에 대해 알아보겠습니다."

"이것은 ~입니다."

"~하는 모습입니다."


============================================================
[소재 트래픽]
============================================================

소재는 일반 대중이 관심을 가질
가능성이 높아야 한다.

특히

공포,
위험,
충격,
궁금증,
비밀,
반전,
의외성

중 하나 이상의 감정적 장치를 가져라.

단순한 산업 기술 설명이나
교과서적인 안전 교육은 피한다.


============================================================
[신선도]
============================================================

novelty_score는 1~10.

7 미만은 실패.

가능하면 8~10.

한국의 일반적인 성인이
이미 대부분 알고 있을 내용이면
소재 자체를 바꿔라.


============================================================
[스토리]
============================================================

다음 흐름을 참고한다.

1. 강력한 후킹
2. 이상한 현상
3. 왜 그런지 질문
4. 일반적인 예상
5. 예상과 다른 문제
6. 실제 해결 방법
7. 핵심 원리
8. 실제 구조/사례
9. 의외의 추가 사실
10. 다른 사례
11. 납득
12. 결론

단순 설명만 계속 이어지는
구간을 만들지 마라.


============================================================
[시각 설계]
============================================================

각 장면의 keyword는
대사의 단어를 기계적으로
번역한 것이 아니다.

반드시 해당 장면의 상황을
직접 보여줄 수 있는
영어 검색어를 작성한다.

좋은 예:

train railway curve

tractor huge tire field

ship dry dock hull

bridge expansion joint

underwater animal hunting

desert camel drinking water

skyscraper wind damper


금지:

science

technology

nature

interesting

amazing

documentary

random

background


============================================================
[장면]
============================================================

12~13개.

첫 장면은 가장 강력해야 한다.

중간 장면은
실제 원리나 구조를 보여줘야 한다.

가능하면 같은 종류의 B-roll을
연속해서 반복하지 마라.


============================================================
[길이]
============================================================

전체 영상은 75~90초를 목표로 한다.

전체 대사는 TTS 기준으로
충분한 분량을 작성한다.


============================================================
[사실성]
============================================================

확인되지 않은 괴담 금지.

근거 없는 숫자 금지.

가짜 연구 금지.

과장된 사실 금지.

확실하지 않은 내용을
사실처럼 만들어내지 마라.


============================================================
[이전 소재]
============================================================

다음 소재와 동일하거나
사실상 같은 소재는 금지한다.

{recent_text}


============================================================
[출력]
============================================================

반드시 JSON 객체 하나만 출력한다.

JSON 외 설명 금지.

형식:

{{
  "title": "호기심을 만드는 제목",
  "topic": "구체적인 실제 소재",
  "category": "{category}",
  "novelty_score": 9,
  "scenes": [
    {{
      "text": "강력한 첫 장면 대사",
      "keyword": "specific visual keyword"
    }}
  ]
}}

12~13개 scenes를 반드시 작성한다.
"""

        try:

            # =================================================
            # V3.2 Budget Guard
            # =================================================

            call_number = (
                authorize_call(
                    MODEL
                )
            )

            print(
                "💳 Script API call "
                f"authorized: "
                f"#{call_number}"
            )

            # =================================================
            # OpenAI
            # =================================================

            response = (
                openai
                .chat
                .completions
                .create(
                    model=MODEL,

                    messages=[
                        {
                            "role":
                                "system",

                            "content": (
                                "너는 V3 Shorts 엔진의 "
                                "콘텐츠 디렉터다. "
                                "평범한 설명 영상보다 "
                                "강한 호기심과 의외성을 "
                                "가진 실제 소재를 선택한다."
                            ),
                        },

                        {
                            "role":
                                "user",

                            "content":
                                prompt,
                        },
                    ],

                    temperature=1.0,
                )
            )

            # =================================================
            # 비용 기록
            # =================================================

            usage = (
                record_usage(
                    MODEL,
                    response,
                )
            )

            print(
                "💰 Script call:"
                f" ${usage['cost_usd']:.6f}"
            )

            print_budget_status()

            # =================================================
            # 응답
            # =================================================

            content = (
                response
                .choices[0]
                .message
                .content
            )

            if not content:

                raise ValueError(
                    "AI 응답 내용이 비어 있습니다."
                )

            result = extract_json(
                content.strip()
            )

            if not isinstance(
                result,
                dict,
            ):

                raise ValueError(
                    "AI 결과가 JSON 객체가 아닙니다."
                )

            actual_topic = str(
                result.get(
                    "topic",
                    "",
                )
            ).strip()

            novelty_score = (
                result.get(
                    "novelty_score",
                    0,
                )
            )

            try:

                novelty_score = int(
                    novelty_score
                )

            except Exception:

                novelty_score = 0

            result[
                "novelty_score"
            ] = novelty_score

            print("")
            print(
                f"🧠 소재: "
                f"{actual_topic}"
            )

            print(
                f"✨ 생성 AI 신선도: "
                f"{novelty_score}/10"
            )

            # =================================================
            # 최근 소재 중복
            # =================================================

            if (
                actual_topic
                in recent_topics
            ):

                print(
                    "🚫 최근 사용 소재 → 폐기"
                )

                continue

            # =================================================
            # V3.2 하드 검사
            # =================================================

            valid, reason = (
                validate_script(
                    result
                )
            )

            if not valid:

                print(
                    "🚫 V3.2 하드 검사 실패: "
                    f"{reason}"
                )

                continue

            # =================================================
            # Scene 정리
            # =================================================

            cleaned_scenes = []

            for scene in (
                result["scenes"]
            ):

                cleaned_scenes.append({
                    "text": str(
                        scene["text"]
                    ).strip(),

                    "keyword": str(
                        scene["keyword"]
                    ).strip(),
                })

            result[
                "scenes"
            ] = cleaned_scenes[
                :MAX_SCENES
            ]

            result[
                "title"
            ] = str(
                result.get(
                    "title",
                    actual_topic,
                )
            ).strip()

            result[
                "topic"
            ] = actual_topic

            result[
                "category"
            ] = category

            # =================================================
            # 성공
            # =================================================

            print("")
            print("=" * 58)

            print(
                "🎯 V3.2 소재 후보 생성 성공"
            )

            print(
                f"🧠 소재: "
                f"{actual_topic}"
            )

            print(
                f"✨ 신선도: "
                f"{novelty_score}/10"
            )

            print(
                f"📝 제목: "
                f"{result['title']}"
            )

            print(
                f"🎬 장면: "
                f"{len(result['scenes'])}개"
            )

            print("")
            print(
                "➡️ 이제 실제 품질 판단은 "
                "V3.2 Judge에게 전달합니다."
            )

            print("=" * 58)

            return result

        except Exception as e:

            print(
                "⚠️ V3.2 생성 실패: "
                f"{e}"
            )

    raise RuntimeError(
        "V3 기준을 통과하는 "
        "소재를 찾지 못했습니다."
)

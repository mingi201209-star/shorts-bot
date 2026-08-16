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
# V3.2.1.1 Shorts Script Generator
# ============================================================
#
# 핵심:
#
# - 명백한 구조 오류만 Hard 차단
# - 실제 Hook / Novelty 품질은 Judge가 담당
# - Novelty 탈락 후 재생성 시:
#
#     이전 소재
#     + Novelty 점수
#     + Novelty Judge 근거
#     + Novelty issues
#
#   를 다음 소재 생성에 전달
#
# - 제목만 바꾸는 가짜 재생성 금지
# - 핵심 대상 / 현상 / 메커니즘 자체를 바꾸도록 요구
#
# ============================================================


MODEL = "gpt-4o-mini"


# ============================================================
# Hook 기준
# ============================================================

HOOK_MIN_SCORE = 8


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

    try:

        return json.loads(
            text
        )

    except Exception:

        pass

    # --------------------------------------------------------
    # 배열
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
    # 객체
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
# 문자열 정규화
# ============================================================

def normalize_topic_text(
    text,
):

    return (
        str(
            text
        )
        .replace(" ", "")
        .replace("\n", "")
        .lower()
        .strip()
    )


# ============================================================
# 이미 거절된 소재인지
# ============================================================

def is_rejected_topic(
    topic,
    rejected_topics,
):

    if not topic:

        return False

    if not rejected_topics:

        return False

    normalized = (
        normalize_topic_text(
            topic
        )
    )

    for rejected in rejected_topics:

        if (
            normalized
            == normalize_topic_text(
                rejected
            )
        ):

            return True

    return False


# ============================================================
# Generation Feedback 텍스트
# ============================================================

def build_generation_feedback_text(
    generation_feedback,
):

    if not generation_feedback:

        return (
            "이전 Novelty 탈락 피드백 없음."
        )

    if isinstance(
        generation_feedback,
        str,
    ):

        return generation_feedback

    try:

        return json.dumps(
            generation_feedback,
            ensure_ascii=False,
            indent=2,
        )

    except Exception:

        return str(
            generation_feedback
        )


# ============================================================
# Reject 목록 텍스트
# ============================================================

def build_rejected_topics_text(
    rejected_topics,
):

    if not rejected_topics:

        return (
            "이번 실행에서 폐기된 소재 없음."
        )

    return "\n".join(
        f"- {item}"

        for item in rejected_topics
    )


# ============================================================
# 너무 흔한 소재 검사
# ============================================================

def looks_too_common(
    topic,
):

    if not topic:

        return True

    normalized = (
        normalize_topic_text(
            topic
        )
    )

    for keyword in (
        COMMON_KNOWLEDGE_KEYWORDS
    ):

        normalized_keyword = (
            normalize_topic_text(
                keyword
            )
        )

        if (
            normalized_keyword
            in normalized
        ):

            return True

    return False


# ============================================================
# 후킹 Hard 검사
# ============================================================

def validate_hook(
    scene,
):

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

    if not text:

        return (
            False,
            "첫 장면 대사가 없음",
        )

    if not keyword:

        return (
            False,
            "첫 장면 검색어가 없음",
        )

    # --------------------------------------------------------
    # 명백한 설명형 시작만 차단
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

    if len(text) < 12:

        return (
            False,
            "첫 장면 대사가 지나치게 짧음",
        )

    # 실제 Hook 품질은 Judge가 판단
    return (
        True,
        "하드 후킹 검사 통과",
    )


# ============================================================
# 대중성 기본 검사
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
# Scene 구조
# ============================================================

def validate_scenes(
    scenes,
):

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
# Keyword 다양성
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
# V3.2.1.1 Script Hard 검사
# ============================================================

def validate_script(
    result,
):

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

    if looks_too_common(
        topic
    ):

        return (
            False,
            "너무 흔한 상식 소재",
        )

    # --------------------------------------------------------
    # 생성 AI 자기평가 최소선
    #
    # Novelty Judge가 이후 독립 판정.
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
        "V3.2.1.1 하드 검사 통과",
    )


# ============================================================
# AI 대본 생성
# ============================================================

def generate_script(
    topic_info,
    *,
    generation_feedback=None,
    rejected_topics=None,
):

    if not isinstance(
        topic_info,
        dict,
    ):

        raise TypeError(
            "topic_info는 dict여야 합니다."
        )

    if rejected_topics is None:

        rejected_topics = []

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

    rejected_text = (
        build_rejected_topics_text(
            rejected_topics
        )
    )

    feedback_text = (
        build_generation_feedback_text(
            generation_feedback
        )
    )

    print("")
    print("=" * 58)
    print(
        "🧠 V3.2.1.1 AI 소재 + 대본 생성 시작"
    )
    print("=" * 58)

    if generation_feedback:

        print("")
        print(
            "♻️ Novelty 탈락 피드백을 "
            "다음 생성에 적용합니다."
        )

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1,
    ):

        print("")
        print(
            f"🔎 V3.2.1.1 소재 탐색 "
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
V3.2.1.1 핵심 목표
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
[Novelty 재생성 피드백]
============================================================

아래 내용은 이전 후보가
실제 독립 Novelty Judge에게 탈락한 기록이다.

{feedback_text}


중요:

이전 후보의 제목만 바꾸는 것은 재생성이 아니다.

이전 후보가 Novelty 부족으로 탈락했다면

- 핵심 대상
- 핵심 현상
- 핵심 메커니즘
- 시청자가 알게 되는 핵심 사실

중 적어도 하나 이상을
완전히 다른 방향으로 바꿔라.

가능하면 이전 후보보다
훨씬 덜 알려진 구체적 현상이나 구조를 선택한다.

"익숙한 기술 + 우주와 관련 있음"
처럼 억지로 의외성을 붙이지 마라.

소재 자체가 낯설고
설명 전부터 궁금해야 한다.


============================================================
[이번 실행에서 이미 폐기된 소재]
============================================================

다음 소재는 다시 사용하지 마라.

{rejected_text}


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

문장 자체가
시청자의 궁금증을 만들어야 한다.


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

중 하나 이상의 장치를 가져라.

하지만 감정 단어만 붙여서
평범한 소재를 자극적으로 포장하지 마라.

소재 그 자체가 흥미로워야 한다.


============================================================
[신선도]
============================================================

novelty_score는 1~10.

7 미만은 실패.

가능하면 8~10.

한국의 일반적인 성인이
이미 대부분 알고 있을 내용이면
소재 자체를 바꿔라.

단순한 상식의 세부 설명보다

- 눈으로 봤을 때 이상한 구조
- 예상과 반대되는 작동 방식
- 평소 보지만 이유를 잘 모르는 현상
- 실제 존재하지만 잘 알려지지 않은 설계
- 대중이 쉽게 오해하는 실제 원리

를 우선한다.


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

같은 종류의 B-roll을
연속 반복하지 마라.


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
[과거 사용 소재]
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
            # Budget Guard
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
                                "너는 V3.2.1.1 Shorts 엔진의 "
                                "콘텐츠 디렉터다. "
                                "평범한 소재를 반복하지 않고, "
                                "이전 Novelty 실패 원인을 분석해 "
                                "더 신선한 실제 소재를 선택한다."
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
            # 응답 파싱
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

            result = (
                extract_json(
                    content.strip()
                )
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
            # 최근 사용 소재
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
            # 이번 실행에서 이미 폐기
            # =================================================

            if is_rejected_topic(
                actual_topic,
                rejected_topics,
            ):

                print(
                    "🚫 이번 실행에서 이미 "
                    "Novelty 탈락한 소재 → 폐기"
                )

                continue

            # =================================================
            # Hard 검사
            # =================================================

            valid, reason = (
                validate_script(
                    result
                )
            )

            if not valid:

                print(
                    "🚫 V3.2.1.1 하드 검사 실패: "
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
                "🎯 V3.2.1.1 소재 후보 생성 성공"
            )

            print(
                f"🧠 소재: "
                f"{actual_topic}"
            )

            print(
                f"✨ 생성 AI 신선도: "
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
                "➡️ 실제 품질 판단은 "
                "독립 Judge에게 전달합니다."
            )

            print("=" * 58)

            return result

        except Exception as e:

            print(
                "⚠️ V3.2.1.1 생성 실패: "
                f"{e}"
            )

    raise RuntimeError(
        "V3.2.1.1 기준을 통과하는 "
        "소재를 찾지 못했습니다."
            )

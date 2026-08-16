# content/script_generator.py

import json
import os
import re

import openai

from config import (
    OPENAI_KEY,
    MIN_SCENES,
    MAX_SCENES,
    MAX_SCRIPT_ATTEMPTS,
    TARGET_MIN_SECONDS,
    TARGET_MAX_SECONDS,
)

from quality.budget_guard import (
    authorize_call,
    record_usage,
    print_budget_status,
)


# ============================================================
# V3.2.1.2 Shorts Script Generator
# ============================================================
#
# 책임:
#
# Candidate Explorer가 확정한 Winner를 받아
# 실제 12~13 Scene Shorts 대본으로 확장한다.
#
#
# 하는 것:
#
# - 제목 작성
# - Scene 대사 작성
# - Scene별 B-roll 검색 keyword 작성
# - 기본적인 Script 구조 검증
#
#
# 하지 않는 것:
#
# - 새로운 소재 탐색
# - Winner 교체
# - Novelty 자기평가
# - 최근 소재 비교
# - Candidate 재선정
# - Fact 검증 완료 선언
#
#
# 핵심 구조:
#
# Candidate Explorer
#       ↓
# Winner
#       ↓
# Script Generator
#       ↓
# Script
#       ↓
# Judge Committee
#
# ============================================================


MODEL = os.environ.get(
    "V3_SCRIPT_MODEL",
    "gpt-4o-mini",
)


if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


# ============================================================
# 첫 장면 Hard 차단 표현
# ============================================================

HOOK_BANNED_PATTERNS = [
    "있는 모습",
    "하는 장면",
    "보이는 모습",
    "보이고 있습니다",
    "놓여 있는",
    "놓여있는",
    "오늘은",
    "이번 영상에서는",
    "알아보겠습니다",
]


# ============================================================
# 지나치게 추상적인 B-roll 검색어
# ============================================================

BAD_VISUAL_KEYWORDS = [
    "science",
    "technology",
    "nature",
    "interesting",
    "amazing",
    "documentary",
    "random",
    "background",
]


# ============================================================
# JSON 추출
# ============================================================

def extract_json(text):

    if not text:

        raise ValueError(
            "Script Generator 응답이 비어 있습니다."
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
    # JSON 객체 추출
    # --------------------------------------------------------

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:

            result = json.loads(
                text[
                    start:end + 1
                ]
            )

            if isinstance(
                result,
                dict,
            ):

                return result

        except Exception:

            pass

    raise ValueError(
        "Script Generator 응답에서 "
        "유효한 JSON 객체를 찾지 못했습니다."
    )


# ============================================================
# 문자열 필드 검사
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
# Candidate Winner 검사
# ============================================================

def validate_candidate(
    candidate,
):

    if not isinstance(
        candidate,
        dict,
    ):

        raise TypeError(
            "candidate는 dict여야 합니다."
        )

    required_fields = (
        "topic",
        "angle",
        "core_question",
        "micro_narrative",
        "fact_check_focus",
        "visual_proof",
    )

    for field in required_fields:

        if field not in candidate:

            raise ValueError(
                "Candidate Winner 필드 누락: "
                f"{field}"
            )

    topic = require_nonempty_string(
        candidate.get(
            "topic"
        ),
        "candidate.topic",
    )

    angle = require_nonempty_string(
        candidate.get(
            "angle"
        ),
        "candidate.angle",
    )

    core_question = (
        require_nonempty_string(
            candidate.get(
                "core_question"
            ),
            "candidate.core_question",
        )
    )

    micro = candidate.get(
        "micro_narrative"
    )

    if not isinstance(
        micro,
        dict,
    ):

        raise ValueError(
            "candidate.micro_narrative는 "
            "dict여야 합니다."
        )

    clean_micro = {}

    for field in (
        "hook",
        "core_question",
        "reveal",
        "payoff",
    ):

        clean_micro[field] = (
            require_nonempty_string(
                micro.get(
                    field
                ),
                (
                    "candidate.micro_narrative."
                    f"{field}"
                ),
            )
        )

    fact_check_focus = (
        candidate.get(
            "fact_check_focus"
        )
    )

    if not isinstance(
        fact_check_focus,
        list,
    ):

        raise ValueError(
            "candidate.fact_check_focus는 "
            "배열이어야 합니다."
        )

    fact_check_focus = [
        str(item).strip()

        for item in fact_check_focus

        if str(item).strip()
    ]

    if not fact_check_focus:

        raise ValueError(
            "candidate.fact_check_focus가 "
            "비어 있습니다."
        )

    visual_proof = (
        candidate.get(
            "visual_proof"
        )
    )

    if not isinstance(
        visual_proof,
        list,
    ):

        raise ValueError(
            "candidate.visual_proof는 "
            "배열이어야 합니다."
        )

    visual_proof = [
        str(item).strip()

        for item in visual_proof

        if str(item).strip()
    ]

    if not visual_proof:

        raise ValueError(
            "candidate.visual_proof가 "
            "비어 있습니다."
        )

    return {
        "topic":
            topic,

        "angle":
            angle,

        "core_question":
            core_question,

        "micro_narrative":
            clean_micro,

        "fact_check_focus":
            fact_check_focus,

        "visual_proof":
            visual_proof,

        "selection_reason":
            str(
                candidate.get(
                    "selection_reason",
                    "",
                )
            ).strip(),
    }


# ============================================================
# 첫 장면 검사
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

    # --------------------------------------------------------
    # 실제 Hook 품질은 Hook Judge가 판단한다.
    # --------------------------------------------------------

    return (
        True,
        "하드 후킹 검사 통과",
    )


# ============================================================
# Scene 구조 검사
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
                    f"{idx + 1}번 장면이 "
                    "객체가 아님"
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
        # B-roll keyword는 영어 검색어
        # ----------------------------------------------------

        if not re.search(
            r"[A-Za-z]",
            keyword,
        ):

            return (
                False,
                (
                    f"{idx + 1}번 검색어가 "
                    "영어 검색어가 아님: "
                    f"{keyword}"
                ),
            )

        normalized = (
            keyword
            .lower()
            .strip()
        )

        if normalized in (
            BAD_VISUAL_KEYWORDS
        ):

            return (
                False,
                (
                    f"{idx + 1}번 검색어가 "
                    "너무 추상적임: "
                    f"{keyword}"
                ),
            )

    return (
        True,
        "Scene 구조 통과",
    )


# ============================================================
# Keyword 다양성 검사
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
        )
        .strip()
        .lower()

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
            (
                "검색어 반복이 지나치게 많음: "
                f"{unique_count}/"
                f"{len(keywords)}"
            ),
        )

    return (
        True,
        "Keyword 다양성 통과",
    )


# ============================================================
# Script Hard Validator
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

    scenes = result.get(
        "scenes",
        [],
    )

    if not title:

        return (
            False,
            "제목 없음",
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
                "후킹 구조 실패: "
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
        "V3.2.1.2 Script 하드 검사 통과",
    )


# ============================================================
# Candidate Context
# ============================================================

def build_candidate_context(
    candidate,
):

    return json.dumps(
        candidate,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# AI 대본 생성
# ============================================================

def generate_script(
    topic_info,
    candidate,
):

    if not isinstance(
        topic_info,
        dict,
    ):

        raise TypeError(
            "topic_info는 dict여야 합니다."
        )

    candidate = (
        validate_candidate(
            candidate
        )
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

    topic = candidate[
        "topic"
    ]

    angle = candidate[
        "angle"
    ]

    core_question = candidate[
        "core_question"
    ]

    micro = candidate[
        "micro_narrative"
    ]

    candidate_context = (
        build_candidate_context(
            candidate
        )
    )

    print("")
    print("=" * 62)

    print(
        "✍️ V3.2.1.2 SCRIPT GENERATOR"
    )

    print("=" * 62)

    print(
        "🧠 확정 소재:",
        topic,
    )

    print(
        "🎯 핵심 질문:",
        core_question,
    )

    # ========================================================
    # Script 생성 Retry
    # ========================================================

    last_error = None

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1,
    ):

        print("")
        print(
            "📝 Script 작성 "
            f"{attempt}/"
            f"{MAX_SCRIPT_ATTEMPTS}"
        )

        prompt = f"""
너는 유튜브 Shorts 전문 Script Writer다.

Candidate Explorer가 이미
무엇을 이야기할지 결정했다.

너는 새로운 소재를 탐색하지 않는다.

너의 역할은 확정된 Winner를
{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 길이의
12~13 Scene Shorts 대본으로 발전시키는 것이다.


============================================================
[ABSOLUTE CONTENT LOCK]
============================================================

아래 Candidate는 이미 선발이 끝난 Winner다.

소재를 새로 선택하지 마라.

다른 소재로 바꾸지 마라.

핵심 질문을 바꾸지 마라.

Reveal의 핵심 메커니즘을 바꾸지 마라.

Payoff를 다른 결론으로 교체하지 마라.


더 재미있게 만들겠다는 이유로

- 새로운 원인
- 새로운 역사적 기원
- 새로운 숫자
- 새로운 연구
- 새로운 숨겨진 목적
- 다른 메커니즘

을 만들어내지 마라.


Candidate Explorer가 정한

HOOK
CORE QUESTION
REVEAL
PAYOFF

의 논리적 관계를 보존하라.


============================================================
[CANDIDATE WINNER]
============================================================

{candidate_context}


============================================================
[CONTEXT]
============================================================

넓은 분야:
{category}

초기 탐색 방향:
{direction}

확정된 소재:
{topic}

확정된 Angle:
{angle}

확정된 Core Question:
{core_question}


============================================================
[MICRO NARRATIVE — STORY SPINE]
============================================================

HOOK:
{micro["hook"]}

CORE QUESTION:
{micro["core_question"]}

REVEAL:
{micro["reveal"]}

PAYOFF:
{micro["payoff"]}


이 네 요소는 이야기의 척추다.

표현은 자연스럽게 다듬을 수 있지만
핵심 의미를 다른 방향으로 바꾸지 마라.


============================================================
[STORY DESIGN]
============================================================

대본은 단순한 설명 목록이 아니다.

시청자가 계속 다음 정보를 알고 싶도록
정보 공개 순서를 설계하라.


권장 흐름:

1. 강한 Hook
2. Core Question 형성
3. 직관적인 예상 또는 일반적 오해
4. 실제 문제 또는 구조
5. Reveal로 접근
6. 핵심 메커니즘 설명
7. 구체적인 시각적 사례
8. 처음의 질문과 다시 연결
9. Payoff
10. 짧고 강한 마무리


정확히 이 번호대로
Scene을 만들 필요는 없다.

하지만

Hook
→ Curiosity
→ Explanation
→ Payoff

의 긴장 구조는 유지해야 한다.


============================================================
[HOOK]
============================================================

첫 Scene에서 바로 본론에 들어가라.

금지:

"오늘은 ~에 대해 알아보겠습니다."

"이것은 ~입니다."

"~하는 모습입니다."

"혹시 알고 계셨나요?"

같은 일반적인 도입.


첫 장면은
Candidate의 실제 Hook을 사용하여

과장 없이
즉시 정보 공백을 만들어야 한다.


============================================================
[PAYOFF]
============================================================

Hook보다 Payoff가 약해지면 실패다.

후반부가 단순 요약으로 끝나지 않게 하라.

마지막에는

"아, 그래서 처음에 저랬던 거구나."

라는 느낌이 들도록

첫 Hook 또는 Core Question과
Reveal을 다시 연결하라.


============================================================
[FACT DISCIPLINE]
============================================================

Candidate에 없는 새로운 사실을
무리하게 추가하지 마라.

특히 다음을 지어내지 마라.

- 구체적인 연도
- 퍼센트
- 연구 결과
- 역사적 인물의 의도
- 설계자의 숨겨진 목적
- 세계 최초 기록
- "~때문에 만들어졌다" 식의 단정


후단 Fact Judge가 검증해야 할 내용:

{json.dumps(
    candidate["fact_check_focus"],
    ensure_ascii=False,
    indent=2,
)}


이 주장들은 이야기에서 사용할 수 있지만
확신을 과장하지 마라.


============================================================
[VISUAL STORYTELLING]
============================================================

Candidate Explorer가 제안한 Visual Proof:

{json.dumps(
    candidate["visual_proof"],
    ensure_ascii=False,
    indent=2,
)}


각 Scene의 keyword는
대사를 그대로 영어로 번역하는 것이 아니다.

그 Scene에서 실제로 보여줘야 할

- 대상
- 구조
- 행동
- 환경
- 비교
- 메커니즘

을 검색할 수 있는
구체적인 영어 B-roll 검색어를 작성하라.


좋은 검색어:

train railway curve

ship dry dock hull

bridge expansion joint

skyscraper wind damper

factory conveyor belt close up


나쁜 검색어:

science

technology

interesting

amazing

documentary

background


가능하면 같은 B-roll 유형이
연속해서 반복되지 않게 하라.


============================================================
[SCENES]
============================================================

장면 수:

{MIN_SCENES}~{MAX_SCENES}개.


각 Scene은 반드시:

- text
- keyword

를 가진다.


첫 Scene이 가장 강한
정보 공백을 가져야 한다.

중간 Scene은
실제 구조나 과정의 이해를 증가시켜야 한다.

후반 Scene은
Reveal과 Payoff를 연결해야 한다.


============================================================
[LENGTH]
============================================================

전체 영상 목표:

{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초.


12~13개의 지나치게 짧은 문장을
억지로 나누지 마라.

TTS로 읽었을 때
전체 목표 길이에 충분한 분량을 작성하라.


============================================================
[TITLE]
============================================================

제목은 Candidate의 실제 질문과
Reveal에 기반해야 한다.

내용보다 강한 약속을 하지 마라.

Clickbait를 위해
Candidate에 없는 사실을 암시하지 마라.


============================================================
[OUTPUT]
============================================================

반드시 JSON 객체 하나만 출력한다.

JSON 외 설명 금지.

Markdown 금지.

코드블록 금지.


형식:

{{
  "title": "콘텐츠 제목",
  "scenes": [
    {{
      "text": "Scene 대사",
      "keyword": "specific english visual search"
    }}
  ]
}}


중요:

topic,
angle,
core_question,
fact_check_focus,
visual_proof

필드는 출력할 필요가 없다.

이 값들은 코드가
Candidate Explorer의 확정값을 다시 붙인다.
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
                                "너는 V3.2.1.2 Shorts "
                                "Script Writer다. "
                                "Candidate Explorer가 "
                                "확정한 Winner를 변경하지 않고 "
                                "정확하고 몰입도 높은 "
                                "Shorts 대본으로 확장한다."
                            ),
                        },

                        {
                            "role":
                                "user",

                            "content":
                                prompt,
                        },
                    ],

                    temperature=0.8,

                    response_format={
                        "type":
                            "json_object",
                    },
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
                    "Script Generator 응답이 "
                    "비어 있습니다."
                )

            generated = (
                extract_json(
                    content
                )
            )

            # =================================================
            # Hard Validation
            # =================================================

            valid, reason = (
                validate_script(
                    generated
                )
            )

            if not valid:

                last_error = reason

                print(
                    "🚫 Script 하드 검사 실패: "
                    f"{reason}"
                )

                continue

            # =================================================
            # Scene 정리
            # =================================================

            cleaned_scenes = []

            for scene in (
                generated[
                    "scenes"
                ]
            ):

                cleaned_scenes.append({
                    "text":
                        str(
                            scene[
                                "text"
                            ]
                        ).strip(),

                    "keyword":
                        str(
                            scene[
                                "keyword"
                            ]
                        ).strip(),
                })

            cleaned_scenes = (
                cleaned_scenes[
                    :MAX_SCENES
                ]
            )

            # =================================================
            # 중요:
            #
            # Candidate 핵심 정보는
            # 생성 AI의 출력이 아니라
            # Explorer 결과에서 직접 복사한다.
            # =================================================

            result = {
                "title":
                    str(
                        generated[
                            "title"
                        ]
                    ).strip(),

                "topic":
                    candidate[
                        "topic"
                    ],

                "category":
                    category,

                "angle":
                    candidate[
                        "angle"
                    ],

                "core_question":
                    candidate[
                        "core_question"
                    ],

                "micro_narrative":
                    candidate[
                        "micro_narrative"
                    ],

                "fact_check_focus":
                    candidate[
                        "fact_check_focus"
                    ],

                "visual_proof":
                    candidate[
                        "visual_proof"
                    ],

                "candidate_selection_reason":
                    candidate.get(
                        "selection_reason",
                        "",
                    ),

                "scenes":
                    cleaned_scenes,
            }

            # =================================================
            # 성공
            # =================================================

            print("")
            print("=" * 62)

            print(
                "✅ V3.2.1.2 SCRIPT GENERATED"
            )

            print(
                "🧠 소재:",
                result[
                    "topic"
                ],
            )

            print(
                "📝 제목:",
                result[
                    "title"
                ],
            )

            print(
                "🎬 장면:",
                len(
                    result[
                        "scenes"
                    ]
                ),
            )

            print("")
            print(
                "➡️ 다음 단계: "
                "독립 Judge Committee"
            )

            print("=" * 62)

            return result

        except Exception as e:

            last_error = str(
                e
            )

            print(
                "⚠️ Script 생성 실패: "
                f"{e}"
            )

    # ========================================================
    # 모든 Script 시도 실패
    # ========================================================

    raise RuntimeError(
        "V3.2.1.2 Script Generator가 "
        "유효한 대본 생성에 실패했습니다. "
        f"마지막 오류: {last_error}"
        )

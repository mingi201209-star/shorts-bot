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


MODEL = os.environ.get(
    "V3_SCRIPT_MODEL",
    "gpt-4o-mini",
)


if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


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
# JSON
# ============================================================

def extract_json(text):

    if not text:

        raise ValueError(
            "Script Generator 응답이 비어 있습니다."
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
        "Script Generator 응답에서 "
        "유효한 JSON 객체를 찾지 못했습니다."
    )


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


# ============================================================
# Candidate Lock Validation
# ============================================================

def validate_candidate(candidate):

    if not isinstance(candidate, dict):

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
        candidate.get("topic"),
        "candidate.topic",
    )

    angle = require_nonempty_string(
        candidate.get("angle"),
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

    if not isinstance(micro, dict):

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
                micro.get(field),
                (
                    "candidate.micro_narrative."
                    f"{field}"
                ),
            )
        )

    # ========================================================
    # fact_check_focus
    #
    # 빈 배열 허용.
    # 별도 검증이 필요한 핵심 Claim이 없다면 []
    # ========================================================

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

    # ========================================================
    # visual_proof
    #
    # 최소 하나는 필수.
    # ========================================================

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
# Hook
# ============================================================

def validate_hook(scene):

    if not isinstance(scene, dict):

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

    for banned in HOOK_BANNED_PATTERNS:

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

    return (
        True,
        "하드 후킹 검사 통과",
    )


# ============================================================
# Scenes
# ============================================================

def validate_scenes(scenes):

    if not isinstance(scenes, list):

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

    for idx, scene in enumerate(scenes):

        if not isinstance(scene, dict):

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

        if normalized in BAD_VISUAL_KEYWORDS:

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


def validate_keyword_variety(scenes):

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
        set(keywords)
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


def validate_script(result):

    if not isinstance(result, dict):

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


def build_candidate_context(candidate):

    return json.dumps(
        candidate,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# Script Generator
# ============================================================

def generate_script(
    topic_info,
    candidate,
):

    if not isinstance(topic_info, dict):

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
너는 YouTube Shorts 전문 Script Writer다.

Candidate Explorer가 이미
무엇을 이야기할지 결정했다.

너는 새로운 소재를 탐색하지 않는다.

확정된 Winner를
{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초 길이의

{MIN_SCENES}~{MAX_SCENES} Scene

Shorts Script로 발전시킨다.


============================================================
ABSOLUTE CONTENT LOCK
============================================================

Candidate는 이미 선발된 Winner다.

다음을 바꾸지 마라.

- topic
- angle
- core_question
- 핵심 Reveal
- Payoff


더 재미있게 만들겠다는 이유로

- 새로운 원인
- 새로운 역사적 기원
- 새로운 숫자
- 새로운 연구 결과
- 새로운 숨겨진 목적
- 다른 Mechanism

을 만들어내지 마라.


HOOK
CORE QUESTION
REVEAL
PAYOFF

의 논리적 관계를 보존한다.


============================================================
CANDIDATE WINNER
============================================================

{candidate_context}


============================================================
CONTEXT
============================================================

넓은 분야:
{category}

초기 탐색 방향:
{direction}

확정 소재:
{topic}

확정 Angle:
{angle}

확정 Core Question:
{core_question}


============================================================
MICRO NARRATIVE
============================================================

HOOK:
{micro["hook"]}

CORE QUESTION:
{micro["core_question"]}

REVEAL:
{micro["reveal"]}

PAYOFF:
{micro["payoff"]}


표현은 자연스럽게 변경할 수 있지만
핵심 의미는 바꾸지 마라.


============================================================
STORY DESIGN
============================================================

단순 설명 목록을 만들지 마라.

시청자가 계속 다음 정보를 알고 싶도록
정보 공개 순서를 설계한다.


권장 흐름:

Hook
→ Core Question
→ 예상 또는 오해
→ 실제 문제
→ Reveal 접근
→ Mechanism
→ 시각적 사례
→ 처음 질문과 재연결
→ Payoff


정확히 이 순서를 기계적으로 사용할 필요는 없다.


============================================================
HOOK
============================================================

첫 Scene부터 본론에 들어간다.


금지 예:

"오늘은 ~에 대해 알아보겠습니다."

"이것은 ~입니다."

"~하는 모습입니다."

"혹시 알고 계셨나요?"


Candidate의 실제 Hook을 이용해
과장 없이 즉시 정보 공백을 만든다.


============================================================
PAYOFF
============================================================

Hook보다 Payoff가 약하면 실패다.

후반부를 단순 요약으로 끝내지 마라.

처음 Hook 또는 Core Question과
Reveal을 다시 연결한다.


============================================================
FACT DISCIPLINE
============================================================

Candidate에 없는 핵심 사실을
무리하게 추가하지 마라.


특히 발명 금지:

- 구체적인 연도
- 퍼센트
- 연구 결과
- 역사 인물의 의도
- 숨겨진 설계 목적
- 세계 최초 기록
- "~때문에 만들어졌다" 같은 인과 단정


후단 Fact Judge 확인 대상:

{json.dumps(
    candidate["fact_check_focus"],
    ensure_ascii=False,
    indent=2,
)}


배열이 비어 있다면
별도 Fact Risk Claim이 지정되지 않았다는 뜻이다.

그렇다고 새로운 사실을 자유롭게 만들어도 된다는 뜻은 아니다.


============================================================
VISUAL STORYTELLING
============================================================

Visual Proof:

{json.dumps(
    candidate["visual_proof"],
    ensure_ascii=False,
    indent=2,
)}


keyword는 대사를 영어로 번역하는 것이 아니다.

실제로 화면에서 보여줄

- 대상
- 구조
- 행동
- 환경
- 과정
- 비교
- Mechanism

을 검색할 수 있는
구체적인 영어 B-roll 검색어를 작성한다.


좋은 예:

train railway curve
ship dry dock hull
bridge expansion joint
skyscraper wind damper
factory conveyor belt close up


나쁜 예:

science
technology
interesting
amazing
documentary
background


같은 B-roll 유형을
연속 반복하지 마라.


============================================================
SCENES
============================================================

장면:

{MIN_SCENES}~{MAX_SCENES}개.


각 Scene은 반드시:

- text
- keyword

를 가진다.


첫 Scene이 가장 강한 정보 공백을 가진다.

중간은 이해를 증가시킨다.

후반은 Reveal과 Payoff를 연결한다.


============================================================
LENGTH
============================================================

전체 영상 목표:

{TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초.


지나치게 짧은 문장을
억지로 {MIN_SCENES}~{MAX_SCENES}개로 쪼개지 마라.

TTS로 읽을 때
목표 길이에 충분한 분량이어야 한다.


============================================================
TITLE
============================================================

Candidate의 실제 질문과 Reveal에 기반한다.

내용보다 강한 약속을 하지 마라.

Candidate에 없는 사실을 암시하지 마라.


============================================================
OUTPUT
============================================================

JSON 객체 하나만 출력한다.

설명 금지.
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


topic,
angle,
core_question,
micro_narrative,
fact_check_focus,
visual_proof

는 출력하지 않아도 된다.

코드가 Candidate Explorer의
확정값을 다시 붙인다.
"""

        try:

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

            cleaned_scenes = []

            for scene in generated[
                "scenes"
            ]:

                cleaned_scenes.append({
                    "text":
                        str(
                            scene["text"]
                        ).strip(),

                    "keyword":
                        str(
                            scene["keyword"]
                        ).strip(),
                })

            cleaned_scenes = (
                cleaned_scenes[
                    :MAX_SCENES
                ]
            )

            # =================================================
            # Candidate의 핵심 값은
            # AI 출력이 아닌 Explorer 결과를 사용.
            # =================================================

            result = {
                "title":
                    str(
                        generated["title"]
                    ).strip(),

                "topic":
                    candidate["topic"],

                "category":
                    category,

                "angle":
                    candidate["angle"],

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

            print("")
            print("=" * 62)

            print(
                "✅ V3.2.1.2 SCRIPT GENERATED"
            )

            print(
                "🧠 소재:",
                result["topic"],
            )

            print(
                "📝 제목:",
                result["title"],
            )

            print(
                "🎬 장면:",
                len(
                    result["scenes"]
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

            last_error = str(e)

            print(
                "⚠️ Script 생성 실패: "
                f"{e}"
            )

    raise RuntimeError(
        "V3.2.1.2 Script Generator가 "
        "유효한 대본 생성에 실패했습니다. "
        f"마지막 오류: {last_error}"
        )

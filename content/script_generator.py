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


BAD_VISUAL_KEYWORDS = {
    "science",
    "technology",
    "nature",
    "interesting",
    "amazing",
    "documentary",
    "random",
    "background",
    "concept",
    "future",
}


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

    if start != -1 and end > start:
        result = json.loads(
            text[start:end + 1]
        )
        if isinstance(result, dict):
            return result

    raise ValueError(
        "Script Generator 응답에서 유효한 JSON 객체를 찾지 못했습니다."
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
# Candidate Lock
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

    micro = candidate.get(
        "micro_narrative"
    )

    if not isinstance(micro, dict):
        raise ValueError(
            "candidate.micro_narrative는 dict여야 합니다."
        )

    clean_micro = {
        key: require_nonempty_string(
            micro.get(key),
            f"candidate.micro_narrative.{key}",
        )
        for key in (
            "hook",
            "core_question",
            "reveal",
            "payoff",
        )
    }

    fact_check_focus = candidate.get(
        "fact_check_focus"
    )

    if not isinstance(
        fact_check_focus,
        list,
    ):
        raise ValueError(
            "candidate.fact_check_focus는 배열이어야 합니다."
        )

    fact_check_focus = [
        str(item).strip()
        for item in fact_check_focus
        if str(item).strip()
    ]

    visual_proof = candidate.get(
        "visual_proof"
    )

    if not isinstance(
        visual_proof,
        list,
    ):
        raise ValueError(
            "candidate.visual_proof는 배열이어야 합니다."
        )

    visual_proof = [
        str(item).strip()
        for item in visual_proof
        if str(item).strip()
    ]

    if not visual_proof:
        raise ValueError(
            "candidate.visual_proof가 비어 있습니다."
        )

    return {
        "topic": require_nonempty_string(
            candidate.get("topic"),
            "candidate.topic",
        ),
        "angle": require_nonempty_string(
            candidate.get("angle"),
            "candidate.angle",
        ),
        "core_question": require_nonempty_string(
            candidate.get("core_question"),
            "candidate.core_question",
        ),
        "micro_narrative": clean_micro,
        "fact_check_focus": fact_check_focus,
        "visual_proof": visual_proof,
        "selection_reason": str(
            candidate.get(
                "selection_reason",
                "",
            )
        ).strip(),
    }


# ============================================================
# Scene Validation
# ============================================================

def validate_hook(scene):

    if not isinstance(scene, dict):
        return False, "첫 장면 데이터가 없음"

    text = str(
        scene.get("text", "")
    ).strip()

    if not text:
        return False, "첫 장면 대사가 없음"

    for banned in HOOK_BANNED_PATTERNS:
        if banned in text:
            return (
                False,
                f"설명조 오프닝 금지 표현: {banned}",
            )

    visible_len = len(
        re.sub(r"\s+", "", text)
    )

    if visible_len < 12:
        return False, "첫 장면 대사가 지나치게 짧음"

    if visible_len > 42:
        return False, "첫 장면 대사가 길어 2~3초 훅으로 부적절함"

    sentence_breaks = re.findall(
        r"[.!?…]+",
        text,
    )

    if len(sentence_breaks) > 1:
        return False, "첫 장면은 한 문장 훅이어야 함"

    return True, "하드 후킹 검사 통과"


def validate_scenes(scenes):

    if not isinstance(scenes, list):
        return False, "scenes가 배열이 아님"

    if len(scenes) < MIN_SCENES:
        return False, f"장면 수 부족: {len(scenes)}"

    if len(scenes) > MAX_SCENES:
        return False, f"장면 수 초과: {len(scenes)}"

    for idx, scene in enumerate(scenes):

        if not isinstance(scene, dict):
            return False, f"{idx + 1}번 장면이 객체가 아님"

        text = str(
            scene.get("text", "")
        ).strip()

        visual_goal = str(
            scene.get("visual_goal", "")
        ).strip()

        keyword = str(
            scene.get("keyword", "")
        ).strip()

        if not text:
            return False, f"{idx + 1}번 장면 대사가 없음"

        if len(visual_goal) < 8:
            return False, (
                f"{idx + 1}번 visual_goal이 없거나 너무 짧음"
            )

        if not keyword:
            return False, f"{idx + 1}번 검색어가 없음"

        if not re.search(
            r"[A-Za-z]",
            keyword,
        ):
            return False, (
                f"{idx + 1}번 검색어가 영어가 아님: {keyword}"
            )

        normalized = " ".join(
            keyword.lower().split()
        )

        words = normalized.split()

        if len(words) < 2 or len(words) > 7:
            return False, (
                f"{idx + 1}번 검색어 토큰 수 부적절: {keyword}"
            )

        if normalized in BAD_VISUAL_KEYWORDS:
            return False, (
                f"{idx + 1}번 검색어가 너무 추상적임: {keyword}"
            )

    return True, "Scene 구조 통과"


def validate_keyword_variety(scenes):

    keywords = [
        " ".join(
            str(
                scene.get("keyword", "")
            ).strip().lower().split()
        )
        for scene in scenes
    ]

    if not keywords:
        return False, "검색어 없음"

    unique_count = len(
        set(keywords)
    )

    required = max(
        6,
        len(keywords) // 2,
    )

    if unique_count < required:
        return False, (
            "검색어 반복이 지나치게 많음: "
            f"{unique_count}/{len(keywords)}"
        )

    return True, "Keyword 다양성 통과"


def validate_script(result):

    if not isinstance(result, dict):
        return False, "AI 결과가 JSON 객체가 아님"

    title = str(
        result.get("title", "")
    ).strip()

    if not title:
        return False, "제목 없음"

    scenes = result.get(
        "scenes",
        [],
    )

    valid, reason = validate_scenes(
        scenes
    )

    if not valid:
        return False, reason

    valid, reason = validate_hook(
        scenes[0]
    )

    if not valid:
        return False, (
            f"후킹 구조 실패: {reason}"
        )

    valid, reason = validate_keyword_variety(
        scenes
    )

    if not valid:
        return False, reason

    return True, "V3.2.1.2 Script 하드 검사 통과"


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

    candidate = validate_candidate(
        candidate
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

    topic = candidate["topic"]
    angle = candidate["angle"]
    core_question = candidate[
        "core_question"
    ]
    micro = candidate[
        "micro_narrative"
    ]

    print("")
    print("=" * 62)
    print("✍️ V3.2.1.2 SCRIPT GENERATOR")
    print("=" * 62)
    print("🧠 확정 소재:", topic)
    print("🎯 핵심 질문:", core_question)

    candidate_context = build_candidate_context(
        candidate
    )

    last_error = None

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1,
    ):

        print("")
        print(
            f"📝 Script 작성 {attempt}/{MAX_SCRIPT_ATTEMPTS}"
        )

        prompt = f"""
너는 YouTube Shorts 전문 Script Writer다.
Candidate Explorer가 이미 소재를 확정했다.
새 소재를 탐색하지 말고 확정 Winner를 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초,
{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.

[CONTENT LOCK]
다음을 바꾸지 마라.
- topic
- angle
- core_question
- 핵심 reveal
- payoff

새로운 원인, 역사적 기원, 숫자, 연구 결과, 숨겨진 목적,
다른 mechanism을 만들어내지 마라.

[CANDIDATE]
{candidate_context}

[CONTEXT]
분야: {category}
탐색 방향: {direction}
소재: {topic}
Angle: {angle}
Core Question: {core_question}

[MICRO NARRATIVE]
HOOK: {micro['hook']}
QUESTION: {micro['core_question']}
REVEAL: {micro['reveal']}
PAYOFF: {micro['payoff']}

[STORY]
Hook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.
첫 장면부터 본론에 들어간다.
"오늘은", "알아보겠습니다", "혹시 알고 계셨나요" 같은 도입은 금지한다.
후반부는 단순 요약이 아니라 처음 질문을 실제 답으로 보상해야 한다.

[QUESTION COVERAGE — REQUIRED]
Hook 또는 Core Question이 비교, 복수 조건, 차이, 원인, 방법을 약속했다면
본문은 그 약속의 핵심 항목을 모두 실제로 설명해야 한다.
한쪽 사례만 설명하고 전체 질문에 답한 것처럼 끝내지 마라.
예: "지형에 따라 왜 달라질까?"라고 물었다면 산악 지형 하나만 설명해서는 안 된다.
Candidate가 허용하는 사실 범위 안에서 대비되는 조건도 설명해 차이가 무엇인지 회수한다.
Candidate 정보만으로 질문 전체를 안전하게 답할 수 없다면 새로운 사실을 지어내지 말고,
질문의 범위를 Candidate가 실제로 답할 수 있는 수준으로 좁혀라.
마지막 Reveal/Payoff 전에 Core Question에 대한 명시적인 답이 존재하는지 스스로 점검한다.

[MECHANISM DEPTH — REQUIRED]
영상의 가장 중요한 주장 1~2개는 단순 사실 나열에서 멈추지 않는다.
가능한 경우 다음 인과 사슬을 대사 안에서 분명하게 연결한다:
현상/사실 → 왜 그런가(원인) → 실제로 어떻게 작동하는가(mechanism) → 그래서 어떤 결과가 생기는가.
"효율적이다", "중요하다", "발달했다", "영향을 준다" 같은 추상 결론만 말하지 마라.
시청자가 "그래서 왜?" 또는 "그래서 어떻게?"를 다시 물어야 이해되는 설명이면 한 단계 더 구체화한다.
단, Candidate에 없는 mechanism이나 검증되지 않은 원인을 새로 만들어내서는 안 된다.

[HOOK FIRST 2~3 SEC]
첫 Scene은 반드시 한 문장으로 만든다.
공백 제외 12~42자 안에서 끝내고 장황한 배경 설명을 넣지 마라.
첫 구절 안에 소재의 구체적인 대상 이름을 바로 말한다.
그 대상의 의외성, 모순, 위험, 숨은 기능 또는 날카로운 질문을 즉시 제시한다.
"이것", "이 기술", "이 시스템"처럼 대상이 무엇인지 늦게 밝혀지는 훅은 금지한다.
첫 Scene의 visual_goal과 keyword도 바로 그 동일한 물리적 대상을 보여줘야 한다.

[FACT]
Candidate에 없는 핵심 사실을 무리하게 추가하지 마라.
검증 대상:
{json.dumps(candidate['fact_check_focus'], ensure_ascii=False)}

[VISUAL V2]
각 Scene에는 text, visual_goal, keyword가 모두 필요하다.

visual_goal:
- 대사를 다시 쓰는 필드가 아니다.
- 그 장면에서 시청자가 실제 화면으로 반드시 봐야 하는 것을 구체적으로 적는다.
- 실제 대상/구조/행동/환경/과정/비교가 보여야 한다.
- "관련 이미지", "과학 장면", "기술 영상" 같은 추상 표현 금지.
- 추상 개념을 말하는 장면도 스마트폰, 주식 차트, 회의, 일반 사람 같은 비유 B-roll로 도망가지 말고 가능하면 핵심 대상 자체를 보여준다.

keyword:
- visual_goal을 Pexels에서 찾기 위한 2~7단어 영어 검색어다.
- 대사를 영어로 번역하지 마라.
- 실제 카메라에 잡힐 수 있는 구체적인 명사와 행동을 사용한다.
- 같은 B-roll 유형을 연속 반복하지 마라.
- 영상 전체에서 topic의 핵심 물리적 대상(subject anchor)이 사라지지 않게 한다.
- 각 keyword에는 가능한 한 그 핵심 대상 또는 직접적인 구조/부품/환경 명사를 포함한다.
- "future", "safety", "training", "data", "business", "smartphone" 같은 주변 개념만 남은 검색어를 만들지 마라.
- 대사와 직접 관련 없는 상징적/비유적 B-roll은 금지한다.

좋은 예:
{{
  "text": "연료 분사량은 계속 실시간으로 조절됩니다.",
  "visual_goal": "자동차 엔진의 연료 분사 장치 또는 인젝터가 실제로 작동하는 클로즈업",
  "keyword": "car fuel injector engine"
}}

나쁜 예:
{{
  "visual_goal": "기술을 보여주는 영상",
  "keyword": "technology future"
}}

Candidate Visual Proof:
{json.dumps(candidate['visual_proof'], ensure_ascii=False, indent=2)}

[LENGTH]
전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다.
너무 짧은 문장을 억지로 Scene 수만 맞추려고 잘게 쪼개지 마라.

[OUTPUT]
JSON 객체 하나만 출력한다.
Markdown, 설명, 코드블록 금지.

{{
  "title": "콘텐츠 제목",
  "scenes": [
    {{
      "text": "한국어 Scene 대사",
      "visual_goal": "이 Scene에서 실제로 보여야 하는 구체적인 화면",
      "keyword": "specific english visual search"
    }}
  ]
}}
"""

        try:
            call_number = authorize_call(
                MODEL
            )

            print(
                "💳 Script API call "
                f"authorized: #{call_number}"
            )

            response = (
                openai
                .chat
                .completions
                .create(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "너는 V3.2.1.2 Shorts Script Writer다. "
                                "Candidate의 사실과 Story Angle을 바꾸지 않고, "
                                "각 Scene에 화면 목표와 구체적 B-roll 검색어를 만든다."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.7,
                    response_format={
                        "type": "json_object",
                    },
                )
            )

            usage = record_usage(
                MODEL,
                response,
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

            generated = extract_json(
                content
            )

            valid, reason = validate_script(
                generated
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
            ][:MAX_SCENES]:

                cleaned_scenes.append({
                    "text": str(
                        scene["text"]
                    ).strip(),
                    "visual_goal": str(
                        scene["visual_goal"]
                    ).strip(),
                    "visual_type": str(
                        scene.get(
                            "visual_type",
                            "real_world_broll",
                        )
                    ).strip()
                    or "real_world_broll",
                    "keyword": " ".join(
                        str(
                            scene["keyword"]
                        ).strip().split()
                    ),
                })

            result = {
                "title": str(
                    generated["title"]
                ).strip(),
                "topic": candidate["topic"],
                "category": category,
                "angle": candidate["angle"],
                "core_question": candidate[
                    "core_question"
                ],
                "micro_narrative": candidate[
                    "micro_narrative"
                ],
                "fact_check_focus": candidate[
                    "fact_check_focus"
                ],
                "visual_proof": candidate[
                    "visual_proof"
                ],
                "candidate_selection_reason": candidate.get(
                    "selection_reason",
                    "",
                ),
                "scenes": cleaned_scenes,
            }

            print("")
            print("=" * 62)
            print("✅ V3.2.1.2 SCRIPT GENERATED")
            print("🧠 소재:", result["topic"])
            print("📝 제목:", result["title"])
            print("🎬 장면:", len(result["scenes"]))
            print("➡️ 다음 단계: 독립 Judge Committee")
            print("=" * 62)

            return result

        except Exception as e:
            last_error = str(e)
            print(
                "⚠️ Script 생성 실패: "
                f"{e}"
            )

    raise RuntimeError(
        "V3.2.1.2 Script Generator가 유효한 대본 생성에 실패했습니다. "
        f"마지막 오류: {last_error}"
    )

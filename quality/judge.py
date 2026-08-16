# quality/judge.py

import json
import re

import openai

from config import OPENAI_KEY


openai.api_key = OPENAI_KEY


# ============================================================
# Judge Base V3
# ============================================================
#
# 책임:
#   - 지정된 전문 영역만 평가
#   - 점수
#   - 근거
#   - confidence
#   - 위험 신호
#
# 절대 하지 않는 것:
#   - 최종 PASS / FAIL 결정
#   - 대본 직접 수정
#   - Validator 규칙 변경
#
# ============================================================


SUPPORTED_JUDGE_TYPES = {
    "hook",
    "novelty",
    "fact",
    "visual",
}


# ============================================================
# JSON 추출
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError(
            "Judge 응답이 비어 있습니다."
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
    )

    text = text.strip()

    try:
        return json.loads(text)

    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        return json.loads(
            text[start:end + 1]
        )

    raise ValueError(
        "Judge 응답에서 JSON을 찾지 못했습니다."
    )


# ============================================================
# Judge 프롬프트
# ============================================================

def build_judge_prompt(
    judge_type,
    script_data,
):

    title = script_data.get(
        "title",
        "",
    )

    topic = script_data.get(
        "topic",
        "",
    )

    scenes = script_data.get(
        "scenes",
        [],
    )

    base = f"""
너는 Shorts V3의 독립 전문 심사위원이다.

중요:

너는 전체 영상을 평가하지 않는다.
오직 지정된 전문 영역만 평가한다.

다른 Judge의 점수나 판단은 알 수 없다.

너는 최종 PASS/FAIL 권한이 없다.

평가 대상:

제목:
{title}

소재:
{topic}

장면:
{json.dumps(
    scenes,
    ensure_ascii=False,
    indent=2
)}

반드시 JSON 하나만 출력한다.

공통 형식:

{{
  "judge_type": "{judge_type}",
  "score": 0,
  "confidence": 0.0,
  "reason": "구체적인 평가 근거",
  "issues": [],
  "critical_risk": false
}}

score:
0~10

confidence:
0.0~1.0

critical_risk:
해당 전문 영역에서 영상 제작 전에 반드시 재검토해야 할
치명적 위험이 있을 때만 true.
"""

    if judge_type == "hook":

        criteria = """
============================================================
HOOK / RETENTION 전담
============================================================

오직 다음만 본다.

1. 첫 장면이 1~3초 안에 관심을 잡는가
2. 설명조로 시작하지 않는가
3. 다음 장면을 보게 만드는 정보 공백이 있는가
4. 질문/위험/의외성/반전이 실제로 작동하는가
5. 억지 자극이나 과장이 아닌가

중후반 내용의 사실성이나 B-roll 품질은 평가하지 마라.

첫 장면이 평범한 장면 설명이라면 점수를 낮게 준다.
"""

    elif judge_type == "novelty":

        criteria = """
============================================================
NOVELTY / TRAFFIC 전담
============================================================

오직 다음만 본다.

1. 일반 대중이 이미 대부분 아는 내용인가
2. 제목만 보고 답을 쉽게 예상할 수 있는가
3. Shorts에서 너무 흔한 소재인가
4. 공유하거나 끝까지 볼 이유가 있는가
5. 소재 자체에 의외성이 있는가

영상 편집이나 사실성은 평가하지 마라.
"""

    elif judge_type == "fact":

        criteria = """
============================================================
FACT / EXAGGERATION 전담
============================================================

오직 다음만 본다.

1. 확인되지 않은 사실을 확정적으로 말하는가
2. 과장된 인과관계가 있는가
3. 근거 없는 숫자/통계/연구가 있는가
4. 복잡한 사실을 지나치게 단순화했는가
5. 제목/후킹이 본문보다 과장됐는가

흥미롭고 재미있는지는 평가하지 마라.

확실히 검증이 필요한 주장이 있으면 critical_risk=true.
"""

    elif judge_type == "visual":

        criteria = """
============================================================
VISUAL / B-ROLL 전담
============================================================

오직 다음만 본다.

1. 각 장면의 keyword가 대사를 실제로 보여줄 수 있는가
2. 단순 단어 매칭에 그치지 않는가
3. 장면끼리 지나치게 랜덤한 장소/톤으로 튀지 않는가
4. 추상적인 원리 설명을 일반 풍경 영상으로 때우고 있지 않은가
5. visual_goal과 keyword가 연결되는가

후킹이나 사실성은 평가하지 마라.
"""

    else:

        raise ValueError(
            f"지원하지 않는 Judge type: {judge_type}"
        )

    return (
        base
        + criteria
    )


# ============================================================
# Judge 응답 검증
# ============================================================

def normalize_judge_result(
    judge_type,
    result,
):

    if not isinstance(
        result,
        dict,
    ):
        raise ValueError(
            "Judge 결과가 dict가 아닙니다."
        )

    try:
        score = float(
            result.get(
                "score",
                0,
            )
        )
    except Exception:
        score = 0.0

    score = max(
        0.0,
        min(
            score,
            10.0,
        )
    )

    try:
        confidence = float(
            result.get(
                "confidence",
                0,
            )
        )
    except Exception:
        confidence = 0.0

    confidence = max(
        0.0,
        min(
            confidence,
            1.0,
        )
    )

    reason = str(
        result.get(
            "reason",
            "",
        )
    ).strip()

    issues = result.get(
        "issues",
        [],
    )

    if not isinstance(
        issues,
        list,
    ):
        issues = [
            str(issues)
        ]

    issues = [
        str(item).strip()
        for item in issues
        if str(item).strip()
    ]

    critical_risk = bool(
        result.get(
            "critical_risk",
            False,
        )
    )

    return {
        "judge_type": judge_type,
        "score": round(
            score,
            2,
        ),
        "confidence": round(
            confidence,
            3,
        ),
        "reason": reason,
        "issues": issues,
        "critical_risk": critical_risk,
    }


# ============================================================
# Judge 실행
# ============================================================

def run_judge(
    judge_type,
    script_data,
    *,
    model="gpt-4o-mini",
):

    if judge_type not in (
        SUPPORTED_JUDGE_TYPES
    ):

        raise ValueError(
            f"지원하지 않는 Judge: "
            f"{judge_type}"
        )

    if not isinstance(
        script_data,
        dict,
    ):

        raise TypeError(
            "script_data는 dict여야 합니다."
        )

    prompt = build_judge_prompt(
        judge_type,
        script_data,
    )

    response = (
        openai
        .chat
        .completions
        .create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 독립적인 Shorts 품질 "
                        "전문 심사위원이다. "
                        "지정된 전문 영역 밖의 판단은 하지 않는다."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )
    )

    content = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    raw_result = extract_json(
        content
    )

    return normalize_judge_result(
        judge_type,
        raw_result,
    )


# ============================================================
# 로그
# ============================================================

def print_judge_result(
    result,
):

    print("")
    print("=" * 50)

    print(
        f"⚖️ JUDGE: "
        f"{result.get('judge_type', '?').upper()}"
    )

    print("=" * 50)

    print(
        f"점수: "
        f"{result.get('score', 0)}/10"
    )

    print(
        f"확신도: "
        f"{result.get('confidence', 0):.3f}"
    )

    print(
        f"Critical risk: "
        f"{result.get('critical_risk', False)}"
    )

    print(
        f"근거: "
        f"{result.get('reason', '')}"
    )

    issues = result.get(
        "issues",
        [],
    )

    if issues:

        print("")
        print(
            "문제:"
        )

        for issue in issues:

            print(
                f" - {issue}"
            )

    print("=" * 50)

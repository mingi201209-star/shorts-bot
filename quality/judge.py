# quality/judge.py

import json
import re

import openai

from config import OPENAI_KEY

from quality.budget_guard import (
    authorize_call,
    record_usage,
    print_budget_status,
)


openai.api_key = OPENAI_KEY


# ============================================================
# Judge Base V3.2
# ============================================================
#
# 책임:
#   - 지정 전문 영역만 평가
#   - score
#   - confidence
#   - issues
#   - critical risk
#
# V3.2:
#   모든 실제 Judge API 호출은
#   Budget Guard를 반드시 통과한다.
#
# 절대 하지 않는 것:
#   - 최종 PASS / FAIL
#   - 대본 수정
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

def extract_json(
    text,
):

    if not text:

        raise ValueError(
            "Judge 응답이 비어 있습니다."
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
    # 그대로 JSON
    # --------------------------------------------------------

    try:

        return json.loads(
            text
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # 객체 영역 추출
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

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except Exception as e:

            raise ValueError(
                "Judge JSON 파싱 실패: "
                f"{e}"
            )

    raise ValueError(
        "Judge 응답에서 JSON을 찾지 못했습니다."
    )


# ============================================================
# Judge Prompt
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

해당 전문 영역에서
영상 제작 전에 반드시 재검토해야 할
치명적 위험이 있을 때만 true.

단순히 조금 아쉬운 점이 있다는 이유로
critical_risk=true를 사용하지 마라.
"""

    # ========================================================
    # Hook Judge
    # ========================================================

    if judge_type == "hook":

        criteria = """
============================================================
HOOK / RETENTION 전담
============================================================

오직 다음만 본다.

1. 첫 장면이 1~3초 안에 관심을 잡는가

2. 단순 장면 설명으로 시작하지 않는가

3. 다음 장면을 보게 만드는
   정보 공백이 있는가

4. 질문 / 위험 / 의외성 / 반전 중
   하나 이상이 실제로 작동하는가

5. 억지 자극이나 사실 왜곡으로
   후킹하지 않는가

중후반 내용의 사실성이나
B-roll 품질은 평가하지 마라.

첫 장면이

"~하는 모습입니다"
"~가 있습니다"
"이것은 ~입니다"

처럼 단순 설명으로 시작한다면
점수를 낮게 평가한다.
"""

    # ========================================================
    # Novelty Judge
    # ========================================================

    elif judge_type == "novelty":

        criteria = """
============================================================
NOVELTY / TRAFFIC 전담
============================================================

오직 다음만 본다.

1. 일반 대중이 이미 대부분 아는 내용인가

2. 제목만 보고 답을 쉽게 예상할 수 있는가

3. Shorts에서 너무 흔하게 소비된 소재인가

4. 사람들이 끝까지 볼 이유가 있는가

5. 공유하거나 다른 사람에게 말하고 싶은
   의외성이 있는가

6. 단순한 상식 전달로 끝나는가

영상 편집이나 사실성은 평가하지 마라.

평범한 상식이라면
문장이 잘 쓰였더라도
높은 점수를 주지 마라.
"""

    # ========================================================
    # Fact Judge
    # ========================================================

    elif judge_type == "fact":

        criteria = """
============================================================
FACT / EXAGGERATION 전담
============================================================

오직 다음만 본다.

1. 확인되지 않은 사실을
   확정적으로 말하는가

2. 실제보다 과장된
   인과관계가 있는가

3. 근거 없는 숫자 / 통계 / 연구 /
   역사적 사실이 있는가

4. 복잡한 사실을 지나치게
   단순화하여 오해를 만들 수 있는가

5. 제목이나 후킹이
   본문보다 과장되어 있는가

6. 사실은 맞더라도
   표현 때문에 다른 의미로
   오해될 가능성이 큰가

흥미롭고 재미있는지는 평가하지 마라.

중요:

단순한 표현 개선 수준은
issues에 기록하고
critical_risk=false로 둔다.

영상 공개 전에 사실 확인이 반드시 필요한
중대한 주장만
critical_risk=true로 판단한다.
"""

    # ========================================================
    # Visual Judge
    # ========================================================

    elif judge_type == "visual":

        criteria = """
============================================================
VISUAL / B-ROLL 전담
============================================================

오직 다음만 본다.

1. 각 장면의 keyword가
   해당 대사를 실제 화면으로
   보여줄 수 있는가

2. 대사의 단어 하나만 뽑은
   단순 키워드 매칭이 아닌가

3. 장면끼리 장소 / 시대 / 색감 /
   분위기가 지나치게 랜덤하게 튀지 않는가

4. 추상적인 과학·공학 원리를
   아무 관련 없는 일반 풍경 영상으로
   대체하려 하고 있지 않은가

5. visual_goal과 keyword가
   직접적으로 연결되는가

6. 실제 스톡 영상 검색에서
   지나치게 추상적인 검색어가 아닌가

후킹이나 사실성은 평가하지 마라.
"""

    else:

        raise ValueError(
            "지원하지 않는 Judge type: "
            f"{judge_type}"
        )

    return (
        base
        + criteria
    )


# ============================================================
# Judge 응답 정규화
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

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

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
        ),
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

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
        ),
    )

    # --------------------------------------------------------
    # Reason
    # --------------------------------------------------------

    reason = str(
        result.get(
            "reason",
            "",
        )
    ).strip()

    # --------------------------------------------------------
    # Issues
    # --------------------------------------------------------

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

        str(
            item
        ).strip()

        for item in issues

        if str(
            item
        ).strip()
    ]

    # --------------------------------------------------------
    # Critical
    # --------------------------------------------------------

    critical_risk = bool(
        result.get(
            "critical_risk",
            False,
        )
    )

    return {

        "judge_type":
            judge_type,

        "score":
            round(
                score,
                2,
            ),

        "confidence":
            round(
                confidence,
                3,
            ),

        "reason":
            reason,

        "issues":
            issues,

        "critical_risk":
            critical_risk,
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

    # ========================================================
    # 입력 검사
    # ========================================================

    if judge_type not in (
        SUPPORTED_JUDGE_TYPES
    ):

        raise ValueError(
            "지원하지 않는 Judge: "
            f"{judge_type}"
        )

    if not isinstance(
        script_data,
        dict,
    ):

        raise TypeError(
            "script_data는 dict여야 합니다."
        )

    # ========================================================
    # Prompt
    # ========================================================

    prompt = build_judge_prompt(
        judge_type,
        script_data,
    )

    # ========================================================
    # V3.2 Budget Guard
    #
    # 모든 실제 Judge API 호출은
    # 반드시 이 지점을 통과해야 한다.
    # ========================================================

    call_number = (
        authorize_call(
            model
        )
    )

    print("")
    print(
        "💳 API Judge call authorized:"
        f" #{call_number}"
    )

    # ========================================================
    # OpenAI API
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

                    "content": (
                        "너는 독립적인 Shorts 품질 "
                        "전문 심사위원이다. "
                        "지정된 전문 영역 밖의 판단은 "
                        "하지 않는다."
                    ),
                },

                {
                    "role":
                        "user",

                    "content":
                        prompt,
                },
            ],

            temperature=0.1,
        )
    )

    # ========================================================
    # 실제 Token / Cost 기록
    # ========================================================

    usage_result = (
        record_usage(
            model,
            response,
        )
    )

    print(
        "💰 This Judge call:"
        f" ${usage_result['cost_usd']:.6f}"
    )

    print(
        "   Input tokens:",
        usage_result[
            "input_tokens"
        ],
    )

    print(
        "   Cached input:",
        usage_result[
            "cached_input_tokens"
        ],
    )

    print(
        "   Output tokens:",
        usage_result[
            "output_tokens"
        ],
    )

    if usage_result.get(
        "over_budget",
        False,
    ):

        print(
            "🚨 실행 비용이 설정된 "
            "Budget을 초과했습니다."
        )

        print(
            "🚫 이후 API 호출은 "
            "Budget Guard가 차단합니다."
        )

    print_budget_status()

    # ========================================================
    # 응답 내용
    # ========================================================

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:

        raise RuntimeError(
            "Judge API 응답 내용이 비어 있습니다."
        )

    content = content.strip()

    # ========================================================
    # JSON
    # ========================================================

    raw_result = (
        extract_json(
            content
        )
    )

    normalized = (
        normalize_judge_result(
            judge_type,
            raw_result,
        )
    )

    return normalized


# ============================================================
# 로그
# ============================================================

def print_judge_result(
    result,
):

    print("")
    print("=" * 50)

    print(
        "⚖️ JUDGE: "
        f"{result.get('judge_type', '?').upper()}"
    )

    print("=" * 50)

    print(
        "점수: "
        f"{result.get('score', 0)}/10"
    )

    print(
        "확신도: "
        f"{result.get('confidence', 0):.3f}"
    )

    print(
        "Critical risk: "
        f"{result.get('critical_risk', False)}"
    )

    print(
        "근거: "
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

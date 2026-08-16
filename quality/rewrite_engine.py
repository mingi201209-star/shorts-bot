# quality/rewrite_engine.py

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


SUPPORTED_DOMAINS = {
    "hook",
    "novelty",
    "fact",
    "visual",
}


def extract_json(text):

    if not text:
        raise ValueError(
            "Rewrite 응답이 비어 있습니다."
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
    ).strip()

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
        "Rewrite 응답에서 JSON을 찾지 못했습니다."
    )


def find_rewrite_domains(
    consensus,
):

    domains = []

    summaries = consensus.get(
        "domain_summaries",
        {},
    )

    for judge_type, summary in (
        summaries.items()
    ):

        score = float(
            summary.get(
                "score",
                0.0,
            )
        )

        confidence = float(
            summary.get(
                "confidence",
                0.0,
            )
        )

        critical = bool(
            summary.get(
                "critical_risk",
                False,
            )
        )

        disagreement = float(
            summary.get(
                "disagreement",
                0.0,
            )
        )

        if (
            critical
            or score < 7.5
            or confidence < 0.65
            or disagreement >= 2.0
        ):

            if (
                judge_type
                in SUPPORTED_DOMAINS
            ):

                domains.append(
                    judge_type
                )

    return list(
        dict.fromkeys(
            domains
        )
    )


def collect_domain_issues(
    consensus,
    domains,
):

    result = {}

    summaries = consensus.get(
        "domain_summaries",
        {},
    )

    for domain in domains:

        summary = summaries.get(
            domain,
            {},
        )

        result[domain] = {
            "score":
                summary.get(
                    "score",
                    0,
                ),

            "confidence":
                summary.get(
                    "confidence",
                    0,
                ),

            "critical_risk":
                summary.get(
                    "critical_risk",
                    False,
                ),

            "issues":
                summary.get(
                    "issues",
                    [],
                ),
        }

    return result


def build_rewrite_prompt(
    script_data,
    consensus,
    domains,
):

    issues = (
        collect_domain_issues(
            consensus,
            domains,
        )
    )

    domain_rules = []

    if "hook" in domains:

        domain_rules.append("""
[HOOK 수정]
- 첫 1~3초의 대사만 우선 개선한다.
- 설명형 오프닝 금지.
- 질문, 위험, 반전, 정보 공백 중 하나를 강화한다.
- 본문 핵심 사실을 왜곡하지 않는다.
""")

    if "novelty" in domains:

        domain_rules.append("""
[NOVELTY 수정]
- 소재 자체가 너무 평범하면 더 구체적이고 의외적인 각도로 좁힌다.
- 단순히 자극적인 제목으로 포장하지 않는다.
- 필요하다면 title/topic과 관련 장면 일부만 수정한다.
""")

    if "fact" in domains:

        domain_rules.append("""
[FACT 수정]
- 근거 불명확한 숫자, 단정, 과장 표현을 제거한다.
- 불확실한 사실은 확정적으로 쓰지 않는다.
- 핵심 재미를 유지하되 정확성을 우선한다.
""")

    if "visual" in domains:

        domain_rules.append("""
[VISUAL 수정]
- 대사는 가급적 유지한다.
- visual_goal / visual_type / keyword를 우선 수정한다.
- keyword는 실제 화면에서 보여줄 수 있는 2~5단어 영어 검색어로 만든다.
- 단순 단어 매칭을 피한다.
""")

    return f"""
너는 Shorts V3의 선택적 Rewrite Engine이다.

전체 대본을 새로 만들지 마라.

정상인 부분은 최대한 보존하고,
지정된 문제 영역만 수정한다.

수정 대상:
{json.dumps(
    domains,
    ensure_ascii=False
)}

문제:
{json.dumps(
    issues,
    ensure_ascii=False,
    indent=2
)}

현재 대본:
{json.dumps(
    script_data,
    ensure_ascii=False,
    indent=2
)}

{chr(10).join(domain_rules)}

절대 규칙:
- scenes 개수는 가능하면 유지한다.
- 정상 scene을 불필요하게 바꾸지 않는다.
- 사실을 새로 만들어내지 않는다.
- keyword는 영어.
- 기존 JSON 구조 유지.

수정된 전체 JSON 객체만 출력한다.
"""


def rewrite_script(
    script_data,
    consensus,
    *,
    model="gpt-4o-mini",
):

    if not isinstance(
        script_data,
        dict,
    ):

        raise TypeError(
            "script_data는 dict여야 합니다."
        )

    domains = (
        find_rewrite_domains(
            consensus
        )
    )

    if not domains:

        return {
            "changed": False,
            "domains": [],
            "script_data":
                script_data,
        }

    prompt = (
        build_rewrite_prompt(
            script_data,
            consensus,
            domains,
        )
    )

    call_number = (
        authorize_call(
            model
        )
    )

    print(
        f"💳 Rewrite API call "
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

                    "content": (
                        "너는 부분 수정 전용 "
                        "Shorts Rewrite Engine이다. "
                        "정상 부분은 보존하고 "
                        "문제 영역만 수정한다."
                    ),
                },
                {
                    "role":
                        "user",

                    "content":
                        prompt,
                },
            ],

            temperature=0.4,
        )
    )

    usage = record_usage(
        model,
        response,
    )

    print(
        "💰 Rewrite call:"
        f" ${usage['cost_usd']:.6f}"
    )

    print_budget_status()

    content = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    rewritten = extract_json(
        content
    )

    if not isinstance(
        rewritten,
        dict,
    ):

        raise ValueError(
            "Rewrite 결과가 dict가 아닙니다."
        )

    return {
        "changed": True,
        "domains": domains,
        "script_data":
            rewritten,
    }


def print_rewrite_result(
    result,
):

    print("")
    print("=" * 54)
    print("🔧 V3.2 REWRITE ENGINE")
    print("=" * 54)

    if not result.get(
        "changed"
    ):

        print(
            "수정 대상 없음"
        )

        print("=" * 54)
        return

    print(
        "수정 영역:",
        ", ".join(
            result.get(
                "domains",
                [],
            )
        ),
    )

    print(
        "✅ 선택적 Rewrite 완료"
    )

    print("=" * 54)

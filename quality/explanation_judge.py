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


def extract_json(text):
    if not text:
        raise ValueError("Explanation Judge 응답이 비어 있습니다.")

    text = str(text).strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])

    raise ValueError("Explanation Judge 응답에서 JSON을 찾지 못했습니다.")


def build_prompt(script_data):
    title = str(script_data.get("title", "")).strip()
    topic = str(script_data.get("topic", "")).strip()
    core_question = str(script_data.get("core_question", "")).strip()
    micro_narrative = script_data.get("micro_narrative", {})
    scenes = script_data.get("scenes", [])

    return f"""
너는 Shorts V3의 EXPLANATION / QUESTION COVERAGE 전문 심사위원이다.
다른 영역은 평가하지 말고, 대본이 스스로 약속한 질문을 실제로 설명하고 회수하는지만 평가한다.

제목:
{title}

소재:
{topic}

Core Question:
{core_question}

Micro Narrative:
{json.dumps(micro_narrative, ensure_ascii=False, indent=2)}

장면:
{json.dumps(scenes, ensure_ascii=False, indent=2)}

============================================================
평가 기준
============================================================

1. QUESTION COVERAGE
- 제목, 첫 훅, Core Question이 비교/복수 조건/차이/원인/방법을 약속했다면 본문이 그 약속의 핵심 항목을 실제로 다루는가.
- 넓은 질문을 던지고 한 사례만 설명한 뒤 전체 답처럼 끝내면 큰 감점.
- 예: '지형에 따라 왜 달라질까?'라고 해놓고 산악 지형 하나만 설명하면 불완전하다.
- Candidate가 허용하는 범위가 좁다면 질문 자체도 그 범위에 맞게 좁혀져 있어야 한다.

2. MECHANISM COMPLETENESS
- 영상의 핵심 주장 1~2개가 단순 사실 나열이나 추상 결론으로 끝나지 않는가.
- 필요한 경우 '현상/사실 → 원인 → 어떻게 작동하는가 → 결과'의 핵심 연결고리가 이해 가능하게 이어지는가.
- 시청자가 핵심 주장 뒤에 다시 '그래서 왜?' 또는 '그래서 어떻게?'를 물어야만 이해된다면 감점한다.
- 모든 문장에 기계적으로 4단계를 요구하지 말고, 영상의 핵심 원리를 이해하는 데 필요한 연결만 평가한다.

3. ANSWER PAYOFF
- 후반부 Reveal/Payoff 전에 Core Question에 대한 명시적인 답이 존재하는가.
- 결론이 단순 반복/요약이 아니라 초반 질문에 대한 정보 보상을 주는가.

4. 범위 제한
- 사실이 맞는지 자체는 Fact Judge의 영역이다.
- 훅의 자극성은 Hook Judge의 영역이다.
- B-roll은 Visual Judge의 영역이다.
- 새로운 사실을 요구하지 말고 현재 Candidate/대본 범위 안에서 설명 완성도만 평가한다.

점수 가이드:
9~10: 질문을 완전히 회수하고 핵심 원리가 명확하다.
7~8: 대체로 완전하지만 한 연결이 조금 압축되어 있다.
5~6: 질문 일부만 답하거나 핵심 mechanism이 얕다. Rewrite 권장.
0~4: 질문과 답이 크게 불일치하거나 핵심 원리 설명이 사실상 없다.

critical_risk는 다음 경우에만 true:
- 훅/Core Question의 핵심 약속을 본문이 명백히 회수하지 못함.
- 핵심 원리 설명이 빠져 영상의 중심 질문에 답하지 못함.
단순히 더 자세히 설명할 수 있다는 이유만으로 true로 두지 마라.

반드시 JSON 객체 하나만 출력한다.
{{
  "judge_type": "explanation",
  "score": 0,
  "confidence": 0.0,
  "reason": "구체적인 평가 근거",
  "issues": [],
  "critical_risk": false
}}
"""


def normalize_result(result):
    if not isinstance(result, dict):
        raise ValueError("Explanation Judge 결과가 dict가 아닙니다.")

    try:
        score = float(result.get("score", 0.0))
    except Exception:
        score = 0.0
    score = max(0.0, min(score, 10.0))

    try:
        confidence = float(result.get("confidence", 0.0))
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))

    issues = result.get("issues", [])
    if not isinstance(issues, list):
        issues = [str(issues)]

    return {
        "judge_type": "explanation",
        "score": round(score, 2),
        "confidence": round(confidence, 3),
        "reason": str(result.get("reason", "")).strip(),
        "issues": [str(item).strip() for item in issues if str(item).strip()],
        "critical_risk": bool(result.get("critical_risk", False)),
    }


def run_explanation_judge(script_data, *, model="gpt-4o-mini"):
    if not isinstance(script_data, dict):
        raise TypeError("script_data는 dict여야 합니다.")

    prompt = build_prompt(script_data)
    call_number = authorize_call(model)
    print(f"💳 Explanation Judge call authorized: #{call_number}")

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
                        "너는 Shorts의 질문 회수와 설명 완성도만 평가하는 독립 심사위원이다. "
                        "새 사실을 만들거나 사실성 자체를 판정하지 않는다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    )

    usage = record_usage(model, response)
    print(f"💰 Explanation Judge call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content
    return normalize_result(extract_json(content))


def print_explanation_result(result):
    print("")
    print("=" * 50)
    print("⚖️ JUDGE: EXPLANATION")
    print("=" * 50)
    print(f"점수: {result.get('score', 0)}/10")
    print(f"확신도: {result.get('confidence', 0):.3f}")
    print(f"Critical risk: {result.get('critical_risk', False)}")
    print(f"근거: {result.get('reason', '')}")
    issues = result.get("issues", [])
    if issues:
        print("문제:")
        for issue in issues:
            print(f" - {issue}")
    print("=" * 50)

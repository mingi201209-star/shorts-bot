# quality/rewrite_engine.py

import copy
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

IMMUTABLE_CANDIDATE_FIELDS = (
    "topic",
    "category",
    "angle",
    "core_question",
    "micro_narrative",
    "fact_check_focus",
    "visual_proof",
    "candidate_selection_reason",
)

FACT_REWRITE_MAX_ATTEMPTS = 2

FACT_TOKEN_STOPWORDS = {
    "근거", "부족", "표현", "주장", "가능성", "오해",
    "구체적인", "역사적", "관련", "일부", "대한", "대해",
    "사람들", "방법", "실제로", "과장", "단순화",
    "있음", "없음", "수", "있다", "없다",
}

KOREAN_SUFFIXES = (
    "이라고", "라는", "다는", "다고", "라고",
    "에서", "으로", "에게", "한테",
    "은", "는", "이", "가", "을", "를",
    "의", "에", "로", "와", "과", "도", "만",
    "고", "며",
)


def extract_json(text):
    if not text:
        raise ValueError("Rewrite 응답이 비어 있습니다.")

    text = str(text).strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])

    raise ValueError("Rewrite 응답에서 JSON을 찾지 못했습니다.")


def find_rewrite_domains(consensus):
    domains = []
    summaries = consensus.get("domain_summaries", {})

    for judge_type, summary in summaries.items():
        score = float(summary.get("score", 0.0))
        confidence = float(summary.get("confidence", 0.0))
        critical = bool(summary.get("critical_risk", False))
        disagreement = float(summary.get("disagreement", 0.0))

        if (
            critical
            or score < 7.5
            or confidence < 0.65
            or disagreement >= 2.0
        ):
            if judge_type in SUPPORTED_DOMAINS:
                domains.append(judge_type)

    return list(dict.fromkeys(domains))


def collect_domain_issues(consensus, domains):
    result = {}
    summaries = consensus.get("domain_summaries", {})

    for domain in domains:
        summary = summaries.get(domain, {})
        result[domain] = {
            "score": summary.get("score", 0),
            "confidence": summary.get("confidence", 0),
            "critical_risk": summary.get("critical_risk", False),
            "issues": summary.get("issues", []),
        }

    return result


def _normalize_fact_token(token):
    token = str(token or "").strip().lower()
    token = re.sub(r"[^0-9a-z가-힣]", "", token)

    if len(token) <= 1:
        return ""

    changed = True
    while changed:
        changed = False
        for suffix in KOREAN_SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                token = token[:-len(suffix)]
                changed = True
                break

    return token


def _fact_tokens(text):
    raw = re.findall(r"[0-9A-Za-z가-힣]+", str(text or ""))
    result = set()

    for token in raw:
        normalized = _normalize_fact_token(token)
        if not normalized:
            continue
        if normalized in FACT_TOKEN_STOPWORDS:
            continue
        result.add(normalized)

    return result


def _fact_issue_list(consensus):
    fact = (
        consensus
        .get("domain_summaries", {})
        .get("fact", {})
    )

    issues = fact.get("issues", [])
    if not isinstance(issues, list):
        return []

    return [
        str(item).strip()
        for item in issues
        if str(item).strip()
    ]


def _scene_texts(script_data):
    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list):
        return []

    return [
        str(scene.get("text", "")).strip()
        for scene in scenes
        if isinstance(scene, dict)
        and str(scene.get("text", "")).strip()
    ]


def find_persistent_fact_issues(consensus, rewritten_script):
    """
    Fact Judge가 구체적으로 지적한 주장/표현이 Rewrite 뒤에도
    거의 같은 핵심어로 남아 있는지 가볍게 확인한다.

    이 검사는 사실 판정기가 아니라 재작성 힌트를 만드는 보조 guard다.
    최종 판정은 Rewrite 후 다시 실행되는 Fact Judge가 맡는다.
    """
    issues = _fact_issue_list(consensus)
    if not issues:
        return []

    scene_tokens = [
        _fact_tokens(text)
        for text in _scene_texts(rewritten_script)
    ]

    persistent = []

    for issue in issues:
        issue_tokens = _fact_tokens(issue)

        if len(issue_tokens) < 2:
            continue

        matched = False

        for tokens in scene_tokens:
            overlap = issue_tokens & tokens

            if len(overlap) >= 2:
                matched = True
                break

            if any(
                len(token) >= 5 and token in tokens
                for token in issue_tokens
            ):
                matched = True
                break

        if matched:
            persistent.append(issue)

    return persistent


def build_rewrite_prompt(
    script_data,
    consensus,
    domains,
    *,
    retry_fact_issues=None,
):
    issues = collect_domain_issues(
        consensus,
        domains,
    )

    domain_rules = []

    if "hook" in domains:
        domain_rules.append("""
[HOOK 수정]

- 첫 1~3초 표현을 우선 개선한다.
- 설명형 오프닝을 피한다.
- 정보 공백과 구체성을 강화한다.
- Candidate의 핵심 질문이나 사실은 바꾸지 않는다.
""")

    if "novelty" in domains:
        domain_rules.append("""
[NOVELTY 수정]

중요:
- 새 소재를 탐색하지 마라.
- 새 Story Angle을 만들지 마라.
- topic / angle / core_question / micro_narrative는 변경할 수 없다.

허용:
- 같은 Story Angle 안에서 예상 밖 요소를 더 일찍 공개
- Reveal 순서 개선
- 평범한 설명 문장 축소
- 구체적 표현 강화
- title / scene text 개선

Candidate 자체가 평범하다면 새 topic을 만들어 억지로 살리지 마라.
""")

    if "fact" in domains:
        domain_rules.append("""
[FACT 수정]

- Judge issues를 항목별로 실제 scene text에서 해결한다.
- '근거 부족', '일반화', '확정적 표현'이 지적된 문장은 그대로 두지 않는다.
- 근거가 불명확한 구체적 사례/숫자/행동은 문장 전체를 삭제하거나,
  Candidate가 이미 보장하는 더 일반적이고 검증 가능한 표현으로 교체한다.
- 단순히 '~라고 알려져 있습니다'를 붙여서 위험한 주장을 보존하지 않는다.
- 과도한 단정을 완화하고 인과관계를 과장하지 않는다.
- 사실을 새로 만들어내지 않는다.
- Candidate 소재와 Core Question은 유지한다.
""")

    if "visual" in domains:
        domain_rules.append("""
[VISUAL 수정]

- 대사는 가급적 유지한다.
- visual_goal / visual_type / keyword를 우선 수정한다.
- keyword는 실제 화면에서 보여줄 수 있는 2~5단어 영어 검색어를 사용한다.
- 단순 단어 매칭을 피한다.
""")

    retry_block = ""

    if retry_fact_issues:
        retry_block = f"""
============================================================
FACT REWRITE RETRY
============================================================

직전 Rewrite에도 아래 Fact Judge 지적의 핵심 표현이 남아 있었다.

{json.dumps(
    retry_fact_issues,
    ensure_ascii=False,
    indent=2,
)}

이번에는 해당 주장을 그대로 보존하지 마라.
근거 부족 사례라면 삭제하고,
일반화/단정 문제라면 의미가 실제로 바뀌도록 재작성한다.
표면적인 어미 변경만 하지 마라.
"""

    return f"""
너는 Shorts V3의 선택적 Rewrite Engine이다.

전체 콘텐츠를 새로 기획하지 마라.
Candidate Explorer가 결정한 '무엇을 이야기할 것인가'는 이미 확정되었다.
너의 역할은 '그 후보를 어떻게 더 잘 표현할 것인가'이다.

============================================================
IMMUTABLE CANDIDATE CONTRACT
============================================================

다음 값은 절대 수정하지 마라.
- topic
- category
- angle
- core_question
- micro_narrative
- fact_check_focus
- visual_proof
- candidate_selection_reason

특히 Novelty 문제를 해결하려고 새 topic이나 새 angle을 만들면 안 된다.

============================================================
수정 대상
============================================================

{json.dumps(domains, ensure_ascii=False)}

============================================================
Judge 문제
============================================================

{json.dumps(
    issues,
    ensure_ascii=False,
    indent=2,
)}

============================================================
현재 Script
============================================================

{json.dumps(
    script_data,
    ensure_ascii=False,
    indent=2,
)}

============================================================
Domain Rules
============================================================

{chr(10).join(domain_rules)}

{retry_block}

============================================================
ABSOLUTE RULES
============================================================

- 정상 영역은 최대한 보존한다.
- scenes 개수는 가능하면 유지한다.
- 사실을 새로 만들어내지 않는다.
- keyword는 영어.
- 기존 JSON 구조를 유지한다.
- Candidate metadata를 재작성하지 않는다.
- Fact Judge가 근거 부족이라고 지적한 구체적 주장을 그대로 남기지 않는다.

수정된 전체 JSON 객체만 출력한다.
"""


def restore_candidate_contract(
    original_script,
    rewritten_script,
):
    for field in IMMUTABLE_CANDIDATE_FIELDS:
        if field in original_script:
            rewritten_script[field] = copy.deepcopy(
                original_script[field]
            )
        else:
            rewritten_script.pop(field, None)

    return rewritten_script


def _run_rewrite_call(
    script_data,
    consensus,
    domains,
    *,
    model,
    retry_fact_issues=None,
):
    prompt = build_rewrite_prompt(
        script_data,
        consensus,
        domains,
        retry_fact_issues=retry_fact_issues,
    )

    call_number = authorize_call(model)
    print(
        "💳 Rewrite API call "
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
                    "role": "system",
                    "content": (
                        "너는 부분 수정 전용 Shorts Rewrite Engine이다. "
                        "Candidate Explorer가 결정한 소재와 Story Angle은 "
                        "절대로 변경하지 않는다. "
                        "Fact Judge가 근거 부족이라고 지적한 주장은 "
                        "표면적으로만 고치지 말고 실제로 제거하거나 완화한다."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,
            response_format={
                "type": "json_object",
            },
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

    rewritten = extract_json(content)

    if not isinstance(rewritten, dict):
        raise ValueError(
            "Rewrite 결과가 dict가 아닙니다."
        )

    return restore_candidate_contract(
        script_data,
        rewritten,
    )


def rewrite_script(
    script_data,
    consensus,
    *,
    model="gpt-4o-mini",
):
    if not isinstance(script_data, dict):
        raise TypeError(
            "script_data는 dict여야 합니다."
        )

    domains = find_rewrite_domains(consensus)

    if not domains:
        return {
            "changed": False,
            "domains": [],
            "script_data": script_data,
        }

    fact_guard_enabled = (
        "fact" in domains
        and bool(_fact_issue_list(consensus))
    )

    max_attempts = (
        FACT_REWRITE_MAX_ATTEMPTS
        if fact_guard_enabled
        else 1
    )

    retry_fact_issues = None
    rewritten = None

    for attempt in range(1, max_attempts + 1):
        if fact_guard_enabled:
            print(
                "🧪 Fact Rewrite Guard "
                f"{attempt}/{max_attempts}"
            )

        rewritten = _run_rewrite_call(
            script_data,
            consensus,
            domains,
            model=model,
            retry_fact_issues=retry_fact_issues,
        )

        if not fact_guard_enabled:
            break

        persistent = find_persistent_fact_issues(
            consensus,
            rewritten,
        )

        if not persistent:
            print(
                "✅ Fact Rewrite Guard 통과: "
                "지적된 핵심 표현이 Rewrite 후 제거/변경됨"
            )
            break

        print(
            "🚫 Fact Rewrite Guard: "
            "지적된 표현과 핵심어가 아직 겹칩니다."
        )
        for issue in persistent:
            print(f" - {issue}")

        retry_fact_issues = persistent

        if attempt >= max_attempts:
            print(
                "⚠️ Fact Rewrite Guard 보조 검사가 여전히 겹침을 감지했습니다. "
                "토큰 겹침만으로 실패시키지 않고, 기존 post-rewrite Fact Judge가 "
                "수정된 문장의 실제 사실성을 다시 판정합니다."
            )
            break

    return {
        "changed": True,
        "domains": domains,
        "script_data": rewritten,
    }


def print_rewrite_result(result):
    print("")
    print("=" * 54)
    print("🔧 V3.2 REWRITE ENGINE")
    print("=" * 54)

    if not result.get("changed"):
        print("수정 대상 없음")
        print("=" * 54)
        return

    print(
        "수정 영역:",
        ", ".join(
            result.get("domains", [])
        ),
    )
    print("🔒 Candidate Contract 유지")
    print("✅ 선택적 Rewrite 완료")
    print("=" * 54)

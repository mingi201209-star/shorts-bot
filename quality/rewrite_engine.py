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
    "explanation",
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
    if start != -1 and end > start:
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
        ) and judge_type in SUPPORTED_DOMAINS:
            domains.append(judge_type)
    return list(dict.fromkeys(domains))


def collect_domain_issues(consensus, domains):
    summaries = consensus.get("domain_summaries", {})
    return {
        domain: {
            "score": summaries.get(domain, {}).get("score", 0),
            "confidence": summaries.get(domain, {}).get("confidence", 0),
            "critical_risk": summaries.get(domain, {}).get("critical_risk", False),
            "issues": summaries.get(domain, {}).get("issues", []),
        }
        for domain in domains
    }


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
        if normalized and normalized not in FACT_TOKEN_STOPWORDS:
            result.add(normalized)
    return result


def _fact_issue_list(consensus):
    issues = (
        consensus.get("domain_summaries", {})
        .get("fact", {})
        .get("issues", [])
    )
    if not isinstance(issues, list):
        return []
    return [str(item).strip() for item in issues if str(item).strip()]


def _scene_texts(script_data):
    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list):
        return []
    return [
        str(scene.get("text", "")).strip()
        for scene in scenes
        if isinstance(scene, dict) and str(scene.get("text", "")).strip()
    ]


def find_persistent_fact_issues(consensus, rewritten_script):
    issues = _fact_issue_list(consensus)
    if not issues:
        return []
    scene_tokens = [_fact_tokens(text) for text in _scene_texts(rewritten_script)]
    persistent = []
    for issue in issues:
        issue_tokens = _fact_tokens(issue)
        if len(issue_tokens) < 2:
            continue
        for tokens in scene_tokens:
            overlap = issue_tokens & tokens
            if len(overlap) >= 2 or any(
                len(token) >= 5 and token in tokens
                for token in issue_tokens
            ):
                persistent.append(issue)
                break
    return persistent


def build_rewrite_prompt(
    script_data,
    consensus,
    domains,
    *,
    retry_fact_issues=None,
):
    issues = collect_domain_issues(consensus, domains)
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
- 새 소재나 새 Story Angle을 만들지 마라.
- 같은 Angle 안에서 예상 밖 요소를 더 일찍 공개하고 평범한 설명을 줄인다.
- topic / angle / core_question / micro_narrative는 변경하지 않는다.
""")

    if "fact" in domains:
        domain_rules.append("""
[FACT 수정]
- Judge issues를 실제 scene text에서 해결한다.
- 근거 부족, 일반화, 확정적 표현이 지적된 문장을 그대로 두지 않는다.
- 불명확한 구체적 사례/숫자는 삭제하거나 Candidate가 보장하는 표현으로 교체한다.
- 사실을 새로 만들지 않는다.
""")

    if "visual" in domains:
        domain_rules.append("""
[VISUAL 수정]
- 대사는 가급적 유지한다.
- visual_goal / visual_type / keyword를 우선 수정한다.
- keyword는 실제 화면에서 찾을 수 있는 구체적인 영어 검색어로 만든다.
""")

    if "explanation" in domains:
        domain_rules.append("""
[EXPLANATION 수정]
- Explanation Judge issues를 scene text에서 직접 해결한다.
- 훅/Core Question이 비교, 복수 조건, 차이, 원인, 방법을 약속했다면 그 약속을 본문에서 실제로 회수한다.
- 한 사례만 설명하고 더 넓은 질문 전체에 답한 것처럼 끝내지 않는다.
- 핵심 주장 1~2개는 필요한 범위에서 '현상/사실 → 원인 → 작동 원리 → 결과'가 이해되도록 연결한다.
- 시청자가 핵심 설명 뒤에 다시 '왜?' 또는 '어떻게?'를 물어야 하는 빈칸을 메운다.
- 후반 Reveal/Payoff 전에 Core Question에 대한 명시적인 답을 넣는다.
- Candidate에 없는 사실이나 mechanism을 새로 만들지 않는다.
- Candidate 범위만으로 넓은 질문에 답할 수 없다면 core_question metadata는 바꾸지 말고, scene text의 약속 표현을 과장하지 않게 좁혀 Candidate와 모순되지 않도록 한다.
""")

    retry_block = ""
    if retry_fact_issues:
        retry_block = f"""
============================================================
FACT REWRITE RETRY
============================================================
직전 Rewrite에도 아래 Fact Judge 지적의 핵심 표현이 남아 있었다.
{json.dumps(retry_fact_issues, ensure_ascii=False, indent=2)}
이번에는 해당 주장을 그대로 보존하지 마라.
"""

    return f"""
너는 Shorts V3의 선택적 Rewrite Engine이다.
전체 콘텐츠를 새로 기획하지 마라.
Candidate Explorer가 결정한 소재와 Story Angle은 확정되어 있다.

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

============================================================
수정 대상
============================================================
{json.dumps(domains, ensure_ascii=False)}

============================================================
Judge 문제
============================================================
{json.dumps(issues, ensure_ascii=False, indent=2)}

============================================================
현재 Script
============================================================
{json.dumps(script_data, ensure_ascii=False, indent=2)}

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
- Fact Judge가 근거 부족이라고 지적한 주장을 그대로 남기지 않는다.
- Explanation 문제를 고치기 위해 검증되지 않은 새 원인을 발명하지 않는다.

수정된 전체 JSON 객체만 출력한다.
"""


def restore_candidate_contract(original_script, rewritten_script):
    for field in IMMUTABLE_CANDIDATE_FIELDS:
        if field in original_script:
            rewritten_script[field] = copy.deepcopy(original_script[field])
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
    print(f"💳 Rewrite API call authorized: #{call_number}")

    response = (
        openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 부분 수정 전용 Shorts Rewrite Engine이다. "
                        "Candidate의 소재와 Story Angle은 변경하지 않는다. "
                        "Fact 문제는 실제로 제거/완화하고 Explanation 문제는 질문 회수와 원리 연결을 실제 대사에서 보강한다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    )

    usage = record_usage(model, response)
    print(f"💰 Rewrite call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    content = response.choices[0].message.content.strip()
    rewritten = extract_json(content)
    if not isinstance(rewritten, dict):
        raise ValueError("Rewrite 결과가 dict가 아닙니다.")
    return restore_candidate_contract(script_data, rewritten)


def rewrite_script(
    script_data,
    consensus,
    *,
    model="gpt-4o-mini",
):
    if not isinstance(script_data, dict):
        raise TypeError("script_data는 dict여야 합니다.")

    domains = find_rewrite_domains(consensus)
    if not domains:
        return {
            "changed": False,
            "domains": [],
            "script_data": script_data,
        }

    fact_guard_enabled = "fact" in domains and bool(_fact_issue_list(consensus))
    max_attempts = FACT_REWRITE_MAX_ATTEMPTS if fact_guard_enabled else 1
    retry_fact_issues = None
    rewritten = None

    for attempt in range(1, max_attempts + 1):
        if fact_guard_enabled:
            print(f"🧪 Fact Rewrite Guard {attempt}/{max_attempts}")

        rewritten = _run_rewrite_call(
            script_data,
            consensus,
            domains,
            model=model,
            retry_fact_issues=retry_fact_issues,
        )

        if not fact_guard_enabled:
            break

        persistent = find_persistent_fact_issues(consensus, rewritten)
        if not persistent:
            print("✅ Fact Rewrite Guard 통과: 지적된 핵심 표현이 Rewrite 후 제거/변경됨")
            break

        print("🚫 Fact Rewrite Guard: 지적된 표현과 핵심어가 아직 겹칩니다.")
        for issue in persistent:
            print(f" - {issue}")
        retry_fact_issues = persistent

        if attempt >= max_attempts:
            print(
                "⚠️ Fact Rewrite Guard 보조 검사가 여전히 겹침을 감지했습니다. "
                "기존 post-rewrite Fact Judge가 실제 사실성을 다시 판정합니다."
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
    print("수정 영역:", ", ".join(result.get("domains", [])))
    print("🔒 Candidate Contract 유지")
    print("✅ 선택적 Rewrite 완료")
    print("=" * 54)

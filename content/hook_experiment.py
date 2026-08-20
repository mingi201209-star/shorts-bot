import json
import os
import re

import openai

from config import OPENAI_KEY
from quality.budget_guard import (
    authorize_call,
    record_usage,
    print_budget_status,
)


MODEL = os.environ.get(
    "V3_HOOK_MODEL",
    os.environ.get("V3_SCRIPT_MODEL", "gpt-4o-mini"),
)
HOOK_CANDIDATE_COUNT = max(
    5,
    int(os.environ.get("HOOK_CANDIDATE_COUNT", "5")),
)
HOOK_MAX_REGENERATIONS = max(
    0,
    int(os.environ.get("HOOK_MAX_REGENERATIONS", "1")),
)
HOOK_MIN_SCORE = float(os.environ.get("HOOK_MIN_SCORE", "7.2"))
HOOK_MIN_CHARS = 12
HOOK_MAX_CHARS = 16

HOOK_CRITERIA = (
    "stop_power",
    "curiosity_gap",
    "clarity",
    "specificity",
    "visual_potential",
    "fact_safety",
)

HOOK_WEIGHTS = {
    "stop_power": 1.25,
    "curiosity_gap": 1.10,
    "clarity": 1.00,
    "specificity": 1.05,
    "visual_potential": 1.15,
    "fact_safety": 1.30,
}

HOOK_CRITERIA_FLOORS = {
    "clarity": 7.0,
    "specificity": 7.0,
    "visual_potential": 8.0,
    "fact_safety": 8.0,
}

INTRODUCTORY_HOOK_PATTERNS = (
    r"알려\s*드(?:려요|립니다)",
    r"알아\s*(?:봅니다|볼게요|보겠습니다)",
    r"보여\s*드(?:려요|립니다)",
    r"소개\s*(?:합니다|할게요|해\s*드려요)",
)

# 검색 결과만 보고는 화면에서 직접 확인하기 어려운 속성이다.
# 이런 단어 자체를 금지하는 것이 아니라, Hook 화면 검색어가 이것에만
# 의존하지 않도록 한다. observable consequence/action 토큰이 함께 있어야 한다.
INVISIBLE_VISUAL_TERMS = {
    "south", "north", "east", "west", "facing", "direction",
    "efficient", "efficiency", "safe", "safety", "important",
}
OBSERVABLE_VISUAL_TERMS = {
    "sunlight", "light", "shadow", "heat", "rain", "snow", "water",
    "moving", "flowing", "opening", "closing", "rotating", "burning",
    "crack", "bending", "falling", "rising", "window", "road", "stone",
    "bridge", "wing", "feather", "engine", "wheel", "door", "roof",
}


if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


def hook_experiment_enabled():
    return str(
        os.environ.get("ENABLE_HOOK_EXPERIMENT", "0")
    ).strip().lower() in {"1", "true", "yes", "on"}


def _extract_json(text):
    text = str(text or "").strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        result = json.loads(text[start:end + 1])
        if isinstance(result, dict):
            return result

    raise ValueError("Hook Selector 응답에서 JSON 객체를 찾지 못했습니다.")


def _visible_len(text):
    return len(re.sub(r"\s+", "", str(text or "")))


def _keyword_words(keyword):
    return {
        word
        for word in re.findall(r"[a-z0-9]+", str(keyword or "").lower())
        if word
    }


def _is_introductory_hook(text):
    compact = str(text or "").strip()
    return any(
        re.search(pattern, compact)
        for pattern in INTRODUCTORY_HOOK_PATTERNS
    )


def _valid_hook_shape(text, keyword):
    visible_len = _visible_len(text)
    if visible_len < HOOK_MIN_CHARS or visible_len > HOOK_MAX_CHARS:
        return False

    if len(re.findall(r"[.!?…]+", text)) > 1:
        return False

    if _is_introductory_hook(text):
        return False

    words = keyword.split()
    if len(words) < 2 or len(words) > 7:
        return False
    if not re.search(r"[A-Za-z]", keyword):
        return False

    keyword_words = _keyword_words(keyword)
    invisible_hits = keyword_words & INVISIBLE_VISUAL_TERMS
    observable_hits = keyword_words & OBSERVABLE_VISUAL_TERMS
    if invisible_hits and not observable_hits:
        return False

    return True


def _score_hook(item):
    scores = {}
    for key in HOOK_CRITERIA:
        try:
            value = float(item.get(key, 0.0))
        except Exception:
            value = 0.0
        scores[key] = max(0.0, min(10.0, value))

    weighted = sum(
        scores[key] * HOOK_WEIGHTS[key]
        for key in HOOK_CRITERIA
    )
    total = weighted / sum(HOOK_WEIGHTS.values())
    return scores, round(total, 3)


def _criteria_pass(scores):
    return all(
        float(scores.get(key, 0.0)) >= minimum
        for key, minimum in HOOK_CRITERIA_FLOORS.items()
    )


def _normalize_candidates(payload):
    if not isinstance(payload, dict):
        return []

    normalized = []
    for index, item in enumerate(payload.get("candidates", []), start=1):
        if not isinstance(item, dict):
            continue

        text = str(item.get("text", "")).strip()
        visual_goal = str(item.get("visual_goal", "")).strip()
        keyword = " ".join(str(item.get("keyword", "")).strip().split())

        if not text or not visual_goal or not keyword:
            continue
        if not _valid_hook_shape(text, keyword):
            continue

        scores, total_score = _score_hook(item)
        normalized.append({
            "id": str(item.get("id") or f"hook_{index}"),
            "text": text,
            "visual_goal": visual_goal,
            "keyword": keyword,
            "scores": scores,
            "criteria_pass": _criteria_pass(scores),
            "total_score": total_score,
            "reason": str(item.get("reason", "")).strip(),
        })

    return normalized


def _request_candidates(topic_info, candidate, generation_round):
    prompt = f"""
너는 YouTube Shorts 첫 1~3초 Hook Selector다.
Candidate Explorer와 Candidate Gate가 이미 소재를 확정했다.
새 소재나 새로운 사실을 만들지 말고 아래 확정 Candidate 안에서만 작업한다.

[TOPIC INFO]
{json.dumps(topic_info, ensure_ascii=False, indent=2)}

[CANDIDATE LOCK]
{json.dumps(candidate, ensure_ascii=False, indent=2)}

서로 다른 Hook 후보를 최소 {HOOK_CANDIDATE_COUNT}개 만든다.
각 Hook을 0~10점으로 평가한다.
평가 기준: stop_power, curiosity_gap, clarity, specificity, visual_potential, fact_safety.

필수 규칙:
- 실제 TTS가 1~3초에 들어오도록 아주 짧은 한 문장만 쓴다.
- 공백 제외 {HOOK_MIN_CHARS}~{HOOK_MAX_CHARS}자다. 16자를 넘기지 마라.
- 첫 구절에 구체적 대상 이름을 바로 넣는다.
- "이것", "이 기술", "이 시스템"처럼 대상을 늦게 밝히지 않는다.
- "알려드려요", "알아봅니다", "보여드려요", "소개합니다"처럼 앞으로 설명할 내용을 예고하는 소개형 문장을 쓰지 않는다.
- 첫 문장에서 Candidate 안의 이상현상, 반전 또는 관찰 가능한 결과를 직접 말해 즉시 "왜?"가 생기게 한다.
- 첫 화면은 대사의 핵심 의미를 영상만 봐도 즉시 이해할 수 있어야 한다.
- 방향, 효율, 안전성처럼 카메라로 바로 확인하기 어려운 속성만 검색하지 마라.
- 그런 속성이 핵심이면 햇빛, 그림자, 움직임, 구조 변화 같은 관찰 가능한 결과를 첫 화면으로 선택한다.
- visual_goal은 핵심 피사체 하나를 모바일에서 즉시 알아볼 수 있는 단순한 구도/클로즈업으로 쓴다.
- keyword는 그 관찰 가능한 화면을 찾는 Pexels용 2~7단어 영어 검색어다.
- Candidate의 micro_narrative, fact_check_focus, visual_proof 범위를 넘지 않는다.
- fact_safety와 visual_potential을 과장 채점하지 않는다.
- generation_round={generation_round}

JSON 객체만 출력한다.
{{
  "candidates": [
    {{
      "id": "hook_1",
      "text": "한국어 Hook 한 문장",
      "visual_goal": "첫 화면에 반드시 보여야 할 구체적 대상과 관찰 가능한 현상",
      "keyword": "specific observable visual search",
      "stop_power": 0,
      "curiosity_gap": 0,
      "clarity": 0,
      "specificity": 0,
      "visual_potential": 0,
      "fact_safety": 0,
      "reason": "짧은 평가 근거"
    }}
  ]
}}
"""

    call_number = authorize_call(MODEL)
    print(f"🪝 Hook API call authorized: #{call_number}")

    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "확정된 Shorts 소재 안에서만 사실 안전성, 실제 1~3초 길이, "
                    "화면으로 직접 증명 가능한 첫 장면을 함께 평가하는 Hook Selector다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.75,
        response_format={"type": "json_object"},
    )

    usage = record_usage(MODEL, response)
    print(f"💰 Hook call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    return _normalize_candidates(
        _extract_json(response.choices[0].message.content)
    )


def _best_passing_candidate(candidates):
    passing = [
        item
        for item in candidates
        if item.get("criteria_pass")
        and item.get("total_score", 0.0) >= HOOK_MIN_SCORE
    ]
    return passing[0] if passing else None


def select_hook(topic_info, candidate):
    audit = {
        "enabled": True,
        "candidate_count_required": HOOK_CANDIDATE_COUNT,
        "hook_char_range": [HOOK_MIN_CHARS, HOOK_MAX_CHARS],
        "criteria": list(HOOK_CRITERIA),
        "criteria_floors": dict(HOOK_CRITERIA_FLOORS),
        "threshold": HOOK_MIN_SCORE,
        "max_regenerations": HOOK_MAX_REGENERATIONS,
        "attempts": [],
        "selected": None,
        "fallback": False,
    }

    best = None
    for attempt in range(1, HOOK_MAX_REGENERATIONS + 2):
        candidates = _request_candidates(topic_info, candidate, attempt)
        candidates.sort(key=lambda item: item["total_score"], reverse=True)
        round_best = _best_passing_candidate(candidates)

        audit["attempts"].append({
            "attempt": attempt,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "best_score": (
                round_best.get("total_score")
                if round_best
                else None
            ),
        })

        if round_best and (
            best is None
            or round_best["total_score"] > best["total_score"]
        ):
            best = round_best

        if len(candidates) >= HOOK_CANDIDATE_COUNT and round_best:
            break

    if best is None:
        audit["fallback"] = True
        audit["fallback_reason"] = (
            "최소 후보 수/길이/개별 기준/종합 점수를 모두 통과한 Hook이 없습니다."
        )
        return None, audit

    audit["selected"] = best
    return best, audit


def print_hook_audit(audit):
    print("")
    print("=" * 64)
    print("🪝 HOOK EXPERIMENT AUDIT JSON")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print("=" * 64)

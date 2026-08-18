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
HOOK_MIN_SCORE = float(
    os.environ.get("HOOK_MIN_SCORE", "7.2")
)

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


if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


def hook_experiment_enabled():
    return str(
        os.environ.get(
            "ENABLE_HOOK_EXPERIMENT",
            "0",
        )
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _extract_json(text):
    text = str(text or "").strip()
    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE,
    )
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

    raise ValueError(
        "Hook Selector 응답에서 JSON 객체를 찾지 못했습니다."
    )


def _visible_len(text):
    return len(
        re.sub(
            r"\s+",
            "",
            str(text or ""),
        )
    )


def _valid_hook_shape(text, keyword):
    if _visible_len(text) < 12:
        return False
    if _visible_len(text) > 42:
        return False
    if len(re.findall(r"[.!?…]+", text)) > 1:
        return False

    words = keyword.split()
    if len(words) < 2 or len(words) > 7:
        return False
    if not re.search(r"[A-Za-z]", keyword):
        return False

    return True


def _score_hook(item):
    scores = {}

    for key in HOOK_CRITERIA:
        try:
            value = float(
                item.get(
                    key,
                    0.0,
                )
            )
        except Exception:
            value = 0.0

        scores[key] = max(
            0.0,
            min(10.0, value),
        )

    weighted = sum(
        scores[key] * HOOK_WEIGHTS[key]
        for key in HOOK_CRITERIA
    )

    total = weighted / sum(
        HOOK_WEIGHTS.values()
    )

    return scores, round(total, 3)


def _normalize_candidates(payload):
    if not isinstance(payload, dict):
        return []

    normalized = []

    for index, item in enumerate(
        payload.get("candidates", []),
        start=1,
    ):
        if not isinstance(item, dict):
            continue

        text = str(
            item.get("text", "")
        ).strip()

        visual_goal = str(
            item.get("visual_goal", "")
        ).strip()

        keyword = " ".join(
            str(
                item.get("keyword", "")
            ).strip().split()
        )

        if not text or not visual_goal or not keyword:
            continue

        if not _valid_hook_shape(
            text,
            keyword,
        ):
            continue

        scores, total_score = (
            _score_hook(item)
        )

        normalized.append({
            "id": str(
                item.get("id")
                or f"hook_{index}"
            ),
            "text": text,
            "visual_goal": visual_goal,
            "keyword": keyword,
            "scores": scores,
            "total_score": total_score,
            "reason": str(
                item.get("reason", "")
            ).strip(),
        })

    return normalized


def _request_candidates(
    topic_info,
    candidate,
    generation_round,
):
    prompt = f"""
너는 YouTube Shorts 첫 1~3초 Hook Selector다.
Candidate Explorer와 Candidate Gate가 이미 소재를 확정했다.
새 소재나 새로운 사실을 만들지 말고 아래 확정 Candidate 안에서만 작업한다.

[TOPIC INFO]
{json.dumps(topic_info, ensure_ascii=False, indent=2)}

[CANDIDATE LOCK]
{json.dumps(candidate, ensure_ascii=False, indent=2)}

서로 다른 Hook 후보를 최소 {HOOK_CANDIDATE_COUNT}개 만든다.
각 Hook을 0~10점으로 독립 평가한다.

평가 기준:
- stop_power
- curiosity_gap
- clarity
- specificity
- visual_potential
- fact_safety

필수 규칙:
- 첫 1~3초용 한 문장만 쓴다.
- 공백 제외 12~42자다.
- 첫 구절에 구체적 대상 이름을 바로 넣는다.
- "이것", "이 기술", "이 시스템"처럼 대상을 늦게 밝히지 않는다.
- visual_goal은 Hook 대사와 같은 물리적 대상/구조/행동을 직접 보여준다.
- 모바일에서 첫눈에 대상이 보이도록 클로즈업 또는 단순한 구도를 요구한다.
- keyword는 Pexels용 2~7단어 영어 검색어다.
- Candidate의 micro_narrative, fact_check_focus, visual_proof 범위를 넘지 않는다.
- 점수를 높이기 위해 사실을 과장하거나 추가하지 않는다.
- generation_round={generation_round}

JSON 객체만 출력한다.

{{
  "candidates": [
    {{
      "id": "hook_1",
      "text": "한국어 Hook 한 문장",
      "visual_goal": "첫 화면에 반드시 보여야 할 구체적 대상과 구도",
      "keyword": "specific english visual search",
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

    call_number = authorize_call(
        MODEL
    )

    print(
        "🪝 Hook API call authorized: "
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
                    "role": "system",
                    "content": (
                        "확정된 Shorts 소재 안에서만 사실 안전성과 "
                        "첫 1~3초 정지력을 함께 평가하는 Hook Selector다."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.75,
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
        "💰 Hook call: "
        f"${usage['cost_usd']:.6f}"
    )

    print_budget_status()

    return _normalize_candidates(
        _extract_json(
            response
            .choices[0]
            .message
            .content
        )
    )


def select_hook(
    topic_info,
    candidate,
):
    audit = {
        "enabled": True,
        "candidate_count_required": (
            HOOK_CANDIDATE_COUNT
        ),
        "criteria": list(
            HOOK_CRITERIA
        ),
        "threshold": HOOK_MIN_SCORE,
        "max_regenerations": (
            HOOK_MAX_REGENERATIONS
        ),
        "attempts": [],
        "selected": None,
        "fallback": False,
    }

    best = None

    for attempt in range(
        1,
        HOOK_MAX_REGENERATIONS + 2,
    ):
        candidates = _request_candidates(
            topic_info,
            candidate,
            attempt,
        )

        candidates.sort(
            key=lambda item: (
                item["total_score"]
            ),
            reverse=True,
        )

        round_best = (
            candidates[0]
            if candidates
            else None
        )

        audit["attempts"].append({
            "attempt": attempt,
            "candidate_count": len(
                candidates
            ),
            "candidates": candidates,
            "best_score": (
                round_best.get(
                    "total_score"
                )
                if round_best
                else None
            ),
        })

        if (
            round_best
            and (
                best is None
                or round_best[
                    "total_score"
                ] > best[
                    "total_score"
                ]
            )
        ):
            best = round_best

        if (
            round_best
            and len(candidates)
            >= HOOK_CANDIDATE_COUNT
            and round_best[
                "total_score"
            ] >= HOOK_MIN_SCORE
        ):
            break

    if best is None:
        audit["fallback"] = True
        audit["fallback_reason"] = (
            "유효한 Hook 후보가 없습니다."
        )
        return None, audit

    if best[
        "total_score"
    ] < HOOK_MIN_SCORE:
        audit["fallback"] = True
        audit["fallback_reason"] = (
            "최고 Hook 점수가 기준 미달: "
            f"{best['total_score']:.3f} "
            f"< {HOOK_MIN_SCORE:.3f}"
        )
        return None, audit

    audit["selected"] = best

    return best, audit


def print_hook_audit(audit):
    print("")
    print("=" * 64)
    print("🪝 HOOK EXPERIMENT AUDIT JSON")
    print(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        )
    )
    print("=" * 64)

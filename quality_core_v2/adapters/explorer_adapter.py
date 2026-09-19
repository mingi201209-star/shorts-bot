"""Explorer adapter: LLM call that proposes a CandidateV2.

Bounded rewrite is handled by the caller (run_candidate_with_recovery),
never inside this module: this file only ever asks the model for ONE
candidate per call.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from quality_core_v2.candidate import MAX_CANDIDATE_REWRITES, evaluate_candidate_v2
from quality_core_v2.schemas import CandidateV2, ShapeError, Verdict

EXPLORER_MODEL = os.environ.get("V3_EXPLORER_V2_MODEL", "gpt-4o-mini")

EXPLORER_V2_SYSTEM_PROMPT = """
너는 YouTube Shorts Candidate Explorer V2다.

정확히 아래 JSON 필드만 반환한다. 그 외 텍스트는 출력하지 않는다.

{
  "topic": "...",
  "concrete_subject": "구체적인 물리적 대상",
  "observable_phenomenon": "카메라로 실제로 보이는 현상",
  "core_question": "구체적인 질문 (왜/어떻게)",
  "mechanism": "비자명한 작동 원리",
  "reveal": "Reveal은 반드시 mechanism을 설명해야 하며, '효율 향상'/'안전성 향상'/'최적화'/'도움이 된다'/'영향을 준다' 같은 결론으로 끝나면 안 된다",
  "canonical_subject": "정규화된 대상 이름 (예: aircraft main wing)",
  "evidence_refs": ["..."],
  "visual_proof": ["..."]
}

Topic direction은 단순 참고가 아니라 scope lock이다.
- 방향이 현상/메커니즘(예: aircraft wing flex)을 지정하면, 성능/안전/편안함 같은 downstream benefit로 주제를 바꾸지 않는다.
- reveal은 mechanism을 한 단계 더 구체화해야 한다. "중요한 역할", "성능/안정성/기동성 향상", "긍정적 영향" 같은 효익 결론은 금지한다.
- bounded rewrite 피드백이 주어지면 같은 오류를 반복하지 말고 그 이유를 직접 수정한 새 Candidate를 낸다.

새 Candidate를 하나만 제안한다. 점수를 매기지 않는다.
"""


def parse_explorer_response(raw_text: str) -> CandidateV2:
    """Pure: raw model text -> CandidateV2. Raises ShapeError/ValueError on
    malformed output rather than silently coercing it -- a malformed
    Candidate must surface as a REGENERATE, not a guess.
    """
    try:
        data: Dict[str, Any] = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ShapeError(f"Explorer response is not valid JSON: {exc}") from exc
    return CandidateV2.from_dict(data)


def call_explorer(
    topic_direction: str,
    recent_topics: Optional[List[str]] = None,
    *,
    client: Any = None,
    rejection_reason: str = "",
) -> str:
    """Impure: the actual OpenAI call. Not exercised in this session (no
    OPENAI_KEY here) -- exists so GitHub Actions (which has the secret)
    can run it for real. `client` is injectable for testing without a key.
    """
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage

    authorize_call(EXPLORER_MODEL)
    user_prompt = (
        f"방향(scope lock): {topic_direction}\n"
        f"최근 사용된 주제 (피할 것): {recent_topics or []}\n"
        f"이전 Candidate 거절 이유 (있으면 반드시 수정): {rejection_reason or '없음'}"
    )
    response = client.chat.completions.create(
        model=EXPLORER_MODEL,
        messages=[
            {"role": "system", "content": EXPLORER_V2_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    record_usage(EXPLORER_MODEL, response)
    return response.choices[0].message.content


def propose_candidate_with_bounded_rewrite(
    topic_direction: str,
    recent_topics: Optional[List[str]] = None,
    *,
    call_fn=call_explorer,
) -> "tuple[Optional[CandidateV2], Verdict]":
    """Orchestrates the ONE allowed bounded rewrite (execution order
    section 3: 'bounded retry 최대 1회'). Returns (candidate_or_none,
    final_verdict). This function's control flow is pure and testable by
    injecting `call_fn`; only `call_fn` itself touches the network.
    """
    last_verdict = Verdict(False, "no attempt made", "candidate")
    for attempt in range(MAX_CANDIDATE_REWRITES + 1):
        if call_fn is call_explorer:
            raw = call_fn(
                topic_direction,
                recent_topics,
                rejection_reason=(last_verdict.reason if attempt else ""),
            )
        else:
            # Preserve the existing injected two-argument test contract.
            raw = call_fn(topic_direction, recent_topics)
        try:
            candidate = parse_explorer_response(raw)
        except (ShapeError, ValueError) as exc:
            last_verdict = Verdict(False, f"malformed Candidate: {exc}", "candidate")
            continue
        verdict = evaluate_candidate_v2(candidate)
        if verdict.passed:
            return candidate, verdict
        last_verdict = verdict
    return None, last_verdict

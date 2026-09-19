"""Writer adapter: LLM call that turns a CandidateV2 into a ScriptPlanV2
(a list of SceneV2), then a VisualPlanV2 per scene.

Two separate calls by design (execution order section 3: Narration must
become a VisualPlan before it becomes a search query -- collapsing script
writing and visual planning into one call would make that ordering
unverifiable).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from quality_core_v2.schemas import CandidateV2, SceneV2, ShapeError, VisualPlanV2

WRITER_MODEL = os.environ.get("V3_WRITER_V2_MODEL", "gpt-4o-mini")
VISUAL_PLANNER_MODEL = os.environ.get("V3_VISUAL_PLANNER_V2_MODEL", "gpt-4o-mini")

WRITER_V2_SYSTEM_PROMPT = """
너는 YouTube Shorts Script Writer V2다.

주어진 Candidate 하나로 정확히 6개 Scene을 작성한다.
각 Scene은 정확히 하나의 owned_claim_id를 가지며, 인접 Scene과 같은 사실을 반복하지 않는다.

고정 구조:
1) phenomenon: 첫 문장부터 관찰되는 현상을 단정한다. 질문/인사/예고 금지.
2) why_question
3) mechanism_input
4) mechanism_change
5) observable_result
6) payoff: Candidate의 mechanism/reveal을 구체적으로 회수한다.

Candidate에 없는 새 효익/수혜자/도메인을 만들지 마라.
특히 승객 편안함, 객실, 성능/안전성 향상 같은 일반적 효익을 Candidate 근거 없이 추가하지 마라.
payoff를 "도움이 됩니다 / 중요한 역할 / 긍정적 영향을 줍니다"로 끝내지 마라.

정확히 아래 JSON만 반환한다:

{
  "scenes": [
    {
      "scene_index": 1,
      "narration": "...",
      "causal_role": "phenomenon|why_question|mechanism_input|mechanism_change|observable_result|payoff",
      "owned_claim_id": "...",
      "new_information": "...",
      "visual_requirement": "..."
    }
  ]
}

TTS narration은 자연스러운 한국어 존댓말로 작성한다.
"""

VISUAL_PLANNER_V2_SYSTEM_PROMPT = """
너는 Visual Plan V2 작성자다.

Narration을 직접 검색어로 바꾸지 마라.
먼저 이 Scene이 실제로 화면에 무엇을 보여줘야 하는지 구조화한다.

Candidate의 canonical_subject와 concrete_subject를 모든 Scene에서 유지한다.
다른 대상(예: 날개 주제에서 객실/승객)으로 바꾸지 마라.
search_queries에는 required_observable_state의 핵심 현상 단어를 반드시 남긴다.
예: bending/flexing이 필요하면 aircraft wing 같은 subject-only 검색어로 축약하지 마라.
required_relation_or_mechanism은 실제 프레임에서 확인 가능한 물리적 관계만 적는다.

정확히 아래 JSON만 반환한다:

{
  "subject": "...",
  "required_visible_components": ["..."],
  "required_observable_state": ["..."],
  "required_relation_or_mechanism": ["..."],
  "forbidden_visuals": ["..."],
  "preferred_source_type": "stock|generated|grounded_explanatory",
  "search_queries": ["..."],
  "generation_prompt_constraints": ["..."]
}
"""


def parse_writer_response(raw_text: str) -> List[SceneV2]:
    try:
        data: Dict[str, Any] = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ShapeError(f"Writer response is not valid JSON: {exc}") from exc
    scenes_raw = data.get("scenes")
    if not isinstance(scenes_raw, list) or not scenes_raw:
        raise ShapeError("Writer response has no 'scenes' list")
    return [SceneV2.from_dict(s) for s in scenes_raw]


def parse_visual_plan_response(raw_text: str, scene_index: int) -> VisualPlanV2:
    try:
        data: Dict[str, Any] = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ShapeError(f"VisualPlanner response is not valid JSON: {exc}") from exc
    data = dict(data)
    data.setdefault("scene_index", scene_index)
    return VisualPlanV2.from_dict(data)


def call_writer(candidate: CandidateV2, *, client: Any = None) -> str:
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage

    authorize_call(WRITER_MODEL)
    user_prompt = json.dumps(
        {
            "topic": candidate.topic,
            "concrete_subject": candidate.concrete_subject,
            "observable_phenomenon": candidate.observable_phenomenon,
            "core_question": candidate.core_question,
            "mechanism": candidate.mechanism,
            "reveal": candidate.reveal,
            "canonical_subject": candidate.canonical_subject,
            "visual_proof": list(candidate.visual_proof),
        },
        ensure_ascii=False,
    )
    response = client.chat.completions.create(
        model=WRITER_MODEL,
        messages=[
            {"role": "system", "content": WRITER_V2_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    record_usage(WRITER_MODEL, response)
    return response.choices[0].message.content


def call_visual_planner(
    scene: SceneV2,
    candidate: CandidateV2 | None = None,
    *,
    client: Any = None,
) -> str:
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage

    authorize_call(VISUAL_PLANNER_MODEL)
    user_prompt = json.dumps(
        {
            "narration": scene.narration,
            "visual_requirement": scene.visual_requirement,
            "candidate": (
                {
                    "topic": candidate.topic,
                    "concrete_subject": candidate.concrete_subject,
                    "observable_phenomenon": candidate.observable_phenomenon,
                    "mechanism": candidate.mechanism,
                    "reveal": candidate.reveal,
                    "canonical_subject": candidate.canonical_subject,
                    "visual_proof": list(candidate.visual_proof),
                }
                if candidate is not None
                else None
            ),
        },
        ensure_ascii=False,
    )
    response = client.chat.completions.create(
        model=VISUAL_PLANNER_MODEL,
        messages=[
            {"role": "system", "content": VISUAL_PLANNER_V2_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    record_usage(VISUAL_PLANNER_MODEL, response)
    return response.choices[0].message.content

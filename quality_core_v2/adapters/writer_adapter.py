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

Retention contract:
- Scene 1은 인사/소개/예고/질문으로 시작하지 않는다. 카메라로 보이는 핵심 결과/현상을 즉시 단정한다.
- Scene 2에서만 "왜?" 질문을 던진다.
- Scene 3은 mechanism_input, Scene 4는 mechanism_change를 구체적으로 설명한다.
- Scene 5는 앞의 메커니즘으로 생기는 observable_result를 보여준다.
- Scene 6 payoff는 메커니즘의 의미를 설명한다. "안전성/성능/효율에 도움" 같은 추상적 효익 문장으로 끝내지 않는다.
- 첫 5초 안에 concrete_subject와 observable_phenomenon이 둘 다 대사에 직접 등장해야 한다.
- 문장은 짧고 자연스러운 한국어 존댓말로 쓴다.
- visual_requirement는 추상어가 아니라 화면에서 확인 가능한 물리적 증거를 적는다.

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

Machine contract:
- subject / required_visible_components / required_observable_state /
  required_relation_or_mechanism / forbidden_visuals / search_queries /
  generation_prompt_constraints 값은 간결한 영어 물리 용어로 작성한다.
- required_observable_state는 실제 프레임에서 확인할 수 있는 상태/변형/움직임이어야 한다.
- required_relation_or_mechanism은 가능하면 두 물리 요소 사이의 보이는 관계로 쓴다.
- search_queries는 generic subject-only 검색어를 금지한다.
- 모든 search_query는 subject/component뿐 아니라 required_observable_state의 핵심 물리 현상 단어를 반드시 포함한다.
  예: aircraft wing flex 주제라면 "aircraft wing flex bending in flight"처럼 flex/bending을 보존한다.
- "aircraft wing", "wing", "airplane"처럼 현상이 빠진 검색어는 반환하지 않는다.
- forbidden_visuals에는 같은 도메인이어도 의미를 증명하지 못하는 generic B-roll을 명시한다.
- user JSON에 candidate_context가 있으면 그것이 이 영상의 identity lock이다.
  subject / required_visible_components / search_queries 중 적어도 하나는
  canonical_subject / concrete_subject의 구체 부품 정체성을 반드시 유지한다.
- 같은 상위 도메인이라고 다른 대상/부품/사용자 결과로 바꾸지 마라.
  예: aircraft main wing을 passenger/cabin/interior/seat/comfort 장면으로 바꾸면 안 된다.
- Scene payoff도 Candidate의 mechanism/reveal을 시각적으로 증명해야 하며,
  편안함/안전성/성능 같은 새로운 결과를 임의로 발명하지 마라.

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
    payload = {
        "scene": {
            "scene_index": scene.scene_index,
            "narration": scene.narration,
            "causal_role": scene.causal_role,
            "owned_claim_id": scene.owned_claim_id,
            "new_information": scene.new_information,
            "visual_requirement": scene.visual_requirement,
        }
    }
    if candidate is not None:
        payload["candidate_context"] = {
            "topic": candidate.topic,
            "concrete_subject": candidate.concrete_subject,
            "observable_phenomenon": candidate.observable_phenomenon,
            "core_question": candidate.core_question,
            "mechanism": candidate.mechanism,
            "reveal": candidate.reveal,
            "canonical_subject": candidate.canonical_subject,
        }
    user_prompt = json.dumps(payload, ensure_ascii=False)
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

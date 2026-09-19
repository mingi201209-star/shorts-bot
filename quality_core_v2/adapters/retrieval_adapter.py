"""Clean V2 visual acquisition.

The important invariant is identity binding:

    VisualPlan -> classify candidate -> Visual QA PASS -> keep exact media_url
    -> render that exact media_url

There is deliberately no later keyword re-search.  Stock classification is
bounded per scene so this adapter cannot turn E2E into an unbounded debugger.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from quality_core_v2.schemas import (
    CandidateVisualV2,
    SceneV2,
    ShapeError,
    Verdict,
    VisualPlanV2,
)
from quality_core_v2.visual_qa import evaluate_scene_visual_qa

CLASSIFIER_MODEL = os.environ.get("V3_VISUAL_CLASSIFIER_V2_MODEL", "gpt-4o-mini")
MAX_CLASSIFICATIONS_PER_SCENE = max(
    1,
    min(4, int(os.environ.get("V3_V2_MAX_VISUAL_CLASSIFICATIONS_PER_SCENE", "2"))),
)

VISUAL_CLASSIFIER_SYSTEM_PROMPT = """
너는 Clean V2 Visual Classifier다.
이미지에 실제로 보이는 것만 판단한다. 검색어/메타데이터를 보고 추측하지 않는다.
description은 narration과 같은 언어로 쓴다. narration의 단어를 복사해서 맞추지 말고,
그 단어가 이미지에서 실제로 확인될 때만 같은 구체 명사/동사를 사용한다.

사용자가 준 VisualPlan의 required_visible_components와
required_observable_state 중 이미지에서 실제로 확인되는 항목만
원문 문자열 그대로 배열에 넣는다. 보이지 않으면 넣지 않는다.

정확히 아래 JSON만 반환한다:
{
  "description": "화면에 실제로 보이는 것을 짧고 구체적으로 설명",
  "visible_components": ["VisualPlan의 원문 항목"],
  "observable_state": ["VisualPlan의 원문 항목"]
}
"""


def parse_visual_classification(
    raw_text: str,
    *,
    source_type: str,
    description: str,
    tags: Optional[List[str]] = None,
    provider: str = "",
    source_id: str = "",
    media_url: str = "",
    thumbnail_url: str = "",
    search_query: str = "",
) -> CandidateVisualV2:
    """Pure: classifier JSON + immutable asset identity -> CandidateVisualV2."""
    try:
        data: Dict[str, Any] = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ShapeError(f"Visual classifier response is not valid JSON: {exc}") from exc

    classified_description = str(data.get("description") or "").strip() or description
    return CandidateVisualV2.from_dict(
        {
            "source_type": source_type,
            "description": classified_description,
            "visible_components": data.get("visible_components") or [],
            "observable_state": data.get("observable_state") or [],
            "tags": tags or [],
            "provider": provider,
            "source_id": source_id,
            "media_url": media_url,
            "thumbnail_url": thumbnail_url,
            "search_query": search_query,
        }
    )


def provider_hit_to_description(hit: Dict[str, Any], provider: str) -> str:
    if provider == "pixabay":
        tags = str(hit.get("tags", "")).strip()
        return tags or str(hit.get("query", ""))
    return str(hit.get("query", ""))


def call_visual_classifier(
    thumbnail_url: str,
    plan: VisualPlanV2,
    scene: Optional[SceneV2] = None,
    *,
    client: Any = None,
) -> str:
    """One bounded vision classification for one concrete provider asset."""
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage

    authorize_call(CLASSIFIER_MODEL)
    plan_payload = {
        "subject": plan.subject,
        "required_visible_components": list(plan.required_visible_components),
        "required_observable_state": list(plan.required_observable_state),
        "required_relation_or_mechanism": list(plan.required_relation_or_mechanism),
        "forbidden_visuals": list(plan.forbidden_visuals),
        "narration": str(scene.narration if scene is not None else ""),
        "visual_requirement": str(scene.visual_requirement if scene is not None else ""),
    }
    response = client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": VISUAL_CLASSIFIER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "VisualPlan:\n" + json.dumps(plan_payload, ensure_ascii=False),
                    },
                    {"type": "image_url", "image_url": {"url": thumbnail_url}},
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    record_usage(CLASSIFIER_MODEL, response)
    return response.choices[0].message.content


def _hit_identity(hit: Dict[str, Any], provider: str, query: str) -> Dict[str, str]:
    media_url = str(hit.get("download_url") or hit.get("url") or "").strip()
    thumbnail_url = str(hit.get("thumbnail") or hit.get("image") or "").strip()
    source_id = str(hit.get("source_id", hit.get("id", "")) or "").strip()
    return {
        "provider": provider,
        "source_id": source_id,
        "media_url": media_url,
        "thumbnail_url": thumbnail_url,
        "search_query": query,
    }


def _classify_hit(
    hit: Dict[str, Any],
    *,
    provider: str,
    query: str,
    plan: VisualPlanV2,
    scene: Optional[SceneV2],
    classify_fn,
) -> CandidateVisualV2:
    identity = _hit_identity(hit, provider, query)
    if not identity["media_url"]:
        raise ValueError("candidate has no media_url")
    if not identity["thumbnail_url"]:
        raise ValueError("candidate has no thumbnail_url")

    raw = (
        classify_fn(identity["thumbnail_url"], plan, scene)
        if classify_fn is call_visual_classifier
        else classify_fn(identity["thumbnail_url"], plan)
    )
    tags = []
    if provider == "pixabay":
        tags = [part.strip() for part in str(hit.get("tags", "")).split(",") if part.strip()]
    return parse_visual_classification(
        raw,
        source_type="stock",
        description=provider_hit_to_description(hit, provider),
        tags=tags,
        **identity,
    )


def _default_provider_searches():
    from video.video_downloader import search_pexels_candidates
    from video.video_providers import search_pixabay_candidates

    return [
        ("pexels", search_pexels_candidates),
        ("pixabay", search_pixabay_candidates),
    ]


def select_visual_for_scene(
    scene: SceneV2,
    plan: VisualPlanV2,
    *,
    provider_searches: Optional[Sequence[Tuple[str, Any]]] = None,
    classify_fn=call_visual_classifier,
    max_classifications: Optional[int] = None,
) -> Tuple[Optional[CandidateVisualV2], Verdict]:
    """Return only an exact asset that already passed V2 semantic QA.

    Classification attempts are globally bounded for the scene.  Failure does
    not relax the plan or substitute a generic B-roll shot.
    """
    searches = list(provider_searches or _default_provider_searches())
    limit = (
        MAX_CLASSIFICATIONS_PER_SCENE
        if max_classifications is None
        else max(1, int(max_classifications))
    )
    queries = [str(q or "").strip() for q in plan.search_queries if str(q or "").strip()]
    if not queries and plan.subject.strip():
        queries = [plan.subject.strip()]

    preferred = str(plan.preferred_source_type or "").strip().lower()
    if preferred and preferred != "stock":
        return None, Verdict(
            False,
            f"VisualPlan requires source_type={preferred!r}, but the current "
            "exact-asset acquisition path only accepts verified stock; "
            "no silent stock substitution is allowed",
            "visual_qa",
        )

    attempts = 0
    last_verdict = Verdict(False, "no visual candidate was classified", "visual_qa")

    for query in queries:
        provider_hits = []
        for provider, search_fn in searches:
            try:
                hits = list(search_fn(query) or [])
            except Exception as exc:
                print(
                    f"[V2_RETRIEVAL_SKIP] provider={provider} "
                    f"reason={type(exc).__name__}"
                )
                hits = []
            provider_hits.append((provider, hits))

        # Interleave providers by rank: Pexels #1, Pixabay #1, then rank #2...
        # A two-call budget therefore samples provider diversity instead of
        # spending both classifications on one provider.
        max_rank = max((len(hits) for _, hits in provider_hits), default=0)
        for rank in range(max_rank):
            for provider, hits in provider_hits:
                if rank >= len(hits):
                    continue
                if attempts >= limit:
                    return None, Verdict(
                        False,
                        f"no exact visual passed within bounded classification budget "
                        f"({attempts}/{limit}); last={last_verdict.reason}",
                        "visual_qa",
                    )

                hit = hits[rank]
                identity = _hit_identity(hit, provider, query)
                if not identity["media_url"] or not identity["thumbnail_url"]:
                    continue

                attempts += 1
                visual = _classify_hit(
                    hit,
                    provider=provider,
                    query=query,
                    plan=plan,
                    scene=scene,
                    classify_fn=classify_fn,
                )
                verdict = evaluate_scene_visual_qa(scene, plan, visual)
                last_verdict = verdict
                print(
                    "[V2_VISUAL_SELECT] "
                    f"scene={scene.scene_index} provider={provider} "
                    f"source_id={visual.source_id or 'unknown'} "
                    f"attempt={attempts}/{limit} "
                    f"status={'PASS' if verdict.passed else 'FAIL'}"
                )
                if verdict.passed:
                    return visual, verdict

    return None, Verdict(
        False,
        f"no exact visual passed V2 QA; last={last_verdict.reason}",
        "visual_qa",
    )


def search_and_classify(
    plan: VisualPlanV2,
    *,
    search_fn=None,
    classify_fn=call_visual_classifier,
):
    """Compatibility helper used by adapter tests; returns the first classified
    Pexels asset with its exact identity, without scene-level acceptance.
    """
    if search_fn is None:
        from video.video_downloader import search_pexels_candidates as search_fn

    for query in plan.search_queries or [plan.subject]:
        hits = list(search_fn(query) or [])
        for hit in hits:
            identity = _hit_identity(hit, "pexels", query)
            if not identity["media_url"] or not identity["thumbnail_url"]:
                continue
            return _classify_hit(
                hit,
                provider="pexels",
                query=query,
                plan=plan,
                scene=None,
                classify_fn=classify_fn,
            )
    return None

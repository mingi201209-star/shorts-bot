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

사용자가 준 VisualPlan의 required_visible_components,
required_observable_state, required_relation_or_mechanism 중
이미지에서 실제로 확인되는 항목만 원문 문자열 그대로 배열에 넣는다.
보이지 않으면 넣지 않는다.

정확히 아래 JSON만 반환한다:
{
  "description": "화면에 실제로 보이는 것을 짧고 구체적으로 설명",
  "visible_components": ["VisualPlan의 원문 항목"],
  "observable_state": ["VisualPlan의 원문 항목"],
  "visible_relations_or_mechanisms": ["VisualPlan의 원문 항목"]
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
            "visible_relations_or_mechanisms": (
                data.get("visible_relations_or_mechanisms") or []
            ),
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


def _generation_scene_payload(scene: SceneV2, plan: VisualPlanV2) -> Dict[str, Any]:
    visual_goal_parts = [
        *plan.required_observable_state,
        *plan.required_relation_or_mechanism,
        *plan.generation_prompt_constraints,
    ]
    query = next(
        (str(q).strip() for q in plan.search_queries if str(q).strip()),
        plan.subject,
    )
    return {
        "scene_id": f"v2-{scene.scene_index}",
        "index": scene.scene_index,
        "text": scene.narration,
        "visual_goal": "; ".join(str(v).strip() for v in visual_goal_parts if str(v).strip()),
        "keyword": str(query or plan.subject).strip(),
        "visual_type": "ai_generated",
    }


def _default_generate_visual(scene: SceneV2, plan: VisualPlanV2) -> Optional[Dict[str, Any]]:
    from pathlib import Path

    from video.still_image_fallback import generate_still_motion_fallback

    output = Path("workspace/temp") / f"v2_generated_scene_{scene.scene_index}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = generate_still_motion_fallback(
        _generation_scene_payload(scene, plan),
        output_path=str(output),
        duration=4.0,
        trigger_reason="v2_plan_generated",
    )
    if not result:
        return None
    return {
        "path": str(result.get("path") or output),
        "provider": str(result.get("provider") or "openai_image"),
        "source_id": str(result.get("source_id") or f"v2-generated-{scene.scene_index}"),
    }


def _default_classify_generated(
    scene: SceneV2,
    plan: VisualPlanV2,
    identity_visual: CandidateVisualV2,
    path: str,
) -> CandidateVisualV2:
    from quality_core_v2.rendered_visual_qa import classify_rendered_visual

    return classify_rendered_visual(
        scene,
        plan,
        identity_visual,
        path,
    )


def _default_download_stock(
    visual: CandidateVisualV2,
    scene: SceneV2,
) -> Optional[str]:
    from pathlib import Path
    import re

    from video.video_downloader import download_video

    safe_id = re.sub(r"[^0-9A-Za-z_-]+", "_", visual.source_id or "unknown")
    path = Path("workspace/temp") / (
        f"v2_stock_scene_{scene.scene_index}_{visual.provider}_{safe_id}.mp4"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    download_video(visual.media_url, str(path))
    return str(path) if path.is_file() else None


def _default_classify_stock_video(
    scene: SceneV2,
    plan: VisualPlanV2,
    identity_visual: CandidateVisualV2,
    path: str,
) -> CandidateVisualV2:
    from quality_core_v2.rendered_visual_qa import classify_rendered_visual

    return classify_rendered_visual(
        scene,
        plan,
        identity_visual,
        path,
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
    generate_fn=None,
    classify_generated_fn=None,
    download_stock_fn=None,
    classify_stock_video_fn=None,
    used_asset_keys: Optional[set] = None,
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
    allow_generated_fallback = preferred == "generated"
    grounded_only_after_stock = preferred == "grounded_explanatory"
    download_stock_fn = download_stock_fn or _default_download_stock
    classify_stock_video_fn = (
        classify_stock_video_fn or _default_classify_stock_video
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
                asset_key = (
                    f"{identity['provider']}:{identity['source_id']}"
                    if identity["source_id"]
                    else identity["media_url"]
                )
                if used_asset_keys and asset_key in used_asset_keys:
                    print(
                        "[V2_VISUAL_SKIP] "
                        f"scene={scene.scene_index} asset={asset_key} reason=already_used"
                    )
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
                    try:
                        local_path = download_stock_fn(visual, scene)
                    except Exception as exc:
                        print(
                            "[V2_STOCK_PREFLIGHT] "
                            f"scene={scene.scene_index} source_id={visual.source_id or 'unknown'} "
                            f"status=ERROR reason={type(exc).__name__}"
                        )
                        local_path = None
                    if not local_path:
                        last_verdict = Verdict(
                            False,
                            "exact stock candidate could not be materialized for frame QA",
                            "visual_qa",
                        )
                        continue

                    local_identity = CandidateVisualV2.from_dict({
                        "source_type": visual.source_type,
                        "description": visual.description,
                        "visible_components": list(visual.visible_components),
                        "observable_state": list(visual.observable_state),
                        "visible_relations_or_mechanisms": list(
                            visual.visible_relations_or_mechanisms
                        ),
                        "tags": list(visual.tags),
                        "provider": visual.provider,
                        "source_id": visual.source_id,
                        "media_url": local_path,
                        "thumbnail_url": visual.thumbnail_url,
                        "search_query": visual.search_query,
                    })
                    actual_visual = classify_stock_video_fn(
                        scene,
                        plan,
                        local_identity,
                        local_path,
                    )
                    exact_verdict = evaluate_scene_visual_qa(
                        scene,
                        plan,
                        actual_visual,
                    )
                    last_verdict = exact_verdict
                    print(
                        "[V2_STOCK_PREFLIGHT] "
                        f"scene={scene.scene_index} provider={provider} "
                        f"source_id={visual.source_id or 'unknown'} "
                        f"status={'PASS' if exact_verdict.passed else 'FAIL'}"
                    )
                    if exact_verdict.passed:
                        return actual_visual, exact_verdict

    if allow_generated_fallback:
        generate_fn = generate_fn or _default_generate_visual
        classify_generated_fn = classify_generated_fn or _default_classify_generated
        generated = generate_fn(scene, plan)
        if generated:
            path = str(generated.get("path") or "").strip()
            if path:
                identity_visual = CandidateVisualV2.from_dict({
                    "source_type": "generated",
                    "description": "",
                    "visible_components": [],
                    "observable_state": [],
                    "visible_relations_or_mechanisms": [],
                    "provider": str(generated.get("provider") or "generated"),
                    "source_id": str(generated.get("source_id") or ""),
                    "media_url": path,
                    "search_query": next(
                        (str(q).strip() for q in plan.search_queries if str(q).strip()),
                        plan.subject,
                    ),
                })
                actual_visual = classify_generated_fn(
                    scene,
                    plan,
                    identity_visual,
                    path,
                )
                generated_verdict = evaluate_scene_visual_qa(
                    scene,
                    plan,
                    actual_visual,
                )
                print(
                    "[V2_VISUAL_SELECT] "
                    f"scene={scene.scene_index} "
                    f"provider={actual_visual.provider or 'generated'} "
                    f"source_id={actual_visual.source_id or 'unknown'} "
                    f"status={'PASS' if generated_verdict.passed else 'FAIL'} "
                    "mode=generated_fallback"
                )
                if generated_verdict.passed:
                    generated_key = (
                        f"{actual_visual.provider}:{actual_visual.source_id}"
                        if actual_visual.source_id
                        else actual_visual.media_url
                    )
                    if used_asset_keys and generated_key in used_asset_keys:
                        last_verdict = Verdict(
                            False,
                            f"generated exact asset already used: {generated_key}",
                            "visual_qa",
                        )
                        print(
                            "[V2_VISUAL_SKIP] "
                            f"scene={scene.scene_index} asset={generated_key} "
                            "reason=already_used"
                        )
                    else:
                        return actual_visual, generated_verdict
                else:
                    last_verdict = generated_verdict

    if grounded_only_after_stock:
        return None, Verdict(
            False,
            "no exact stock visual proved the plan and V2 has no exact-asset "
            "grounded explanatory renderer; no silent substitution is allowed",
            "visual_qa",
        )

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

"""Retrieval/Generation adapter: turns a VisualPlanV2 into a
CandidateVisualV2, by (a) reusing V1's existing provider search functions
unchanged (video/video_downloader.search_pexels_candidates,
video/video_providers.search_pixabay_candidates -- per the execution
order, provider/renderer infrastructure is not to be rewritten), then
(b) classifying what the top hit actually shows against the plan's
required components/state with a vision-LLM call, since neither
provider's metadata includes that on its own (Pexels: none; Pixabay:
free-text tags only).

Falls back to AI generation (video/ai_visual_provider.generate_ai_visual,
also reused unchanged) only when no provider hit clears classification --
matching the "prove the same meaning a different way" rule, never a
silent downgrade to a lower bar.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from quality_core_v2.schemas import CandidateVisualV2, ShapeError, VisualPlanV2

CLASSIFIER_MODEL = os.environ.get("V3_VISUAL_CLASSIFIER_V2_MODEL", "gpt-4o-mini")

VISUAL_CLASSIFIER_SYSTEM_PROMPT = """
너는 Visual Classifier V2다. 주어진 이미지(비디오 썸네일)가 실제로 무엇을 보여주는지만 보고 판단한다.
주어진 subject를 안다고 가정하지 말고, 이미지에서 실제로 보이는 것만 기술한다.

정확히 아래 JSON만 반환한다:

{
  "visible_components": ["실제로 화면에 보이는 물체/부위"],
  "observable_state": ["실제로 관찰되는 상태/현상 (정적이면 빈 배열이 아니라 'static'처럼 명시)"]
}
"""


def parse_visual_classification(
    raw_text: str,
    *,
    source_type: str,
    description: str,
    tags: Optional[List[str]] = None,
) -> CandidateVisualV2:
    """Pure: classifier JSON + provider metadata -> CandidateVisualV2."""
    try:
        data: Dict[str, Any] = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ShapeError(f"Visual classifier response is not valid JSON: {exc}") from exc
    return CandidateVisualV2.from_dict(
        {
            "source_type": source_type,
            "description": description,
            "visible_components": data.get("visible_components") or [],
            "observable_state": data.get("observable_state") or [],
            "tags": tags or [],
        }
    )


def provider_hit_to_description(hit: Dict[str, Any], provider: str) -> str:
    """Pure: what little text a provider hit carries, for the classifier
    prompt and for narration<->visual overlap. Pexels hits have no
    semantic text at all (only technical fields), so this can legitimately
    return just the query for that provider.
    """
    if provider == "pixabay":
        tags = str(hit.get("tags", "")).strip()
        return tags or str(hit.get("query", ""))
    return str(hit.get("query", ""))


def call_visual_classifier(thumbnail_url: str, *, client: Any = None) -> str:
    """Impure: vision-LLM call. Untested here (no OPENAI_KEY in this
    session); real execution happens in GitHub Actions.
    """
    if client is None:
        import openai

        from config import OPENAI_KEY

        openai.api_key = OPENAI_KEY
        client = openai

    from quality.budget_guard import authorize_call, record_usage

    authorize_call(CLASSIFIER_MODEL)
    response = client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": VISUAL_CLASSIFIER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": thumbnail_url}},
                ],
            },
        ],
        response_format={"type": "json_object"},
    )
    record_usage(CLASSIFIER_MODEL, response)
    return response.choices[0].message.content


def search_and_classify(plan: VisualPlanV2, *, search_fn=None, classify_fn=call_visual_classifier):
    """Impure orchestration: try each of plan.search_queries against
    Pexels (reused from video.video_downloader), classify the top hit,
    return a CandidateVisualV2 or None if the provider genuinely has
    nothing. Caller (not this function) decides whether a None here means
    "try Pixabay next" or "fall back to generation" -- kept here as a
    single-provider function so it stays unit-testable by injecting
    search_fn/classify_fn.
    """
    if search_fn is None:
        from video.video_downloader import search_pexels_candidates as search_fn

    for query in plan.search_queries or [plan.subject]:
        hits = search_fn(query)
        if not hits:
            continue
        top = hits[0]
        raw = classify_fn(top.get("thumbnail", ""))
        return parse_visual_classification(
            raw,
            source_type="stock",
            description=provider_hit_to_description(top, "pexels"),
            tags=[],
        )
    return None

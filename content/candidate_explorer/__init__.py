"""Safe wrapper for Candidate Explorer placeholder regeneration.

This package intentionally shadows ``content/candidate_explorer.py`` without
modifying the large legacy module in-place.  The legacy implementation is
loaded from its file path and remains the source of truth for normal runs.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_LEGACY_PATH = Path(__file__).resolve().parent.parent / "candidate_explorer.py"
_SPEC = importlib.util.spec_from_file_location(
    "content._candidate_explorer_legacy",
    _LEGACY_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load Candidate Explorer: {_LEGACY_PATH}")

_LEGACY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_LEGACY)


_PLACEHOLDER_REASONS = {
    "재탐색이 필요한 구체적인 이유",
    "구체적인 이유",
}


def _is_placeholder_regenerate(result):
    if not isinstance(result, dict):
        return False
    if str(result.get("status", "")).strip().upper() != "REGENERATE":
        return False

    reason = str(result.get("reason", "")).strip()
    if reason in _PLACEHOLDER_REASONS:
        return True

    compact = reason.replace(" ", "")
    return (
        "재탐색이필요한구체적인이유" in compact
        or reason.lower() in {"reason", "specific reason"}
    )


def _retry_topic_info(topic_info):
    retry_info = dict(topic_info or {})
    direction = str(retry_info.get("topic", "")).strip()
    retry_info["topic"] = (
        f"{direction}\n\n"
        "[PLACEHOLDER REGENERATE RETRY]\n"
        "직전 응답이 실제 판단 없이 OUTPUT 예시의 placeholder reason을 그대로 반환했다.\n"
        "이번 호출에서는 내부 탐색을 다시 수행한다.\n"
        "제작 가능한 후보가 하나라도 있으면 반드시 SELECTED와 구체적인 Winner를 반환한다.\n"
        "정말 모든 후보가 실패한 경우에만 REGENERATE를 반환하고, reason에는 실제로 실패한 대상/질문/메커니즘과 실패 이유를 구체적으로 적는다.\n"
        "'재탐색이 필요한 구체적인 이유', '구체적인 이유' 같은 예시 문구를 그대로 출력하지 않는다."
    )
    return retry_info


def _call_legacy_explore_candidates(topic_info, kwargs):
    """Run the legacy Explorer call, converting its own known malformed-
    response signals into the same bounded REGENERATE contract it already
    uses for an explicit REGENERATE.

    _LEGACY.explore_candidates() parses raw model JSON and deliberately
    raises for a known, bounded set of failure modes:
    - ValueError (via extract_json()/validate_explorer_output()) for
      invalid/truncated JSON, or a syntactically valid object that fails
      schema validation (missing/wrong-type required field, unrecognized
      status, ...).
    - RuntimeError ("Candidate Explorer 응답이 비어 있습니다.") when the
      model response content is empty/falsy -- the same deliberate
      empty-content guard used identically in content/candidate_gate.py and
      quality/judge.py, and the only RuntimeError this module ever raises
      (verified), so catching it here narrowly cannot mask an unrelated bug.

    Nothing upstream (main.py's "CANDIDATE ATTEMPT N/total" loop) catches
    either signal, so it previously escaped uncaught and crashed the whole
    production run on whichever attempt hit it -- bypassing the remaining
    bounded retries instead of using them, exactly like the
    CANDIDATE_POOL-outside-scope crash fixed for Run 34459538824. This
    wrapper is the one safe place to fix that: it never touches
    content/candidate_explorer.py, so it cannot disturb the exact-text
    anchors several production hotfixes match against that file.
    """
    try:
        return _LEGACY.explore_candidates(topic_info, **kwargs)
    except (ValueError, RuntimeError) as malformed_response_error:
        return {
            "status": "REGENERATE",
            "reason": (
                "malformed Candidate Explorer response: "
                f"{malformed_response_error}"
            ),
        }


def explore_candidates(
    topic_info,
    *,
    recent_topics=None,
    recent_content=None,
    rejected_topics=None,
    fixed_topic=None,
    model=None,
):
    kwargs = {
        "recent_topics": recent_topics,
        "recent_content": recent_content,
        "rejected_topics": rejected_topics,
    }
    if fixed_topic is not None:
        kwargs["fixed_topic"] = fixed_topic
    if model is not None:
        kwargs["model"] = model

    result = _call_legacy_explore_candidates(topic_info, kwargs)

    if not _is_placeholder_regenerate(result):
        return result

    print("")
    print("♻️ Candidate Explorer placeholder 감지: 강제 재탐색 1회")

    retry_result = _call_legacy_explore_candidates(
        _retry_topic_info(topic_info),
        kwargs,
    )

    if _is_placeholder_regenerate(retry_result):
        retry_result = dict(retry_result)
        retry_result["reason"] = (
            "Candidate Explorer가 placeholder REGENERATE를 두 번 반환해 "
            "현재 방향을 폐기하고 다음 Candidate 방향으로 이동합니다."
        )

    return retry_result


# Preserve compatibility for code that may read the configured model.
MODEL = _LEGACY.MODEL

"""Small deterministic helpers for human-visible Shorts quality.

This module is intentionally provider/model free. It does not change any budget,
retry, model, or score threshold; it only detects the exact opening failure seen
in production Run 34616204901 and provides a narrow fact-neutral normalization
for the aircraft-window fixed topic.
"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List

_STOPWORDS = {
    "그런데", "그리고", "하지만", "그래서", "되어", "됩니다", "있습니다",
    "무엇일까요", "왜일까요", "이유", "이유는", "정도", "정말", "바로", "굳이",
}
_PARTICLES = (
    "으로부터", "에서부터", "에게서", "까지는", "이라는", "라는", "으로", "에서",
    "에게", "처럼", "보다", "부터", "까지", "이나", "거나", "하고", "이며",
    "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "와", "과",
)


def opening_terms(text: Any) -> set[str]:
    raw = re.findall(r"[0-9A-Za-z가-힣]+", str(text or "").lower())
    terms: set[str] = set()
    for token in raw:
        if len(token) < 2 or token in _STOPWORDS:
            continue
        compact = token
        for suffix in _PARTICLES:
            if compact.endswith(suffix) and len(compact) - len(suffix) >= 2:
                compact = compact[:-len(suffix)]
                break
        if len(compact) >= 2 and compact not in _STOPWORDS:
            terms.add(compact)
    return terms


def opening_repeat_issue(scenes: List[Dict[str, Any]] | Any) -> str | None:
    """Detect the Run 34616204901 pattern: Scene 2 re-asks Scene 1 verbosely."""
    if not isinstance(scenes, list) or len(scenes) < 2:
        return None
    if not isinstance(scenes[0], dict) or not isinstance(scenes[1], dict):
        return None
    first = str(scenes[0].get("text", "")).strip()
    second = str(scenes[1].get("text", "")).strip()
    if not first or not second:
        return None
    first_terms = opening_terms(first)
    second_terms = opening_terms(second)
    if not first_terms or not second_terms:
        return None
    shared = first_terms & second_terms
    overlap = len(shared) / max(1, min(len(first_terms), len(second_terms)))
    second_reasks_reason = bool(re.search(r"(?:왜|이유|무엇일까요|어째서)", second))
    if second_reasks_reason and len(shared) >= 2 and overlap >= 0.50:
        return (
            "scene 2 verbosely re-asks scene 1 "
            f"(shared={','.join(sorted(shared))})"
        )
    return None


def is_aircraft_window_round_topic(candidate: Dict[str, Any] | Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    values = [
        candidate.get("topic"), candidate.get("core_question"),
        (candidate.get("micro_narrative") or {}).get("hook")
        if isinstance(candidate.get("micro_narrative"), dict) else "",
    ]
    text = " ".join(str(value or "") for value in values)
    return "비행기" in text and "창문" in text and ("둥글" in text or "모서리" in text)


def normalize_aircraft_window_opening(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Improve only the already-observable wording; introduce no new fact.

    Scene 1 remains the same visible fact (aircraft windows have rounded rather
    than square corners). Scene 2 remains the existing why-question, but avoids
    repeating the full subject phrase word-for-word. The causal answer still
    belongs to the existing causal-clue/reveal/payoff chain.
    """
    result = deepcopy(candidate)
    if not is_aircraft_window_round_topic(result):
        return result
    micro = result.get("micro_narrative")
    if not isinstance(micro, dict):
        return result
    micro = dict(micro)

    hook = str(micro.get("hook", "")).strip()
    question = str(micro.get("core_question") or result.get("core_question") or "").strip()
    probe = [
        {"text": hook or "비행기 창문 모서리는 둥글게 되어 있습니다."},
        {"text": question},
    ]
    issue = opening_repeat_issue(probe)
    bland_hook = (
        "둥글게 되어 있습니다" in hook
        or "모서리는 둥글" in hook
        or "모서리가 둥글" in hook
    )
    if bland_hook or issue:
        micro["hook"] = "비행기 창문은 네모가 아니라 모서리가 둥근 형태입니다."
    if question and (issue or "비행기 창문" in question or "창문 모서리" in question):
        micro["core_question"] = "그런데 왜 굳이 이런 모양일까요?"
        result["core_question"] = micro["core_question"]

    payoff = str(micro.get("payoff", "")).strip()
    # Remove the Run's unnecessarily dramatic transition word while retaining
    # the trusted FAA record's fatigue -> fuselage rupture progression.
    payoff = payoff.replace(
        "동체 파열로 빠르게 이어질 수 있었습니다",
        "동체 파열로 진행될 수 있었습니다",
    )
    if payoff:
        micro["payoff"] = payoff

    result["micro_narrative"] = micro
    return result

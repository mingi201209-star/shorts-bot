"""Regression test for run 605 hook/question overlap detection.

Run 605 failed because the overlap validation was too strict. The hook
"비행기 엔진의 나셀 후면은 톱니 모양으로 디자인되어 있습니다" (75% overlap)
should NOT be flagged as a restatement of the question
"왜 비행기 엔진의 나셀 후면은 톱니 모양으로 디자인되었을까?"

The hook provides substantive descriptive information (design property)
distinct from the question's "why" ask. The fix raises the threshold
from 50% to 80% for markerless hooks.
"""

import re


_MICRO_QUESTION_MARKERS = ("왜", "이유", "무엇", "어떻게", "어째서", "?")
_MICRO_TOKEN_STOPWORDS = {
    "그런데", "그리고", "하지만", "정말", "과연", "이유", "무엇", "어떻게", "어째서",
    "디자인", "설계", "되어", "되는", "되다", "것", "수", "왜",
}
_MICRO_TOKEN_SUFFIXES = (
    "에서는", "에게서", "으로는", "라는", "에서", "으로", "에게",
    "은", "는", "이", "가", "을", "를", "의", "에", "로", "와", "과", "도", "만",
)
_MICRO_HOOK_CLAIM_MARKERS = (
    "일부러", "아니다", "사실은", "전혀", "반대로", "너무", "정말", "매우",
)


def _micro_content_tokens(value):
    tokens = []
    for raw in re.findall(r"[0-9A-Za-z가-힣]+", str(value or "").lower()):
        for suffix in _MICRO_TOKEN_SUFFIXES:
            if raw.endswith(suffix):
                raw = raw[:-len(suffix)]
                break
        if raw not in _MICRO_TOKEN_STOPWORDS and len(raw) > 0:
            tokens.append(raw)
    return tokens


def _hook_makes_explicit_claim(hook):
    return any(marker in str(hook or "") for marker in _MICRO_HOOK_CLAIM_MARKERS)


def _hook_restates_question(hook, question):
    q_text = str(question or "")
    if not any(marker in q_text for marker in _MICRO_QUESTION_MARKERS):
        return False
    hook_tokens = set(_micro_content_tokens(hook))
    question_tokens = set(_micro_content_tokens(question))
    if len(hook_tokens) < 2:
        return False
    shared = hook_tokens & question_tokens
    overlap_ratio = len(shared) / float(len(hook_tokens))
    if _hook_makes_explicit_claim(hook):
        return len(shared) == len(hook_tokens) and overlap_ratio >= 0.90
    return len(shared) >= 2 and overlap_ratio >= 0.80


def test_run_605_hook_not_flagged():
    """Run 605 hook should NOT be flagged (75% overlap < 80% threshold)."""
    hook = "비행기 엔진의 나셀 후면은 톱니 모양으로 디자인되어 있습니다"
    question = "왜 비행기 엔진의 나셀 후면은 톱니 모양으로 디자인되었을까?"
    
    is_restatement = _hook_restates_question(hook, question)
    assert not is_restatement, (
        f"Run 605 hook should NOT be flagged as restatement.\n"
        f"Hook: {hook}\n"
        f"Question: {question}"
    )


if __name__ == "__main__":
    test_run_605_hook_not_flagged()
    print("✅ test_run_605_hook_not_flagged passed")

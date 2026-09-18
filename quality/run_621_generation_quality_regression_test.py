"""Regression test for the run-621 generation-quality fix.

Run 621 (job 35401815431, commit 11c151f) showed that both bounded-recovery
mechanisms added earlier this session (Narrowness self-critique recovery in
content/candidate_explorer.py, Candidate Gate recovery in
content/candidate_gate.py) worked exactly as designed -- bounded, no
forced-pass -- but kept failing anyway: candidates rejected as "too broad"
were rewritten and rechecked, but the rewrites themselves kept coming back
broad/generic, exhausting both 2-cycle bounds repeatedly and burning API
calls up to 57/60 without ever producing a passing Winner.

Per 민기's explicit decision, this fix does NOT touch any gate threshold or
add more recovery calls. It:

  1. Strengthens the Explorer's generation prompt (section 3C) with a
     semantic (not keyword) 4-element contract -- concrete subject,
     observable phenomenon, specific question, specific reveal -- plus
     short BAD->GOOD few-shot blocks for questions and reveals.
  2. Strengthens both rewrite prompts (_NARROWNESS_REWRITE_PROMPT,
     _CANDIDATE_GATE_REWRITE_PROMPT) to require narrowing along one
     concrete axis (part/location/condition/number/exception/before-after/
     shape) instead of vague "be more specific", and to instruct against a
     reveal that stops at a bare generic-purpose word.
  3. Adds budget-awareness (`has_budget_for_rewrite`) to both recovery
     loops so a rewrite cycle is skipped -- discarding the candidate, same
     as hitting the existing 2-rewrite cap -- once the API budget reserve
     is too low, instead of risking exhausting V3_MAX_API_CALLS /
     V3_MAX_COST_USD mid-call.
  4. Adds a conservative, deterministic pre-check
     (`_is_trivially_generic_question`) that skips the expensive LLM
     Narrowness self-critique call only for a bare "왜 효율적/안전/
     최적화되는가" pattern with nothing else concrete in the sentence.

None of this changes any PASS/FAIL threshold or adds a forced-pass path.
This test uses a mocked OpenAI client / mocked budget accessor (no real API
calls, no network).
"""

import json
from unittest.mock import MagicMock, patch


def _load_legacy_module():
    import content.candidate_explorer as ce_pkg

    return ce_pkg._LEGACY


def _load_gate_module():
    import content.candidate_gate as cg

    return cg


def _make_response(payload):
    msg = MagicMock()
    msg.content = json.dumps(payload, ensure_ascii=False)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _candidate(topic, question, reveal, angle="테스트 앵글"):
    return {
        "topic": topic,
        "angle": angle,
        "core_question": question,
        "micro_narrative": {
            "hook": "테스트 hook",
            "core_question": question,
            "reveal": reveal,
            "payoff": "테스트 payoff",
        },
        "fact_check_focus": [],
        "visual_proof": ["테스트 증거"],
        "selection_reason": "테스트 이유",
    }


_FAKE_USAGE = {"cost_usd": 0.0001, "over_budget": False}

# Concrete examples drawn from this session's own material (used in the
# strengthened prompt's few-shot blocks), for the false-positive-safety
# checks below.
_CONCRETE_EXAMPLES = [
    "맨홀 뚜껑은 왜 대부분 원형일까?",
    "사막의 카나트는 왜 지하에 완만한 경사를 만들었을까?",
    "비행기 날개 끝은 왜 위로 꺾여 있을까?",
    "다리 상판 사이의 틈은 왜 일부러 비워둘까?",
]

_GENERIC_EXAMPLES = [
    "비행기 날개는 왜 효율적일까?",
    "이 구조물은 왜 안전한가?",
    "이 시스템은 왜 최적화되는가?",
]


def _patched_explorer(ce, side_effect):
    return (
        patch.object(ce, "authorize_call", return_value=1),
        patch.object(ce, "record_usage", return_value=_FAKE_USAGE),
        patch.object(ce, "print_budget_status"),
        patch.object(ce.openai.chat.completions, "create", side_effect=side_effect),
    )


# ------------------------------------------------------------------
# Gate behavior unchanged: concrete-subject + generic reveal still
# rejected; concrete/specific reveal still accepted. (Thresholds live in
# the LLM-judged gate itself, so this exercises the wiring around it with
# a mocked verdict -- the point is that neither PASS/FAIL branch changed.)
# ------------------------------------------------------------------

def test_generic_reveal_still_rejected_by_unmodified_narrowness_gate():
    ce = _load_legacy_module()
    winner = _candidate(
        "비행기 날개",
        "비행기 날개는 왜 공기 흐름을 최적화할까?",
        "공기의 흐름을 최적화하기 위해 설계되었다.",
    )
    critique = {"verdict": "TOO_BROAD", "reason": "일반적 목적어로 끝남 (test)"}
    side_effect = [_make_response(critique)]

    p1, p2, p3, p4 = _patched_explorer(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce._self_critique_narrowness(winner)
        assert result["verdict"] == "TOO_BROAD"


def test_concrete_reveal_still_accepted_by_unmodified_narrowness_gate():
    ce = _load_legacy_module()
    winner = _candidate(
        "맨홀 뚜껑",
        "맨홀 뚜껑은 왜 대부분 원형일까?",
        "원형이 아니면 대각선으로 기울여 구멍 아래로 빠뜨릴 수 있지만, "
        "원형은 어느 방향으로 기울여도 지름보다 커서 구멍에 빠지지 않기 때문이다.",
    )
    critique = {"verdict": "NARROW_ENOUGH", "reason": "구체적 메커니즘 (test)"}
    side_effect = [_make_response(critique)]

    p1, p2, p3, p4 = _patched_explorer(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce._self_critique_narrowness(winner)
        assert result["verdict"] == "NARROW_ENOUGH"


# ------------------------------------------------------------------
# Rewrite prompts: subject preservation + concrete-axis instruction.
# ------------------------------------------------------------------

def test_narrowness_rewrite_prompt_requires_same_subject_and_concrete_axis():
    ce = _load_legacy_module()
    prompt = ce._NARROWNESS_REWRITE_PROMPT

    assert "같은 대상" in prompt
    assert "다른 사물/장소/현상으로 바꾸면 안 된다" in prompt

    for axis_word in ("부품", "위치", "조건", "수치", "예외", "전후", "모양"):
        assert axis_word in prompt

    # Anti-generic-reveal instruction present, phrased as guidance, not a
    # literal string ban (the words themselves are allowed to appear, but
    # the model must not stop there).
    assert "일반적 목적어" in prompt
    assert "한 단계 더" in prompt


def test_candidate_gate_rewrite_prompt_requires_same_subject_and_concrete_axis():
    cg = _load_gate_module()
    prompt = cg._CANDIDATE_GATE_REWRITE_PROMPT

    assert "같은 대상" in prompt
    assert "다른 사물/장소/현상으로 바꾸면 안 된다" in prompt

    for axis_word in ("부품", "위치", "조건", "수치", "예외", "전후", "모양"):
        assert axis_word in prompt

    assert "일반적 목적어" in prompt
    assert "한 단계 더" in prompt


def test_rewrite_preserves_same_subject_topic():
    ce = _load_legacy_module()
    winner = _candidate(
        "비행기 날개 끝 윙렛",
        "비행기 날개는 왜 공기 흐름을 최적화할까?",
        "공기의 흐름을 최적화하기 위해서다.",
    )
    rewritten_payload = _candidate(
        "비행기 날개 끝 윙렛",
        "비행기 날개 끝은 왜 위로 꺾여 있을까?",
        "임계각을 넘는 순간에만 유도 항력이 급격히 커지기 때문이다.",
    )
    side_effect = [_make_response(rewritten_payload)]

    p1, p2, p3, p4 = _patched_explorer(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce._rewrite_narrower_candidate(winner, "너무 넓음 (test)")
        assert result["topic"] == winner["topic"]


# ------------------------------------------------------------------
# Max rewrite count still respected (unchanged bound of 2).
# ------------------------------------------------------------------

def test_max_narrowness_rewrites_still_two():
    ce = _load_legacy_module()
    assert ce.MAX_NARROWNESS_REWRITES == 2


def test_max_candidate_gate_rewrites_still_two():
    cg = _load_gate_module()
    assert cg.MAX_CANDIDATE_GATE_REWRITES == 2


# ------------------------------------------------------------------
# Budget-reserve logic: below reserve -> no rewrite attempted.
# ------------------------------------------------------------------

def test_has_budget_for_rewrite_true_when_plenty_left():
    from quality import budget_guard

    with patch.object(
        budget_guard,
        "get_budget_status",
        return_value={
            "calls": 5,
            "max_calls": 60,
            "cost_usd": 0.001,
            "max_cost_usd": 0.05,
        },
    ):
        assert budget_guard.has_budget_for_rewrite() is True


def test_has_budget_for_rewrite_false_when_reserve_too_low():
    from quality import budget_guard

    with patch.object(
        budget_guard,
        "get_budget_status",
        return_value={
            "calls": 57,
            "max_calls": 60,
            "cost_usd": 0.0495,
            "max_cost_usd": 0.05,
        },
    ):
        assert budget_guard.has_budget_for_rewrite() is False


def test_narrowness_recovery_skips_rewrite_when_budget_low_no_extra_call():
    """When the budget reserve is too low, the recovery loop must discard
    the candidate WITHOUT making the rewrite API call at all (verified by
    the mocked `create` never being invoked for a rewrite)."""

    ce = _load_legacy_module()

    winner_response = _candidate(
        "비행기 날개",
        "비행기 날개는 왜 공기 흐름을 최적화할까?",
        "공기의 흐름을 최적화하기 위해서다.",
    )
    broad_critique = {"verdict": "TOO_BROAD", "reason": "너무 넓음 (test)"}

    create_mock = MagicMock(
        side_effect=[_make_response(broad_critique)],
    )

    with patch.object(ce, "authorize_call", return_value=1), patch.object(
        ce, "record_usage", return_value=_FAKE_USAGE
    ), patch.object(ce, "print_budget_status"), patch.object(
        ce.openai.chat.completions, "create", create_mock
    ), patch.object(
        ce, "has_budget_for_rewrite", return_value=False
    ):
        critique = ce._self_critique_narrowness(winner_response["micro_narrative"] and winner_response)
        rewrite_attempts = 0
        while (
            critique.get("verdict") == "TOO_BROAD"
            and rewrite_attempts < ce.MAX_NARROWNESS_REWRITES
        ):
            if not ce.has_budget_for_rewrite():
                break
            rewrite_attempts += 1

        assert rewrite_attempts == 0
        # Only the initial critique call happened -- no rewrite call.
        assert create_mock.call_count == 1


# ------------------------------------------------------------------
# No forced-pass path: rewrite loop discards after bound is hit, never
# fabricates a NARROW_ENOUGH / PASS verdict.
# ------------------------------------------------------------------

def test_no_forced_pass_after_rewrites_exhausted():
    ce = _load_legacy_module()

    still_broad = {"verdict": "TOO_BROAD", "reason": "여전히 넓음 (test)"}
    rewritten = _candidate("주제", "여전히 넓은 질문?", "여전히 일반적인 답이다.")

    side_effect = [
        _make_response(still_broad),
        _make_response(rewritten),
        _make_response(still_broad),
        _make_response(rewritten),
        _make_response(still_broad),
    ]

    p1, p2, p3, p4 = _patched_explorer(ce, side_effect)
    winner = _candidate("주제", "넓은 질문?", "일반적인 답이다.")
    with p1, p2, p3, p4:
        critique = ce._self_critique_narrowness(winner)
        rewrite_attempts = 0
        while (
            critique.get("verdict") == "TOO_BROAD"
            and rewrite_attempts < ce.MAX_NARROWNESS_REWRITES
        ):
            r = ce._rewrite_narrower_candidate(winner, critique.get("reason", ""))
            rewrite_attempts += 1
            if r is None:
                continue
            winner = r
            critique = ce._self_critique_narrowness(winner)

        assert critique["verdict"] == "TOO_BROAD"
        assert rewrite_attempts == ce.MAX_NARROWNESS_REWRITES


# ------------------------------------------------------------------
# D.3 deterministic pre-check: true positive + false-positive safety.
# ------------------------------------------------------------------

def test_precheck_catches_bare_generic_question():
    ce = _load_legacy_module()
    for q in _GENERIC_EXAMPLES:
        assert ce._is_trivially_generic_question(q) is True, q


def test_precheck_does_not_flag_concrete_questions():
    ce = _load_legacy_module()
    for q in _CONCRETE_EXAMPLES:
        assert ce._is_trivially_generic_question(q) is False, q


def test_precheck_skips_llm_call_for_generic_question():
    ce = _load_legacy_module()
    winner = _candidate(
        "비행기 날개",
        "비행기 날개는 왜 효율적일까?",
        "효율적으로 설계되었기 때문이다.",
    )
    create_mock = MagicMock()
    with patch.object(ce.openai.chat.completions, "create", create_mock):
        result = ce._self_critique_narrowness(winner)
        assert result["verdict"] == "TOO_BROAD"
        create_mock.assert_not_called()


if __name__ == "__main__":
    import sys
    import traceback

    tests = [
        (name, obj)
        for name, obj in list(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)

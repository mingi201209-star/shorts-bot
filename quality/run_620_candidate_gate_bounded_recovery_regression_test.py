"""Regression test for the run-618/619 Candidate Gate bounded-recovery fix.

Production runs 618/619 showed the same failure mode Narrowness
self-critique had before its own bounded recovery (see
``quality/run_618_narrowness_bounded_recovery_regression_test.py``), but for
a DIFFERENT, SEPARATE gate: Candidate Gate (content/candidate_gate.py,
"V3.2.1.2 CANDIDATE GATE"), which runs after Candidate Gate's own
independent LLM-judge call, later in the pipeline than the Narrowness
self-critique. Run 619's candidate "광활한 사막에 위치한 마을의 수원지"
(Question: "이 마을 사람들은 어떻게 한정된 물을 효과적으로 관리할 수
있을까?") was correctly rejected by Candidate Gate with reason "질문이
지나치게 넓고 일반적이며, Reveal이 구체적인 메커니즘이나 예상 밖의 연결을
제공하지 않음" -- but the only reaction available was to discard the whole
subject and spend a fresh Candidate Explorer attempt on an unrelated topic.

The fix is bounded recovery, NOT a weaker gate, applying the exact same
shape as the Narrowness self-critique fix:

  - When Candidate Gate returns REGENERATE, ``evaluate_candidate`` now
    feeds the Gate's own rejection reason back into a targeted rewrite of
    the SAME subject (never a new topic) asking for a version that
    resolves it, and reruns the EXACT SAME, unmodified
    ``_evaluate_candidate_once()`` on the rewrite.
  - Because a rewrite could plausibly reintroduce the kind of broadness the
    separate Narrowness self-critique gate already guards against, the
    rewritten candidate is also re-checked there before being resubmitted
    to Candidate Gate -- exactly as rigorously as a freshly generated
    Winner.
  - This can happen at most ``MAX_CANDIDATE_GATE_REWRITES`` (2) times per
    candidate. After that many failures, the candidate is discarded and
    the original REGENERATE result is returned exactly like before, so the
    outer Candidate Loop in main.py still moves on to a fresh topic
    direction (unchanged discard-and-retry logic in main.py around
    "🚫 WINNER CANDIDATE GATE REJECT" / "➡️ Candidate Explorer 재탐색").
  - There is no bypass, no forced-pass, and no boosted score anywhere in
    this path: the only way a recovered candidate is accepted is by the
    real, unmodified ``_evaluate_candidate_once()`` returning PASS (and,
    before that, the real, unmodified Narrowness self-critique not
    flagging TOO_BROAD).

This test uses a mocked OpenAI client / mocked gate functions (no real API
calls, no network) and covers:
  1. A genuinely broad/generic Candidate Gate rejection (the run-619
     "사막 마을 수원지" case) is still rejected by the unmodified
     ``_evaluate_candidate_once`` itself, no rewrite loop involved.
  2. A rejected candidate gets rewritten narrower using the Gate's own
     rejection reason as input, preserving the same subject/topic, and the
     rewritten candidate is re-submitted to the SAME Gate function; a
     single successful rewrite is accepted, and the caller's candidate
     dict is mutated in place so the rest of the pipeline uses the
     rewritten (passing) content, not the original discarded one.
  3. The rewrite/recovery loop is bounded: after
     ``MAX_CANDIDATE_GATE_REWRITES`` rewrites that are still REGENERATE,
     ``evaluate_candidate`` gives up and returns REGENERATE -- it does not
     loop forever.
  4. A rewrite that would pass Candidate Gate but reintroduces broadness at
     the separate Narrowness self-critique gate is still rejected (the
     recovered candidate is validated exactly as rigorously as a fresh
     one), and that failed attempt still counts against the bound.
  5. There is no forced-pass path: the original candidate's own dict is
     untouched unless a rewrite genuinely passes both gates, and PASS is
     only reachable via a real PASS verdict from the unmodified Gate.
"""

import json
from unittest.mock import MagicMock, patch


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

# Run 619's actual rejected candidate and the Gate's actual rejection
# reason text.
_BROAD_CANDIDATE = _candidate(
    "광활한 사막에 위치한 마을의 수원지",
    "이 마을 사람들은 어떻게 한정된 물을 효과적으로 관리할 수 있을까?",
    "마을 사람들은 물을 아껴 쓰고 효율적으로 분배한다.",
)
_BROAD_GATE_REASON = (
    "질문이 지나치게 넓고 일반적이며, Reveal이 구체적인 메커니즘이나 "
    "예상 밖의 연결을 제공하지 않음"
)


def _patched(cg, side_effect):
    return (
        patch.object(cg, "authorize_call", return_value=1),
        patch.object(cg, "record_usage", return_value=_FAKE_USAGE),
        patch.object(cg, "print_budget_status"),
        patch.object(cg.openai.chat.completions, "create", side_effect=side_effect),
    )


# ------------------------------------------------------------------
# 1: the unmodified underlying Gate check itself is untouched.
# ------------------------------------------------------------------

def test_broad_candidate_rejected_by_unmodified_gate():
    cg = _load_gate_module()
    gate_response = {"status": "REGENERATE", "reason": _BROAD_GATE_REASON}
    side_effect = [_make_response(gate_response)]

    p1, p2, p3, p4 = _patched(cg, side_effect)
    with p1, p2, p3, p4:
        result = cg._evaluate_candidate_once(dict(_BROAD_CANDIDATE))
        assert result["status"] == "REGENERATE"
        assert result["reason"] == _BROAD_GATE_REASON


# ------------------------------------------------------------------
# 2: targeted rewrite on the SAME subject, using the Gate's own reason,
# succeeding on the first retry, with the caller's dict mutated in place.
# ------------------------------------------------------------------

def test_rejected_candidate_rewritten_and_accepted_mutates_in_place():
    cg = _load_gate_module()

    reject = {"status": "REGENERATE", "reason": _BROAD_GATE_REASON}
    passed = {"status": "PASS", "reason": "구체적인 관개 시스템 임계 조건 (test)"}

    rewritten = _candidate(
        "광활한 사막에 위치한 마을의 수원지",
        "이 마을은 지하수위가 특정 깊이 아래로 떨어지는 순간에만 "
        "저수조 밸브를 자동으로 잠그는데, 그 임계 깊이는 어떻게 정해졌을까?",
        "지하수위가 임계 깊이를 넘으면 염분 역류가 급격히 심해지기 때문에, "
        "그 직전 지점에서 자동으로 취수를 끊도록 설계했다.",
    )

    # narrowness self-critique recheck used by the recovery path.
    narrow_ok_critique = {"verdict": "NARROW_ENOUGH", "reason": "임계 깊이 조건 구체적 (test)"}

    side_effect = [
        _make_response(reject),      # 1: initial Gate call -> REGENERATE
        _make_response(rewritten),   # 2: rewrite call
        _make_response(passed),      # 3: Gate re-check on rewrite -> PASS
    ]

    candidate = dict(_BROAD_CANDIDATE)

    p1, p2, p3, p4 = _patched(cg, side_effect)
    with p1, p2, p3, p4 as mock_create, patch.object(
        cg, "_narrowness_recheck_ok", return_value=(True, "")
    ) as mock_narrowness:
        result = cg.evaluate_candidate(candidate)

        assert result["status"] == "PASS"
        # Same subject preserved.
        assert candidate["topic"] == "광활한 사막에 위치한 마을의 수원지"
        assert "지하수위" in candidate["core_question"]
        assert mock_create.call_count == 3
        assert mock_narrowness.call_count == 1


def test_gate_rewrite_preserves_grounding_and_evidence_authority():
    cg = _load_gate_module()

    original = _candidate(
        "비행기 날개",
        "비행기 날개는 하중을 받을 때 왜 휘고 비틀리는가?",
        "하중에 따라 날개 구조가 탄성 변형한다.",
    )
    original["fact_check_focus"] = [
        "주익의 스파와 윙박스가 하중을 분산한다.",
    ]
    original["visual_proof"] = [
        "비행 중 같은 날개의 실제 flex 변화",
    ]
    original["subject_kind"] = "physical_entity"
    original["canonical_subject"] = "비행기 날개"
    original["subject_identity_confidence"] = 0.95
    original["grounding_evidence"] = [
        {
            "evidence_type": "explicit_candidate_identity",
            "supports_subject": "비행기 날개",
            "source": "candidate_text",
            "detail": "topic explicitly names 비행기 날개",
        }
    ]

    model_rewrite = _candidate(
        "비행기 날개",
        "비행기 날개는 하중을 받을 때 어느 구조가 먼저 휘는가?",
        "스파와 윙박스가 하중을 나누며 탄성 변형한다.",
    )
    model_rewrite["fact_check_focus"] = ["모델이 새로 만든 미확인 주장"]
    model_rewrite["visual_proof"] = ["모델이 새로 만든 미확인 화면"]

    p1, p2, p3, p4 = _patched(cg, [_make_response(model_rewrite)])
    with p1, p2, p3, p4:
        rewritten = cg._rewrite_candidate_for_gate_feedback(
            original,
            "Reveal이 일반적임 (test)",
        )

    assert rewritten is not None
    assert rewritten["topic"] == original["topic"]
    assert rewritten["fact_check_focus"] == original["fact_check_focus"]
    assert rewritten["visual_proof"] == original["visual_proof"]
    assert rewritten["subject_kind"] == "physical_entity"
    assert rewritten["canonical_subject"] == "비행기 날개"
    assert rewritten["grounding_evidence"] == original["grounding_evidence"]


def test_gate_rewrite_rejects_unsupported_numeric_detail():
    cg = _load_gate_module()

    original = _candidate(
        "비행기 날개",
        "비행기 날개는 하중을 받을 때 왜 휘고 비틀리는가?",
        "하중에 따라 날개 구조가 탄성 변형한다.",
    )
    original["fact_check_focus"] = ["날개 하중과 탄성 변형의 관계"]
    original["visual_proof"] = ["비행 중 같은 날개의 실제 flex 변화"]

    fabricated = _candidate(
        "비행기 날개",
        "날개 끝 비틀림이 중간부보다 20% 더 큰 이유는 무엇인가?",
        "특정 재료 조합 때문에 20% 차이가 난다.",
    )

    p1, p2, p3, p4 = _patched(cg, [_make_response(fabricated)])
    with p1, p2, p3, p4:
        rewritten = cg._rewrite_candidate_for_gate_feedback(
            original,
            "Reveal이 일반적임 (test)",
        )

    assert rewritten is None


# ------------------------------------------------------------------
# 3: bounded retry -- stops after MAX_CANDIDATE_GATE_REWRITES and discards.
# ------------------------------------------------------------------

def test_recovery_limit_respected_then_discards():
    cg = _load_gate_module()
    assert cg.MAX_CANDIDATE_GATE_REWRITES == 2, (
        "spec calls for 2 rewrite attempts; if this constant changes, "
        "update this test's expected call_count deliberately"
    )

    reject = {"status": "REGENERATE", "reason": _BROAD_GATE_REASON}
    rewritten = _candidate(
        "광활한 사막에 위치한 마을의 수원지",
        "이 마을 사람들은 어떻게 한정된 물을 효과적으로 관리할 수 있을까?",
        "여전히 일반적인 설명이다.",
    )

    side_effect = [
        _make_response(reject),      # initial Gate call
        _make_response(rewritten),   # rewrite attempt 1
        _make_response(reject),      # Gate re-check -> still REGENERATE
        _make_response(rewritten),   # rewrite attempt 2
        _make_response(reject),      # Gate re-check -> still REGENERATE, limit reached
    ]

    candidate = dict(_BROAD_CANDIDATE)

    p1, p2, p3, p4 = _patched(cg, side_effect)
    with p1, p2, p3, p4 as mock_create, patch.object(
        cg, "_narrowness_recheck_ok", return_value=(True, "")
    ):
        result = cg.evaluate_candidate(candidate)
        assert result["status"] == "REGENERATE"
        assert result["reason"] == _BROAD_GATE_REASON
        # 1 (initial) + 2 * (rewrite + re-check) == 5 calls, no more.
        assert mock_create.call_count == 5
        # original candidate is untouched (no successful rewrite ever
        # passed both gates).
        assert candidate == _BROAD_CANDIDATE


# ------------------------------------------------------------------
# 4: a rewrite that would satisfy Candidate Gate but reintroduces
# broadness at the Narrowness self-critique gate must still be rejected.
# ------------------------------------------------------------------

def test_rewrite_still_blocked_by_narrowness_recheck():
    cg = _load_gate_module()

    reject = {"status": "REGENERATE", "reason": _BROAD_GATE_REASON}
    rewritten = _candidate(
        "광활한 사막에 위치한 마을의 수원지",
        "이 마을은 물을 어떻게 관리할까? (더 구체적으로 보이지만 여전히 넓음)",
        "효율적으로 분배한다.",
    )

    # The Narrowness recheck is mocked to always fail below, so the
    # (mocked) Candidate Gate re-check is never actually reached on either
    # rewrite attempt -- only the initial Gate call and the two rewrite
    # calls hit the OpenAI client.
    side_effect = [
        _make_response(reject),    # initial Gate call
        _make_response(rewritten),  # rewrite attempt 1
        _make_response(rewritten),  # rewrite attempt 2
    ]

    candidate = dict(_BROAD_CANDIDATE)

    p1, p2, p3, p4 = _patched(cg, side_effect)
    with p1, p2, p3, p4 as mock_create, patch.object(
        cg, "_narrowness_recheck_ok", return_value=(False, "여전히 넓음 (test)")
    ) as mock_narrowness:
        result = cg.evaluate_candidate(candidate)

        # The Gate call that would have PASSed is never even reached
        # because the Narrowness recheck blocked it first, both times.
        assert result["status"] == "REGENERATE"
        assert "Narrowness" in result["reason"]
        assert mock_narrowness.call_count == 2
        assert mock_create.call_count == 3
        # No forced pass; original candidate untouched.
        assert candidate == _BROAD_CANDIDATE


# ------------------------------------------------------------------
# 5: no forced-pass path exists anywhere in this code.
# ------------------------------------------------------------------

def test_no_forced_pass_in_source():
    import inspect

    cg = _load_gate_module()
    source = inspect.getsource(cg.evaluate_candidate)
    source += inspect.getsource(cg._rewrite_candidate_for_gate_feedback)
    source += inspect.getsource(cg._narrowness_recheck_ok)

    # The only strings that assign a "PASS" status anywhere in this new
    # code are the ones flowing straight from _evaluate_candidate_once's
    # real result -- there is no `"status": "PASS"` literal fabricated by
    # the recovery wiring itself.
    assert '"status": "PASS"' not in source
    assert "status='PASS'" not in source


if __name__ == "__main__":
    test_broad_candidate_rejected_by_unmodified_gate()
    print("✓ test_broad_candidate_rejected_by_unmodified_gate")

    test_rejected_candidate_rewritten_and_accepted_mutates_in_place()
    print("✓ test_rejected_candidate_rewritten_and_accepted_mutates_in_place")

    test_gate_rewrite_preserves_grounding_and_evidence_authority()
    print("✓ test_gate_rewrite_preserves_grounding_and_evidence_authority")

    test_gate_rewrite_rejects_unsupported_numeric_detail()
    print("✓ test_gate_rewrite_rejects_unsupported_numeric_detail")

    test_recovery_limit_respected_then_discards()
    print("✓ test_recovery_limit_respected_then_discards")

    test_rewrite_still_blocked_by_narrowness_recheck()
    print("✓ test_rewrite_still_blocked_by_narrowness_recheck")

    test_no_forced_pass_in_source()
    print("✓ test_no_forced_pass_in_source")

    print("\n✅ All tests passed")

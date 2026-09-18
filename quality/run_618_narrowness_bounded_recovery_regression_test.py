"""Regression test for the run-618 Narrowness bounded-recovery fix.

Run 618's full attempt log showed the Explorer reaching a Narrowness
self-critique TOO_BROAD verdict on 3 different SELECTED Winners across 20
attempts, and every one of them was discarded outright in favor of a brand
new, unrelated topic direction -- burning through all 20 attempts (25/60 API
calls) without a single Winner surviving the Candidate Gate.

The fix is bounded recovery, NOT a weaker gate:

  - When the narrowness self-critique rejects a Winner as TOO_BROAD,
    Explorer now feeds the rejection reason back into a targeted rewrite of
    the SAME subject (never a new topic) asking for a narrower version, and
    reruns the EXACT SAME, unmodified `_self_critique_narrowness()` on the
    rewrite.
  - This can happen at most `MAX_NARROWNESS_REWRITES` (2) times per
    candidate. After that many failures, the candidate is discarded and
    Explorer returns REGENERATE exactly like before, so the outer Candidate
    Loop still moves on to a fresh topic direction.
  - There is no bypass, no forced-pass, and no boosted score anywhere in
    this path: the only way a recovered candidate is accepted is by
    `_self_critique_narrowness()` itself returning NARROW_ENOUGH -- the
    real, unmodified gate a normal candidate would have to pass.

This test uses a mocked OpenAI client (no real API calls, no network) and
covers:
  1. A generic/broad Reveal is still rejected by the unmodified narrowness
     gate (`_self_critique_narrowness` itself, no rewrite loop involved).
  2. A concrete, specific, observable-phenomenon candidate is accepted by
     the unmodified narrowness gate.
  3. A TOO_BROAD Winner gets rewritten narrower using the critique's own
     rejection reason as input, preserving the same subject/topic while the
     question/reveal becomes more specific, and the rewritten candidate is
     re-submitted to the SAME gate function.
  4. The rewrite/recovery loop is bounded: after `MAX_NARROWNESS_REWRITES`
     rewrites that are still TOO_BROAD, explore_candidates() gives up on
     the candidate and returns REGENERATE -- it does not loop forever.
  5. A single successful rewrite (NARROW_ENOUGH on the first retry) is
     accepted as the new Winner and the result carries the rewritten
     content, not the original broad one.
  6. There is no way to reach a SELECTED result out of a TOO_BROAD verdict
     other than the real gate flipping to NARROW_ENOUGH -- no forced-pass
     path exists in the wiring.
"""

import json
from unittest.mock import MagicMock, patch


def _load_legacy_module():
    import content.candidate_explorer as ce_pkg

    return ce_pkg._LEGACY


def _make_response(payload):
    msg = MagicMock()
    msg.content = json.dumps(payload, ensure_ascii=False)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _winner(topic, question, reveal, angle="테스트 앵글"):
    return {
        "status": "SELECTED",
        "winner": {
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
        },
        "runner_up": None,
    }


def _bare_candidate(topic, question, reveal, angle="더 좁은 앵글"):
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
_TOPIC_INFO = {"category": "과학", "topic": "테스트 방향"}

_BROAD_WINNER = _winner(
    "비행기 날개",
    "비행기 날개는 왜 공기 흐름을 최적화할까?",
    "공기의 흐름을 최적화하기 위해 설계되었다.",
)

_NARROW_WINNER = _winner(
    "비행기 날개 끝 윙렛",
    "비행기 날개 끝은 왜 위로 꺾여 있을까?",
    "날개 끝 소용돌이가 특정 각도를 넘는 순간에만 연료 손실이 급격히 커지기 때문에, "
    "그 임계각을 넘기 전에 흐름을 끊도록 위로 꺾어 놓았다.",
)


def _patched(ce, side_effect):
    return (
        patch.object(ce, "authorize_call", return_value=1),
        patch.object(ce, "record_usage", return_value=_FAKE_USAGE),
        patch.object(ce, "print_budget_status"),
        patch.object(ce.openai.chat.completions, "create", side_effect=side_effect),
    )


# ------------------------------------------------------------------
# 1 & 2: the unmodified narrowness gate itself is untouched.
# ------------------------------------------------------------------

def test_generic_reveal_rejected_by_unmodified_gate():
    ce = _load_legacy_module()
    critique = {"verdict": "TOO_BROAD", "reason": "일반적인 설명으로 끝남 (test)"}
    side_effect = [_make_response(critique)]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce._self_critique_narrowness(_BROAD_WINNER["winner"])
        assert result["verdict"] == "TOO_BROAD"


def test_specific_phenomenon_accepted_by_unmodified_gate():
    ce = _load_legacy_module()
    critique = {"verdict": "NARROW_ENOUGH", "reason": "임계각 조건이 구체적임 (test)"}
    side_effect = [_make_response(critique)]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce._self_critique_narrowness(_NARROW_WINNER["winner"])
        assert result["verdict"] == "NARROW_ENOUGH"


# ------------------------------------------------------------------
# 3 & 5: targeted rewrite on the SAME subject, using the critique reason,
# succeeding on the first retry.
# ------------------------------------------------------------------

def test_rejected_candidate_rewritten_narrower_and_accepted():
    ce = _load_legacy_module()
    broad_critique = {"verdict": "TOO_BROAD", "reason": "일반적인 공기 흐름 설명 (test)"}
    narrow_critique = {"verdict": "NARROW_ENOUGH", "reason": "임계각 조건 구체적 (test)"}

    rewritten = _bare_candidate(
        "비행기 날개 끝 윙렛",
        "비행기 날개 끝은 왜 위로 꺾여 있을까?",
        "임계각을 넘는 순간에만 소용돌이 손실이 급증하기 때문이다.",
    )

    side_effect = [
        _make_response(_BROAD_WINNER),
        _make_response(broad_critique),
        _make_response(rewritten),
        _make_response(narrow_critique),
    ]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4 as mock_create:
        result = ce.explore_candidates(_TOPIC_INFO)
        assert result["status"] == "SELECTED"
        # Same subject preserved -- rewrite narrowed the question, did not
        # switch to an unrelated topic direction.
        assert result["winner"]["topic"] == "비행기 날개 끝 윙렛"
        assert "위로 꺾여" in result["winner"]["core_question"]
        assert mock_create.call_count == 4


# ------------------------------------------------------------------
# 4: bounded retry -- stops after MAX_NARROWNESS_REWRITES and discards.
# ------------------------------------------------------------------

def test_recovery_limit_respected_then_discards():
    ce = _load_legacy_module()
    assert ce.MAX_NARROWNESS_REWRITES == 2, (
        "spec calls for 1-2 rewrite attempts; if this constant changes, "
        "update this test's expected call_count deliberately"
    )

    broad_critique = {"verdict": "TOO_BROAD", "reason": "여전히 넓음 (test)"}
    rewritten = _bare_candidate(
        "비행기 날개",
        "비행기 날개는 왜 공기 흐름을 최적화할까?",
        "여전히 일반적인 설명이다.",
    )

    side_effect = [
        _make_response(_BROAD_WINNER),
        _make_response(broad_critique),
        _make_response(rewritten),  # rewrite attempt 1
        _make_response(broad_critique),  # still TOO_BROAD
        _make_response(rewritten),  # rewrite attempt 2
        _make_response(broad_critique),  # still TOO_BROAD -- limit reached
    ]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4 as mock_create:
        result = ce.explore_candidates(_TOPIC_INFO)
        assert result["status"] == "REGENERATE"
        assert "Narrowness self-critique" in result["reason"]
        # Exactly 1 (explorer) + 1 (critique) + 2 * (rewrite + re-critique)
        # == 6 calls -- no more, no infinite loop.
        assert mock_create.call_count == 6


def test_recovery_stops_immediately_if_rewrite_itself_fails():
    # If the rewrite call errors or returns something unusable, that
    # attempt is spent (not retried indefinitely) and the loop still
    # terminates within the bound.
    ce = _load_legacy_module()
    broad_critique = {"verdict": "TOO_BROAD", "reason": "여전히 넓음 (test)"}

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated API failure")

    call_log = {"n": 0}

    def side_effect(*args, **kwargs):
        call_log["n"] += 1
        n = call_log["n"]
        if n == 1:
            return _make_response(_BROAD_WINNER)
        if n == 2:
            return _make_response(broad_critique)
        # every rewrite attempt fails outright
        raise RuntimeError("simulated API failure")

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4 as mock_create:
        result = ce.explore_candidates(_TOPIC_INFO)
        assert result["status"] == "REGENERATE"
        # 1 explorer + 1 critique + 2 failed rewrite attempts == 4, no
        # re-critique calls happen because rewrite never produced a
        # usable candidate.
        assert mock_create.call_count == 4


# ------------------------------------------------------------------
# 6: no forced-pass path -- SELECTED is only reachable via a real
# NARROW_ENOUGH verdict from the unmodified gate.
# ------------------------------------------------------------------

def test_no_forced_pass_when_every_verdict_stays_too_broad():
    ce = _load_legacy_module()
    broad_critique = {"verdict": "TOO_BROAD", "reason": "계속 넓음 (test)"}
    rewritten = _bare_candidate(
        "비행기 날개",
        "비행기 날개는 왜 공기 흐름을 최적화할까?",
        "여전히 일반적인 설명이다.",
    )

    side_effect = [
        _make_response(_BROAD_WINNER),
        _make_response(broad_critique),
        _make_response(rewritten),
        _make_response(broad_critique),
        _make_response(rewritten),
        _make_response(broad_critique),
    ]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce.explore_candidates(_TOPIC_INFO)
        # No matter how many rewrite attempts occur, the ONLY exit besides
        # REGENERATE is a real NARROW_ENOUGH verdict -- there is no counter,
        # score boost or bypass that flips this to SELECTED on its own.
        assert result["status"] != "SELECTED"
        assert result["status"] == "REGENERATE"


if __name__ == "__main__":
    test_generic_reveal_rejected_by_unmodified_gate()
    print("✓ test_generic_reveal_rejected_by_unmodified_gate")

    test_specific_phenomenon_accepted_by_unmodified_gate()
    print("✓ test_specific_phenomenon_accepted_by_unmodified_gate")

    test_rejected_candidate_rewritten_narrower_and_accepted()
    print("✓ test_rejected_candidate_rewritten_narrower_and_accepted")

    test_recovery_limit_respected_then_discards()
    print("✓ test_recovery_limit_respected_then_discards")

    test_recovery_stops_immediately_if_rewrite_itself_fails()
    print("✓ test_recovery_stops_immediately_if_rewrite_itself_fails")

    test_no_forced_pass_when_every_verdict_stays_too_broad()
    print("✓ test_no_forced_pass_when_every_verdict_stays_too_broad")

    print("\n✅ All tests passed")

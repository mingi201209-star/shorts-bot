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
        "비행기 날개",
        "비행기 날개 끝은 왜 위로 꺾여 있을까?",
        "날개 끝의 흐름을 바꿔 소용돌이 손실을 줄이기 때문이다.",
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
        assert result["winner"]["topic"] == "비행기 날개"
        assert "위로 꺾여" in result["winner"]["core_question"]
        assert mock_create.call_count == 4


def test_rewrite_prompt_reuses_grounded_candidate_evidence():
    ce = _load_legacy_module()
    broad = _winner(
        "비행기 날개",
        "비행기 날개는 하중을 받으면 왜 휘고 비틀릴까?",
        "하중 때문에 날개가 변형되기 때문이다.",
    )
    broad["winner"]["fact_check_focus"] = [
        "주익의 스파와 윙박스가 하중을 분산하고 휨 강성을 만든다.",
        "공력 중심과 구조 중심의 차이는 비틀림 하중과 연결된다.",
    ]
    broad["winner"]["visual_proof"] = [
        "비행 중 날개 끝의 실제 flex 변화",
        "윙박스 또는 스파 구조 단면",
    ]

    broad_critique = {
        "verdict": "TOO_BROAD",
        "reason": "Reveal이 하중 때문에 변형된다는 일반 설명에 머문다.",
    }
    rewritten = _bare_candidate(
        "비행기 날개",
        "비행기 날개는 하중을 받으면 왜 위로 휘면서 동시에 비틀릴까?",
        "스파와 윙박스가 휨 하중을 나누는 동안 공력 중심과 구조 중심의 차이가 비틀림 하중을 만든다.",
    )
    rewritten["fact_check_focus"] = list(broad["winner"]["fact_check_focus"])
    rewritten["visual_proof"] = list(broad["winner"]["visual_proof"])
    narrow_critique = {
        "verdict": "NARROW_ENOUGH",
        "reason": "구체적인 구조 요소와 비틀림 원인이 명시됨 (test)",
    }

    side_effect = [
        _make_response(broad),
        _make_response(broad_critique),
        _make_response(rewritten),
        _make_response(narrow_critique),
    ]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4 as mock_create:
        result = ce.explore_candidates(_TOPIC_INFO)

    assert result["status"] == "SELECTED"
    rewrite_call = mock_create.call_args_list[2]
    user_content = rewrite_call.kwargs["messages"][1]["content"]
    system_content = rewrite_call.kwargs["messages"][0]["content"]

    assert "[FACT CHECK FOCUS]" in user_content
    assert "스파와 윙박스가 하중을 분산" in user_content
    assert "공력 중심과 구조 중심의 차이" in user_content
    assert "[VISUAL PROOF]" in user_content
    assert "비행 중 날개 끝의 실제 flex 변화" in user_content
    assert "없는 숫자를 만들어 구체적으로 보이게 하지 마라" in system_content
    assert "[NUMERIC AUTHORITY]" in system_content


def test_rewrite_preserves_grounding_and_evidence_authority():
    ce = _load_legacy_module()

    original = _bare_candidate(
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

    model_rewrite = _bare_candidate(
        "비행기 날개",
        "비행기 날개는 하중을 받을 때 어느 구조가 먼저 휘는가?",
        "스파와 윙박스가 하중을 나누며 탄성 변형한다.",
    )
    # The rewrite model is not allowed to replace evidence authority.
    model_rewrite["fact_check_focus"] = ["모델이 새로 만든 미확인 주장"]
    model_rewrite["visual_proof"] = ["모델이 새로 만든 미확인 화면"]

    p1, p2, p3, p4 = _patched(ce, [_make_response(model_rewrite)])
    with p1, p2, p3, p4:
        rewritten = ce._rewrite_narrower_candidate(
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


def test_rewrite_rejects_unsupported_numeric_detail():
    ce = _load_legacy_module()

    original = _bare_candidate(
        "비행기 날개",
        "비행기 날개는 하중을 받을 때 왜 휘고 비틀리는가?",
        "하중에 따라 날개 구조가 탄성 변형한다.",
    )
    original["fact_check_focus"] = ["날개 하중과 탄성 변형의 관계"]
    original["visual_proof"] = ["비행 중 같은 날개의 실제 flex 변화"]

    fabricated = _bare_candidate(
        "비행기 날개",
        "날개 끝 비틀림이 중간부보다 20% 더 큰 이유는 무엇인가?",
        "특정 재료 조합 때문에 20% 차이가 난다.",
    )

    p1, p2, p3, p4 = _patched(ce, [_make_response(fabricated)])
    with p1, p2, p3, p4:
        rewritten = ce._rewrite_narrower_candidate(
            original,
            "Reveal이 일반적임 (test)",
        )

    assert rewritten is None


def test_fixed_topic_deterministic_grounded_rewrite_can_pass_without_llm_rewrite():
    ce = _load_legacy_module()
    fixed_topic = "비행기 날개"
    ce._NARROWNESS_FIXED_TOPIC_LLM_BLOCKED.clear()

    broad = _winner(
        fixed_topic,
        "비행기 날개는 하중을 받으면 왜 휘고 비틀릴까?",
        "하중 때문에 날개가 변형되기 때문이다.",
    )
    broad["winner"]["fact_check_focus"] = [
        "주익의 스파와 윙박스가 하중을 분산하고 휨 강성을 만든다.",
    ]
    broad["winner"]["visual_proof"] = [
        "비행 중 같은 날개의 실제 flex 변화",
    ]
    broad["winner"]["canonical_subject"] = "비행기 날개"
    broad["winner"]["grounding_evidence"] = [
        {
            "evidence_type": "explicit_candidate_identity",
            "supports_subject": "비행기 날개",
            "source": "candidate_text",
            "detail": "topic explicitly names 비행기 날개",
        }
    ]

    broad_critique = {
        "verdict": "TOO_BROAD",
        "reason": "Reveal이 일반 상식 수준이다.",
    }
    narrow_critique = {
        "verdict": "NARROW_ENOUGH",
        "reason": "기존 grounded 구조가 Reveal에 직접 명시되었다.",
    }

    # Authority preservation belongs to the deterministic rewrite helper itself.
    # validate_explorer_output intentionally returns the public Candidate schema,
    # so private/canonical metadata can be supplied later by the grounding layer.
    direct = ce._deterministic_grounded_narrowness_rewrite(broad["winner"])
    assert direct is not None
    assert direct["canonical_subject"] == "비행기 날개"
    assert direct["grounding_evidence"] == broad["winner"]["grounding_evidence"]

    side_effect = [
        _make_response(broad),
        _make_response(broad_critique),
        _make_response(narrow_critique),
    ]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with patch.dict("os.environ", {"SHORTS_TOPIC": fixed_topic}, clear=False):
        with p1, p2, p3, p4 as mock_create:
            result = ce.explore_candidates(_TOPIC_INFO)

    assert result["status"] == "SELECTED"
    assert mock_create.call_count == 3, (
        "deterministic rewrite must replace the first LLM rewrite call"
    )
    assert (
        result["winner"]["micro_narrative"]["reveal"]
        == broad["winner"]["fact_check_focus"][0]
    )
    assert result["winner"]["fact_check_focus"] == broad["winner"]["fact_check_focus"]
    assert result["winner"]["visual_proof"] == broad["winner"]["visual_proof"]
    assert fixed_topic not in ce._NARROWNESS_FIXED_TOPIC_LLM_BLOCKED


def test_exact_repo_owned_wing_flex_seed_is_used_before_llm_rewrite():
    ce = _load_legacy_module()
    fixed_topic = "비행기 날개는 하중을 받으면 왜 휘고 비틀릴까?"
    ce._NARROWNESS_FIXED_TOPIC_LLM_BLOCKED.clear()

    broad = _winner(
        fixed_topic,
        "비행기 날개가 하중을 받으면 왜 변형될까?",
        "날개는 하중을 받으면 변형될 수 있다.",
    )
    broad["winner"]["fact_check_focus"] = [
        "날개 하중과 탄성 변형의 관계",
    ]
    broad["winner"]["visual_proof"] = [
        "비행 중 날개 flex 변화",
    ]
    broad["winner"]["canonical_subject"] = (
        "aircraft wing structure under aerodynamic load"
    )

    broad_critique = {
        "verdict": "TOO_BROAD",
        "reason": "Reveal이 일반 상식 수준이다.",
    }
    narrow_critique = {
        "verdict": "NARROW_ENOUGH",
        "reason": "하중 전달 경로와 휨/비틀림 모드가 구체적이다.",
    }

    direct = None
    with patch.dict("os.environ", {"SHORTS_TOPIC": fixed_topic}, clear=False):
        direct = ce._deterministic_grounded_narrowness_rewrite(broad["winner"])

    assert direct is not None
    assert direct["topic"] == fixed_topic
    assert direct["core_question"] == "날개 끝은 위로 휘는데, 왜 같은 비행 하중에서 단면 비틀림까지 별도 탄성 모드로 나타날까?"
    assert "리브와 스파" in direct["micro_narrative"]["reveal"]
    assert "flapwise/chordwise bending" in direct["micro_narrative"]["reveal"]
    assert "torsion" in direct["micro_narrative"]["reveal"]
    # Model-authored authority fields remain authoritative; the exact seed only
    # supplies grounded editorial specificity for another real gate decision.
    assert direct["fact_check_focus"] == broad["winner"]["fact_check_focus"]
    assert direct["visual_proof"] == broad["winner"]["visual_proof"]

    side_effect = [
        _make_response(broad),
        _make_response(broad_critique),
        _make_response(narrow_critique),
    ]
    p1, p2, p3, p4 = _patched(ce, side_effect)
    with patch.dict("os.environ", {"SHORTS_TOPIC": fixed_topic}, clear=False):
        with p1, p2, p3, p4 as mock_create:
            result = ce.explore_candidates(_TOPIC_INFO)

    assert result["status"] == "SELECTED"
    assert mock_create.call_count == 3, (
        "exact trusted seed should replace both LLM narrowness rewrites when "
        "the unchanged self-critique accepts the deterministic result"
    )
    assert result["winner"]["topic"] == fixed_topic
    assert "리브와 스파" in result["winner"]["micro_narrative"]["reveal"]
    assert fixed_topic not in ce._NARROWNESS_FIXED_TOPIC_LLM_BLOCKED


def test_fixed_topic_unusable_llm_rewrite_is_not_repeated_across_attempts():
    ce = _load_legacy_module()
    fixed_topic = "비행기 날개"
    ce._NARROWNESS_FIXED_TOPIC_LLM_BLOCKED.clear()

    broad = _winner(
        fixed_topic,
        "비행기 날개는 하중을 받으면 왜 휘고 비틀릴까?",
        "하중 때문에 날개가 변형되기 때문이다.",
    )
    broad["winner"]["fact_check_focus"] = [
        "주익의 스파와 윙박스가 하중을 분산한다.",
    ]
    broad["winner"]["visual_proof"] = [
        "비행 중 같은 날개의 실제 flex 변화",
    ]

    broad_critique = {
        "verdict": "TOO_BROAD",
        "reason": "여전히 일반적인 설명이다.",
    }
    fabricated = _bare_candidate(
        fixed_topic,
        "날개 끝이 15도 비틀리는 이유는 무엇인가?",
        "하중이 5000N을 넘으면 15도 비틀린다.",
    )

    # First explore:
    #   explorer + critique + deterministic re-critique + one bad LLM rewrite
    # Second explore, same exact fixed topic:
    #   explorer + critique only; deterministic/LLM rewrite are skipped because
    #   the process has already seen an unusable rewrite for this fixed topic.
    side_effect = [
        _make_response(broad),
        _make_response(broad_critique),
        _make_response(broad_critique),
        _make_response(fabricated),
        _make_response(broad),
        _make_response(broad_critique),
    ]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with patch.dict("os.environ", {"SHORTS_TOPIC": fixed_topic}, clear=False):
        with p1, p2, p3, p4 as mock_create:
            first = ce.explore_candidates(_TOPIC_INFO)
            second = ce.explore_candidates(_TOPIC_INFO)

    assert first["status"] == "REGENERATE"
    assert second["status"] == "REGENERATE"
    assert mock_create.call_count == 6, (
        "same fixed topic must not re-enter the LLM rewrite loop after an "
        "unusable rewrite"
    )
    assert fixed_topic in ce._NARROWNESS_FIXED_TOPIC_LLM_BLOCKED


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

    test_rewrite_prompt_reuses_grounded_candidate_evidence()
    print("✓ test_rewrite_prompt_reuses_grounded_candidate_evidence")

    test_rewrite_preserves_grounding_and_evidence_authority()
    print("✓ test_rewrite_preserves_grounding_and_evidence_authority")

    test_rewrite_rejects_unsupported_numeric_detail()
    print("✓ test_rewrite_rejects_unsupported_numeric_detail")

    test_fixed_topic_deterministic_grounded_rewrite_can_pass_without_llm_rewrite()
    print("✓ test_fixed_topic_deterministic_grounded_rewrite_can_pass_without_llm_rewrite")

    test_exact_repo_owned_wing_flex_seed_is_used_before_llm_rewrite()
    print("✓ test_exact_repo_owned_wing_flex_seed_is_used_before_llm_rewrite")

    test_fixed_topic_unusable_llm_rewrite_is_not_repeated_across_attempts()
    print("✓ test_fixed_topic_unusable_llm_rewrite_is_not_repeated_across_attempts")

    test_recovery_limit_respected_then_discards()
    print("✓ test_recovery_limit_respected_then_discards")

    test_recovery_stops_immediately_if_rewrite_itself_fails()
    print("✓ test_recovery_stops_immediately_if_rewrite_itself_fails")

    test_no_forced_pass_when_every_verdict_stays_too_broad()
    print("✓ test_no_forced_pass_when_every_verdict_stays_too_broad")

    print("\n✅ All tests passed")

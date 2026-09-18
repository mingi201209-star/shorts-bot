"""Regression test for the Explorer narrowness self-critique (option E).

Runs 607 and 608 both exhausted all 7 candidate attempts on the same
failure mode: Explorer submitted a Winner whose Core Question answer was
guessable and whose Reveal stopped at common-knowledge level, and the
independent, more expensive Winner Candidate Gate rejected it after a
full round-trip. Adding worked bad/good examples to Explorer's own Hard
Gate section 8 (run 607's fix) was not enough on its own (run 608 failed
identically), so this adds a second, narrowly-scoped self-critique call
right after Explorer selects a Winner: a cheap judge-only pass that asks
"is this too broad?" on the fixed candidate, separate from the harder
generative task of picking one.

This test verifies the wiring in content/candidate_explorer.py using a
mocked OpenAI client (no real API calls):
  1. When the self-critique verdict is TOO_BROAD, explore_candidates()
     must return status REGENERATE (so main.py's existing retry loop
     handles it exactly like an Explorer/Gate rejection).
  2. When the verdict is NARROW_ENOUGH, the original SELECTED result must
     be returned unchanged.
  3. When Explorer itself already returns REGENERATE, the self-critique
     call must NOT fire at all (no wasted API cost on a non-existent
     winner).
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


_WINNER_PAYLOAD = {
    "status": "SELECTED",
    "winner": {
        "topic": "테스트 주제",
        "angle": "테스트 앵글",
        "core_question": "왜 테스트 주제가 발생할까요?",
        "micro_narrative": {
            "hook": "테스트 hook",
            "core_question": "왜 그런가요?",
            "reveal": "테스트 reveal",
            "payoff": "테스트 payoff",
        },
        "fact_check_focus": [],
        "visual_proof": ["테스트 증거"],
        "selection_reason": "테스트 이유",
    },
    "runner_up": None,
}

_FAKE_USAGE = {"cost_usd": 0.0001, "over_budget": False}
_TOPIC_INFO = {"category": "과학", "topic": "테스트 방향"}


def _patched(ce, side_effect):
    return (
        patch.object(ce, "authorize_call", return_value=1),
        patch.object(ce, "record_usage", return_value=_FAKE_USAGE),
        patch.object(ce, "print_budget_status"),
        patch.object(ce.openai.chat.completions, "create", side_effect=side_effect),
    )


def test_too_broad_verdict_becomes_regenerate():
    ce = _load_legacy_module()
    critique = {"verdict": "TOO_BROAD", "reason": "질문이 너무 넓음 (test)"}
    side_effect = [_make_response(_WINNER_PAYLOAD), _make_response(critique)]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4 as mock_create:
        result = ce.explore_candidates(_TOPIC_INFO)
        assert result["status"] == "REGENERATE"
        assert "Narrowness self-critique" in result["reason"]
        assert mock_create.call_count == 2


def test_narrow_enough_verdict_preserves_original_result():
    ce = _load_legacy_module()
    critique = {"verdict": "NARROW_ENOUGH", "reason": "충분히 구체적 (test)"}
    side_effect = [_make_response(_WINNER_PAYLOAD), _make_response(critique)]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4:
        result = ce.explore_candidates(_TOPIC_INFO)
        assert result["status"] == "SELECTED"
        assert result["winner"]["topic"] == "테스트 주제"


def test_self_critique_not_called_on_explorer_own_regenerate():
    ce = _load_legacy_module()
    regen_payload = {"status": "REGENERATE", "reason": "no good candidate"}
    side_effect = [_make_response(regen_payload)]

    p1, p2, p3, p4 = _patched(ce, side_effect)
    with p1, p2, p3, p4 as mock_create:
        result = ce.explore_candidates(_TOPIC_INFO)
        assert result["status"] == "REGENERATE"
        assert mock_create.call_count == 1, (
            "self-critique must not fire when Explorer already returned "
            "REGENERATE -- there is no winner to critique"
        )


if __name__ == "__main__":
    test_too_broad_verdict_becomes_regenerate()
    print("✓ test_too_broad_verdict_becomes_regenerate")

    test_narrow_enough_verdict_preserves_original_result()
    print("✓ test_narrow_enough_verdict_preserves_original_result")

    test_self_critique_not_called_on_explorer_own_regenerate()
    print("✓ test_self_critique_not_called_on_explorer_own_regenerate")

    print("\n✅ All tests passed")

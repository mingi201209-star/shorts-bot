"""Regression test for run 612's chevron script-generation crash.

Run 612 (2026-09-18) finally got a Winner past Candidate Explorer/Gate
("jet engine nacelle/nozzle chevrons") but then crashed 3/3 script
writer attempts on retention_structure.validate_new_information():
scene 5's payoff ("noise_reduction") was flagged as a duplicate of
scene 1's opening, because the Writer's scene 1 already stated the
chevron's noise-reduction purpose while merely describing what it
looks like. That premature reveal is itself the underlying defect (the
phenomenon scene is supposed to withhold purpose/effect until later
scenes), and the validator is correctly catching it -- but the Writer
kept repeating the mistake, exhausting all 3 attempts and crashing the
whole run (no fallback to another candidate).

Fix: content/retention_structure.py's first5_prompt_contract() now
explicitly tells the Writer that Scene 1 must describe only what is
visibly observable, never why the shape exists or what effect it has
(noise/efficiency/performance/stability etc.) -- that's reserved for
the causal-clue/reveal/payoff scenes.

This test verifies the validator's existing (correct) behavior on both
sides of the contract using content/retention_structure.py directly
(no LLM calls):
  1. A scene 1 that leaks the noise-reduction purpose collides with the
     payoff scene and is flagged (the failure mode actually observed in
     run 612).
  2. A scene 1 that only describes the visible shape, with the
     noise-reduction claim reserved for the payoff scene, passes clean.
"""

from content.retention_structure import validate_new_information


def _plan():
    return {
        "contracts": [
            {"index": 1, "role": "phenomenon", "locked": False},
            {"index": 2, "role": "question", "locked": False},
            {"index": 3, "role": "causal_clue", "locked": False},
            {"index": 4, "role": "reveal", "locked": False},
            {"index": 5, "role": "payoff", "locked": False},
        ],
    }


def test_scene1_purpose_leak_collides_with_payoff():
    scenes = [
        {"text": "제트 엔진 노즐의 가장자리는 톱니 모양으로 소음을 줄이기 위해 설계되었습니다."},
        {"text": "그런데 왜 하필 톱니 모양이어야 할까요?"},
        {"text": "고속 배기 흐름과 주변 공기가 만나는 경계가 문제입니다."},
        {"text": "톱니 모양은 두 흐름이 섞이는 방식을 바꿉니다."},
        {"text": "그 결과 엔진 주변의 소음이 줄어듭니다."},
    ]
    failures = validate_new_information(scenes, _plan())
    reasons = [f["reason"] for f in failures]
    assert any("noise_reduction" in r and "reserved for scene 1" in r for r in reasons), reasons


def test_scene1_pure_observation_passes():
    scenes = [
        {"text": "제트 엔진 노즐의 뒤쪽 가장자리는 톱니 모양으로 되어 있습니다."},
        {"text": "그런데 왜 가장자리가 톱니 모양일까요?"},
        {"text": "고속 배기 흐름과 주변 공기가 만나는 경계가 문제입니다."},
        {"text": "톱니 모양은 두 흐름이 섞이는 방식을 바꿉니다."},
        {"text": "그 결과 엔진 주변의 소음이 줄어듭니다."},
    ]
    failures = validate_new_information(scenes, _plan())
    reasons = [f["reason"] for f in failures]
    assert not any("noise_reduction" in r for r in reasons), reasons


if __name__ == "__main__":
    test_scene1_purpose_leak_collides_with_payoff()
    print("✓ test_scene1_purpose_leak_collides_with_payoff")

    test_scene1_pure_observation_passes()
    print("✓ test_scene1_pure_observation_passes")

    print("\n✅ All tests passed")

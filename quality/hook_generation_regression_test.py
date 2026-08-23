import json

from content import hook_experiment


def _assert(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def _item(index, text, **overrides):
    item = {
        "id": f"hook_{index}",
        "text": text,
        "visual_goal": f"구체적인 화면 {index}",
        "keyword": f"drone camera crack {index}",
        "stop_power": 8.4,
        "curiosity_gap": 8.2,
        "clarity": 8.5,
        "specificity": 8.4,
        "visual_potential": 8.6,
        "fact_safety": 8.7,
        "reason": "fixture",
    }
    item.update(overrides)
    return item


VALID_TEXTS = [
    "드론이 균열을 먼저 찾습니다",
    "수도관은 물을 흘려보냅니다",
    "남극 기지는 위로 올라갑니다",
    "사막여우 귀는 열을 내보냅니다",
    "화면은 손가락을 감지합니다",
    "비행기 창문은 압력을 견딥니다",
    "로마 도로는 물을 빼냅니다",
    "벌집은 공간을 육각형으로 채웁니다",
    "문어 피부는 색을 바꿉니다",
    "낙타 콧속은 수분을 모읍니다",
]


def _payload(items):
    return {"candidates": items}


def test_production_like_parse_to_scoring_pool():
    raw = json.dumps(
        _payload([_item(i, text) for i, text in enumerate(VALID_TEXTS, 1)]),
        ensure_ascii=False,
    )
    parsed = hook_experiment._extract_json(raw)
    candidates, diagnostics = hook_experiment._diagnose_candidates(parsed)

    _assert("Raw 10 candidates parsed", diagnostics["raw_candidate_count"] == 10)
    _assert("All 10 schema candidates parsed", diagnostics["parsed_candidate_count"] == 10)
    _assert("At least five survive full scoring-pool gates", diagnostics["scoring_pool_count"] >= 5)
    _assert("At least five remain threshold-eligible", diagnostics["eligible_candidate_count"] >= 5)
    _assert("Normalized candidates retain scoring data", len(candidates) >= 5)


def test_too_long_reason():
    items = [
        _item(
            i,
            f"드론이 산업 현장의 아주 작은 {i}번 균열까지 먼저 찾아내고 알려줍니다",
        )
        for i in range(1, 6)
    ]
    _, diagnostics = hook_experiment._diagnose_candidates(_payload(items))
    _assert("All long candidates report too_long", diagnostics["rejected"].get("too_long") == 5)


def test_speech_style_reason():
    items = [_item(i, f"드론{i}이 균열을 먼저 찾아내요") for i in range(1, 4)]
    _, diagnostics = hook_experiment._diagnose_candidates(_payload(items))
    _assert(
        "Casual-polite candidates report speech_style_failure",
        diagnostics["rejected"].get("speech_style_failure") == 3,
    )


def test_question_hook_reserved_for_scene_two():
    question = "드론은 왜 균열을 먼저 찾을까요?"
    candidates, diagnostics = hook_experiment._diagnose_candidates(
        _payload([
            _item(1, question, stop_power=9.8),
            _item(2, VALID_TEXTS[0]),
        ])
    )
    texts = [item["text"] for item in candidates]
    _assert("Question-shaped Hook is excluded upstream", question not in texts)
    _assert(
        "Question-shaped Hook exposes dedicated rejection reason",
        diagnostics["rejected"].get("question_hook_not_allowed") == 1,
    )
    _assert("Declarative Hook remains eligible beside rejected question", VALID_TEXTS[0] in texts)


def test_duplicate_reason():
    repeated = VALID_TEXTS[0]
    items = [_item(1, repeated), _item(2, repeated)]
    _, diagnostics = hook_experiment._diagnose_candidates(_payload(items))
    _assert("Duplicate Hook is rejected deterministically", diagnostics["rejected"].get("duplicate") == 1)


def test_hard_floor_reason_codes():
    items = [
        _item(1, VALID_TEXTS[0], clarity=6.9),
        _item(2, VALID_TEXTS[1], specificity=6.9),
        _item(3, VALID_TEXTS[2], visual_potential=7.9),
        _item(4, VALID_TEXTS[3], fact_safety=7.9),
    ]
    _, diagnostics = hook_experiment._diagnose_candidates(_payload(items))
    rejected = diagnostics["rejected"]
    _assert("clarity floor reason recorded", rejected.get("clarity_below_floor") == 1)
    _assert("specificity floor reason recorded", rejected.get("specificity_below_floor") == 1)
    _assert("visual floor reason recorded", rejected.get("visual_potential_below_floor") == 1)
    _assert("fact floor reason recorded", rejected.get("fact_safety_below_floor") == 1)


def _diag(scoring_pool, rejected, repair_candidates=None):
    result = hook_experiment._empty_hook_diagnostics()
    result.update({
        "raw_candidate_count": scoring_pool,
        "parsed_candidate_count": scoring_pool,
        "normalized_candidate_count": scoring_pool,
        "length_valid_count": scoring_pool,
        "shape_valid_count": scoring_pool,
        "speech_style_valid_count": scoring_pool,
        "clarity_valid_count": scoring_pool,
        "specificity_valid_count": scoring_pool,
        "visual_potential_valid_count": scoring_pool,
        "fact_safety_valid_count": scoring_pool,
        "scoring_pool_count": scoring_pool,
        "eligible_candidate_count": scoring_pool,
        "rejected": dict(rejected),
        "repair_candidates": list(repair_candidates or []),
    })
    return result


def test_bounded_attempt_two_receives_feedback_and_accumulates():
    original = hook_experiment._request_candidates
    calls = []

    first_candidates, _ = hook_experiment._diagnose_candidates(
        _payload([_item(1, VALID_TEXTS[0]), _item(2, VALID_TEXTS[1])])
    )
    second_candidates, _ = hook_experiment._diagnose_candidates(
        _payload([_item(i + 3, text) for i, text in enumerate(VALID_TEXTS[2:5])])
    )
    repair_items = [{
        "text": "드론은 균열을 확인합니다",
        "visible_len": 11,
        "visual_goal": "드론 점검 화면",
        "keyword": "drone inspection",
    }]

    def fake_request(topic_info, candidate, generation_round, rejection_feedback=None):
        del topic_info, candidate
        calls.append((generation_round, dict(rejection_feedback or {})))
        if generation_round == 1:
            return first_candidates, _diag(2, {"too_short": 8}, repair_items)
        return second_candidates, _diag(3, {})

    hook_experiment._request_candidates = fake_request
    try:
        selected, audit = hook_experiment.select_hook({}, {"topic": "fixture"})
    finally:
        hook_experiment._request_candidates = original

    _assert("Attempt 2 runs after insufficient attempt 1", len(calls) == 2)
    _assert("Attempt 2 receives attempt-1 rejection counts", calls[1][1].get("rejection_counts") == {"too_short": 8})
    _assert("Attempt 2 receives bounded repair candidates", calls[1][1].get("repair_candidates") == repair_items)
    _assert("Validated candidates accumulate across bounded attempts", audit["attempts"][-1]["cumulative_scoring_pool_count"] == 5)
    _assert("Cumulative pool can select normal threshold winner", bool(selected))
    _assert("Successful bounded repair avoids fallback", not audit["fallback"])


def test_attempt_two_failure_preserves_legacy_fallback():
    original = hook_experiment._request_candidates
    calls = []

    def fake_request(topic_info, candidate, generation_round, rejection_feedback=None):
        del topic_info, candidate
        calls.append((generation_round, dict(rejection_feedback or {})))
        return [], _diag(0, {"too_short": 10})

    hook_experiment._request_candidates = fake_request
    try:
        selected, audit = hook_experiment.select_hook({}, {"topic": "fixture"})
    finally:
        hook_experiment._request_candidates = original

    _assert("Hook generation remains bounded to two attempts", len(calls) == 2)
    _assert("Second failure returns no experimental Hook", selected is None)
    _assert("Existing legacy fallback signal remains enabled", audit["fallback"] is True)


def test_legacy_three_argument_request_contract():
    original = hook_experiment._request_candidates
    fixture_candidates, _ = hook_experiment._diagnose_candidates(
        _payload([_item(i, text) for i, text in enumerate(VALID_TEXTS[:5], 1)])
    )
    calls = []

    def legacy_request(topic_info, candidate, generation_round):
        del topic_info, candidate
        calls.append(generation_round)
        return fixture_candidates

    hook_experiment._request_candidates = legacy_request
    try:
        selected, audit = hook_experiment.select_hook({}, {"topic": "fixture"})
    finally:
        hook_experiment._request_candidates = original

    _assert("Legacy fixture contract is called once", calls == [1])
    _assert("Legacy fixture contract still selects Hook", bool(selected))
    _assert("Legacy fixture contract does not force fallback", not audit["fallback"])


def test_existing_thresholds_unchanged():
    _assert("Hook score threshold remains 7.2", hook_experiment.HOOK_MIN_SCORE == 7.2)
    _assert(
        "Hook hard floors unchanged",
        hook_experiment.HOOK_CRITERIA_FLOORS == {
            "clarity": 7.0,
            "specificity": 7.0,
            "visual_potential": 8.0,
            "fact_safety": 8.0,
        },
    )
    _assert("Hook length lower bound remains 12", hook_experiment.HOOK_MIN_CHARS == 12)
    _assert("Hook length upper bound remains 16", hook_experiment.HOOK_MAX_CHARS == 16)
    _assert("Default production raw generation pool is 10+", hook_experiment.HOOK_GENERATION_COUNT >= 10)
    _assert("Maximum regeneration count remains one", hook_experiment.HOOK_MAX_REGENERATIONS == 1)


def main():
    test_production_like_parse_to_scoring_pool()
    test_too_long_reason()
    test_speech_style_reason()
    test_question_hook_reserved_for_scene_two()
    test_duplicate_reason()
    test_hard_floor_reason_codes()
    test_bounded_attempt_two_receives_feedback_and_accumulates()
    test_attempt_two_failure_preserves_legacy_fallback()
    test_legacy_three_argument_request_contract()
    test_existing_thresholds_unchanged()
    print("✅ HOOK GENERATION REGRESSION TESTS PASS")


if __name__ == "__main__":
    main()

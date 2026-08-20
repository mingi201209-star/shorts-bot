import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content import hook_experiment as hook
from quality.consensus import build_consensus


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"✅ PASS | {name}")


def hook_item(index, text, score=8.5):
    return {
        "id": f"hook_{index}",
        "text": text,
        "visual_goal": "뉴욕 건물과 위쪽 빈 공간이 한 화면에 명확히 보이는 장면",
        "keyword": "new york building air space",
        "stop_power": score,
        "curiosity_gap": score,
        "clarity": score,
        "specificity": score,
        "visual_potential": max(score, 8.0),
        "fact_safety": max(score, 8.0),
        "reason": "focused regression",
    }


def test_hook_length_pool():
    texts = [
        "공중권은 건물 위에서 거래돼요",
        "건물 위 빈공간도 돈이 됩니다",
        "뉴욕 하늘 공간도 사고팔아요",
        "빌딩 위 공간에도 값이 붙어요",
        "빈 하늘이 건물 높이를 바꿔요",
    ]
    payload = {"candidates": [hook_item(i, text) for i, text in enumerate(texts, 1)]}
    candidates, diagnostics = hook._diagnose_candidates(payload)
    check("1 five valid Hook candidates enter scoring pool", diagnostics["scoring_pool_count"] >= 5 and len(candidates) >= 5)

    too_long = hook_item(99, "뉴욕의 아주 높은 건물 위 빈 공간도 실제 부동산 권리처럼 사고팔 수 있어요")
    _, diagnostics = hook._diagnose_candidates({"candidates": [too_long]})
    check("2 overlong Hook remains rejected", diagnostics["rejected"].get("too_long") == 1)


def normalized_candidate(index, text):
    scores = {key: 8.5 for key in hook.HOOK_CRITERIA}
    return {
        "id": f"n{index}",
        "text": text,
        "visual_goal": "clear visual",
        "keyword": "new york building space",
        "scores": scores,
        "criteria_pass": True,
        "total_score": 8.5,
        "reason": "fixture",
    }


def test_bounded_regeneration():
    original = hook._request_candidates
    calls = []
    first = [
        normalized_candidate(1, "공중권은 건물 위에서 거래돼요"),
        normalized_candidate(2, "건물 위 빈공간도 돈이 됩니다"),
        normalized_candidate(3, "뉴욕 하늘 공간도 사고팔아요"),
        normalized_candidate(4, "빌딩 위 공간에도 값이 붙어요"),
    ]
    second = [normalized_candidate(5, "빈 하늘이 건물 높이를 바꿔요")]

    def request(topic_info, candidate, generation_round, rejection_feedback=None):
        calls.append(generation_round)
        items = first if generation_round == 1 else second
        return items, {
            "raw_candidate_count": len(items),
            "parsed_candidate_count": len(items),
            "normalized_candidate_count": len(items),
            "length_valid_count": len(items),
            "speech_style_valid_count": len(items),
            "scoring_pool_count": len(items),
            "eligible_candidate_count": len(items),
            "rejected": {},
            "length_histogram": {},
            "repair_candidates": [],
        }

    try:
        hook._request_candidates = request
        selected, audit = hook.select_hook({}, {})
        check("3 bounded retry reaches cumulative five-candidate pool", selected is not None and len(calls) == 2 and audit["fallback"] is False)

        hook._request_candidates = lambda topic_info, candidate, generation_round, rejection_feedback=None: (
            first[:1],
            {
                "raw_candidate_count": 1,
                "parsed_candidate_count": 1,
                "normalized_candidate_count": 1,
                "length_valid_count": 1,
                "speech_style_valid_count": 1,
                "scoring_pool_count": 1,
                "eligible_candidate_count": 1,
                "rejected": {},
                "length_histogram": {},
                "repair_candidates": [],
            },
        )
        selected, audit = hook.select_hook({}, {})
        check("3 regeneration remains bounded at two attempts", selected is None and len(audit["attempts"]) == hook.HOOK_MAX_REGENERATIONS + 1 == 2)
    finally:
        hook._request_candidates = original


def judge(score, critical=False):
    return {
        "score": score,
        "confidence": 0.9,
        "critical_risk": critical,
        "issues": [],
    }


def consensus_for(hook_score, novelty, fact, visual, *, fact_critical=False):
    return build_consensus({
        "hook": [judge(hook_score)],
        "novelty": [judge(novelty)],
        "fact": [judge(fact, fact_critical)],
        "visual": [judge(visual)],
    })


def test_quality_final_decision():
    good = consensus_for(7, 6, 7, 8)
    check(
        "6 sufficient total plus all judged Good Enough floors can ship",
        good["decision"] == "PASS" and good["pass_tier"] == "GOOD_ENOUGH" and good["weighted_score"] >= 6.8,
    )

    low_hook = consensus_for(6, 5, 7, 8)
    check("4 clearly weak operational Hook remains REWRITE", low_hook["decision"] == "REWRITE")

    low_novelty = consensus_for(8, 4.9, 8, 8)
    check("4 low novelty remains REWRITE", low_novelty["decision"] == "REWRITE")

    fact_critical = consensus_for(9, 9, 9, 9, fact_critical=True)
    check("5 Fact critical risk can never PASS", fact_critical["decision"] != "PASS")

    low_fact_floor = consensus_for(9, 9, 6.4, 9)
    check("7 high total cannot bypass a failed fact domain floor", low_fact_floor["decision"] != "PASS")

    with_explanation = build_consensus({
        "hook": [judge(8)],
        "novelty": [judge(7)],
        "fact": [judge(8)],
        "visual": [judge(8)],
        "explanation": [judge(6.0)],
    })
    check("optional explanation floor is still enforced when judged", with_explanation["decision"] != "PASS")


def test_contract_constants():
    check("Hook validator remains 12..16", hook.HOOK_MIN_CHARS == 12 and hook.HOOK_MAX_CHARS == 16)
    check("Hook score threshold unchanged", abs(hook.HOOK_MIN_SCORE - 7.2) < 1e-9)
    check("Hook generation attempts remain two", hook.HOOK_MAX_REGENERATIONS == 1)
    check(
        "Hook quality floors unchanged",
        hook.HOOK_CRITERIA_FLOORS == {
            "clarity": 7.0,
            "specificity": 7.0,
            "visual_potential": 8.0,
            "fact_safety": 8.0,
        },
    )


def test_pr14_contract_preserved():
    config_text = (ROOT / "config.py").read_text(encoding="utf-8")
    script_text = (ROOT / "content" / "script_generator.py").read_text(encoding="utf-8")
    subtitle_text = (ROOT / "video" / "subtitle_engine.py").read_text(encoding="utf-8")
    tts_text = (ROOT / "integrations" / "tts.py").read_text(encoding="utf-8")

    check("8 PR14 Hook/base TTS +13% preserved", '"+13%"' in config_text)
    check("8 PR14 first-five retention structure preserved", "FIRST 5 SECONDS — RETENTION" in script_text)
    check("8 PR14 exact Hook subtitle 0.000s preserved", "subtitle_start=0.000s" in subtitle_text)
    check("8 PR14 TTS humanization path preserved", "resolve_tts_prosody" in tts_text and "TTS_BODY_RATE" in tts_text)


def main():
    test_hook_length_pool()
    test_bounded_regeneration()
    test_quality_final_decision()
    test_contract_constants()
    test_pr14_contract_preserved()
    print("✅ THROUGHPUT RECOVERY FOCUSED REGRESSION PASS")


if __name__ == "__main__":
    main()

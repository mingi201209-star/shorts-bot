from copy import deepcopy

from analytics.feedback_contract import make_video_lineage
from content.growth_candidate_ranker import annotate_explorer_output, score_growth_candidate


def aviation_candidate(topic, question, *, visual=True, observation=None, condition=None):
    value = {
        "topic": topic,
        "angle": "승객이 실제로 보는 항공 설계의 이유",
        "core_question": question,
        "micro_narrative": {
            "hook": topic,
            "core_question": question,
            "reveal": "눈에 보이는 구조가 특정 물리 제약을 처리한다.",
            "payoff": "그래서 승객이 보는 작은 구조가 실제 안전 설계와 연결된다.",
        },
        "visual_proof": ["aircraft close-up", "visible mechanism"] if visual else [],
        "fact_check_focus": [],
    }
    if observation:
        value["specific_observation"] = observation
    if condition:
        value["concrete_condition"] = condition
    return value


def main():
    window = aviation_candidate(
        "비행기 창문 아래 작은 구멍",
        "비행기 창문에는 왜 작은 구멍이 있을까?",
        observation="승객이 직접 볼 수 있는 창문 아래 작은 구멍",
        condition="고도 상승으로 객실과 외부 압력 차가 커지는 조건",
    )
    lights = aviation_candidate(
        "착륙할 때 어두워지는 객실 조명",
        "착륙할 때 객실 조명을 왜 어둡게 할까?",
        observation="착륙 전 실제로 어두워지는 객실 조명",
        condition="비상 탈출 가능성이 상대적으로 높은 이착륙 단계",
    )

    no_history = score_growth_candidate(window, history=[])
    assert set(no_history["axes"]) == {
        "audience_continuity", "subscriber_potential", "series_potential", "visual_proof"
    }
    assert no_history["evidence_state"] == "pending"
    assert no_history["subscriber_evidence_state"] == "pending"
    assert no_history["subscriber_observations"] == 0
    assert no_history["production_authoritative"] is True

    unknown_history = [make_video_lineage("unknown-1", candidate=lights)]
    unknown = score_growth_candidate(window, history=unknown_history)
    assert unknown["subscriber_evidence_state"] == "pending"
    assert unknown["subscriber_observations"] == 0

    observed_zero = [
        make_video_lineage(
            "zero-1",
            candidate=lights,
            snapshots={"24h": {"state": "complete", "views": 500, "subscriber_gain": 0}},
        )
    ]
    zero_score = score_growth_candidate(window, history=observed_zero)
    assert zero_score["subscriber_evidence_state"] == "observed"
    assert zero_score["subscriber_observations"] == 1

    observed_gain = [
        make_video_lineage(
            "gain-1",
            candidate=lights,
            snapshots={"24h": {"state": "complete", "views": 500, "subscriber_gain": 4}},
        )
    ]
    gain_score = score_growth_candidate(window, history=observed_gain)
    assert gain_score["axes"]["subscriber_potential"] > zero_score["axes"]["subscriber_potential"]

    duplicate_history = [make_video_lineage("dup-1", candidate=window)]
    duplicate = score_growth_candidate(window, history=duplicate_history)
    related = score_growth_candidate(window, history=[make_video_lineage("related-1", candidate=lights)])
    assert duplicate["duplication_penalty"] > related["duplication_penalty"]
    assert related["axes"]["audience_continuity"] >= no_history["axes"]["audience_continuity"]

    payload = {"status": "SELECTED", "winner": window, "runner_up": lights, "reason": "legacy winner"}
    original = deepcopy(payload)
    annotated = annotate_explorer_output(payload, history=observed_gain)
    assert payload == original, "shadow scorer mutated authoritative explorer output"
    assert annotated["winner"] == original["winner"]
    assert annotated["runner_up"] == original["runner_up"]
    assert annotated["status"] == "SELECTED"
    assert annotated["reason"] == "legacy winner"
    assert annotated["growth_shadow"]["mode"] == "shadow"
    assert set(annotated["growth_shadow"]["candidates"]) == {"winner", "runner_up"}

    assert score_growth_candidate(window, history=observed_gain) == score_growth_candidate(
        window, history=observed_gain
    ), "shadow score must be deterministic"

    print("PASS: growth-aware shadow ranker; zero!=unknown; continuity!=duplication; production winner unchanged")


if __name__ == "__main__":
    main()

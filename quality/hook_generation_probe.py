import json

from content import hook_experiment
from quality.budget_guard import reset_budget


CASES = [
    (
        {
            "category": "기술",
            "direction": "산업 현장에서 실제로 사용하는 의외의 기술",
        },
        {
            "topic": "산업 현장에서 사용되는 드론의 비밀 기능",
            "core_question": "드론은 어떻게 산업 현장에서 물체를 인식하고 이를 활용해 안전성을 높일 수 있을까?",
            "micro_narrative": "산업 현장의 드론이 카메라와 센서로 위험 요소를 식별하는 과정을 설명한다.",
            "fact_check_focus": "드론이 실제로 관찰 가능한 센서·카메라 기능 범위만 다룬다.",
            "visual_proof": "산업 시설을 촬영하거나 점검하는 드론과 카메라 화면",
        },
    ),
    (
        {
            "category": "역사",
            "direction": "지금 보면 이상하지만 당시에는 합리적이었던 기술",
        },
        {
            "topic": "지중해 지역의 고대 로마의 수도관",
            "core_question": "왜 고대 로마의 수도관은 현대와 다른 방식으로 설계되었을까?",
            "micro_narrative": "로마 수도관이 중력을 이용해 낮은 경사로 물을 이동시키는 구조를 보여준다.",
            "fact_check_focus": "중력식 흐름과 구조적 특징만 다룬다.",
            "visual_proof": "로마 수도교의 아치와 물길 구조",
        },
    ),
    (
        {
            "category": "지리",
            "direction": "사람이 살기 어려운 지역의 독특한 해결책",
        },
        {
            "topic": "안타르ctica의 연구 기지",
            "core_question": "안타르ctica의 연구 기지는 어떻게 극한의 날씨에서 안전하게 운영될 수 있을까?",
            "micro_narrative": "강풍과 적설을 견디기 위한 연구 기지의 외형과 운영 방식을 보여준다.",
            "fact_check_focus": "확인 가능한 기지 구조와 극지 환경 대응만 다룬다.",
            "visual_proof": "눈 위의 남극 연구 기지 외관과 강풍·적설",
        },
    ),
]


def main():
    reset_budget()
    summary = []

    for index, (topic_info, candidate) in enumerate(CASES, start=1):
        print("")
        print("=" * 64)
        print(f"[HOOK PROBE] case={index} topic={candidate['topic']}")
        print("=" * 64)

        selected, audit = hook_experiment.select_hook(topic_info, candidate)
        attempts = audit.get("attempts", [])
        summary.append({
            "case": index,
            "topic": candidate["topic"],
            "attempt_candidate_counts": [
                attempt.get("candidate_count", 0)
                for attempt in attempts
            ],
            "selected": bool(selected),
            "fallback": bool(audit.get("fallback")),
        })

    print("[HOOK PROBE SUMMARY] " + json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

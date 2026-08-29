from content.retention_structure import validate_new_information
from content.script_engine_v2_validation import validate_script_v2


def _scene(index, text, role, retention_role=""):
    scene = {
        "text": text,
        "visual_goal": f"Concrete explanatory visual for stage {index}",
        "keyword": f"aircraft detail stage{index}",
        "role": role,
    }
    if retention_role:
        scene["retention_role"] = retention_role
    return scene


def _plan(count, *, reveal_index, payoff_index):
    roles = ["phenomenon", "question", "causal_clue"]
    while len(roles) < count - 2:
        roles.append(f"mechanism_{len(roles) - 2}")
    roles.extend(["reveal", "payoff"])
    contracts = []
    for index, role in enumerate(roles, start=1):
        contracts.append({
            "index": index,
            "role": role,
            "locked": index in (reveal_index, payoff_index),
            "required_concepts": [
                "jet exhaust airflow mixing",
                "vortex noise reduction",
            ],
        })
    return {"contracts": contracts}


def production_counterexample():
    plan = _plan(12, reveal_index=11, payoff_index=12)
    scenes = [
        _scene(1, "비행기 엔진의 뒤쪽을 보면 톱니 모양의 구조가 있습니다.", "phenomenon", "phenomenon"),
        _scene(2, "그런데 왜 비행기 엔진 뒤는 톱니처럼 생겼을까요?", "question", "question"),
        _scene(3, "원인의 첫 단서는 이 톱니 모양은 소음 감소에 도움을 줍니다.", "causal_clue", "causal_clue"),
        _scene(4, "톱니 모양은 공기의 흐름을 조절합니다.", "mechanism_1"),
        _scene(5, "이 구조는 소음의 소용돌이를 줄입니다.", "mechanism_2"),
        _scene(6, "비행기 엔진의 소음은 승객에게 영향을 미칩니다.", "mechanism_3"),
        _scene(7, "소음이 줄어들면 비행기 여행이 더 편안해집니다.", "mechanism_4"),
        _scene(8, "톱니 모양은 엔진의 효율성을 높입니다.", "mechanism_5"),
        _scene(9, "이 구조는 비행기의 성능에도 긍정적인 영향을 줍니다.", "mechanism_6"),
        _scene(10, "비행기 엔진의 톱니 모양은 혁신적인 디자인입니다.", "mechanism_7"),
        _scene(11, "이 톱니 모양은 엔진 뒤쪽에서 발생하는 소음의 소용돌이를 줄이기 위해 설계되었습니다.", "reveal"),
        _scene(12, "결과적으로 비행기의 소음이 줄어들어 승객과 주변 환경의 편안함을 높입니다.", "payoff"),
    ]
    return scenes, plan


def compressed_example():
    plan = _plan(6, reveal_index=5, payoff_index=6)
    scenes = [
        _scene(1, "비행기 엔진의 뒤쪽을 보면 톱니 모양의 구조가 있습니다.", "phenomenon", "phenomenon"),
        _scene(2, "그런데 왜 비행기 엔진 뒤는 톱니처럼 생겼을까요?", "question", "question"),
        _scene(3, "원인의 첫 단서는 뜨거운 배기와 주변 공기의 속도 차이입니다.", "causal_clue", "causal_clue"),
        _scene(4, "톱니 가장자리는 두 흐름이 여러 작은 구역에서 섞이게 합니다.", "mechanism_1"),
        _scene(5, "이렇게 경계가 완만해져 큰 소용돌이가 약해지면서 제트 소음이 줄어듭니다.", "reveal"),
        _scene(6, "그래서 공항 주변의 체감 소음 부담을 낮추는 데 도움이 됩니다.", "payoff"),
    ]
    return scenes, plan


def main():
    scenes, plan = production_counterexample()
    failures = validate_new_information(scenes, plan)
    reasons = [item["reason"] for item in failures]
    indexes = {item["scene_index"] for item in failures}

    # Run 33237719797 production shape: the locked reveal/payoff stay authoritative,
    # so earlier restatements are the repair targets rather than deleting locked text.
    assert {3, 5}.issubset(indexes), failures
    assert {6, 7}.issubset(indexes), failures
    assert 10 in indexes, failures
    assert 8 in indexes and 9 in indexes, failures
    assert any("noise_reduction" in reason or "vortex_reduction" in reason for reason in reasons)
    assert any("payoff contract" in reason for reason in reasons)
    assert any("generic evaluation filler" in reason for reason in reasons)
    assert any("unsupported generic positive effect (efficiency)" in reason for reason in reasons)
    assert any("unsupported generic positive effect (performance)" in reason for reason in reasons)

    full = validate_script_v2({"scenes": scenes}, plan)
    assert full["valid"] is False
    assert {3, 5, 6, 7, 8, 9, 10}.issubset(set(full["failed_scene_indexes"]))

    compact_scenes, compact_plan = compressed_example()
    compact = validate_script_v2({"scenes": compact_scenes}, compact_plan)
    assert compact["valid"] is True, compact

    print("PASS: Retention Story V2 live-shaped new-information contract")


if __name__ == "__main__":
    main()

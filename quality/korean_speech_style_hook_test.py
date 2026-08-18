from content import hook_experiment


def _item(index, text, score=9.0):
    return {
        "id": f"hook_{index}",
        "text": text,
        "visual_goal": "태양 아래 이동하는 개미가 화면 중앙에 크게 보이는 장면",
        "keyword": "ant sunlight walking closeup",
        "stop_power": score,
        "curiosity_gap": score,
        "clarity": score,
        "specificity": score,
        "visual_potential": score,
        "fact_safety": score,
        "reason": "test",
    }


def main():
    payload = {
        "candidates": [
            _item(1, "개미는 태양으로 방향을 잡는다!", 10.0),
            _item(2, "개미는 태양으로 길을 찾아요!", 9.5),
            _item(3, "개미는 태양을 보고 움직여요!", 9.4),
            _item(4, "개미는 태양으로 길을 찾을까요?", 9.3),
            _item(5, "개미는 태양을 이용해 돌아와요!", 9.2),
            _item(6, "개미는 태양을 따라 길을 찾아요!", 9.1),
        ]
    }
    candidates = hook_experiment._normalize_candidates(payload)
    assert len(candidates) >= 5, candidates
    assert all("잡는다" not in item["text"] for item in candidates), candidates
    candidates.sort(key=lambda item: item["total_score"], reverse=True)
    winner = hook_experiment._best_passing_candidate(candidates)
    assert winner, candidates
    assert "잡는다" not in winner["text"], winner
    print("✅ Informal Hook cannot enter the selectable candidate pool")


if __name__ == "__main__":
    main()

import subprocess
import sys

subprocess.run([sys.executable, "ci_script_v2_visual_goal_hotfix.py"], check=True)

from content.script_engine_v2_runner import _normalize_scene_fields


def main():
    cases = (
        ({"spoken_line": "날개 끝에서는 압력 차이가 생깁니다."}, "날개 끝에서는 압력 차이가 생깁니다."),
        ({"primary_narration_copy": "공기가 날개 끝을 돌아 흐릅니다."}, "공기가 날개 끝을 돌아 흐릅니다."),
        ({"content": "윙렛은 날개 끝의 흐름을 바꿉니다."}, "윙렛은 날개 끝의 흐름을 바꿉니다."),
        ({"body": "그 결과 유도항력이 줄어듭니다."}, "그 결과 유도항력이 줄어듭니다."),
    )
    for scene, expected in cases:
        normalized = _normalize_scene_fields(scene)
        assert normalized["text"] == expected

    metadata_only = {
        "visual_description": "close-up of wingtip airflow",
        "search_query": "aircraft wingtip airflow",
        "role": "causal_clue",
        "scene_type": "explanation",
    }
    normalized = _normalize_scene_fields(metadata_only)
    assert not str(normalized.get("text", "")).strip(), normalized

    original = {
        "text": "기존 대사는 그대로 유지됩니다.",
        "content": "이 값으로 덮어쓰면 안 됩니다.",
        "visual_goal": "show the aircraft wingtip clearly",
        "keyword": "aircraft wingtip detail",
    }
    normalized = _normalize_scene_fields(original)
    assert normalized["text"] == original["text"]
    assert normalized["visual_goal"] == original["visual_goal"]
    assert normalized["keyword"] == original["keyword"]

    ambiguous = {
        "primary_narration_copy": "첫 대사 후보",
        "secondary_spoken_line": "두 번째 대사 후보",
        "visual_description": "winglet close-up",
    }
    normalized = _normalize_scene_fields(ambiguous)
    assert not str(normalized.get("text", "")).strip(), normalized

    print("PASS: Script Engine V2 safe writer text alias normalization (Run 32671180410 class)")


if __name__ == "__main__":
    main()

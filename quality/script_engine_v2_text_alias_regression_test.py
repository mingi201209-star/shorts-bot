import subprocess
import sys

subprocess.run([sys.executable, "ci_script_v2_visual_goal_hotfix.py"], check=True)

from content.script_engine_v2_runner import _normalize_repair_item, _normalize_scene_fields


def main():
    cases = (
        ({"spoken_line": "날개 끝에서는 압력 차이가 생깁니다."}, "날개 끝에서는 압력 차이가 생깁니다."),
        ({"primary_narration_copy": "공기가 날개 끝을 돌아 흐릅니다."}, "공기가 날개 끝을 돌아 흐릅니다."),
        ({"content": "윙렛은 날개 끝의 흐름을 바꿉니다."}, "윙렛은 날개 끝의 흐름을 바꿉니다."),
        ({"body": "그 결과 유도항력이 줄어듭니다."}, "그 결과 유도항력이 줄어듭니다."),
        ({"narration": {"text": "날개 끝 소용돌이가 약해집니다."}}, "날개 끝 소용돌이가 약해집니다."),
        ({"voiceover": {"content": "윙렛이 공기 흐름을 바꿉니다."}}, "윙렛이 공기 흐름을 바꿉니다."),
        ({"primary_narration_copy": {"body": "유도항력이 줄어듭니다."}}, "유도항력이 줄어듭니다."),
    )
    for scene, expected in cases:
        normalized = _normalize_scene_fields(scene)
        assert normalized["text"] == expected, normalized

    nested_repair = _normalize_repair_item({
        "scene_number": 3,
        "narration": {"text": "압력 차이 때문에 공기가 끝을 돌아 흐릅니다."},
        "search_query": "wingtip airflow pressure",
    })
    assert nested_repair["scene_index"] == 3
    assert nested_repair["text"] == "압력 차이 때문에 공기가 끝을 돌아 흐릅니다."

    metadata_only = {
        "visual_description": {"text": "close-up of wingtip airflow"},
        "search_query": "aircraft wingtip airflow",
        "role": "causal_clue",
        "scene_type": "explanation",
    }
    normalized = _normalize_scene_fields(metadata_only)
    assert not str(normalized.get("text", "")).strip(), normalized

    original = {
        "text": "기존 대사는 그대로 유지됩니다.",
        "content": "이 값으로 덮어쓰면 안 됩니다.",
        "narration": {"text": "이 중첩 값으로도 덮어쓰면 안 됩니다."},
        "visual_goal": "show the aircraft wingtip clearly",
        "keyword": "aircraft wingtip detail",
    }
    normalized = _normalize_scene_fields(original)
    assert normalized["text"] == original["text"]
    assert normalized["visual_goal"] == original["visual_goal"]
    assert normalized["keyword"] == original["keyword"]

    ambiguous = {
        "primary_narration_copy": {"text": "첫 대사 후보"},
        "secondary_spoken_line": {"content": "두 번째 대사 후보"},
        "visual_description": "winglet close-up",
    }
    normalized = _normalize_scene_fields(ambiguous)
    assert not str(normalized.get("text", "")).strip(), normalized

    print("PASS: Script Engine V2 flat+nested writer/repair text alias normalization")


if __name__ == "__main__":
    main()

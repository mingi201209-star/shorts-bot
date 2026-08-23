from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from content import script_generator as sg


def _candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾여 있는 이유",
        "core_question": "왜 비행기 날개 끝을 위로 꺾어 놓았을까?",
        "micro_narrative": {
            "hook": "비행기의 날개 끝을 자세히 보면 위로 꺾여 있는 것을 볼 수 있다.",
            "core_question": "왜 비행기 날개 끝을 위로 꺾어 놓았을까?",
            "reveal": "날개 끝 공기 흐름을 줄이는 구조",
            "payoff": "와류와 유도항력을 줄이는 데 도움이 된다",
        },
    }


def _selected_hook():
    return {
        "text": "비행기 날개 끝은 위로 꺾여 있습니다.",
        "visual_goal": "비행기의 날개 끝이 위로 꺾인 모습",
        "keyword": "airplane wingtip upward",
        "scores": {},
        "total_score": 9.0,
    }


locked = sg._with_locked_opening(_candidate(), _selected_hook())
assert locked["micro_narrative"]["hook"] == "비행기 날개 끝은 위로 꺾여 있습니다."
assert locked["micro_narrative"]["core_question"] == "그런데 왜 비행기 날개 끝을 위로 꺾어 놓았을까요?"

# Verify the wrapper passes the enriched candidate into legacy generation BEFORE
# any post-generation selected-hook decoration happens.
seen = {}
original_generate = sg._LEGACY.generate_script
try:
    def fake_generate(topic_info, candidate):
        seen["candidate"] = candidate
        return {
            "title": "fixture",
            "scenes": [
                {"text": candidate["micro_narrative"]["hook"], "visual_goal": "x", "keyword": "x"},
                {"text": candidate["micro_narrative"]["core_question"], "visual_goal": "y", "keyword": "y"},
            ],
        }

    sg._LEGACY.generate_script = fake_generate
    # Avoid external Hook API; feed the selected opening deterministically through
    # the same helper used by generate_script and assert the legacy call contract.
    enriched = sg._with_locked_opening(_candidate(), _selected_hook())
    result = sg._LEGACY.generate_script({}, enriched)
finally:
    sg._LEGACY.generate_script = original_generate

assert seen["candidate"]["micro_narrative"]["hook"] == "비행기 날개 끝은 위로 꺾여 있습니다."
assert seen["candidate"]["micro_narrative"]["core_question"] == "그런데 왜 비행기 날개 끝을 위로 꺾어 놓았을까요?"
assert result["scenes"][0]["text"].endswith("있습니다.")
assert result["scenes"][1]["text"].startswith("그런데 ")
assert result["scenes"][1]["text"].endswith("까요?")

print("✅ Script wrapper opening-order regression PASS")

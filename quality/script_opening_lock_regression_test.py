from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Apply only the hotfix that owns this contract. It must remain compatible with
# the base source as well as the full production chain.
subprocess.run(
    [sys.executable, "ci_script_validation_recovery_hotfix.py"],
    cwd=ROOT,
    check=True,
)

from content import script_generator as sg


def candidate():
    return {
        "topic": "비행기 날개 끝이 위로 꺾여 있는 이유",
        "angle": "winglet causal explanation",
        "core_question": "그런데 왜 이렇게 꺾여 있을까요?",
        "micro_narrative": {
            "hook": "비행기 날개 끝이 위로 꺾여 있습니다.",
            "core_question": "그런데 왜 이렇게 꺾여 있을까요?",
            "reveal": "날개 끝 공기 흐름을 줄이는 구조다",
            "payoff": "와류와 유도항력을 줄이는 데 도움이 된다",
        },
        "fact_check_focus": ["wingtip vortex", "induced drag"],
        "visual_proof": ["airplane winglet close up"],
    }


def scene(text, goal="항공기 날개 끝 구조", keyword="airplane winglet close up"):
    return {"text": text, "visual_goal": goal, "keyword": keyword}


payload = {
    "title": "fixture",
    "scenes": [
        scene("LLM이 첫 문장을 질문으로 바꿨나요?"),
        scene("왜 필요한지 지금 알려드려요."),
        scene("날개 끝에서는 소용돌이가 생기는데요."),
        scene("그 흐름 때문에 저항이 생기죠."),
        scene("직접 보세요."),
    ],
}

locked = sg._script_opening_lock_apply(payload, sg.validate_candidate(candidate()))

# 1/2: LLM cannot replace the approved opening narration.
assert locked["scenes"][0]["text"] == "비행기 날개 끝이 위로 꺾여 있습니다."
assert locked["scenes"][1]["text"] == "그런데 왜 이렇게 꺾여 있을까요?"

# Visual metadata survives the narration lock.
assert locked["scenes"][0]["visual_goal"] == "항공기 날개 끝 구조"
assert locked["scenes"][0]["keyword"] == "airplane winglet close up"

# 3: whitelisted style-only repairs happen without another LLM call.
assert locked["scenes"][2]["text"] == "날개 끝에서는 소용돌이가 생깁니다."
assert locked["scenes"][3]["text"] == "그 흐름 때문에 저항이 생깁니다."
assert locked["scenes"][4]["text"] == "직접 볼 수 있습니다."

# 4: non-whitelisted wording remains untouched so existing validators still
# fail closed instead of silently changing facts/meaning.
unrepairable = {"title": "fixture", "scenes": [scene("x"), scene("y"), scene("정말 놀라워요.")]}
result = sg._script_opening_lock_apply(unrepairable, sg.validate_candidate(candidate()))
assert result["scenes"][2]["text"] == "정말 놀라워요."

print("✅ Script opening lock regression PASS")

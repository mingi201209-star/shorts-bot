from pathlib import Path
import subprocess
import sys

for hotfix in (
    "ci_hotfix.py",
    "ci_novelty_budget_hotfix.py",
    "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py",
    "ci_first5_retention_tts_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py",
):
    subprocess.run([sys.executable, hotfix], check=True)

from content import script_generator as sg
from content import hook_experiment as he
from video import hook_visual_dominance as hvd
from video import video_downloader as vd

candidate = {
    "reveal": "작은 구멍은 창문 사이 압력을 단계적으로 조절한다",
    "payoff": "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다",
}

def result(texts):
    return {
        "_candidate_retention": candidate,
        "scenes": [
            {"text": text, "visual_goal": "airplane window detail visible", "keyword": "airplane window detail"}
            for text in texts
        ],
    }

# A: immediate full answer leakage is rejected.
bad_leak = result([
    "비행기 창문에는 일부러 작은 구멍을 뚫어놓는다.",
    "작은 구멍은 창문 사이 압력을 단계적으로 조절한다.",
    "창문은 여러 겹으로 구성된다.",
    "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
])
ok, reason = sg.validate_curiosity_retention(bad_leak)
assert not ok and "answer leakage" in reason, reason

# B/D: clue -> mechanism -> payoff progression passes and payoff answers the lock.
good = result([
    "비행기 창문에는 일부러 작은 구멍을 뚫어놓는다.",
    "이 구멍은 바깥 공기를 들이기 위한 통로가 아니다.",
    "비행기 창문은 한 장이 아니라 여러 겹으로 구성된다.",
    "고도가 올라가면 창문 안팎의 압력 차이가 커진다.",
    "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
])
ok, reason = sg.validate_curiosity_retention(good)
assert ok, reason

# C: repeated tease without new information is rejected.
bad_tease = result([
    "비행기 창문에는 일부러 작은 구멍을 뚫어놓는다.",
    "이 작은 구멍에는 중요한 비밀이 숨어 있다.",
    "이 작은 구멍에는 중요한 비밀이 숨어 있다.",
    "창문은 여러 겹으로 구성된다.",
    "그래서 객실 쪽 창에 부담이 집중되지 않게 압력을 조절한다.",
])
ok, reason = sg.validate_curiosity_retention(bad_tease)
assert not ok and "repeated tease" in reason, reason

# E: #20 information-density protection remains present and payoff filler is rejected.
assert hasattr(sg, "detect_information_density_issue")
filler = [
    {"text": "압력 차이는 창문 여러 겹에 나뉘어 전달됩니다."},
    {"text": "압력 차이는 창문 여러 겹에 나뉘어 전달되는 역할을 합니다."},
]
assert sg.detect_information_density_issue(filler) is not None

# F: #20 contracts remain active.
assert he._output_quality_is_declarative_hook("비행기 창문에는 작은 구멍이 있다.")
assert not he._output_quality_is_declarative_hook("비행기 창문 구멍은 뭘까요?")
assert hvd.HOOK_SUBJECT_VISIBILITY_MIN == 8.0
assert vd.current_narration_semantic_match(
    {"title": "airplane window condensation layers", "tags": "window condensation layers"},
    "airplane window condensation layers",
) > vd.current_narration_semantic_match(
    {"title": "airplane cockpit", "tags": "airplane cockpit pilot"},
    "airplane window condensation layers",
)

# G: production contracts and bounded chain remain intact.
workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
for token in (
    "ci_output_quality_hotfix.py",
    "ci_curiosity_retention_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "SHORTS_TOPIC: ${{ inputs.topic }}",
    "SHORTS_CANDIDATE_SCOPE: ${{ inputs.candidate_scope }}",
):
    assert token in workflow, token
providers = Path("video/video_providers.py").read_text(encoding="utf-8")
assert "Pexels" in providers and "Pixabay" in providers
assert "provider failure" in providers.lower() or "except" in providers

print("PASS: answer leakage, clue progression, anti-tease, payoff alignment, #20 contracts, production chain")

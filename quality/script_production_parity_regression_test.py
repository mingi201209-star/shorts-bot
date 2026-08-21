from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HOTFIXES = (
    "ci_hotfix.py", "ci_novelty_budget_hotfix.py", "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py", "ci_hook_generation_hotfix.py", "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py", "ci_first5_retention_tts_hotfix.py", "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py", "ci_topic_input_hotfix.py", "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py", "ci_curiosity_retention_hotfix.py", "ci_visual_specificity_hotfix.py",
    "ci_design_causality_hotfix.py", "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py", "ci_visible_evidence_provenance_hotfix.py",
    "ci_hook_production_parity_hotfix.py", "ci_hook_fallback_quality_floor_hotfix.py",
    "ci_ai_visual_fallback_hotfix.py", "ci_ai_visual_mechanism_fallback_hotfix.py",
    "ci_causal_information_progression_hotfix.py", "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
)
for hotfix in HOTFIXES:
    subprocess.run([sys.executable, hotfix], cwd=ROOT, check=True)

from content import script_generator as sg
legacy = getattr(sg, "_LEGACY", sg)


def scene(text, goal, keyword):
    return {"text": text, "visual_goal": goal, "keyword": keyword}


def design_candidate():
    return {
        "topic": "항공기 객실 소음 제어 장치의 구조와 작동 방식",
        "angle": "객실 소음 제어 장치의 감지·처리·대응 신호 causal chain",
        "core_question": "객실 소음 제어 장치는 어떤 단계로 반복 소음을 줄이는가",
        "micro_narrative": {
            "hook": "항공기 객실 소음 제어 장치에는 숨은 구조가 있습니다.",
            "core_question": "소음을 어떤 순서로 감지하고 줄이는가",
            "reveal": "감지된 반복 소음에 대응하는 신호를 사용한다",
            "payoff": "목표 소음 성분이 서로 간섭하면서 작게 들리게 된다",
        },
        "fact_check_focus": [
            "마이크 또는 센서가 반복 소음을 감지할 수 있다",
            "제어기가 감지 신호를 처리할 수 있다",
            "스피커가 대응 신호를 재생하는 active noise control 방식이 존재한다",
            "반대 위상 성분의 간섭으로 목표 소음 성분을 줄일 수 있다",
            "모든 소리를 완전히 제거하는 기능으로 일반화하지 않는다",
        ],
        "visual_proof": ["aircraft cabin microphone", "audio controller", "cabin speaker"],
        "selection_reason": "design mechanism regression fixture",
    }


def non_design_candidate():
    return {
        "topic": "비가 그친 뒤 무지개가 보이는 자연 현상",
        "angle": "관찰 가능한 자연 현상 소개",
        "core_question": "무지개는 어떤 조건에서 보이는가",
        "micro_narrative": {
            "hook": "비가 그친 하늘에 무지개가 나타납니다.",
            "core_question": "무지개는 언제 보이는가",
            "reveal": "빛과 물방울이 함께 있는 조건에서 보인다",
            "payoff": "관찰 위치와 빛의 조건이 맞아야 한다",
        },
        "fact_check_focus": ["빛과 물방울 조건"],
        "visual_proof": ["rainbow after rain"],
        "selection_reason": "non-design regression fixture",
    }


def good_scenes():
    return [
        scene("항공기 소음 제어 장치에는 숨은 구조가 있습니다.", "항공기 객실의 소음 제어 장치", "aircraft cabin noise system"),
        scene("객실 소음은 엔진과 공기 흐름에서 계속 들어옵니다.", "비행 중인 항공기 객실 내부", "aircraft cabin flight noise"),
        scene("좁은 객실에서는 소음을 줄이는 장치가 공간 제약 안에서 작동해야 합니다.", "항공기 객실 벽과 좌석 구조", "aircraft cabin interior wall"),
        scene("마이크가 객실의 반복 소음을 감지합니다.", "객실 내부 마이크 또는 소음 센서", "aircraft cabin microphone sensor"),
        scene("제어기가 감지된 신호의 특징을 계산합니다.", "오디오 제어기와 신호 처리 장치", "audio controller signal processing"),
        scene("스피커가 반대 위상의 소리를 만들어 냅니다.", "객실 스피커가 소리를 재생하는 모습", "aircraft cabin speaker audio"),
        scene("두 소리가 겹치면 목표로 삼은 성분이 작아집니다.", "두 음파가 겹치는 교육용 파형", "sound wave interference diagram"),
        scene("이 과정은 모든 소리를 없애는 방식은 아닙니다.", "여러 소리가 남아 있는 객실 환경", "aircraft cabin ambient sound"),
        scene("비행 상태가 달라지면 들어오는 소음 특성도 달라집니다.", "비행 중 객실과 엔진 환경 변화", "aircraft cabin engine flight"),
        scene("제어기는 그 변화에 맞춰 출력을 조절합니다.", "오디오 제어기의 출력 조절", "audio controller output adjustment"),
        scene("스피커 출력도 계산된 변화에 맞춰 이어집니다.", "객실 스피커 출력 장면", "cabin speaker playback system"),
        scene("그 결과 목표로 삼은 소음 성분이 더 작게 들립니다.", "소음이 줄어든 항공기 객실", "aircraft cabin reduced noise"),
    ]


def repeated_mechanism_scenes():
    scenes = good_scenes()
    scenes[4] = scene("시스템은 특정 주파수를 분석합니다.", "소음 주파수 분석 화면", "noise frequency analysis display")
    scenes[5] = scene("이어서 방향과 주파수를 분석합니다.", "소리 방향과 주파수 분석", "sound direction frequency analysis")
    scenes[9] = scene("반대 신호를 만들어 냅니다.", "반대 위상 신호 파형", "inverse sound signal waveform")
    scenes[10] = scene("상쇄음을 다시 발생시킵니다.", "상쇄 소리를 재생하는 스피커", "cancellation sound speaker")
    return scenes


def payload(scenes):
    return {"title": "production parity fixture", "scenes": scenes}


class FakeCompletions:
    def __init__(self, outputs, prompts):
        self.outputs = list(outputs)
        self.prompts = prompts
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        self.prompts.append(kwargs["messages"][1]["content"])
        if not self.outputs:
            raise AssertionError("unexpected extra Script API call")
        item = self.outputs.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(item, ensure_ascii=False)))],
            usage=SimpleNamespace(),
        )


def install_fake(outputs, prompts):
    fake = FakeCompletions(outputs, prompts)
    runtime_fn = getattr(
        legacy,
        "_script_parity_original_generate_script",
        getattr(legacy, "generate_script"),
    )
    runtime = runtime_fn.__globals__
    installed = False
    for name, value in list(runtime.items()):
        try:
            completions = value.chat.completions
        except Exception:
            continue
        if hasattr(completions, "create"):
            runtime[name] = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=fake.create))
            )
            installed = True
            break
    if not installed:
        runtime["openai"] = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake.create))
        )
    runtime["authorize_call"] = lambda model: fake.calls + 1
    runtime["record_usage"] = lambda model, response: {"cost_usd": 0.0}
    runtime["print_budget_status"] = lambda: None
    return fake


# A/B/E: exercise the exported production sg.generate_script() entrypoint across the
# compatibility wrapper. The first response must be rejected only when context reaches legacy validation.
design_prompts = []
fake = install_fake([payload(repeated_mechanism_scenes()), payload(good_scenes())], design_prompts)
result = sg.generate_script(
    {"category": "engineering", "topic": "aircraft cabin noise control"},
    design_candidate(),
)
assert fake.calls == 2, f"design production path should reject first script, calls={fake.calls}"
assert result["scenes"][4]["text"] == good_scenes()[4]["text"]
assert legacy._SCRIPT_PARITY_ACTIVE_CONTEXT is None

# G: actual production design prompt uses a max cap, not legacy minimum-fill pressure.
assert design_prompts, "design prompt not captured"
assert "최대 90초" in design_prompts[-1], design_prompts[-1]
assert "75~90초가 되도록 충분한 문장 분량" not in design_prompts[-1], design_prompts[-1]
assert "TARGET_MIN_SECONDS를 채우기 위해" in design_prompts[-1], design_prompts[-1]

# C/G: non-design topics retain legacy duration behavior.
general_prompts = []
fake_general = install_fake([payload(good_scenes())], general_prompts)
general_result = sg.generate_script(
    {"category": "nature", "topic": "rainbow after rain"},
    non_design_candidate(),
)
assert fake_general.calls == 1
assert general_result["title"] == "production parity fixture"
assert "75~90초" in general_prompts[0], general_prompts[0]
assert not legacy.design_causality_applicable(legacy._script_parity_context(non_design_candidate()))

# D: repeated result/outcome language remains rejected.
repeated_result = [
    scene("이 구조는 안전성을 높입니다.", "안전한 구조", "aircraft structure safety"),
    scene("그래서 파손 위험을 줄입니다.", "파손 위험 감소", "aircraft damage risk"),
    scene("결과적으로 더 안전한 운용이 가능합니다.", "안전한 운용", "aircraft safe operation"),
]
assessment = legacy.causal_information_progression_assessment(repeated_result, legacy._script_parity_context(design_candidate()))
assert not assessment["pass"] and (
    "result repetition" in assessment["reason"] or "result enumeration" in assessment["reason"]
), assessment

# E: same mechanism wording/detail is not over-counted as independent information units.
mechanism_repeat = [
    scene("시스템은 특정 주파수를 분석합니다.", "주파수 분석", "noise frequency analysis"),
    scene("이어서 방향과 주파수를 분석합니다.", "방향과 주파수 분석", "sound direction frequency"),
]
assessment = legacy.causal_information_progression_assessment(mechanism_repeat, legacy._script_parity_context(design_candidate()))
assert not assessment["pass"] and "mechanism paraphrase" in assessment["reason"], assessment

# F: genuinely distinct component/causal steps remain valid.
genuine_steps = [
    scene("마이크가 객실 소음을 감지합니다.", "객실 마이크", "aircraft microphone noise"),
    scene("제어기가 감지 신호를 분석합니다.", "오디오 제어기", "audio controller analysis"),
    scene("스피커가 반대 위상의 소리를 만들어 냅니다.", "객실 스피커", "cabin speaker inverse sound"),
]
assessment = legacy.causal_information_progression_assessment(genuine_steps, legacy._script_parity_context(design_candidate()))
assert assessment["pass"], assessment

# H: generic outro after payoff remains rejected by #30.
outro = good_scenes() + [scene("이처럼 작은 설계에서 안전은 시작됩니다.", "일반 항공기", "generic airplane flight")]
assessment = legacy.causal_information_progression_assessment(outro, legacy._script_parity_context(design_candidate()))
assert not assessment["pass"] and "generic outro" in assessment["reason"], assessment

# I: exercise the existing bounded quality rewrite loop without API calls.
import main as production_main
rewrite_calls = {"count": 0}
consensus_calls = {"count": 0}
production_main.run_initial_judges = lambda script: {"hook": [{}], "novelty": [{}], "fact": [{}], "visual": [{}]}

def fake_consensus(pool):
    consensus_calls["count"] += 1
    if consensus_calls["count"] == 1:
        return {"decision": "REWRITE", "weak_domains": []}
    return {"decision": "PASS", "weak_domains": []}
production_main.build_consensus = fake_consensus
production_main.print_consensus = lambda value: None
production_main.has_hard_novelty_failure = lambda value: False

def fake_rewrite(script, consensus, model=None):
    rewrite_calls["count"] += 1
    return {"changed": True, "script_data": script, "domains": ["hook"]}
production_main.rewrite_script = fake_rewrite
production_main.print_rewrite_result = lambda value: None
production_main.enrich_visual_plan = lambda scenes: scenes
production_main.validate_visual_plan = lambda scenes: (True, "ok")
production_main.rerun_changed_domains = lambda pool, script, domains: pool
quality_result = production_main.run_quality_process({"scenes": good_scenes()})
assert quality_result["status"] == "PASS", quality_result
assert rewrite_calls["count"] == 1, rewrite_calls
assert quality_result["rewrite_count"] == 1, quality_result
assert production_main.MAX_REWRITES == 1

# Script-only scope and #29 OFF production contract.
changed = subprocess.check_output(
    ["git", "diff", "--name-only", "41cf642dd47c12380027ef549f52475d55ea3b1f...HEAD"],
    cwd=ROOT,
    text=True,
).splitlines()
assert not any(name.startswith("video/") for name in changed), changed
main_workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
assert 'AI_VISUAL_FALLBACK_ENABLED: "false"' in main_workflow

print("PASS: script production parity A-I; #20/#21/#23/#30 preserved; video #24-#29 untouched; no Sora/API calls")

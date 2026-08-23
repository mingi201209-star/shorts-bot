"""Deterministic retention-structure planning for Shorts scripts.

The experiment adapts runtime/scene density to the Candidate's causal complexity.
It is intentionally provider-free and does not weaken existing Hook/FACT/visual gates.
"""

from copy import deepcopy
import re

RETENTION_STRUCTURE_VERSION = 1

RUNTIME_BUCKETS = {
    "24-30s": {"min_seconds": 24, "max_seconds": 30, "min_scenes": 7, "max_scenes": 9},
    "32-42s": {"min_seconds": 32, "max_seconds": 42, "min_scenes": 9, "max_scenes": 11},
    "45-55s": {"min_seconds": 45, "max_seconds": 55, "min_scenes": 12, "max_scenes": 13},
}

_LONG_SIGNALS = (
    "역사", "처음", "과거", "변화", "바뀌", "발전", "설계 변화", "사고", "실패",
    "history", "evolution", "redesign", "failure",
)
_MECHANISM_SIGNALS = (
    "원리", "압력", "구조", "작동", "mechanism", "때문", "원인", "결과", "그래서",
)
_CAUSAL_CLUE_SIGNALS = (
    "때문", "원인", "압력", "힘", "공기", "구조", "작동", "차이", "분산", "조절", "균형",
)
_CONSEQUENCE_SIGNALS = (
    "위험", "문제", "없으면", "그래서", "필요", "중요", "버티", "막", "줄", "안전", "더",
)
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _candidate_text(candidate):
    if not isinstance(candidate, dict):
        return ""
    parts = []
    for key in (
        "topic", "angle", "core_question", "specific_observation", "constraint",
        "counterintuitive_result", "tradeoff", "concrete_condition", "selection_reason",
    ):
        value = candidate.get(key)
        if value:
            parts.append(str(value))
    micro = candidate.get("micro_narrative") or {}
    if isinstance(micro, dict):
        parts.extend(str(v) for v in micro.values() if v)
    return " ".join(parts).lower()


def classify_runtime_bucket(candidate):
    """Classify a Candidate without network/model calls."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a mapping")

    text = _candidate_text(candidate)
    visual_proof = candidate.get("visual_proof") or []
    facts = candidate.get("fact_check_focus") or []
    micro = candidate.get("micro_narrative") or {}

    long_hits = sum(1 for signal in _LONG_SIGNALS if signal in text)
    mechanism_hits = sum(1 for signal in _MECHANISM_SIGNALS if signal in text)
    evidence_items = len(visual_proof) if isinstance(visual_proof, list) else 1
    fact_items = len(facts) if isinstance(facts, list) else 1

    # History/design-evolution genuinely needs more causal beats; do not squeeze it.
    if long_hits >= 2 or (long_hits >= 1 and fact_items >= 3):
        return "45-55s"

    # Cause + mechanism or several distinct evidence beats fits the middle bucket.
    if mechanism_hits >= 2 or evidence_items >= 3 or fact_items >= 3:
        return "32-42s"

    # One self-contained why/how question should not be padded toward ~50 seconds.
    if isinstance(micro, dict) and micro.get("reveal") and micro.get("payoff"):
        return "24-30s"
    return "32-42s"


def build_retention_plan(candidate):
    bucket = classify_runtime_bucket(candidate)
    spec = RUNTIME_BUCKETS[bucket]
    return {
        "version": RETENTION_STRUCTURE_VERSION,
        "runtime_bucket": bucket,
        **spec,
        "first5_contract": [
            {"role": "phenomenon", "window": "0.0-1.5s"},
            {"role": "consequence", "window": "1.5-3.0s"},
            {"role": "causal_clue", "window": "3.0-5.0s"},
        ],
        "visual_update_target_seconds": [2.5, 4.0],
    }


def runtime_instruction(plan):
    return (
        f"Retention 실험 bucket={plan['runtime_bucket']}: 전체 TTS를 "
        f"{plan['min_seconds']}~{plan['max_seconds']}초, "
        f"{plan['min_scenes']}~{plan['max_scenes']} Scene으로 만든다. "
        "Scene 수를 채우기 위한 반복/filler는 금지하고 각 Scene은 새로운 causal 또는 visual beat를 가져야 한다."
    )


def first5_prompt_contract():
    return """[FIRST 5 SEC MINI NARRATIVE — REQUIRED]\n첫 3 Scene은 같은 말을 반복하지 않고 정보를 전진시킨다.\n- Scene 1 retention_role=phenomenon: 0.0~1.5초. 이상한 현상/결론을 대상 이름과 함께 직접 제시한다.\n- Scene 2 retention_role=consequence: 1.5~3.0초. 그 현상이 왜 중요/위험/의외인지 결과나 제약을 제시한다.\n- Scene 3 retention_role=causal_clue: 3.0~5.0초. 정답 전체를 미루지 말고 원인의 첫 단서를 공개한다.\nScene 1~3은 서로 다른 visual_goal/keyword로 시각 정보도 전진시킨다.\n"""


def density_prompt_contract():
    return """[RETENTION DENSITY — REQUIRED]\n- 답이 이미 완결된 뒤 같은 뜻을 다시 요약하지 않는다.\n- 동일 mechanism/result를 표현만 바꿔 반복하지 않는다.\n- 답에 필요하지 않고 화면으로 증명하기도 어려운 문장은 제거한다.\n- 한 Scene에는 핵심 개념 1개를 우선한다.\n- 가능한 경우 2.5~4초마다 새로운 시각 정보가 나타나도록 Scene/visual_goal을 설계한다.\n"""


def _normalized_tokens(text):
    return set(_TOKEN_RE.findall(str(text or "").lower()))


def _text_similarity(left, right):
    a, b = _normalized_tokens(left), _normalized_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def validate_first5_progression(scenes):
    if not isinstance(scenes, list) or len(scenes) < 3:
        return False, "first5 requires at least 3 scenes"
    expected = ("phenomenon", "consequence", "causal_clue")
    for index, role in enumerate(expected):
        scene = scenes[index]
        if str(scene.get("retention_role", "")).strip() != role:
            return False, f"scene {index + 1} retention_role must be {role}"
        if not str(scene.get("text", "")).strip():
            return False, f"scene {index + 1} text missing"
        if not str(scene.get("visual_goal", "")).strip():
            return False, f"scene {index + 1} visual_goal missing"

    second = str(scenes[1].get("text", ""))
    third = str(scenes[2].get("text", ""))
    if not any(signal in second for signal in _CONSEQUENCE_SIGNALS):
        return False, "scene 2 lacks an explicit consequence/constraint cue"
    if not any(signal in third for signal in _CAUSAL_CLUE_SIGNALS):
        return False, "scene 3 lacks an explicit causal clue"

    if _text_similarity(scenes[0].get("text"), scenes[1].get("text")) >= 0.72:
        return False, "scene 1 and 2 repeat the same information"
    if _text_similarity(scenes[1].get("text"), scenes[2].get("text")) >= 0.72:
        return False, "scene 2 and 3 repeat the same information"
    return True, "first5 progression pass"


def validate_density(scenes):
    if not isinstance(scenes, list):
        return False, "scenes must be a list"
    texts = [str(scene.get("text", "")).strip() for scene in scenes if isinstance(scene, dict)]
    for index in range(1, len(texts)):
        if _text_similarity(texts[index - 1], texts[index]) >= 0.78:
            return False, f"adjacent scenes {index}/{index + 1} are redundant"
    for index, scene in enumerate(scenes):
        text = str(scene.get("text", ""))
        # Three or more semicolon/comma-separated causal clauses usually overload one visual beat.
        clause_count = len(re.findall(r"[,;]|그리고|또한|동시에", text)) + 1
        if clause_count > 4:
            return False, f"scene {index + 1} carries too many concepts"
    return True, "density pass"


def annotate_script(script, plan):
    result = deepcopy(script)
    result["retention_structure"] = deepcopy(plan)
    result["runtime_bucket"] = plan["runtime_bucket"]
    return result

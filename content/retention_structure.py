"""Deterministic retention-structure planning for Shorts scripts.

The experiment adapts runtime/scene density to the Candidate's causal complexity.
It is intentionally provider-free and does not weaken existing Hook/FACT/visual gates.
"""

from copy import deepcopy
import re

RETENTION_STRUCTURE_VERSION = 4

# Runtime is a preference, not a quota. Scene count is derived from the amount
# of distinct supported information instead of padding every topic to a minute.
RUNTIME_BUCKETS = {
    "20-28s": {"min_seconds": 20, "max_seconds": 28},
    "24-35s": {"min_seconds": 24, "max_seconds": 35},
    "30-42s": {"min_seconds": 30, "max_seconds": 42},
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
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")

_GENERIC_EVALUATION_PATTERNS = (
    r"혁신적(?:인)?\s*(?:디자인|설계|구조)",
    r"긍정적(?:인)?\s*영향",
    r"좋은\s*(?:디자인|결과|효과|구조)",
    r"훌륭한\s*(?:디자인|설계|구조)",
    r"매우\s*(?:중요|효과적)",
)
_META_NARRATION_PATTERNS = (
    r"실제\s*(?:사진|영상)입니다",
    r"다이어그램입니다",
    r"화면에\s*(?:보이는|나오는)",
    r"visual[_ ]?goal",
)
_POSITIVE_EFFECT_TERMS = {
    "efficiency": ("효율", "연료", "efficiency", "fuel"),
    "performance": ("성능", "performance"),
    "stability": ("안정성", "안정적", "stability"),
}
_SEMANTIC_ATOMS = {
    "noise_reduction": (
        ("소음", "noise"),
        ("줄", "감소", "낮", "완화", "reduce", "quiet"),
    ),
    "vortex_reduction": (
        ("소용돌이", "vortex"),
        ("줄", "감소", "약", "reduce"),
    ),
    "airflow_mixing": (
        ("공기", "배기", "흐름", "airflow", "exhaust", "air"),
        ("섞", "혼합", "mix", "조절", "control"),
    ),
    "experience_payoff": (
        ("승객", "여행", "주변 환경", "환경", "공항", "passenger", "comfort", "environment"),
        ("편안", "쾌적", "영향", "부담", "quiet", "comfort", "소음"),
    ),
}


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


def _evidence_counts(candidate):
    text = _candidate_text(candidate)
    visual_proof = candidate.get("visual_proof") or []
    facts = candidate.get("fact_check_focus") or []
    long_hits = sum(1 for signal in _LONG_SIGNALS if signal in text)
    mechanism_hits = sum(1 for signal in _MECHANISM_SIGNALS if signal in text)
    evidence_items = len(visual_proof) if isinstance(visual_proof, list) else 1
    fact_items = len(facts) if isinstance(facts, list) else 1
    return long_hits, mechanism_hits, evidence_items, fact_items


def suggest_scene_count(candidate):
    """Choose a content-derived scene count; do not pad to a runtime quota."""
    long_hits, mechanism_hits, evidence_items, fact_items = _evidence_counts(candidate)
    # Six is the smallest practical V2 story: opening observation, question,
    # causal clue, one explanatory step, reveal, payoff. Extra scenes require
    # additional supported information; runtime never creates slots by itself.
    count = 6
    if fact_items >= 2 or evidence_items >= 2:
        count += 1
    if mechanism_hits >= 2:
        count += 1
    if long_hits >= 1:
        count += 1
    if long_hits >= 2 and (fact_items + evidence_items) >= 5:
        count += 1
    return count


def classify_runtime_bucket(candidate):
    """Classify a preferred duration without network/model calls."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a mapping")
    count = suggest_scene_count(candidate)
    if count <= 6:
        return "20-28s"
    if count <= 8:
        return "24-35s"
    return "30-42s"


def build_retention_plan(candidate):
    bucket = classify_runtime_bucket(candidate)
    spec = RUNTIME_BUCKETS[bucket]
    return {
        "version": RETENTION_STRUCTURE_VERSION,
        "runtime_bucket": bucket,
        "target_scene_count": suggest_scene_count(candidate),
        **spec,
        "first5_contract": [
            {"role": "phenomenon", "window": "0.0-1.5s"},
            {"role": "question", "window": "1.5-3.0s"},
            {"role": "causal_clue", "window": "3.0-5.0s"},
        ],
        "visual_update_target_seconds": [2.5, 4.0],
    }


def runtime_instruction(plan):
    return (
        f"Retention preferred bucket={plan['runtime_bucket']}: 전체 TTS는 보통 "
        f"{plan['min_seconds']}~{plan['max_seconds']}초를 선호하지만 시간은 quota가 아니다. "
        f"현재 근거가 지지하는 정보량 기준 target_scene_count={plan['target_scene_count']}를 사용한다. "
        "목표 시간을 채우려고 문장이나 Scene을 추가하지 않는다. 각 Scene은 이전 Scene에 없던 "
        "새 정보를 최소 하나 추가하고, 같은 mechanism/payoff를 표현만 바꿔 반복하지 않는다."
    )


def first5_prompt_contract():
    return """[FIRST 5 SEC MINI NARRATIVE — REQUIRED]\n첫 3 Scene은 같은 말을 반복하지 않고 정보를 전진시킨다.\n- Scene 1 retention_role=phenomenon: 0.0~1.5초. 화면에서 바로 확인 가능한 이상한 현상/상태를 대상 이름과 함께 격식체로 단정한다. 질문으로 시작하지 않는다.\n- Scene 2 retention_role=question: 1.5~3.0초. 반드시 '그런데'로 시작해 Scene 1의 관찰을 왜 그런지 묻는다. 자연스러운 질문형은 ~까요?만 사용한다. ~나요?/~어요?/~예요?는 금지한다.\n- Scene 3 retention_role=causal_clue: 3.0~5.0초. 최종 정답을 공개하지 말고 원인의 첫 단서 또는 물리적 제약을 한 단계만 공개한다.\nScene 1~3은 서로 다른 visual_goal/keyword로 시각 정보도 전진시킨다.\n"""


def density_prompt_contract():
    return """[RETENTION STORY V2 — REQUIRED]\n- 각 Scene은 앞 Scene들에 없던 NEW INFORMATION을 최소 하나 추가한다.\n- 이미 설명한 mechanism/result/payoff를 표현만 바꿔 새 Scene으로 만들지 않는다.\n- 단순 평가, 일반적인 긍정 표현, visual_goal/meta 설명은 독립 narration Scene이 될 수 없다.\n- 한 causal chain은 자연스럽게 압축하며 같은 원리를 여러 summary Scene으로 쪼개지 않는다.\n- payoff는 마지막에 한 번 명확하게 회수하고 그 뒤 comfort/benefit/result를 반복하지 않는다.\n- 5~8 Scene, 20~35초는 짧은 설명형 Shorts의 선호값일 뿐 quota가 아니다.\n- 설명이 더 짧게 끝나면 짧게 끝낸다. 목표 시간을 채우려고 문장이나 Scene을 추가하지 않는다.\n- facts에 없는 효율/성능/안정성 같은 일반적 positive effect를 길이 확보용으로 만들지 않는다.\n"""


def _normalized_tokens(text):
    return set(_TOKEN_RE.findall(str(text or "").lower()))


def _text_similarity(left, right):
    a, b = _normalized_tokens(left), _normalized_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _contains_any(text, terms):
    value = str(text or "").lower()
    return any(term.lower() in value for term in terms)


def _semantic_atoms(text):
    atoms = set()
    for name, (left_terms, right_terms) in _SEMANTIC_ATOMS.items():
        if _contains_any(text, left_terms) and _contains_any(text, right_terms):
            atoms.add(name)
    return atoms


def _supported_fact_text(plan):
    values = []
    if isinstance(plan, dict):
        for contract in plan.get("contracts") or []:
            if isinstance(contract, dict):
                values.extend(str(x) for x in contract.get("required_concepts") or [] if x)
    return " ".join(values).lower()


def validate_new_information(scenes, plan=None):
    """Return scene-local failures for semantic repetition/filler without LLM calls."""
    if not isinstance(scenes, list):
        return [{"scene_index": None, "reason": "scenes must be a list"}]

    contracts = (plan or {}).get("contracts") or []
    role_by_index = {
        int(item.get("index")): str(item.get("role", ""))
        for item in contracts
        if isinstance(item, dict) and item.get("index") is not None
    }
    locked_by_index = {
        int(item.get("index")): bool(item.get("locked"))
        for item in contracts
        if isinstance(item, dict) and item.get("index") is not None
    }
    support_text = _supported_fact_text(plan or {})
    failures = []

    atom_occurrences = {}
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        text = str(scene.get("text", "")).strip()
        if not text:
            continue

        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _GENERIC_EVALUATION_PATTERNS):
            failures.append({
                "scene_index": index,
                "reason": "new-information contract: generic evaluation filler is not a scene",
            })

        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _META_NARRATION_PATTERNS):
            failures.append({
                "scene_index": index,
                "reason": "new-information contract: visual/meta narration is not new story information",
            })

        # This is a Writer-filler guard, not a second FACT Judge. Candidate-owned
        # locked reveal/payoff text remains under the existing FACT pipeline.
        if not locked_by_index.get(index, False):
            for effect, terms in _POSITIVE_EFFECT_TERMS.items():
                if _contains_any(text, terms) and not _contains_any(support_text, terms):
                    failures.append({
                        "scene_index": index,
                        "reason": f"fact-safe filler guard: unsupported generic positive effect ({effect})",
                    })

        for atom in _semantic_atoms(text):
            atom_occurrences.setdefault(atom, []).append(index)

    for atom, indexes in atom_occurrences.items():
        if len(indexes) < 2:
            continue

        if atom == "experience_payoff":
            protected = [
                i for i in indexes
                if role_by_index.get(i) == "payoff" and locked_by_index.get(i)
            ]
            anchor = protected[-1] if protected else indexes[0]
        else:
            protected = [
                i for i in indexes
                if role_by_index.get(i) == "reveal" and locked_by_index.get(i)
            ]
            anchor = protected[-1] if protected else indexes[0]

        for index in indexes:
            if index == anchor:
                continue
            # A final locked payoff may restate the user-facing consequence once
            # after a locked reveal; the payoff semantic is checked separately.
            if (
                atom != "experience_payoff"
                and role_by_index.get(index) == "payoff"
                and locked_by_index.get(index)
            ):
                continue
            if atom == "experience_payoff":
                reason = f"payoff contract: scene repeats payoff already reserved for scene {anchor}"
            else:
                reason = f"new-information contract: scene repeats semantic claim {atom} reserved for scene {anchor}"
            failures.append({"scene_index": index, "reason": reason})

    deduped = []
    seen = set()
    for failure in failures:
        key = (failure.get("scene_index"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)
    return deduped


def validate_first5_progression(scenes):
    if not isinstance(scenes, list) or len(scenes) < 3:
        return False, "first5 requires at least 3 scenes"
    expected = ("phenomenon", "question", "causal_clue")
    for index, role in enumerate(expected):
        scene = scenes[index]
        if str(scene.get("retention_role", "")).strip() != role:
            return False, f"scene {index + 1} retention_role must be {role}"
        if not str(scene.get("text", "")).strip():
            return False, f"scene {index + 1} text missing"
        if not str(scene.get("visual_goal", "")).strip():
            return False, f"scene {index + 1} visual_goal missing"

    first = str(scenes[0].get("text", "")).strip()
    second = str(scenes[1].get("text", "")).strip()
    third = str(scenes[2].get("text", "")).strip()

    if first.endswith("?"):
        return False, "scene 1 must state the observable phenomenon before asking"
    if not second.startswith("그런데") or not second.endswith("?"):
        return False, "scene 2 must use 그런데 + opening question"
    if not second.endswith("까요?"):
        return False, "scene 2 question must use formal ~까요? ending"
    if not any(signal in third for signal in _CAUSAL_CLUE_SIGNALS):
        return False, "scene 3 lacks an explicit causal clue"

    if _text_similarity(first, second) >= 0.72:
        return False, "scene 1 and 2 repeat the same information"
    if _text_similarity(second, third) >= 0.72:
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
        clause_count = len(re.findall(r"[,;]|그리고|또한|동시에", text)) + 1
        if clause_count > 4:
            return False, f"scene {index + 1} carries too many concepts"
    return True, "density pass"


def annotate_script(script, plan):
    result = deepcopy(script)
    result["retention_structure"] = deepcopy(plan)
    result["runtime_bucket"] = plan["runtime_bucket"]
    return result

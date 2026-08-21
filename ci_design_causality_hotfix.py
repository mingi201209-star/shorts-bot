from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
if "[DESIGN CAUSALITY — PREFERRED]" not in text:
    text = text.replace(
        "[CURIOSITY RETENTION — REQUIRED]\n",
        "[DESIGN CAUSALITY — PREFERRED]\n"
        "구체적인 설계/구조/기능을 설명하는 주제에만 적용한다. 일반 현상·인물·사건 주제에는 기존 narrative path를 유지한다.\n"
        "장점 목록보다 OBSERVATION/HOOK → PROBLEM → CONSTRAINT → DESIGN CHOICE → MECHANISM → RESULT/PAYOFF의 검증 가능한 인과 흐름을 우선한다.\n"
        "핵심은 '무슨 장점이 있는가'보다 '어떤 문제와 제약 때문에 이 설계가 필요하고, 그 선택이 어떻게 작동하는가'를 이해시키는 것이다.\n"
        "PROBLEM과 CONSTRAINT는 Curiosity Retention의 CLUE 1/2로 사용할 수 있지만 Hook 직후 reveal/payoff 전체를 공개하지 않는다.\n"
        "각 causal Scene의 visual_goal/keyword는 problem, constraint, design, mechanism, result 중 그 Scene에서 설명하는 실제 대상을 직접 보여준다.\n"
        "FUNCTION(현재 역할), DESIGN INTENT(설계 목적), HISTORICAL CAUSE(실제 기원)를 구분한다. Candidate/Fact가 FUNCTION만 뒷받침하면 '이 때문에 설계됐다/발명됐다'고 단정하지 않는다.\n"
        "Candidate/Fact에 없는 constraint, 설계 의도, 역사적 원인을 스토리를 위해 만들어내지 않는다. 검증 근거가 부족하면 해당 causal 단계를 생략하고 사실 안전성을 우선한다.\n"
        "'A에도 도움이 되고 B에도 좋고 C 역할도 한다' 식 benefit enumeration은 피한다.\n\n"
        "[CURIOSITY RETENTION — REQUIRED]\n",
        1,
    )

text = append_once(
    text,
    "DESIGN_CAUSALITY_HELPER_V2",
    r'''
# DESIGN_CAUSALITY_HELPER_V2
_DESIGN_TOPIC_MARKERS = (
    "설계", "구조", "장치", "부품", "기능", "왜 이렇게", "왜 이런", "만들었", "작동",
    "design", "structure", "mechanism", "device", "component",
)
_DESIGN_STAGE_MARKERS = {
    "problem": ("문제", "위험", "부담", "차이가 커", "견뎌", "막히", "손상", "불안정"),
    "constraint": ("제약", "하지만", "그런데", "한계", "공간", "무게", "압력", "열", "하중", "유지보수", "비용"),
    "design": ("그래서", "설계", "구조를", "사용한다", "배치", "선택", "여러 겹", "장치를"),
    "mechanism": ("작동", "조절", "통해", "분산", "전달", "흐르", "열리", "닫히", "담당"),
    "result": ("그 결과", "결과적으로", "덕분에", "유지", "가능", "막을 수", "견딜 수"),
}
_DESIGN_FEATURE_LIST_PATTERNS = (
    "도움이 된다", "도움이 됩니다", "좋습니다", "좋다", "효과가 있다", "효과가 있습니다",
    "역할도 한다", "역할도 합니다", "에도 도움", "에도 좋", "또한", "뿐만 아니라",
)
_DESIGN_INTENT_CLAIMS = (
    "때문에 설계", "위해 설계", "위해 만들", "때문에 만들", "목적으로 설계", "발명되", "개발되",
)
_DESIGN_EVIDENCE_INTENT_MARKERS = (
    "설계 목적", "설계 의도", "위해 설계", "위해 만들", "때문에 설계", "발명", "개발 이유", "historical",
)


def design_causality_applicable(context):
    if not isinstance(context, dict):
        return False
    haystack = " ".join(str(context.get(key, "")) for key in ("topic", "angle", "core_question")).lower()
    return any(marker.lower() in haystack for marker in _DESIGN_TOPIC_MARKERS)


def _design_scene_texts(scenes):
    return [
        str(scene.get("text", "")).strip()
        for scene in (scenes or [])
        if isinstance(scene, dict) and str(scene.get("text", "")).strip()
    ]


def design_causality_assessment(scenes, context=None):
    texts = _design_scene_texts(scenes)
    joined = " ".join(texts)
    applicable = design_causality_applicable(context or {})
    stages = {
        stage: any(marker in joined for marker in markers)
        for stage, markers in _DESIGN_STAGE_MARKERS.items()
    }
    benefit_hits = sum(joined.count(marker) for marker in _DESIGN_FEATURE_LIST_PATTERNS)
    causal_stage_count = sum(1 for present in stages.values() if present)

    evidence_parts = []
    if isinstance(context, dict):
        evidence_parts.extend(str(item) for item in context.get("fact_check_focus", []) if str(item).strip())
        micro = context.get("micro_narrative", {})
        if isinstance(micro, dict):
            evidence_parts.extend(str(value) for value in micro.values() if str(value).strip())
    evidence = " ".join(evidence_parts)
    intent_claim = any(marker in joined for marker in _DESIGN_INTENT_CLAIMS)
    intent_supported = any(marker in evidence for marker in _DESIGN_EVIDENCE_INTENT_MARKERS)

    if not applicable:
        return {"applicable": False, "pass": True, "reason": "design causality not applicable", "stages": stages}
    if intent_claim and not intent_supported:
        return {"applicable": True, "pass": False, "reason": "unsupported design intent or historical cause", "stages": stages}
    if benefit_hits >= 2 and causal_stage_count < 3:
        return {"applicable": True, "pass": False, "reason": "benefit enumeration without causal chain", "stages": stages}
    return {
        "applicable": True,
        "pass": True,
        "reason": "design causality acceptable",
        "stages": stages,
        "benefit_hits": benefit_hits,
        "causal_stage_count": causal_stage_count,
    }


def design_causality_preference_score(scenes, context=None):
    assessment = design_causality_assessment(scenes, context or {"topic": "설계 구조"})
    if not assessment.get("applicable"):
        return 0
    stage_count = sum(1 for value in assessment.get("stages", {}).values() if value)
    penalty = int(assessment.get("benefit_hits", 0)) * 3
    if not assessment.get("pass"):
        penalty += 6
    return stage_count * 3 - penalty


def validate_design_causality(result):
    if not isinstance(result, dict):
        return True, "design causality skipped"
    context = result.get("_design_causality_context", {})
    assessment = design_causality_assessment(result.get("scenes", []), context)
    if not assessment.get("pass", True):
        return False, assessment.get("reason", "design causality failed")
    return True, assessment.get("reason", "design causality passed")


_design_causality_original_validate_script = validate_script


def validate_script(result):
    valid, reason = _design_causality_original_validate_script(result)
    if not valid:
        return valid, reason
    valid, causal_reason = validate_design_causality(result)
    if not valid:
        return False, f"Design Causality 실패: {causal_reason}"
    return True, reason
''',
)

# The Candidate already contains the only facts this layer may use. Pass that locked
# context into deterministic validation, then remove it from the generated payload.
needle = "            valid, reason = validate_script(\n                result\n            )"
replacement = "            result[\"_design_causality_context\"] = {\n                \"topic\": candidate[\"topic\"],\n                \"angle\": candidate[\"angle\"],\n                \"core_question\": candidate[\"core_question\"],\n                \"fact_check_focus\": candidate[\"fact_check_focus\"],\n                \"micro_narrative\": candidate[\"micro_narrative\"],\n            }\n            valid, reason = validate_script(\n                result\n            )\n            result.pop(\"_design_causality_context\", None)"
if needle in text and "result[\"_design_causality_context\"]" not in text:
    text = text.replace(needle, replacement, 1)
path.write_text(text, encoding="utf-8")


# Extend the existing explanation judge; no separate scoring framework or threshold.
path = Path("quality/explanation_judge.py")
text = path.read_text(encoding="utf-8")
if "5. DESIGN CAUSALITY" not in text:
    text = text.replace(
        "4. 범위 제한\n",
        "4. DESIGN CAUSALITY (설계/구조/기능형 주제에만 적용)\n"
        "- feature → benefit A → benefit B → benefit C 식 설명서형 나열이면 감점한다.\n"
        "- 가능한 경우 problem → constraint → design choice → mechanism → result가 검증된 사실 범위에서 자연스럽게 이어지는지 본다.\n"
        "- constraint가 근거에 없다면 억지로 요구하지 않는다. FUNCTION 근거만으로 DESIGN INTENT/HISTORICAL CAUSE를 단정하면 큰 문제다.\n"
        "- 일반 주제에는 이 구조를 강제하지 않는다.\n\n"
        "5. 범위 제한\n",
        1,
    )
path.write_text(text, encoding="utf-8")


path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
if "[DESIGN CAUSALITY 수정]" not in text:
    text = text.replace(
        "[CURIOSITY RETENTION 수정]\n",
        "[DESIGN CAUSALITY 수정]\n"
        "- 설계/구조/기능형 주제에서만 장점 목록을 검증된 problem → constraint → design choice → mechanism → result 흐름으로 재구성한다.\n"
        "- PROBLEM/CONSTRAINT를 #21의 clue로 활용하되 Hook 직후 reveal/payoff 전체를 공개하지 않는다.\n"
        "- Candidate/Fact에 없는 constraint, design intent, historical cause는 절대 추가하지 않는다. FUNCTION과 DESIGN INTENT를 동일시하지 않는다.\n"
        "- causal Scene의 visual_goal/keyword는 해당 problem/constraint/design/mechanism/result를 직접 보여주도록 유지한다.\n"
        "[CURIOSITY RETENTION 수정]\n",
        1,
    )
path.write_text(text, encoding="utf-8")

print("✅ Script Design Causality Layer applied")

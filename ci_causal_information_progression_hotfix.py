from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Extend the existing #23 design-causality path. This does not create a second
# narrative engine; it adds a stricter information-progression contract on top
# of the existing validator/judge/rewrite path.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
if "[CAUSAL NARRATIVE + NEW INFORMATION — REQUIRED]" not in text:
    text = text.replace(
        "[DESIGN CAUSALITY — PREFERRED]\n",
        "[DESIGN CAUSALITY — PREFERRED]\n"
        "[CAUSAL NARRATIVE + NEW INFORMATION — REQUIRED]\n"
        "설계/구조/장치/부품/기능형 주제에서만 적용한다. 비설계 주제에는 기존 narrative path를 유지한다.\n"
        "가능한 경우 OBSERVATION/HOOK → PROBLEM → CONSTRAINT → WEAK/FAILED ALTERNATIVE → DESIGN CHOICE → MECHANISM → RESULT/PAYOFF의 검증 가능한 causal spine을 먼저 잡는다. 모든 단계를 기계적으로 채우지 말고 근거 없는 단계는 생략한다.\n"
        "weak/failed alternative는 Candidate/Fact가 실제로 뒷받침할 때만 clue로 사용한다. 현재 FUNCTION만 확인됐다는 이유로 과거의 실패 방식, 설계 의도, 역사적 원인을 만들어내지 않는다.\n"
        "각 설명 Scene은 직전까지 없었던 새 information unit을 최소 하나 추가하는 것을 우선한다. 표현만 다른 동일 RESULT(예: 안전/위험 감소/더 안전함)를 새 정보로 세지 않는다.\n"
        "MECHANISM 뒤 RESULT를 한 번 회수했다면 같은 RESULT를 다른 표현으로 반복하거나 generic summary/outro를 붙이지 않는다. payoff가 끝났고 새 정보가 없으면 즉시 끝낸다.\n"
        "영상 길이를 맞추기 위해 filler를 추가하지 않는다. 정보가 짧으면 짧게 끝내며 duration 자체를 품질 목표로 사용하지 않는다.\n"
        "각 causal stage의 visual_goal/keyword는 그 stage에서 새로 설명하는 실제 대상/현상(problem, constraint, weak alternative, design, mechanism, result)을 직접 보여주도록 구체화한다.\n",
        1,
    )

text = append_once(
    text,
    "CAUSAL_INFORMATION_PROGRESSION_LAYER_V1",
    r'''
# CAUSAL_INFORMATION_PROGRESSION_LAYER_V1
_CAUSAL_GENERIC_TOKENS = {
    "그리고", "하지만", "그런데", "그래서", "결국", "때문", "이것", "이렇게",
    "합니다", "됩니다", "있습니다", "없습니다", "가능합니다", "역할", "효과",
    "도움", "도움이", "좋습니다", "결과", "결과적으로", "더", "또", "또한",
    "비행", "기능", "설계", "구조", "장치", "부분", "것입니다", "수", "있다",
}
_CAUSAL_RESULT_FAMILIES = {
    "safety_risk": (
        r"안전", r"파손\s*위험", r"손상\s*위험", r"고장\s*위험", r"사고\s*위험",
        r"위험.{0,8}(줄|낮|감소|방지)", r"파손.{0,8}(줄|낮|감소|방지)",
        r"손상.{0,8}(줄|낮|감소|방지)", r"더\s*안전",
    ),
    "efficiency": (r"효율", r"에너지.{0,8}(절약|감소|줄)", r"소모.{0,8}(줄|감소)"),
    "reliability": (r"신뢰성", r"안정적", r"고장.{0,8}(줄|감소|방지)"),
    "comfort": (r"편안", r"쾌적", r"불편.{0,8}(줄|감소)"),
}
_CAUSAL_GENERIC_OUTRO_PATTERNS = (
    r"알고\s*계셨나요", r"이해하는\s*기회가\s*되었", r"이처럼.+중요",
    r"오늘은.+알아봤", r"오늘.+살펴봤", r"작은\s*설계에서.*시작",
    r"기억해\s*두", r"흥미로운\s*사실",
)
_CAUSAL_WEAK_ALTERNATIVE_PATTERNS = (
    r"만약.+(?:문제|위험|집중|깨|파손|손상|견디|불가능|어렵)",
    r"(?:그대로|기존\s*방식|평범한\s*방식).+(?:문제|위험|한계|불가능|어렵)",
    r"(?:없으면|없다면).+(?:문제|위험|불가능|어렵)",
    r"(?:각진|네모난|날카로운).+(?:응력|힘|압력|문제|위험|집중|균열)",
)
_CAUSAL_STAGE_MARKERS_V2 = {
    "problem": ("문제", "위험", "부담", "손상", "파손", "균열", "차이가 커", "집중"),
    "constraint": ("제약", "한계", "하지만", "그런데", "압력", "무게", "공간", "열", "하중", "비용", "유지보수"),
    "weak_alternative": ("만약", "그대로라면", "그대로 두면", "기존 방식", "평범한 방식", "없으면", "없다면", "각진", "네모난"),
    "design": ("그래서", "선택", "사용", "배치", "바꾸", "둥글", "여러 겹", "설계"),
    "mechanism": ("작동", "조절", "분산", "전달", "집중을 줄", "흐르", "담당", "통해"),
    "result": ("그 결과", "결과적으로", "덕분에", "안전", "위험을 줄", "위험이 줄", "유지", "가능"),
}


def _causal_info_tokens(text):
    tokens = {
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣]+", str(text or ""))
        if len(token) >= 2
    }
    return {token for token in tokens if token not in _CAUSAL_GENERIC_TOKENS}


def _causal_result_families(text):
    compact = str(text or "")
    return {
        family
        for family, patterns in _CAUSAL_RESULT_FAMILIES.items()
        if any(re.search(pattern, compact) for pattern in patterns)
    }


def _causal_stage_presence(text):
    compact = str(text or "")
    return {
        stage
        for stage, markers in _CAUSAL_STAGE_MARKERS_V2.items()
        if any(marker in compact for marker in markers)
    }


def _causal_evidence_text(context):
    if not isinstance(context, dict):
        return ""
    parts = []
    parts.extend(str(item) for item in context.get("fact_check_focus", []) if str(item).strip())
    micro = context.get("micro_narrative", {})
    if isinstance(micro, dict):
        parts.extend(str(value) for value in micro.values() if str(value).strip())
    return " ".join(parts)


def _causal_weak_alternative_claimed(text):
    compact = str(text or "")
    return any(re.search(pattern, compact) for pattern in _CAUSAL_WEAK_ALTERNATIVE_PATTERNS)


def _causal_weak_alternative_supported(text, context):
    if not _causal_weak_alternative_claimed(text):
        return True
    evidence = _causal_evidence_text(context)
    if not evidence:
        return False
    claim_tokens = _causal_info_tokens(text)
    evidence_tokens = _causal_info_tokens(evidence)
    # Require concrete overlap; generic causal language alone is not evidence.
    return len(claim_tokens & evidence_tokens) >= 2


def causal_information_progression_assessment(scenes, context=None):
    context = context or {}
    applicable = design_causality_applicable(context)
    if not applicable:
        return {
            "applicable": False,
            "pass": True,
            "reason": "causal information progression not applicable",
            "repeated_result_scenes": [],
            "unsupported_alternatives": [],
        }

    scene_list = [scene for scene in (scenes or []) if isinstance(scene, dict)]
    seen_result_families = set()
    seen_concepts = set()
    repeated_result_scenes = []
    unsupported_alternatives = []
    generic_outro_scenes = []
    stage_union = set()
    scene_units = []

    for index, scene in enumerate(scene_list):
        body = str(scene.get("text", "")).strip()
        stages = _causal_stage_presence(body)
        stage_union.update(stages)
        families = _causal_result_families(body)
        concepts = _causal_info_tokens(body)
        new_concepts = concepts - seen_concepts

        non_result_causal = bool(stages & {"problem", "constraint", "weak_alternative", "design", "mechanism"})
        repeated_family = families & seen_result_families
        # A repeated outcome family with no new causal stage is a paraphrased result,
        # even if surface words differ (안전/파손 위험 감소/더 안전한 비행).
        if repeated_family and not non_result_causal:
            repeated_result_scenes.append(index)

        if _causal_weak_alternative_claimed(body) and not _causal_weak_alternative_supported(body, context):
            unsupported_alternatives.append(index)

        if any(re.search(pattern, body) for pattern in _CAUSAL_GENERIC_OUTRO_PATTERNS):
            generic_outro_scenes.append(index)

        scene_units.append({
            "index": index,
            "stages": sorted(stages),
            "result_families": sorted(families),
            "new_concepts": sorted(new_concepts),
        })
        seen_result_families.update(families)
        seen_concepts.update(concepts)

    result_only_count = sum(
        1
        for item in scene_units
        if item["result_families"] and not (
            set(item["stages"]) & {"problem", "constraint", "weak_alternative", "design", "mechanism"}
        )
    )
    causal_depth = len(stage_union & {"problem", "constraint", "weak_alternative", "design", "mechanism"})

    if unsupported_alternatives:
        return {
            "applicable": True,
            "pass": False,
            "reason": "unsupported weak/failed alternative",
            "unsupported_alternatives": unsupported_alternatives,
            "repeated_result_scenes": repeated_result_scenes,
            "scene_units": scene_units,
        }
    if repeated_result_scenes:
        return {
            "applicable": True,
            "pass": False,
            "reason": "result repetition without a new information unit",
            "repeated_result_scenes": repeated_result_scenes,
            "unsupported_alternatives": [],
            "scene_units": scene_units,
        }
    if result_only_count >= 3 and causal_depth < 2:
        return {
            "applicable": True,
            "pass": False,
            "reason": "result enumeration without causal progression",
            "repeated_result_scenes": [],
            "unsupported_alternatives": [],
            "scene_units": scene_units,
        }
    if generic_outro_scenes and generic_outro_scenes[-1] == len(scene_list) - 1:
        return {
            "applicable": True,
            "pass": False,
            "reason": "generic outro after payoff adds no information",
            "generic_outro_scenes": generic_outro_scenes,
            "scene_units": scene_units,
        }

    return {
        "applicable": True,
        "pass": True,
        "reason": "causal narrative adds distinct information units",
        "stages": sorted(stage_union),
        "causal_depth": causal_depth,
        "scene_units": scene_units,
        "repeated_result_scenes": [],
        "unsupported_alternatives": [],
    }


def causal_visual_progression_assessment(scenes):
    scene_list = [scene for scene in (scenes or []) if isinstance(scene, dict)]
    seen = set()
    distinct = 0
    for scene in scene_list:
        goal = str(scene.get("visual_goal", "")).strip()
        tokens = _causal_info_tokens(goal)
        if tokens and tokens != seen:
            if tokens - seen:
                distinct += 1
            seen.update(tokens)
    return {"distinct_visual_units": distinct, "scene_count": len(scene_list)}


_causal_progression_original_validate_script = validate_script


def validate_script(result):
    valid, reason = _causal_progression_original_validate_script(result)
    if not valid:
        return valid, reason
    if not isinstance(result, dict):
        return valid, reason
    context = result.get("_design_causality_context", {})
    assessment = causal_information_progression_assessment(result.get("scenes", []), context)
    if not assessment.get("pass", True):
        return False, f"Causal Information Progression 실패: {assessment.get('reason')}"
    return True, reason
''',
)
path.write_text(text, encoding="utf-8")


# Design-topic Hook guidance: preserve the declarative/fact-safe #20 contract,
# but prefer observation/problem-first rather than stating the final benefit.
path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")
if "[CAUSAL HOOK PREFERENCE]" not in text:
    text = text.replace(
        "- 첫 문장에서 Candidate 안의 이상현상, 반전 또는 관찰 가능한 결과를 직접 말해 즉시 \"왜?\"가 생기게 한다.\n",
        "- 첫 문장에서 Candidate 안의 이상현상, 반전 또는 관찰 가능한 결과를 직접 말해 즉시 \"왜?\"가 생기게 한다.\n"
        "- [CAUSAL HOOK PREFERENCE] Candidate가 설계/구조/장치/부품/기능형이라면 최종 장점/안전성/payoff를 먼저 말하기보다 관찰 가능한 이상한 설계 또는 problem-first 문장을 우선한다.\n"
        "- 설계형 Hook에서도 '~다.' 단정형, fact safety, curiosity gap을 유지하고 핵심 mechanism/payoff 전체를 첫 문장에서 공개하지 않는다.\n",
        1,
    )
path.write_text(text, encoding="utf-8")


# Extend the existing judge/rewrite prompts instead of adding another model call.
path = Path("quality/explanation_judge.py")
text = path.read_text(encoding="utf-8")
if "NEW INFORMATION PROGRESSION" not in text:
    text += '''\n\n# NEW INFORMATION PROGRESSION is injected by the production hotfix.\n'''
    text = text.replace(
        "DESIGN CAUSALITY (설계/구조/기능형 주제에만 적용)",
        "DESIGN CAUSALITY + NEW INFORMATION PROGRESSION (설계/구조/기능형 주제에만 적용)",
        1,
    )
    text = text.replace(
        "- 일반 주제에는 이 구조를 강제하지 않는다.\n",
        "- 일반 주제에는 이 구조를 강제하지 않는다.\n"
        "- 가능하고 근거가 있을 때 problem → constraint → weak/failed alternative → design choice → mechanism → result의 인과 흐름을 선호한다. weak alternative를 위해 사실을 만들면 안 된다.\n"
        "- '안전성 향상', '파손 위험 감소', '더 안전함'처럼 표현만 다른 동일 RESULT는 새 information unit이 아니다. 각 설명 문장이 새 원인/제약/구조/메커니즘/결과 정보를 추가하는지 본다.\n"
        "- payoff 이후 generic summary/outro가 새 사실을 추가하지 않으면 강하게 감점한다. 짧게 끝나는 것 자체는 감점 사유가 아니다.\n",
        1,
    )
path.write_text(text, encoding="utf-8")

path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
if "[CAUSAL INFORMATION PROGRESSION 수정]" not in text:
    text = text.replace(
        "[DESIGN CAUSALITY 수정]\n",
        "[DESIGN CAUSALITY 수정]\n"
        "[CAUSAL INFORMATION PROGRESSION 수정]\n"
        "- 설계형 대본의 repeated benefit/result를 표현만 바꾸지 말고 삭제/압축하고, 검증된 problem → constraint → weak alternative(근거 있을 때만) → design → mechanism → payoff 흐름으로 재구성한다.\n"
        "- 각 남는 설명 Scene에는 이전까지 없던 새 information unit이 있어야 한다. 동일 RESULT의 재표현은 하나만 남긴다.\n"
        "- FUNCTION 근거만 있을 때 weak alternative, DESIGN INTENT, HISTORICAL CAUSE를 새로 만들지 않는다. 근거가 없으면 해당 causal 단계를 생략한다.\n"
        "- payoff 이후 새 정보 없는 generic outro/summary를 제거한다. 길이를 채우기 위한 문장은 추가하지 않는다.\n"
        "- 각 causal Scene의 visual_goal/keyword는 그 Scene의 새 problem/constraint/alternative/design/mechanism/result를 직접 보여주게 유지한다.\n",
        1,
    )
path.write_text(text, encoding="utf-8")

print("✅ Causal Narrative + New Information Progression Layer applied")
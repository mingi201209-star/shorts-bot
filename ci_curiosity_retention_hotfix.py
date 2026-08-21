from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Keep the change on top of the existing script/quality path: generation guidance +
# deterministic validation. No new scoring framework or unbounded regeneration.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
if "[CURIOSITY RETENTION — REQUIRED]" not in text:
    text = text.replace(
        "[STORY]\nHook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.\n",
        "[STORY]\nHook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.\n"
        "[CURIOSITY RETENTION — REQUIRED]\n"
        "시간을 기계적으로 맞추지 말고 정보 공개 순서를 설계한다. Hook 직후 핵심 answer/reveal/payoff를 완전히 공개하지 마라.\n"
        "Hook 다음에는 Candidate가 허용하는 첫 단서를 주고, 이어서 새로운 단서 또는 mechanism을 누적한 뒤 후반에 핵심 payoff를 명확하게 공개한다.\n"
        "권장 정보 진행은 HOOK → CLUE → MECHANISM/SECOND CLUE → PAYOFF → END다. 같은 tease를 말만 바꿔 반복하지 마라.\n"
        "'끝까지 보면 알려드립니다' 같은 retention bait는 금지한다. payoff는 Hook/Core Question에 직접 답하고, payoff 이후 새 정보 없는 반복은 즉시 끝낸다.\n"
        "각 Scene의 visual_goal/keyword도 그 Scene에서 새로 공개되는 clue/mechanism/payoff를 직접 보여주게 하여 장면 정보도 함께 진행시킨다.\n",
        1,
    )
text = append_once(
    text,
    "CURIOSITY_RETENTION_LAYER",
    r'''
# CURIOSITY_RETENTION_LAYER
_CURIOSITY_BAIT_PATTERNS = (
    "끝까지 보면", "끝까지 보시면", "잠시 후 알려", "나중에 알려",
)


def _curiosity_tokens(text):
    return {
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣]+", str(text or ""))
        if len(token) >= 2
    }


def _curiosity_overlap(left, right):
    a = _curiosity_tokens(left)
    b = _curiosity_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def validate_curiosity_retention(result):
    scenes = result.get("scenes", []) if isinstance(result, dict) else []
    if len(scenes) < 4:
        return False, "curiosity progression requires hook, clue, mechanism, payoff"

    texts = [str(scene.get("text", "")).strip() for scene in scenes if isinstance(scene, dict)]
    if len(texts) < 4:
        return False, "curiosity progression scenes are incomplete"

    joined = " ".join(texts)
    if any(pattern in joined for pattern in _CURIOSITY_BAIT_PATTERNS):
        return False, "artificial retention bait detected"

    # Candidate reveal/payoff are the locked answer. Full near-verbatim disclosure in
    # the first two post-Hook scenes is answer leakage; later payoff remains allowed.
    candidate = result.get("_candidate_retention", {}) if isinstance(result, dict) else {}
    reveal = str(candidate.get("reveal", "")).strip()
    payoff = str(candidate.get("payoff", "")).strip()
    early = texts[1:min(3, len(texts))]
    for answer in (reveal, payoff):
        if not answer:
            continue
        for scene_text in early:
            if answer in scene_text or scene_text in answer or _curiosity_overlap(answer, scene_text) >= 0.72:
                return False, "answer leakage: locked reveal/payoff disclosed immediately after Hook"

    # A delayed answer is not enough: middle scenes must add distinct information,
    # rather than repeat the same tease with paraphrases.
    middle = texts[1:-1]
    for index, current in enumerate(middle):
        for prior in middle[:index]:
            if _curiosity_overlap(current, prior) >= 0.72:
                return False, "information progression failure: repeated tease without a new clue"

    # The final payoff must directly recover the locked reveal/payoff language enough
    # to answer the Hook/Core Question, not end ambiguously.
    final_window = " ".join(texts[max(1, len(texts) - 2):])
    locked_answers = [item for item in (payoff, reveal) if item]
    if locked_answers and max(_curiosity_overlap(item, final_window) for item in locked_answers) < 0.18:
        return False, "payoff alignment failure: ending does not answer the locked reveal/payoff"

    return True, "curiosity retention progression passed"


_curiosity_original_validate_script = validate_script


def validate_script(result):
    valid, reason = _curiosity_original_validate_script(result)
    if not valid:
        return valid, reason
    valid, reason = validate_curiosity_retention(result)
    if not valid:
        return False, f"Curiosity Retention 실패: {reason}"
    return True, reason
''',
)

# Pass only the already-locked Candidate reveal/payoff into validation. This is
# validation context, not a new generated fact or provider/search path.
needle = "            valid, reason = validate_script(\n                result\n            )"
replacement = "            result[\"_candidate_retention\"] = {\n                \"reveal\": micro[\"reveal\"],\n                \"payoff\": micro[\"payoff\"],\n            }\n            valid, reason = validate_script(\n                result\n            )\n            result.pop(\"_candidate_retention\", None)"
if needle in text and "result[\"_candidate_retention\"]" not in text:
    text = text.replace(needle, replacement, 1)
path.write_text(text, encoding="utf-8")


# Extend existing quality/rewrite guidance instead of creating another judge.
path = Path("quality/explanation_judge.py")
text = path.read_text(encoding="utf-8")
if "CURIOSITY RETENTION" not in text:
    text += '''\n\n# CURIOSITY RETENTION guidance is injected into the existing judge prompt by the production hotfix.\n'''
    text = text.replace(
        "INFORMATION DENSITY",
        "CURIOSITY RETENTION / INFORMATION DENSITY",
        1,
    )
path.write_text(text, encoding="utf-8")

path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
if "[CURIOSITY RETENTION 수정]" not in text:
    text = text.replace(
        "[INFORMATION DENSITY 수정]\n",
        "[CURIOSITY RETENTION 수정]\n"
        "- Hook 직후 locked reveal/payoff를 완전히 공개했다면 첫 단서 → mechanism/두 번째 단서 → 후반 payoff 순으로 재배치한다.\n"
        "- 정답을 미루기만 하며 같은 tease를 반복하지 말고 각 중간 Scene에 새로운 정보 보상을 둔다.\n"
        "- payoff는 Hook/Core Question에 짧고 구체적으로 직접 답하고, 이후 새 정보 없는 반복은 제거한다.\n"
        "- Candidate에 없는 사실은 추가하지 않는다.\n"
        "[INFORMATION DENSITY 수정]\n",
        1,
    )
path.write_text(text, encoding="utf-8")

print("✅ Curiosity Retention Layer applied")

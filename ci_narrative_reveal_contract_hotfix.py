from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Script contract: observation -> question -> causal journey -> final reveal.
path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
marker = "NARRATIVE_REVEAL_CONTRACT_V1"
block = r'''
# NARRATIVE_REVEAL_CONTRACT_V1
# Production narrative contract (#97): make the viewer understand why a design
# became necessary, but reserve the direct answer/payoff for the ending.
NARRATIVE_REVEAL_PROMPT = r"""
[NARRATIVE REVEAL CONTRACT — REQUIRED]
설계/구조/현상형 주제에서는 다음 순서를 우선한다.
1) 첫 대사: 화면에서 바로 확인 가능한 이상한 사실/상태를 격식체로 단정한다.
   예: "비행기 날개 끝이 위로 꺾여 있습니다."
2) 바로 다음 대사: "그런데"로 이어 그 관찰 사실을 질문한다.
   예: "그런데 왜 이렇게 꺾여 있을까요?"
3) 중간: 정답을 말하지 말고, 왜 이런 구조가 필요해졌는지 문제와 원인을 쉬운 말로 한 단계씩 설명한다.
4) 마지막 reveal: opening 질문의 직접 답을 마지막 payoff에서 회수한다.
   예: "그래서 날개 끝을 위로 꺾어 이 공기 흐름을 줄이는 것입니다."

중간 설명에서는 final answer를 미리 말하지 않는다. "~하기 위해 만들어졌습니다"처럼 opening 질문을 즉시 끝내는 문장을 reveal 이전에 쓰지 않는다.
전문용어보다 현상을 쉬운 말로 먼저 설명한다. 전문용어가 필요하면 쉬운 설명 뒤에 이름을 붙인다.
"안전/효율/성능 때문입니다" 같은 추상적 결론만 말하지 말고, 문제 -> 원인 -> 물리적/구조적 제약 -> 해결 구조가 필요해지는 과정을 구체적으로 설명한다.
한 문장에는 가능한 한 하나의 인과 아이디어만 담는다.
대사는 해요체(~요/~해요/~돼요/~이에요/~예요)를 쓰지 않고 ~습니다/~입니다/~합니다/~됩니다/~있습니다 계열 격식체를 사용한다. 질문의 자연스러운 ~까요?는 허용한다.
"""

# Inject this contract into the prompt source without replacing existing fact,
# causality, retention, or quality instructions.
try:
    _narrative_prompt_anchor = "[CAUSAL NARRATIVE + NEW INFORMATION — REQUIRED]"
    if _narrative_prompt_anchor in SCRIPT_PROMPT and "[NARRATIVE REVEAL CONTRACT — REQUIRED]" not in SCRIPT_PROMPT:
        SCRIPT_PROMPT = SCRIPT_PROMPT.replace(
            _narrative_prompt_anchor,
            NARRATIVE_REVEAL_PROMPT + "\n" + _narrative_prompt_anchor,
            1,
        )
except NameError:
    pass

_PREMATURE_REVEAL_PATTERNS = (
    r"(?:이|그|해당|이런|이러한)?\s*(?:구조|장치|부품|설계|형태|윙렛).{0,24}(?:위해|목적|역할).{0,12}(?:만들|설계|사용|달|적용)",
    r"(?:정답|이유|비밀)은?.{0,35}(?:때문|것입니다|데 있습니다)",
)


def delayed_answer_reveal_assessment(scenes):
    scene_list = [scene for scene in (scenes or []) if isinstance(scene, dict)]
    if len(scene_list) < 3:
        return {"pass": True, "reason": "short script; defer to existing validators"}

    first = str(scene_list[0].get("text", "")).strip()
    second = str(scene_list[1].get("text", "")).strip()
    opening_ok = bool(first) and not first.endswith("?")
    question_ok = second.startswith("그런데") and "?" in second and second.rstrip().endswith("?")

    # Reserve the final 25% (at least one scene) for payoff.  Before that point,
    # direct purpose/answer formulations are considered premature; causal clues
    # remain legal.
    reveal_start = max(2, int(len(scene_list) * 0.75))
    leaks = []
    for index, scene in enumerate(scene_list[2:reveal_start], start=2):
        body = str(scene.get("text", "")).strip()
        if any(re.search(pattern, body) for pattern in _PREMATURE_REVEAL_PATTERNS):
            leaks.append(index)

    final_text = " ".join(
        str(scene.get("text", "")).strip() for scene in scene_list[reveal_start:]
    )
    final_reveal_ok = bool(final_text) and any(
        token in final_text for token in ("그래서", "때문입니다", "것입니다", "이유")
    )

    if not opening_ok:
        return {"pass": False, "reason": "opening must state an observable fact before asking"}
    if not question_ok:
        return {"pass": False, "reason": "second scene must use 그런데 + opening question"}
    if leaks:
        return {"pass": False, "reason": "direct answer revealed before final payoff", "leak_scenes": leaks}
    if not final_reveal_ok:
        return {"pass": False, "reason": "final section does not explicitly resolve opening question"}
    return {"pass": True, "reason": "observation-question-causal-journey-final-reveal contract"}


_narrative_reveal_original_validate_script = validate_script


def validate_script(result):
    valid, reason = _narrative_reveal_original_validate_script(result)
    if not valid:
        return valid, reason
    if not isinstance(result, dict):
        return valid, reason
    assessment = delayed_answer_reveal_assessment(result.get("scenes", []))
    if not assessment.get("pass", True):
        return False, f"Narrative Reveal Contract 실패: {assessment.get('reason')}"
    return True, reason
'''
text = append_once(text, marker, block)
path.write_text(text, encoding="utf-8")


# Hook generation: make the preferred first two beats explicit while preserving
# existing scoring/fact safety.
path = Path("content/hook_experiment.py")
text = path.read_text(encoding="utf-8")
if "[OBSERVATION -> QUESTION HOOK CONTRACT]" not in text:
    anchor = "- 첫 문장에서 Candidate 안의 이상현상, 반전 또는 관찰 가능한 결과를 직접 말해 즉시 \"왜?\"가 생기게 한다.\n"
    addition = (
        anchor
        + "- [OBSERVATION -> QUESTION HOOK CONTRACT] 설계/구조/현상형 Hook은 첫 문장에서 화면에 보이는 상태를 ~습니다/~있습니다 격식체로 단정하고, 바로 다음 문장에서 '그런데 왜 ...까요?' 형태로 질문한다. 첫 문장부터 질문하거나 정답/설계 목적을 공개하지 않는다.\n"
        + "- 예: '비행기 날개 끝이 위로 꺾여 있습니다. 그런데 왜 이렇게 꺾여 있을까요?'\n"
        + "- 해요체(~요/~해요/~돼요/~이에요/~예요)는 사용하지 않는다. 자연스러운 질문형 ~까요?는 허용한다.\n"
    )
    if text.count(anchor) != 1:
        raise RuntimeError("hook observation-question anchor mismatch")
    text = text.replace(anchor, addition, 1)
path.write_text(text, encoding="utf-8")


# Rewrite prompt: prevent a rewrite from destroying the narrative/speech contract.
path = Path("quality/rewrite_engine.py")
text = path.read_text(encoding="utf-8")
text = append_once(
    text,
    "NARRATIVE_REVEAL_REWRITE_CONTRACT_V1",
    r'''
# NARRATIVE_REVEAL_REWRITE_CONTRACT_V1
# Marker consumed by regression/production prompt assembly: rewrites must retain
# observation -> 그런데 question -> causal clues -> final answer ordering, must
# not move the direct answer earlier, and must use formal ~습니다/~입니다 style
# (with natural ~까요? questions) rather than 해요체.
''',
)
path.write_text(text, encoding="utf-8")

print("✅ narrative reveal + formal narration contract hotfix applied")

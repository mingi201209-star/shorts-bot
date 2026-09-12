from pathlib import Path

PATH = Path("content/script_engine_v2_validation.py")
MARKER = "# RUN_34663907508_OPENING_HUMAN_CONTRACT_V1"

# Run 34663907508 (HUMAN QA FAILURE A): the final, post-Rewrite Scene 1/2
# pair still repeated the same information stage despite PR #330's Candidate-
# level `_hook_restates_question` guard passing it. Root cause: that guard's
# shared-token-overlap ratio is diluted by the Writer/Rewrite's longer,
# meta-teaser-padded prose ("...사실은 많은 분들이 간과하시지만, 이 디자인에는
# 중요한 이유가 있습니다.") -- lots of filler tokens lower the overlap ratio
# below the reject threshold even though zero real causal/constraint/result
# content was added. This is a second, independent, additive gate at the
# final Script Engine V2 level (a safety net for exactly this Rewrite-stage
# escape -- Section 3/CASE OPENING-7), not a relaxation or replacement of the
# existing Candidate-level check, which stays unchanged.
_APPEND = r'''

# RUN_34663907508_OPENING_HUMAN_CONTRACT_V1
# Wraps the already-twice-wrapped validate_scene_basics (PR #330's own
# SCRIPT_HUMAN_QUALITY_SCENE_PROGRESSION_V1 sits on top of
# ci_grounded_keyword_contract_hotfix.py's wrap) the same late-binding way --
# additive only, never removing or loosening an existing check.
_OPENING_CONTRACT_BEFORE_HUMAN_QA_V1 = validate_scene_basics

# General (non-topic-specific) Korean meta-teaser phrases: a scene that only
# says "there's a reason/secret" without stating the reason itself. Not a
# semantic classifier -- a closed, literal marker list, the same style as
# PR #330's own _HUMAN_QUALITY_FILLER_PHRASES.
_OPENING_META_TEASER_PHRASES = (
    "중요한 이유가 있습니다",
    "중요한 이유가 있다",
    "이유가 숨어 있습니다",
    "이유가 숨어 있다",
    "간과",
    "흥미로운 사실이 있습니다",
    "흥미로운 사실이 있다",
    "비밀이 있습니다",
    "비밀이 있다",
    "비밀이 숨어",
    "그냥 그런 것이 아닙니다",
    "그냥 그런 것이 아니다",
    "알고 보면",
    "생각보다",
)

# The same closed causal-content word family PR #330 already uses
# (CAUSAL_CLUE_TOKENS) plus a few additional constraint/result/contrast
# words. Presence of any of these means Scene 1 actually stated real
# progression content, so a meta-teaser phrase appearing alongside one is
# not this escape (CASE OPENING-3): a real causal clue/constraint/result/
# contrast always wins over a coincidental teaser-like word.
_OPENING_CAUSAL_CONTENT_TOKENS = (
    "때문", "원인", "압력", "응력", "힘", "공기", "구조", "작동",
    "차이", "분산", "조절", "균형", "제약", "대조", "결과",
)

_OPENING_QUESTION_MARKERS = ("왜", "이유", "무엇", "어떻게", "어째서", "?")

# Defense-in-depth for CASE OPENING-7 (a Rewrite-stage regression must be
# caught here even when it takes the *original* PR #330 bare-restatement
# shape, not just the meta-teaser-padded one): an independent, final-level
# replica of candidate_explorer.py's own _hook_restates_question contract.
# Deliberately duplicated rather than imported -- Section 4's layer
# separation keeps Candidate-level and Script-Engine-V2-level validators
# independent so neither has to reach into the other's module.
_OPENING_CLAIM_MARKERS = (
    "일부러", "의도적으로", "고의로",
    "아니다", "아닙니다", "아니라", "않습니다", "않는다",
    "사실은", "실제로는", "오히려", "대신",
)
_OPENING_TOKEN_STOPWORDS = {"그런데", "그리고", "하지만", "그래서", "그렇다면", "정말", "과연", "왜", "이유"}
_OPENING_TOKEN_SUFFIXES = (
    "에서는", "에게서", "으로는", "라는", "에서", "으로", "에게",
    "은", "는", "이", "가", "을", "를", "의", "에", "로", "와", "과", "도", "만",
)


def _opening_content_tokens(text):
    tokens = []
    for raw in re.findall(r"[0-9A-Za-z가-힣]+", str(text or "")):
        token = raw
        changed = True
        while changed:
            changed = False
            for suffix in _OPENING_TOKEN_SUFFIXES:
                if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                    token = token[:-len(suffix)]
                    changed = True
                    break
        if len(token) < 2 or token in _OPENING_TOKEN_STOPWORDS:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens


def _opening_scene1_lacks_real_progression(text):
    value = str(text or "")
    if not any(phrase in value for phrase in _OPENING_META_TEASER_PHRASES):
        return False
    if any(token in value for token in _OPENING_CAUSAL_CONTENT_TOKENS):
        return False
    return True


def _opening_scene2_asks_why_same_subject(scene1_text, scene2_text):
    q = str(scene2_text or "")
    if not any(marker in q for marker in _OPENING_QUESTION_MARKERS):
        return False
    s1_tokens = set(re.findall(r"[0-9A-Za-z가-힣]{2,}", str(scene1_text or "")))
    s2_tokens = set(re.findall(r"[0-9A-Za-z가-힣]{2,}", q))
    return bool(s1_tokens & s2_tokens)


def _opening_scene1_bare_restatement(scene1_text, scene2_text):
    q = str(scene2_text or "")
    if not any(marker in q for marker in _OPENING_QUESTION_MARKERS):
        return False
    hook_tokens = set(_opening_content_tokens(scene1_text))
    question_tokens = set(_opening_content_tokens(q))
    if len(hook_tokens) < 2:
        return False
    shared = hook_tokens & question_tokens
    overlap_ratio = len(shared) / float(len(hook_tokens))
    if any(marker in str(scene1_text or "") for marker in _OPENING_CLAIM_MARKERS):
        return len(shared) == len(hook_tokens) and overlap_ratio >= 0.90
    return len(shared) >= 2 and overlap_ratio >= 0.50


def opening_human_contract_violation_reason(scene1_text, scene2_text):
    if (
        _opening_scene1_lacks_real_progression(scene1_text)
        and _opening_scene2_asks_why_same_subject(scene1_text, scene2_text)
    ):
        return (
            "opening states no real progression (meta-teaser only) before "
            "scene 2 asks why about the same subject"
        )
    if _opening_scene1_bare_restatement(scene1_text, scene2_text):
        return "opening scene 1 restates the same proposition scene 2 asks as a question"
    return ""


def opening_human_contract_violated(scene1_text, scene2_text):
    return bool(opening_human_contract_violation_reason(scene1_text, scene2_text))


def validate_scene_basics(script, plan):
    ok, failures = _OPENING_CONTRACT_BEFORE_HUMAN_QA_V1(script, plan)
    failures = list(failures)

    scenes = script.get("scenes") if isinstance(script, dict) else None
    if isinstance(scenes, list) and len(scenes) >= 2:
        scene1 = scenes[0] if isinstance(scenes[0], dict) else {}
        scene2 = scenes[1] if isinstance(scenes[1], dict) else {}
        scene1_text = str(scene1.get("text", "")).strip()
        scene2_text = str(scene2.get("text", "")).strip()
        if scene1_text and scene2_text:
            reason = opening_human_contract_violation_reason(scene1_text, scene2_text)
            if reason:
                failures.append({"scene_index": 1, "reason": reason})

    deduped = []
    seen = set()
    for failure in failures:
        key = (failure.get("scene_index"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)

    return not deduped, deduped
'''


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("Run 34663907508 opening human contract already installed")
        return
    if "def validate_scene_basics(" not in text:
        raise RuntimeError(
            "Run 34663907508 opening human contract requires "
            "script_engine_v2_validation.validate_scene_basics"
        )
    PATH.write_text(text.rstrip() + "\n" + _APPEND + "\n", encoding="utf-8")
    print("✅ Run 34663907508 opening human contract installed; no threshold/retry/budget change")


if __name__ == "__main__":
    main()

from pathlib import Path
import runpy


# Apply the narrow deterministic repair before speech validation is injected.
# This prevents a single safe 하다-style ending from forcing a full Script retry.
runpy.run_path("ci_script_local_formal_repair_hotfix.py", run_name="__main__")


# ============================================================
# Script Generator: sentence-level deterministic validation
# ============================================================
script_path = Path("content/script_generator.py")
script_source = script_path.read_text(encoding="utf-8")

# Local formal repair may already have inserted validate_korean_speech_text
# between openai and config. Anchor on config instead of the fragile full block.
script_import_marker = "from config import (\n"
script_import_replacement = (
    "from quality.korean_speech_style import validate_scenes_speech_style\n\n"
    "from config import (\n"
)
if "from quality.korean_speech_style import validate_scenes_speech_style" not in script_source:
    if script_source.count(script_import_marker) != 1:
        raise RuntimeError("script_generator.py speech-style import marker mismatch")
    script_source = script_source.replace(script_import_marker, script_import_replacement, 1)

script_validation_marker = '    return True, "V3.2.1.2 Script 하드 검사 통과"\n'
script_validation_replacement = '''    valid, reason = validate_scenes_speech_style(scenes)\n\n    if not valid:\n        return False, reason\n\n    return True, "V3.2.1.2 Script 하드 검사 통과"\n'''
if script_validation_replacement not in script_source:
    if script_source.count(script_validation_marker) != 1:
        raise RuntimeError("script_generator.py speech-style validation marker mismatch")
    script_source = script_source.replace(script_validation_marker, script_validation_replacement, 1)

script_path.write_text(script_source, encoding="utf-8")


# ============================================================
# Hook Experiment: reject non-formal Hook candidates before scoring
# ============================================================
hook_path = Path("content/hook_experiment.py")
hook_source = hook_path.read_text(encoding="utf-8")

hook_import_marker = "import openai\n\nfrom config import OPENAI_KEY\n"
hook_import_replacement = (
    "import openai\n\n"
    "from quality.korean_speech_style import validate_korean_speech_text\n\n"
    "from config import OPENAI_KEY\n"
)
if "from quality.korean_speech_style import validate_korean_speech_text" not in hook_source:
    if hook_source.count(hook_import_marker) != 1:
        raise RuntimeError("hook_experiment.py speech-style import marker mismatch")
    hook_source = hook_source.replace(hook_import_marker, hook_import_replacement, 1)

hook_shape_marker = '''        if not _valid_hook_shape(text, keyword):\n            continue\n\n        scores, total_score = _score_hook(item)\n'''
hook_shape_replacement = '''        if not _valid_hook_shape(text, keyword):\n            continue\n\n        speech_valid, _ = validate_korean_speech_text(\n            text,\n            allow_nominal=True,\n        )\n        if not speech_valid:\n            continue\n\n        scores, total_score = _score_hook(item)\n'''
if hook_shape_replacement not in hook_source:
    if hook_source.count(hook_shape_marker) != 1:
        raise RuntimeError("hook_experiment.py speech-style candidate marker mismatch")
    hook_source = hook_source.replace(hook_shape_marker, hook_shape_replacement, 1)

hook_path.write_text(hook_source, encoding="utf-8")


# ============================================================
# Downstream Hook generation hotfix: keep generation and validation contracts
# aligned. ci_hook_generation_hotfix.py runs AFTER this file in production, so
# patch its prompt source now to prevent it from reintroducing 해요체 examples.
# Preserve legacy marker sentences that later hotfixes search for exactly.
# ============================================================
hook_generation_hotfix_path = Path("ci_hook_generation_hotfix.py")
if hook_generation_hotfix_path.exists():
    generation_source = hook_generation_hotfix_path.read_text(encoding="utf-8")
    generation_source = generation_source.replace(
        "- 모든 spoken Hook은 자연스러운 한국어 존댓말로 끝낸다. 예: ~요, ~죠, ~니다, ~니까, ~세요.\n"
        "- 반말/해라체 종결인 ~다, ~한다, ~했다, ~이다를 사용하지 않는다.\n",
        "- 모든 spoken Hook은 격식체 존댓말로 끝낸다. 평서문은 ~습니다/~입니다/~합니다/~됩니다/~있습니다 계열을 사용한다.\n"
        "- 해요체인 ~요/~해요/~돼요/~이에요/~예요/~죠/~세요는 사용하지 않는다. 자연스러운 질문형 ~까요?만 예외로 허용한다.\n"
        "- 반말/해라체 종결인 ~다, ~한다, ~했다, ~이다도 사용하지 않는다.\n",
    )
    legacy_feedback = "길이 탈락이면 13~15자 목표를 우선하고, speech_style_failure면 반드시 존댓말 종결을 사용한다.\n"
    formal_feedback = legacy_feedback + "- 추가 문체 계약: speech_style_failure를 고칠 때 해요체를 쓰지 말고 반드시 ~습니다/~입니다/~합니다/~있습니다 계열 격식체로 고친다. 질문은 ~까요?만 허용한다.\n"
    if formal_feedback not in generation_source:
        generation_source = generation_source.replace(legacy_feedback, formal_feedback)
    generation_source = generation_source.replace(
        '"text": "한국어 존댓말 Hook 한 문장",',
        '"text": "한국어 격식체 Hook 한 문장",',
    )
    generation_source = generation_source.replace(
        '"자연스러운 한국어 존댓말, 화면으로 직접 증명 가능한 첫 장면을 "',
        '"~습니다/~입니다 계열의 격식체 한국어, 화면으로 직접 증명 가능한 첫 장면을 "',
    )
    hook_generation_hotfix_path.write_text(generation_source, encoding="utf-8")


# ============================================================
# Rewrite Engine: validate rewritten narration without spending a second LLM
# call merely to normalize speech style. FACT-owned retry semantics remain
# untouched and can still use FACT_REWRITE_MAX_ATTEMPTS=2.
# ============================================================
rewrite_path = Path("quality/rewrite_engine.py")
rewrite_source = rewrite_path.read_text(encoding="utf-8")

rewrite_import_marker = "import openai\n\nfrom config import OPENAI_KEY\n"
rewrite_import_replacement = (
    "import openai\n\n"
    "from quality.korean_speech_style import validate_script_speech_style\n\n"
    "from config import OPENAI_KEY\n"
)
if "from quality.korean_speech_style import validate_script_speech_style" not in rewrite_source:
    if rewrite_source.count(rewrite_import_marker) != 1:
        raise RuntimeError("rewrite_engine.py speech-style import marker mismatch")
    rewrite_source = rewrite_source.replace(rewrite_import_marker, rewrite_import_replacement, 1)

# Run 34670696121 authority: the previous speech hotfix changed non-FACT
# rewrites from one attempt to two. A Hook rewrite then spent a whole second
# LLM call solely because one line ended in "...되어 있는데요", pushing the
# production over the unchanged $0.05 cost ceiling. Keep base semantics:
# non-FACT = one LLM rewrite; FACT = FACT_REWRITE_MAX_ATTEMPTS.
max_attempts_marker = "    max_attempts = FACT_REWRITE_MAX_ATTEMPTS if fact_guard_enabled else 1\n"
if rewrite_source.count(max_attempts_marker) != 1:
    raise RuntimeError("rewrite_engine.py max_attempts marker mismatch")

repair_helper_marker = "# REWRITE_SPEECH_DETERMINISTIC_REPAIR_V1\n"
repair_helper = r'''# REWRITE_SPEECH_DETERMINISTIC_REPAIR_V1
_REWRITE_SAFE_FORMAL_ENDING_REPAIRS = (
    (re.compile(r"되어 있는데요(?P<p>[.!?]?)$"), r"되어 있습니다\g<p>"),
    (re.compile(r"있는데요(?P<p>[.!?]?)$"), r"있습니다\g<p>"),
    (re.compile(r"인데요(?P<p>[.!?]?)$"), r"입니다\g<p>"),
    (re.compile(r"(?:이에요|예요)(?P<p>[.!?]?)$"), r"입니다\g<p>"),
    (re.compile(r"(?:거예요|것이에요)(?P<p>[.!?]?)$"), r"것입니다\g<p>"),
    (re.compile(r"(?:돼요|되어요)(?P<p>[.!?]?)$"), r"됩니다\g<p>"),
)


def _repair_rewrite_speech_style(script_data):
    """Repair only semantically unambiguous terminal casual forms.

    This is intentionally narrower than the validator. Ambiguous endings such
    as ~네요/~군요/~나요/~죠/~세요/~해요 are not rewritten here; if one of
    those remains, the non-FACT Rewrite is discarded rather than spending a
    second model call. No keyword/visual/grounding/ownership field is touched.
    """
    repaired = copy.deepcopy(script_data)
    changed = False
    for scene in repaired.get("scenes", []):
        text = scene.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        candidate = text.rstrip()
        for pattern, replacement in _REWRITE_SAFE_FORMAL_ENDING_REPAIRS:
            updated = pattern.sub(replacement, candidate)
            if updated != candidate:
                scene["text"] = updated
                changed = True
                break

    if not changed:
        return None

    speech_valid, _ = validate_script_speech_style(repaired)
    return repaired if speech_valid else None


'''
rewrite_def_marker = "def rewrite_script(script_data, consensus, *, model=DEFAULT_MODEL):\n"
if repair_helper_marker not in rewrite_source:
    if rewrite_source.count(rewrite_def_marker) != 1:
        raise RuntimeError("rewrite_engine.py rewrite_script marker mismatch")
    rewrite_source = rewrite_source.replace(rewrite_def_marker, repair_helper + rewrite_def_marker, 1)

rewrite_call_marker = '''        rewritten = _run_rewrite_call(\n            script_data,\n            consensus,\n            domains,\n            model=model,\n            retry_fact_issues=retry_fact_issues,\n        )\n\n        if not fact_guard_enabled:\n            break\n'''
rewrite_call_replacement = '''        rewritten = _run_rewrite_call(\n            script_data,\n            consensus,\n            domains,\n            model=model,\n            retry_fact_issues=retry_fact_issues,\n        )\n\n        speech_valid, speech_reason = validate_script_speech_style(rewritten)\n        if not speech_valid:\n            print(f"🚫 Rewrite speech-style 검사 실패: {speech_reason}")\n            repaired = _repair_rewrite_speech_style(rewritten)\n            if repaired is not None:\n                rewritten = repaired\n                print("✅ Rewrite speech-style을 deterministic 격식체 repair로 복구했습니다.")\n            elif fact_guard_enabled and attempt < max_attempts:\n                # FACT-owned bounded retry semantics are preserved. This path\n                # can still use the existing second rewrite call, because the\n                # rewrite is already FACT-critical rather than speech-only.\n                print("➡️ FACT Rewrite의 기존 bounded 재시도를 유지합니다.")\n                continue\n            else:\n                print(\n                    "⚠️ Rewrite speech-style을 안전하게 복구할 수 없어 "\n                    "추가 LLM 호출 없이 원본 Script로 복귀합니다."\n                )\n                rewritten = copy.deepcopy(script_data)\n                break\n\n        if not fact_guard_enabled:\n            break\n'''
if rewrite_call_replacement not in rewrite_source:
    if rewrite_source.count(rewrite_call_marker) != 1:
        raise RuntimeError("rewrite_engine.py speech-style repair marker mismatch")
    rewrite_source = rewrite_source.replace(rewrite_call_marker, rewrite_call_replacement, 1)

rewrite_path.write_text(rewrite_source, encoding="utf-8")

# #97 extends the mandatory speech path with the observation-question-delayed-
# reveal narrative contract. Chaining it here guarantees every production/CI
# path that already applies ci_speech_style_hotfix.py also applies #97.
runpy.run_path("ci_narrative_reveal_contract_hotfix.py", run_name="__main__")

print("✅ Korean formal speech-style + narrative reveal hotfix applied")

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

script_import_marker = "import openai\n\nfrom config import (\n"
script_import_replacement = (
    "import openai\n\n"
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
# Rewrite Engine: validate rewritten narration and retry at most once
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

max_attempts_marker = "    max_attempts = FACT_REWRITE_MAX_ATTEMPTS if fact_guard_enabled else 1\n"
max_attempts_replacement = "    max_attempts = FACT_REWRITE_MAX_ATTEMPTS if fact_guard_enabled else 2\n"
if max_attempts_replacement not in rewrite_source:
    if rewrite_source.count(max_attempts_marker) != 1:
        raise RuntimeError("rewrite_engine.py max_attempts marker mismatch")
    rewrite_source = rewrite_source.replace(max_attempts_marker, max_attempts_replacement, 1)

rewrite_call_marker = '''        rewritten = _run_rewrite_call(\n            script_data,\n            consensus,\n            domains,\n            model=model,\n            retry_fact_issues=retry_fact_issues,\n        )\n\n        if not fact_guard_enabled:\n            break\n'''
rewrite_call_replacement = '''        rewritten = _run_rewrite_call(\n            script_data,\n            consensus,\n            domains,\n            model=model,\n            retry_fact_issues=retry_fact_issues,\n        )\n\n        speech_valid, speech_reason = validate_script_speech_style(rewritten)\n        if not speech_valid:\n            print(f"🚫 Rewrite speech-style 검사 실패: {speech_reason}")\n            if attempt < max_attempts:\n                print("➡️ 동일 Rewrite를 격식체 조건으로 제한 재시도합니다.")\n                continue\n\n            print(\n                "⚠️ Rewrite speech-style 재시도 한도 초과. "\n                "비격식/해요체 Rewrite 결과를 사용하지 않고 원본 Script로 복귀합니다."\n            )\n            rewritten = copy.deepcopy(script_data)\n            break\n\n        if not fact_guard_enabled:\n            break\n'''
if rewrite_call_replacement not in rewrite_source:
    if rewrite_source.count(rewrite_call_marker) != 1:
        raise RuntimeError("rewrite_engine.py speech-style retry marker mismatch")
    rewrite_source = rewrite_source.replace(rewrite_call_marker, rewrite_call_replacement, 1)

rewrite_path.write_text(rewrite_source, encoding="utf-8")

# #97 extends the mandatory speech path with the observation-question-delayed-
# reveal narrative contract. Chaining it here guarantees every production/CI
# path that already applies ci_speech_style_hotfix.py also applies #97.
runpy.run_path("ci_narrative_reveal_contract_hotfix.py", run_name="__main__")

print("✅ Korean formal speech-style + narrative reveal hotfix applied")

from pathlib import Path

# Post-Writer safety net retained from #287.
PATH = Path("content/script_generator.py")
text = PATH.read_text(encoding="utf-8")

marker = '''            generated = extract_json(
                content
            )
'''
insertion = '''
            # WRITER_OBSERVABLE_OPENING_V1
            # Production requires Scene 1 to be an observable statement. Keep
            # the Writer's grounded subject/visual fields intact and only
            # replace a question-form opening with the already locked,
            # candidate-owned observable hook when that hook is declarative.
            scenes = generated.get("scenes") if isinstance(generated, dict) else None
            if isinstance(scenes, list) and scenes and isinstance(scenes[0], dict):
                opening = str(scenes[0].get("text", "")).strip()
                locked_hook = str(micro.get("hook", "")).strip()
                question_form = bool(re.search(r"[?？]\\s*$", opening)) or bool(
                    re.search(r"(?:왜|어째서|어떻게|무엇|뭘|뭐가|무슨|어떤|일까|걸까|까요|나요|죠)\\s*[?？]?\\s*$", opening)
                )
                locked_question = bool(re.search(r"[?？]\\s*$", locked_hook)) or bool(
                    re.search(r"(?:왜|어째서|어떻게|무엇|뭘|뭐가|무슨|어떤|일까|걸까|까요|나요|죠)\\s*[?？]?\\s*$", locked_hook)
                )
                if question_form and locked_hook and not locked_question:
                    scenes[0]["text"] = locked_hook
                    print("[WRITER_OBSERVABLE_OPENING_V1] restored candidate-owned declarative hook")
'''

if "# WRITER_OBSERVABLE_OPENING_V1" in text:
    print("Writer Observable Opening V1 already installed")
elif marker not in text:
    raise RuntimeError("writer observable opening extraction marker mismatch")
else:
    text = text.replace(marker, marker + insertion, 1)
    PATH.write_text(text, encoding="utf-8")
    print("Writer Observable Opening V1 installed")


# Run 33954034420 fails earlier than Writer JSON generation: the grounded
# Script Engine V2 opening contract receives a factual/physical question-form
# hook such as "왜 비행기 창문은 둥글게 설계되었을까?". Production hotfix
# composition may preserve the base question-repair table or may replace the
# engine and later append _grounded_opening(). Support both final shapes.
ENGINE = Path("content/script_engine_v2.py")
engine = ENGINE.read_text(encoding="utf-8")
ENGINE_MARKER = "# PREWRITER_OBSERVABLE_OPENING_RUN_33954034420"
anchor = '''_QUESTION_HOOK_REPAIRS = (
    (r"있을까요$", "있습니다"),
'''
replacement = '''# PREWRITER_OBSERVABLE_OPENING_RUN_33954034420
_QUESTION_HOOK_REPAIRS = (
    (r"었을까$", "었습니다"),
    (r"았을까$", "았습니다"),
    (r"였을까$", "였습니다"),
    (r"있을까$", "있습니다"),
    (r"없을까$", "없습니다"),
    (r"일까$", "입니다"),
    (r"될까$", "됩니다"),
    (r"할까$", "합니다"),
    (r"있을까요$", "있습니다"),
'''

grounded_anchor = '''    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):
        hook = _question_hook_to_observation(hook, candidate.get("topic"))
        if not hook:
            raise ValueError("scene 1 hook must be an observable statement, not a question")
'''
grounded_replacement = '''    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):
        original_hook = hook
        hook = _question_hook_to_observation(hook, candidate.get("topic"))
        if not hook:
            value = re.sub(r"^(?:그런데\\s+)?왜\\s+", "", _text(original_hook)).rstrip().rstrip(".?!")
            repairs = (
                (r"었을까$", "었습니다"),
                (r"았을까$", "았습니다"),
                (r"였을까$", "였습니다"),
                (r"있을까$", "있습니다"),
                (r"없을까$", "없습니다"),
                (r"일까$", "입니다"),
                (r"될까$", "됩니다"),
                (r"할까$", "합니다"),
            )
            for pattern, ending in repairs:
                converted, count = re.subn(pattern, ending, value)
                if count:
                    hook = converted + "."
                    break
        if not hook:
            raise ValueError("scene 1 hook must be an observable statement, not a question")
'''

if ENGINE_MARKER in engine:
    print("Pre-Writer Observable Opening Run 33954034420 already installed")
elif anchor in engine:
    engine = engine.replace(anchor, replacement, 1)
    ENGINE.write_text(engine, encoding="utf-8")
    print("Pre-Writer Observable Opening Run 33954034420 installed via base repair table")
elif grounded_anchor in engine:
    engine = engine.replace(grounded_anchor, grounded_replacement, 1)
    engine += "\n# PREWRITER_OBSERVABLE_OPENING_RUN_33954034420\n"
    ENGINE.write_text(engine, encoding="utf-8")
    print("Pre-Writer Observable Opening Run 33954034420 installed via grounded final-composition fallback")
else:
    raise RuntimeError("pre-Writer observable opening final-composition marker mismatch")

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
# hook such as "왜 비행기 창문은 둥글게 설계되었을까?". Extend the existing
# deterministic repair table at the actual pre-Writer boundary. Production
# composition may reorder/extend the table before this installer runs, so use
# only the table declaration as the stable anchor instead of coupling to its
# first row.
ENGINE = Path("content/script_engine_v2.py")
engine = ENGINE.read_text(encoding="utf-8")
ENGINE_MARKER = "# PREWRITER_OBSERVABLE_OPENING_RUN_33954034420"
TABLE_ANCHOR = "_QUESTION_HOOK_REPAIRS = ("
rows = (
    '    (r"었을까$", "었습니다"),',
    '    (r"았을까$", "았습니다"),',
    '    (r"였을까$", "였습니다"),',
    '    (r"있을까$", "있습니다"),',
    '    (r"없을까$", "없습니다"),',
    '    (r"일까$", "입니다"),',
    '    (r"될까$", "됩니다"),',
    '    (r"할까$", "합니다"),',
)

if ENGINE_MARKER in engine and all(row in engine for row in rows):
    print("Pre-Writer Observable Opening Run 33954034420 already installed")
elif TABLE_ANCHOR not in engine:
    raise RuntimeError("pre-Writer observable opening repair table declaration missing")
else:
    missing = [row for row in rows if row not in engine]
    if missing:
        payload = (
            ENGINE_MARKER
            + "\n"
            + TABLE_ANCHOR
            + "\n"
            + "\n".join(missing)
        )
        engine = engine.replace(TABLE_ANCHOR, payload, 1)
        ENGINE.write_text(engine, encoding="utf-8")
    elif ENGINE_MARKER not in engine:
        engine = engine.replace(TABLE_ANCHOR, ENGINE_MARKER + "\n" + TABLE_ANCHOR, 1)
        ENGINE.write_text(engine, encoding="utf-8")
    print("Pre-Writer Observable Opening Run 33954034420 installed")

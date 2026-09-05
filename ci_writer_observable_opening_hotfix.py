from pathlib import Path

PATH = Path("content/script_generator.py")
text = PATH.read_text(encoding="utf-8")

marker = '''            generated = extract_json(
                content
            )

            valid, reason = validate_script(
                generated
            )
'''
replacement = '''            generated = extract_json(
                content
            )

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

            valid, reason = validate_script(
                generated
            )
'''

if marker not in text:
    raise RuntimeError("writer observable opening marker mismatch")

text = text.replace(marker, replacement, 1)
PATH.write_text(text, encoding="utf-8")
print("Writer Observable Opening V1 installed")

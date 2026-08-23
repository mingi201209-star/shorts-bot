from pathlib import Path

path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")
marker = "SCRIPT_LOCAL_FORMAL_REPAIR_V1"

if marker not in text:
    import_anchor = "import re\n\nimport openai\n"
    import_replacement = "import re\n\nimport openai\n\nfrom quality.korean_speech_style import validate_korean_speech_text\n"
    if "from quality.korean_speech_style import validate_korean_speech_text" not in text:
        if text.count(import_anchor) != 1:
            raise RuntimeError("script local formal repair import anchor mismatch")
        text = text.replace(import_anchor, import_replacement, 1)

    anchor = "# ============================================================\n# Scene Validation\n# ============================================================\n"
    addition = r'''# SCRIPT_LOCAL_FORMAL_REPAIR_V1
# Repair only unambiguous declarative 하다-style endings. This is deliberately
# narrow: no facts, wording, scene order, questions, or visual fields change.
_SAFE_FORMAL_ENDING_REPAIRS = (
    (re.compile(r"한다(?=[.!?…]*$)"), "합니다"),
    (re.compile(r"된다(?=[.!?…]*$)"), "됩니다"),
    (re.compile(r"이다(?=[.!?…]*$)"), "입니다"),
    (re.compile(r"있다(?=[.!?…]*$)"), "있습니다"),
    (re.compile(r"없다(?=[.!?…]*$)"), "없습니다"),
    (re.compile(r"줄인다(?=[.!?…]*$)"), "줄입니다"),
    (re.compile(r"높인다(?=[.!?…]*$)"), "높입니다"),
    (re.compile(r"낮춘다(?=[.!?…]*$)"), "낮춥니다"),
    (re.compile(r"감소한다(?=[.!?…]*$)"), "감소합니다"),
    (re.compile(r"증가한다(?=[.!?…]*$)"), "증가합니다"),
)


def repair_scene_formal_endings(scenes):
    if not isinstance(scenes, list):
        return scenes, []

    repaired = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        original = str(scene.get("text", ""))
        if not original.strip():
            continue

        valid, _ = validate_korean_speech_text(original, allow_nominal=False)
        if valid:
            continue

        candidate = original
        for pattern, replacement in _SAFE_FORMAL_ENDING_REPAIRS:
            candidate = pattern.sub(replacement, candidate)

        if candidate == original:
            continue

        valid, _ = validate_korean_speech_text(candidate, allow_nominal=False)
        if not valid:
            continue

        scene["text"] = candidate
        repaired.append({
            "scene": index + 1,
            "before": original,
            "after": candidate,
        })

    return scenes, repaired


'''
    if text.count(anchor) != 1:
        raise RuntimeError("script local formal repair validation anchor mismatch")
    text = text.replace(anchor, addition + anchor, 1)

    validate_anchor = '''    scenes = result.get(\n        "scenes",\n        [],\n    )\n\n    valid, reason = validate_scenes(\n'''
    validate_replacement = '''    scenes = result.get(\n        "scenes",\n        [],\n    )\n\n    scenes, formal_repairs = repair_scene_formal_endings(scenes)\n    if formal_repairs:\n        result["scenes"] = scenes\n        print(f"🩹 Script local formal repair: {len(formal_repairs)} scene(s)")\n        for repair in formal_repairs:\n            print(\n                f"   Scene {repair['scene']}: "\n                f"{repair['before']} -> {repair['after']}"\n            )\n\n    valid, reason = validate_scenes(\n'''
    if text.count(validate_anchor) != 1:
        raise RuntimeError("script local formal repair validate_script anchor mismatch")
    text = text.replace(validate_anchor, validate_replacement, 1)

path.write_text(text, encoding="utf-8")
print("✅ Script local formal-ending repair hotfix applied")

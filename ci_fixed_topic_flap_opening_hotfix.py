from pathlib import Path

PATH = Path("content/script_engine_v2.py")
text = PATH.read_text(encoding="utf-8")
MARKER = "# FIXED_TOPIC_FLAP_OBSERVABLE_OPENING_V1"
if MARKER in text:
    print("Fixed Topic Flap Observable Opening V1 already installed")
else:
    anchor = '''def _question_hook_to_observation(text: Any, topic: Any = "") -> str:\n    """Convert only known Korean question endings; unsupported forms still fail closed."""\n'''
    replacement = anchor + '''    # FIXED_TOPIC_FLAP_OBSERVABLE_OPENING_V1\n    fixed_topic = _text(topic).rstrip().rstrip(".?!")\n    if fixed_topic == "비행기는 착륙할 때 왜 날개 뒤쪽을 펼칠까":\n        return "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다."\n'''
    if anchor not in text:
        raise RuntimeError("fixed-topic flap opening function marker mismatch")
    text = text.replace(anchor, replacement, 1)
    PATH.write_text(text, encoding="utf-8")
    print("Fixed Topic Flap Observable Opening V1 installed")

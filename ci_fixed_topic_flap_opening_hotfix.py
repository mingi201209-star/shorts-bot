"""Production composition hotfix for the landing-flap fixed-topic opening.

Run 33967122592 proved grounding and four claims were live, then failed before
Writer because the fixed topic itself was a why-question. This adds one
repo-owned, evidence-neutral observable projection for that exact fixed topic.
It changes no quality threshold and does not answer the question in Scene 1.
"""
from pathlib import Path

PATH = Path("content/script_engine_v2.py")
text = PATH.read_text(encoding="utf-8")
MARKER = "# FIXED_TOPIC_FLAP_OBSERVABLE_OPENING_V1"

if MARKER in text:
    print("Fixed Topic Flap Observable Opening V1 already installed")
else:
    anchor = '''def _question_hook_to_observation(hook: str, topic: str | None = None) -> str:
'''
    if anchor not in text:
        raise RuntimeError("fixed-topic flap opening function marker mismatch")
    insertion = '''# FIXED_TOPIC_FLAP_OBSERVABLE_OPENING_V1
_FIXED_TOPIC_OBSERVABLE_OPENINGS = {
    "비행기는 착륙할 때 왜 날개 뒤쪽을 펼칠까?": "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다.",
    "비행기는 착륙할 때 왜 날개 뒤쪽을 펼칠까": "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다.",
}

'''
    text = text.replace(anchor, insertion + anchor, 1)

    body_anchor = '''def _question_hook_to_observation(hook: str, topic: str | None = None) -> str:
'''
    body_replacement = body_anchor + '''    fixed = _FIXED_TOPIC_OBSERVABLE_OPENINGS.get(_text(topic))
    if fixed:
        return fixed
'''
    text = text.replace(body_anchor, body_replacement, 1)
    PATH.write_text(text, encoding="utf-8")
    print("Fixed Topic Flap Observable Opening V1 installed")

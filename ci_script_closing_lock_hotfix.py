from pathlib import Path


path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

marker = "SCRIPT_CLOSING_LOCK_V1"
if marker not in text:
    anchor = '''            generated = _script_opening_lock_apply(
                generated,
                candidate,
            )

            valid, reason = validate_script(
                generated
            )
'''
    replacement = '''            generated = _script_opening_lock_apply(
                generated,
                candidate,
            )
            generated = _script_closing_lock_apply(
                generated,
                candidate,
            )

            valid, reason = validate_script(
                generated
            )
'''
    if text.count(anchor) != 1:
        raise RuntimeError(
            f"script closing lock validation marker mismatch: {text.count(anchor)}"
        )
    text = text.replace(anchor, replacement, 1)

    text += r'''

# SCRIPT_CLOSING_LOCK_V1
# The Candidate Explorer has already approved reveal/payoff. Keep the LLM's
# visual metadata, but deterministically restore those two final narrative beats
# before all existing validators run. This mirrors SCRIPT_OPENING_LOCK_V1 and
# closes the same contract at the other end without weakening any validator.
def _script_closing_lock_apply(payload, candidate):
    if not isinstance(payload, dict) or not isinstance(candidate, dict):
        return payload

    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 4:
        return payload

    micro = candidate.get("micro_narrative")
    if not isinstance(micro, dict):
        return payload

    locked_reveal = str(micro.get("reveal", "")).strip()
    locked_payoff = str(micro.get("payoff", "")).strip()

    # Final section is the last two narrative beats. Preserve the LLM-selected
    # visual_goal/keyword/retention metadata and only lock narration text.
    if isinstance(scenes[-2], dict) and locked_reveal:
        scenes[-2]["text"] = locked_reveal
    if isinstance(scenes[-1], dict) and locked_payoff:
        scenes[-1]["text"] = locked_payoff

    return payload
'''

path.write_text(text, encoding="utf-8")
print("✅ Approved reveal/payoff closing lock applied before Script validation")

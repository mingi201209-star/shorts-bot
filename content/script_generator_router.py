"""Stable Script Generator router.

Production stays on legacy unless SCRIPT_ENGINE_MODE=v2 is explicitly enabled.
This makes the eventual cutover a configuration change instead of another hotfix.
"""
import os


def generate_script(topic_info, candidate):
    mode = os.environ.get("SCRIPT_ENGINE_MODE", "legacy").strip().lower()
    if mode == "v2":
        from content.script_engine_v2_runner import generate_script_v2
        return generate_script_v2(candidate)

    if mode not in ("", "legacy", "v1"):
        raise ValueError(f"Unsupported SCRIPT_ENGINE_MODE: {mode}")

    from content.script_generator import generate_script as legacy_generate_script
    return legacy_generate_script(topic_info, candidate)

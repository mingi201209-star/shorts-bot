from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


LEGACY_PATH = Path(__file__).with_name("ci_topic_input_hotfix_legacy.py")
spec = spec_from_file_location("_topic_input_hotfix_legacy", LEGACY_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("failed to load topic input hotfix implementation")
legacy = module_from_spec(spec)
spec.loader.exec_module(legacy)

_original_replace_once = legacy.replace_once


def _compatible_replace_once(text, marker, replacement, label):
    if label != "main fixed topic novelty lock":
        return _original_replace_once(text, marker, replacement, label)

    if replacement in text or "🔒 FIXED TOPIC NOVELTY LOCK" in text:
        return text

    count = text.count(marker)
    if count == 1:
        return text.replace(marker, replacement, 1)

    # Earlier production hotfixes can rewrite comments surrounding Candidate
    # Regeneration while leaving the actual status branch intact. Anchor only to
    # that executable branch so late application remains safe and deterministic.
    stable_branch = '''            if (
                status
                == "REGENERATE_TOPIC"
            ):
'''
    stable_count = text.count(stable_branch)
    if stable_count != 1:
        raise RuntimeError(
            "main fixed topic novelty lock stable branch count mismatch: "
            f"{stable_count}"
        )

    replacement_pos = replacement.rfind(stable_branch)
    if replacement_pos < 0:
        raise RuntimeError("fixed topic novelty replacement lost stable branch")

    lock_prefix = replacement[:replacement_pos]
    patched = text.replace(stable_branch, lock_prefix + stable_branch, 1)
    print("🧩 fixed-topic Novelty lock applied through stable REGENERATE_TOPIC compatibility anchor")
    return patched


legacy.replace_once = _compatible_replace_once


def main():
    legacy.main()


if __name__ == "__main__":
    main()

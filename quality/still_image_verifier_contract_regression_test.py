import ast
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_still_image_verifier_contract_hotfix as hotfix


def _load_normalizer(source):
    tree = ast.parse(source)
    body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "normalize_dominance_result":
            body.append(node)
    namespace = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), "<normalizer>", "exec"), namespace)
    return namespace["normalize_dominance_result"]


def main():
    hook_source = (ROOT / "video/hook_visual_dominance.py").read_text(encoding="utf-8")
    still_source = (ROOT / "video/still_image_fallback.py").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        hook_path = tmp / "hook_visual_dominance.py"
        still_path = tmp / "still_image_fallback.py"
        hook_path.write_text(hook_source, encoding="utf-8")
        still_path.write_text(still_source, encoding="utf-8")

        original_path = Path
        original_hook = hotfix.Path

        class RedirectPath:
            def __new__(cls, value):
                if value == "video/hook_visual_dominance.py":
                    return hook_path
                if value == "video/still_image_fallback.py":
                    return still_path
                return original_path(value)

        hotfix.Path = RedirectPath
        try:
            hotfix.main()
            hotfix.main()
        finally:
            hotfix.Path = original_hook

        patched_hook = hook_path.read_text(encoding="utf-8")
        patched_still = still_path.read_text(encoding="utf-8")
        assert patched_hook.count(hotfix.MARKER) == 1
        # The still fallback intentionally carries the same contract marker at
        # both patched boundaries: generation prompt + verifier gate. Calling
        # the hotfix twice must keep exactly those two markers (idempotent).
        assert patched_still.count(hotfix.MARKER) == 2
        assert 'if not result.get("pass", False):' in patched_still
        assert '"visible_components"' in patched_hook
        assert '"factual_visual_contradiction"' in patched_hook

        # Production counterexample: narration/visual goal can be broader than
        # the keyword contract ("aircraft and runway contact" vs aircraft+wing).
        # Generation must explicitly preserve every concrete search component
        # because verification is intentionally fail-closed on those anchors.
        assert "Every concrete physical component named in the Search concept" in patched_still
        assert "aircraft+wing search concept must visibly show both the aircraft and its wing" in patched_still

        normalize = _load_normalizer(patched_hook)
        accepted = normalize({
            "target_subject": "passenger aircraft wing",
            "subject_dominance": 9,
            "action_match": 10,
            "competing_subject_risk": 1,
            "vertical_crop_subject_visible": True,
            "visible_components": ["aircraft", "wing"],
            "obvious_generation_artifact": False,
            "factual_visual_contradiction": False,
        }, action_required=False)
        assert accepted["subject_visibility"] == 9
        assert accepted["visible_components"] == ["aircraft", "wing"]
        assert accepted["obvious_generation_artifact"] is False
        assert accepted["factual_visual_contradiction"] is False

        incomplete = normalize({
            "target_subject": "aircraft",
            "subject_dominance": 9,
            "action_match": 10,
            "competing_subject_risk": 1,
            "vertical_crop_subject_visible": True,
            "visible_components": ["aircraft"],
        }, action_required=False)
        assert "wing" not in incomplete["visible_components"]

    print("STILL IMAGE VERIFIER CONTRACT REGRESSION: PASS")


if __name__ == "__main__":
    main()

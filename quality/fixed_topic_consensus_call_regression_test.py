import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_script_v2_visual_goal_hotfix as hotfix
from ci_fixed_topic_gate_advisory_hotfix import apply_fixed_topic_hook_quality_guard


def _judge(score):
    return {
        "score": float(score),
        "confidence": 0.9,
        "critical_risk": False,
        "issues": [],
    }


def main():
    source = (ROOT / "quality" / "consensus.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "consensus.py"
        # Production order: ci_topic_input_hotfix installs the fixed-topic Hook
        # quality guard before ci_script_v2_visual_goal_hotfix softens the
        # non-fact fixed-topic Judge decision set.
        target.write_text(
            apply_fixed_topic_hook_quality_guard(source), encoding="utf-8"
        )
        original_path = hotfix.CONSENSUS_PATH
        try:
            hotfix.CONSENSUS_PATH = target
            hotfix._apply_fixed_topic_soft_judges()
        finally:
            hotfix.CONSENSUS_PATH = original_path

        patched = target.read_text(encoding="utf-8")
        assert "def meets_good_enough_floors(summaries):" in patched
        assert (
            "and meets_good_enough_floors(decision_summaries):"
            in patched
        )
        assert "FIXED_TOPIC_HOOK_QUALITY_GUARD_V1" in patched
        namespace = {}
        exec(compile(patched, "<consensus>", "exec"), namespace)

        previous_topic = os.environ.get("SHORTS_TOPIC")
        os.environ["SHORTS_TOPIC"] = "비행기 창문 모서리는 왜 둥글까"
        try:
            # Run 34616204901 had Hook 6.0 and Fact 8.0.  A fixed topic may keep
            # Novelty/Visual advisory, but this opening must not be production PASS.
            weak_hook = namespace["build_consensus"]({
                "hook": [_judge(6.0)],
                "fact": [_judge(8.0)],
            })
            assert weak_hook["decision"] == "REWRITE", weak_hook
            assert weak_hook["pass_tier"] is None, weak_hook
            hook_weak = [
                item for item in weak_hook["weak_domains"]
                if item.get("judge_type") == "hook"
            ]
            assert hook_weak and hook_weak[0]["minimum"] == 7.0, weak_hook

            # Do not raise or lower any threshold: satisfying the repository's
            # existing Hook Good-Enough floor still permits the fixed topic.
            good_hook = namespace["build_consensus"]({
                "hook": [_judge(7.2)],
                "fact": [_judge(8.0)],
            })
            assert good_hook["decision"] == "PASS", good_hook
            assert good_hook["domain_summaries"]["fact"]["score"] == 8.0
            assert good_hook["domain_summaries"]["hook"]["score"] == 7.2
        finally:
            if previous_topic is None:
                os.environ.pop("SHORTS_TOPIC", None)
            else:
                os.environ["SHORTS_TOPIC"] = previous_topic

    print("FIXED TOPIC CONSENSUS CALL TARGET REGRESSION: PASS")


if __name__ == "__main__":
    main()

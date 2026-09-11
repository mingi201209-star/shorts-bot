import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_script_v2_visual_goal_hotfix as soft_hotfix
import ci_fixed_topic_gate_advisory_hotfix as fixed_hotfix


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
        target.write_text(source, encoding="utf-8")

        # Reproduce the real production composition path: ci_topic_input_hotfix
        # imports apply_fixed_topic_gate_advisory() and calls it with the full
        # main.py.  The full-main call must install the Hook wrapper into the
        # composed consensus before Script-V2 later makes Novelty/Visual advisory.
        old_fixed_path = fixed_hotfix.CONSENSUS_PATH
        old_soft_path = soft_hotfix.CONSENSUS_PATH
        try:
            fixed_hotfix.CONSENSUS_PATH = target
            soft_hotfix.CONSENSUS_PATH = target
            production_main_fixture = (
                "def run_quality_process():\n    pass\n\n"
                + fixed_hotfix.MARKER
                + "\n"
            )
            fixed_hotfix.apply_fixed_topic_gate_advisory(production_main_fixture)
            soft_hotfix._apply_fixed_topic_soft_judges()
        finally:
            fixed_hotfix.CONSENSUS_PATH = old_fixed_path
            soft_hotfix.CONSENSUS_PATH = old_soft_path

        patched = target.read_text(encoding="utf-8")
        assert "FIXED_TOPIC_HOOK_QUALITY_GUARD_V1" in patched
        assert "and meets_good_enough_floors(decision_summaries):" in patched

        namespace = {}
        exec(compile(patched, "<consensus>", "exec"), namespace)

        previous_topic = os.environ.get("SHORTS_TOPIC")
        os.environ["SHORTS_TOPIC"] = "비행기 창문 모서리는 왜 둥글까"
        try:
            # Production Run 34625637738 had Hook 6.0 + Fact 8.0 and wrongly
            # passed.  The existing 7.0 Good-Enough floor must now force rewrite.
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

            # No threshold change: a Hook above the existing floor still passes.
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

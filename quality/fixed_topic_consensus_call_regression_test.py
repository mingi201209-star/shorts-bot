import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ci_script_v2_visual_goal_hotfix as hotfix


def main():
    source = (ROOT / "quality" / "consensus.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "consensus.py"
        target.write_text(source, encoding="utf-8")
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
        namespace = {}
        exec(compile(patched, "<consensus>", "exec"), namespace)
        previous_topic = os.environ.get("SHORTS_TOPIC")
        os.environ["SHORTS_TOPIC"] = "비행기 날개는 비행 중 일부러 휘어지게 만든다"
        try:
            result = namespace["build_consensus"]({
                "fact": [{
                    "score": 8.0,
                    "confidence": 0.9,
                    "critical_risk": False,
                    "issues": [],
                }],
            })
        finally:
            if previous_topic is None:
                os.environ.pop("SHORTS_TOPIC", None)
            else:
                os.environ["SHORTS_TOPIC"] = previous_topic
        assert result["decision"] == "PASS"
        assert result["domain_summaries"]["fact"]["score"] == 8.0

    print("FIXED TOPIC CONSENSUS CALL TARGET REGRESSION: PASS")


if __name__ == "__main__":
    main()

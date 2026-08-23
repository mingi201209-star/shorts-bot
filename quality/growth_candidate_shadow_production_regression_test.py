import json
from pathlib import Path
import subprocess
import sys
import tempfile

from analytics.feedback_contract import make_video_lineage
from content.growth_candidate_ranker import load_growth_history

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert load_growth_history(path="missing-growth-history.json") == []

    record = make_video_lineage(
        "history-1",
        candidate={"topic": "비행기 창문 작은 구멍"},
        snapshots={"24h": {"state": "complete", "views": 500, "subscriber_gain": 2}},
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "history.json"
        path.write_text(json.dumps({"records": [record]}, ensure_ascii=False), encoding="utf-8")
        loaded = load_growth_history(str(path))
        assert len(loaded) == 1
        assert loaded[0]["lineage_id"] == "history-1"

    main_path = ROOT / "main.py"
    before = main_path.read_text(encoding="utf-8")
    subprocess.run([sys.executable, "ci_growth_candidate_shadow_hotfix.py"], cwd=ROOT, check=True)
    after = main_path.read_text(encoding="utf-8")

    assert "GROWTH_CANDIDATE_SHADOW_V1" in after
    assert "Growth Shadow (non-authoritative)" in after
    assert "annotate_explorer_output" in after
    assert "load_growth_history" in after
    assert after.count("explore_candidates(") == before.count("explore_candidates(")
    assert after.count("evaluate_candidate(") == before.count("evaluate_candidate(")
    assert "winner = (" in after and "explorer_result[" in after

    print("PASS: growth shadow is attached to production path without changing selection/gate call counts")


if __name__ == "__main__":
    main()

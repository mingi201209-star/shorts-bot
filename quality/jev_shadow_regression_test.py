import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import types

os.environ["JEV_SHADOW_ENABLED"] = "1"
os.environ["JEV_API_KEY"] = "test-key"

import quality.jev_shadow as js


def main():
    with tempfile.TemporaryDirectory() as td:
        js.JEV_SHADOW_LOG = Path(td) / "jev.jsonl"
        fake = Mock()
        fake.raise_for_status.return_value = None
        fake.json.return_value = {"answers": {"route": {"choice": "REWRITE"}}}
        candidate = {"topic": "비행기 창문", "core_question": "왜 모서리가 둥글까?", "reveal": "응력 집중을 줄이기 위해서다."}
        fake_requests = types.SimpleNamespace(post=Mock(return_value=fake))
        with patch.dict(sys.modules, {"requests": fake_requests}):
            result = js.evaluate_candidate_shadow(candidate, "PASS", "existing gate stays authoritative")
        assert result["status"] == "OK"
        payload = fake_requests.post.call_args.kwargs["json"]
        second = js.evaluate_candidate_shadow(candidate, "PASS", "second observation")
        assert second["status"] == "SKIPPED"
        assert second["reason"] == "JEV_SHADOW_MAX_CALLS reached"
        assert fake_requests.post.call_count == 1
        assert set(payload["questions"]) == {"route", "specificity", "grounded"}
        assert payload["state"]["existing_gate"]["verdict"] == "PASS"
        row = json.loads(js.JEV_SHADOW_LOG.read_text(encoding="utf-8").strip())
        assert row["existing_verdict"] == "PASS"
    print("Jev shadow regression: PASS")


if __name__ == "__main__":
    main()

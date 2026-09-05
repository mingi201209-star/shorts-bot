"""Regression for Run 33967122592 fixed-topic question opening."""
import subprocess
import sys
from pathlib import Path

subprocess.run([sys.executable, "ci_fixed_topic_flap_opening_hotfix.py"], check=True)
from content.script_engine_v2 import _question_hook_to_observation

topic = "비행기는 착륙할 때 왜 날개 뒤쪽을 펼칠까?"
assert _question_hook_to_observation(topic, topic) == "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다."
assert _question_hook_to_observation("왜 비행기는 착륙할 때 날개 뒤쪽을 펼칠까?", topic) == "비행기는 착륙할 때 날개 뒤쪽 플랩을 펼칩니다."
source = Path("content/script_engine_v2.py").read_text(encoding="utf-8")
assert "FIXED_TOPIC_FLAP_OBSERVABLE_OPENING_V1" in source
print("RUN_33967122592_FLAP_OPENING_REGRESSION=PASS")

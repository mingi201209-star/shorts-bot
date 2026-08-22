import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content import topic_selector


# Aviation scope must never fall back to the general science/traffic/history RNG pool.
with patch.dict(os.environ, {"SHORTS_CANDIDATE_SCOPE": "aviation"}, clear=False):
    with patch("content.topic_selector.random.choice", side_effect=lambda items: items[0]):
        selected = topic_selector.choose_topic_direction()

assert selected["category"] == "항공", selected
assert selected["topic"] in topic_selector.AVIATION_TOPIC_POOL, selected
assert selected not in topic_selector.ALL_TOPICS, selected
assert len(topic_selector.AVIATION_TOPIC_POOL) >= 8

# Scope directions are broad aviation curiosity spaces, not fixed topic answers.
required_spaces = (
    "객실",
    "날개",
    "엔진",
    "착륙장치",
    "압력",
    "안전장치",
    "공항",
    "이륙",
)
joined = "\n".join(topic_selector.AVIATION_TOPIC_POOL)
for token in required_spaces:
    assert token in joined, token

# Default behavior remains the existing general pool when aviation is not requested.
with patch.dict(os.environ, {}, clear=True):
    with patch("content.topic_selector.random.choice", side_effect=lambda items: items[0]):
        general = topic_selector.choose_topic_direction()

assert general in topic_selector.ALL_TOPICS, general
assert general["category"] != "항공", general

print("PASS: aviation scope stays inside aviation exploration space; default RNG preserved")

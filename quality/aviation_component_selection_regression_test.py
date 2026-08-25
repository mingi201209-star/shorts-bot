"""Regression for production Run 32796378299 partial aircraft-component selection."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality import general_scene_visual_parity_regression_test as base

vd = base.vd

# The candidate is in the aircraft domain but does not evidence the required wing.
base.reset()
query = "aircraft wing airflow stage 8"
partial = base.c(9001, "aircraft drone beach flight technology", 1)
assert vd.candidate_anchor_compatibility(partial, query)["matched"] == 1
assert vd.candidate_anchor_compatibility(partial, query)["total"] == 2
assert vd.general_scene_unknown_safe_tier(partial, query)[0] == 4
assert vd.choose_best_candidate([partial], subject_filter_query=query) is None

# A complete aircraft+wing candidate remains selectable; the gate is component-specific,
# not a blanket rejection of UNKNOWN stock.
base.reset()
complete = base.c(9002, "aircraft wing airflow closeup", 1)
selected = vd.choose_best_candidate([complete], subject_filter_query=query)
assert selected is not None and selected["id"] == 9002

print("PASS: partial aviation component stock rejected before render; complete anchor match preserved")

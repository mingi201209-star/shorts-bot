from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ci_static_wick_fallback_provenance_hotfix import PATCH


CURRENT_CONTRACT = {}
SENTINEL = {"provider": "pixabay", "source_id": "contextual-airplane"}


def normalize_search_query(value):
    return " ".join(str(value or "").lower().replace("-", " ").split())


def get_current_visual_subject_anchor_contract():
    return dict(CURRENT_CONTRACT)


def previous_choose(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    return SENTINEL if candidates else None


namespace = {
    "choose_best_candidate": previous_choose,
    "normalize_search_query": normalize_search_query,
    "get_current_visual_subject_anchor_contract": get_current_visual_subject_anchor_contract,
}
exec(PATCH, namespace)
choose_best_candidate = namespace["choose_best_candidate"]


# Run 34342636322 exact failure shape: the trusted static-wick authority is
# still active, but the specificity ladder has broadened the selector query to
# generic aircraft footage. Contextual stock must not escape back into render.
CURRENT_CONTRACT.clear()
CURRENT_CONTRACT.update(
    {
        "required": True,
        "original_query": "aircraft static charge dissipation",
        "effective_query": "aircraft static charge dissipation",
    }
)
assert choose_best_candidate([SENTINEL], subject_filter_query="airplane detail") is None
assert choose_best_candidate([SENTINEL], subject_filter_query="airplane") is None

CURRENT_CONTRACT.update(
    {
        "required": True,
        "original_query": "aircraft static radio interference reduction",
        "effective_query": "aircraft static radio interference reduction",
    }
)
assert choose_best_candidate([SENTINEL], subject_filter_query="aircraft wing detail") is None

# Historical selection is deliberately outside this new provenance gate.
assert (
    choose_best_candidate(
        [SENTINEL], historical=True, subject_filter_query="airplane detail"
    )
    is SENTINEL
)

# Unrelated aviation explanatory/identity scenes keep the exact previous
# selector behavior; no broad anti-stock rule is introduced.
CURRENT_CONTRACT.update(
    {
        "required": True,
        "original_query": "aircraft rounded window pressure distribution",
        "effective_query": "aircraft rounded window pressure distribution",
    }
)
assert choose_best_candidate([SENTINEL], subject_filter_query="airplane window detail") is SENTINEL

CURRENT_CONTRACT.clear()
assert choose_best_candidate([SENTINEL], subject_filter_query="airplane detail") is SENTINEL

# No quality, retry, API, cost, still-generation, or Director escape hatch.
for forbidden in (
    "V3_MAX_API_CALLS =",
    "V3_MAX_COST_USD =",
    "MAX_TOPIC_REGENERATIONS =",
    "MAX_EXPLANATION_TRANSFORMS_PER_VIDEO =",
    "DIRECTOR_THRESHOLD =",
    "explanatory_power_min =",
    "still_generation_budget =",
):
    assert forbidden not in PATCH, forbidden

print("STATIC_WICK_FALLBACK_PROVENANCE_REGRESSION_PASS")

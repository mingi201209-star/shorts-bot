from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOWNLOADER_PATH = ROOT / "video/video_downloader.py"
MARKER = "STATIC_WICK_FALLBACK_PROVENANCE_V1"


PATCH = r'''

# STATIC_WICK_FALLBACK_PROVENANCE_V1
# Run 34342636322: the exact static-wick query correctly fail-closed generic
# stock, but the later specificity/contextual ladder broadened the query and
# reintroduced generic aircraft footage. Preserve the original trusted visual
# authority through the entire selector chain so deterministic explanation can
# run. Run 34347759937 proved that explanatory static-wick claims without a
# concrete subject still retain their original/effective authority in the
# subject-anchor contract even when `required=False`; that authority must remain
# usable here. No threshold, provider, model call, retry, or budget is changed.
_STATIC_WICK_FALLBACK_PROVENANCE_PREVIOUS_CHOOSE = choose_best_candidate


def _static_wick_contract_authority():
    try:
        contract = get_current_visual_subject_anchor_contract()
    except Exception:
        return ""
    if not isinstance(contract, dict):
        return ""
    return normalize_search_query(
        contract.get("effective_query") or contract.get("original_query") or ""
    )


def _static_wick_trusted_authority(value):
    query = normalize_search_query(value)
    return any(
        phrase in query
        for phrase in (
            "static charge dissipation",
            "static wick location",
            "static radio interference reduction",
            "radio interference reduction",
        )
    )


def choose_best_candidate(candidates, relevant_top_n=None, *, historical=False, subject_filter_query=None):
    selected = _STATIC_WICK_FALLBACK_PROVENANCE_PREVIOUS_CHOOSE(
        candidates,
        relevant_top_n=relevant_top_n,
        historical=historical,
        subject_filter_query=subject_filter_query,
    )

    # Historical selection and unrelated scenes preserve existing behavior.
    if historical:
        return selected

    authority = _static_wick_contract_authority()
    if not _static_wick_trusted_authority(authority):
        return selected

    # The original trusted explanatory scene already failed closed against
    # generic stock in STATIC_WICK_VISUAL_EXPLANATION_V1. A broadened fallback
    # query must not erase that decision by returning contextual aircraft stock.
    # `required=False` means there is no concrete physical subject anchor; it
    # does not erase the trusted explanatory claim/query provenance.
    if selected is not None:
        print(
            "[STATIC_WICK_FALLBACK_PROVENANCE] "
            f"authority={authority} "
            f"fallback_query={normalize_search_query(subject_filter_query or '')} "
            f"candidate={selected.get('source_id', selected.get('id'))} status=reject_contextual_escape"
        )
        return None
    return None
'''


def main():
    text = DOWNLOADER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("Static-wick fallback provenance already installed")
        return
    required = (
        "STATIC_WICK_VISUAL_EXPLANATION_V1",
        "GENERAL_SCENE_VISUAL_PARITY_UNKNOWN_SAFE",
        "def get_current_visual_subject_anchor_contract(",
        "def choose_best_candidate(",
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise RuntimeError(f"static-wick fallback provenance prerequisites missing: {missing}")
    DOWNLOADER_PATH.write_text(text.rstrip() + PATCH + "\n", encoding="utf-8")
    print("✅ Static-wick fallback provenance installed; contextual stock escape blocked")


if __name__ == "__main__":
    main()

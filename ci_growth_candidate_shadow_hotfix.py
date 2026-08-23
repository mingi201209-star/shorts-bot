from pathlib import Path


MAIN_PATH = Path("main.py")


def replace_once(text, marker, replacement, label):
    if replacement in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label} marker count mismatch: {count}")
    return text.replace(marker, replacement, 1)


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")

    import_marker = '''from content.candidate_gate import (
    evaluate_candidate,
)
'''
    import_replacement = '''from content.candidate_gate import (
    evaluate_candidate,
)

from content.growth_candidate_ranker import (
    annotate_explorer_output,
    load_growth_history,
)
'''
    text = replace_once(text, import_marker, import_replacement, "growth shadow import")

    call_marker = '''            explorer_status = (
                explorer_result.get(
                    "status"
                )
            )
'''
    call_replacement = '''            # GROWTH_CANDIDATE_SHADOW_V1
            # Observational only: attach a copied shadow score beside the
            # authoritative Candidate Explorer result. Winner/runner-up order
            # and all existing gates remain unchanged.
            growth_history = load_growth_history()
            explorer_result = annotate_explorer_output(
                explorer_result,
                history=growth_history,
            )

            growth_shadow = explorer_result.get("growth_shadow", {})
            if growth_shadow.get("candidates"):
                print("")
                print("📈 Growth Shadow (non-authoritative):")
                for growth_role, growth_score in growth_shadow["candidates"].items():
                    print(
                        f"   {growth_role}: total={growth_score.get('total')} "
                        f"axes={growth_score.get('axes')} "
                        f"dup_penalty={growth_score.get('duplication_penalty')} "
                        f"evidence={growth_score.get('evidence_state')}"
                    )

            explorer_status = (
                explorer_result.get(
                    "status"
                )
            )
'''
    text = replace_once(text, call_marker, call_replacement, "growth shadow execution")

    MAIN_PATH.write_text(text, encoding="utf-8")
    print("✅ growth candidate shadow hotfix applied")


if __name__ == "__main__":
    main()

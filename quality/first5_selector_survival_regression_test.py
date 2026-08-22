from pathlib import Path


HOTFIX_PATH = Path("ci_hook_production_parity_hotfix.py")
SELECTOR_SYMBOL = "fetch_early_retention_pexels_video"


def main():
    source = HOTFIX_PATH.read_text(encoding="utf-8")

    # The production parity hotfix runs after ci_first5_visual_contract_hotfix.py.
    # Its fallback-body rewrite must stop before the first-5 selector helper or the
    # later import in video_engine.py fails at runtime.
    required_boundary = (
        "def (?:fetch_early_retention_pexels_video|print_hook_visual_audit)"
    )
    if required_boundary not in source:
        raise AssertionError(
            "Hook production parity rewrite no longer preserves the first-5 "
            "selector boundary"
        )

    if SELECTOR_SYMBOL not in source:
        raise AssertionError(
            "First-5 selector symbol is not represented in the parity hotfix guard"
        )

    print("FIRST5 SELECTOR SURVIVAL REGRESSION: PASS")


if __name__ == "__main__":
    main()

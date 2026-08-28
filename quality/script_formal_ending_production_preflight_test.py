"""Deterministic production preflight for Script ending/visual-budget contracts."""
from quality.script_formal_ending_production_corpus_regression_test import run_after_corpus
from quality.script_visual_budget_regression_test import run as run_script_visual_budget


def main():
    run_after_corpus()
    run_script_visual_budget()
    print("SCRIPT PRODUCTION PREFLIGHT V1: PASS")


if __name__ == "__main__":
    main()

"""Regression test for run 607's "too broad / generic reveal" Explorer failures.

Run 607 exhausted all 7 candidate attempts. Two candidates reached the
independent Winner Candidate Gate and were rejected there for exactly the
condition Explorer's own Hard Gate section 8 (GENERIC EXPLANATION / BROAD
THEME) is supposed to catch:

  - "인간이 만든 계단식 농장" / "왜 산속에 계단식 농장이 만들어졌을까요?"
  - "개미의 비밀스러운 의사소통 방식" / "어떻게 개미는 화학물질로 서로의
    위치와 상태를 알릴 수 있을까?"

Both have Core Questions whose answers are guessable from the question
itself, and Reveals that stop at common-knowledge level ("adapted to
terrain", "uses pheromones"). Explorer's own Hard Gate should have rejected
these before they ever reached the Winner Gate, but section 8 previously
had no concrete good/bad examples -- only abstract rules -- so gpt-4o-mini
could not reliably self-apply the "too broad" check.

This test asserts that content/candidate_explorer.py's Hard Gate section 8
now includes both real failure cases as worked bad examples (so Explorer
recognizes this exact failure shape) and at least one good example showing
what a sufficiently narrow question/Reveal pair looks like on similar
subject matter (so Explorer has a template to imitate).
"""

import re


def _load_prompt_source():
    return open("content/candidate_explorer.py", encoding="utf-8").read()


def test_broad_theme_section_has_terrace_farm_bad_example():
    src = _load_prompt_source()
    assert "계단식 농장" in src, (
        "Explorer prompt must reference the terraced-farm case from run 607 "
        "as a worked bad example under GENERIC EXPLANATION / BROAD THEME"
    )


def test_broad_theme_section_has_ant_pheromone_bad_example():
    src = _load_prompt_source()
    assert "페로몬" in src and "개미" in src, (
        "Explorer prompt must reference the ant-pheromone case from run 607 "
        "as a worked bad example"
    )


def test_broad_theme_section_has_a_good_example():
    src = _load_prompt_source()
    assert "좋은 예 (통과 가능)" in src, (
        "GENERIC EXPLANATION / BROAD THEME section must contrast the bad "
        "examples with at least one good example of a sufficiently narrow "
        "question/Reveal pair"
    )


def test_self_check_question_present():
    src = _load_prompt_source()
    assert "질문만 읽고 이미 알고 있는가" in src, (
        "Explorer prompt must give a concrete self-check question so the "
        "model can apply the too-broad rule to its own candidate before "
        "returning it"
    )


def test_explorer_module_still_parses_and_loads():
    import ast

    src = _load_prompt_source()
    ast.parse(src)

    import importlib
    import sys

    for mod_name in list(sys.modules):
        if mod_name.startswith("content.candidate_explorer") or mod_name.startswith(
            "content._candidate_explorer_legacy"
        ):
            del sys.modules[mod_name]

    import content.candidate_explorer as ce

    assert hasattr(ce, "_LEGACY"), "package shadow must still expose _LEGACY"
    assert "계단식 농장" in ce._LEGACY.CANDIDATE_EXPLORER_PROMPT


if __name__ == "__main__":
    test_broad_theme_section_has_terrace_farm_bad_example()
    print("✓ test_broad_theme_section_has_terrace_farm_bad_example")

    test_broad_theme_section_has_ant_pheromone_bad_example()
    print("✓ test_broad_theme_section_has_ant_pheromone_bad_example")

    test_broad_theme_section_has_a_good_example()
    print("✓ test_broad_theme_section_has_a_good_example")

    test_self_check_question_present()
    print("✓ test_self_check_question_present")

    test_explorer_module_still_parses_and_loads()
    print("✓ test_explorer_module_still_parses_and_loads")

    print("\n✅ All tests passed")

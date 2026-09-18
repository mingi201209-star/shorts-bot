"""Regression test for run 606's canonical subject grounding false-block.

Run 606 failed at the Winner Candidate Gate because Explorer could not
confidently classify a biological subject:

  Topic: "흰개미가 나무를 부식시키는 독특한 방법"
  Question: "흰개미는 어떻게 나무를 부식시키기 위해 특정 미생물을 활용할까요?"
  Result: subject_kind was neither "physical_entity" nor "non_physical_concept",
  so CANONICAL_SUBJECT_GROUNDING_GATE_V1 blocked with
  "physical/non-physical subject kind is unresolved".

The gate itself (quality/canonical_subject_grounding.py) is correct and
untouched: a physical subject must have a resolved identity. The actual
problem is the Explorer-facing instructions in
ci_canonical_subject_grounding_hotfix.py's CANDIDATE_PATCH never told the
model that a living organism (an insect, a microorganism, an animal) counts
as a physical_entity, so on a biology-domain candidate the model had no
confident category to pick.

This test asserts the patch text explicitly includes organism/biological
guidance under the physical_entity definition, so Explorer has a clear rule
to classify candidates like the termite case above.
"""

import re


def _load_candidate_patch():
    src = open("ci_canonical_subject_grounding_hotfix.py", encoding="utf-8").read()
    ns = {}
    src_no_apply = src.rsplit('append_once("content/candidate_explorer.py"', 1)[0]
    exec(compile(src_no_apply, "ci_canonical_subject_grounding_hotfix.py", "exec"), ns)
    return ns["CANDIDATE_PATCH"]


def test_physical_entity_definition_covers_living_organisms():
    patch = _load_candidate_patch()

    assert "living organism" in patch, (
        "physical_entity definition must explicitly mention living organisms"
    )
    assert "microorganism" in patch, (
        "physical_entity definition must explicitly mention microorganisms "
        "(the run 606 candidate's mechanism was a gut microbiome)"
    )
    assert "biological" in patch.lower(), (
        "physical_entity definition must clarify that a biological/chemical "
        "mechanism does not make the organism itself unresolved"
    )


def test_patch_still_parses_as_valid_python_once_applied():
    import ast

    patch = _load_candidate_patch()
    dummy_base = 'CANDIDATE_EXPLORER_PROMPT = """BASE"""\n'
    ast.parse(dummy_base + patch)


if __name__ == "__main__":
    test_physical_entity_definition_covers_living_organisms()
    print("✓ test_physical_entity_definition_covers_living_organisms")

    test_patch_still_parses_as_valid_python_once_applied()
    print("✓ test_patch_still_parses_as_valid_python_once_applied")

    print("\n✅ All tests passed")

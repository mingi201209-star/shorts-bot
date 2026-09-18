"""Regression test for runs 618/619's canonical subject grounding false-block.

Both runs blocked at CANONICAL_SUBJECT_GROUNDING because Explorer could not
confidently classify a subject that is unambiguously physical:

  Run 619: "고대 로마의 하수도 시스템" (Ancient Rome's sewer system) --
  Question: "고대 로마의 하수도 시스템은 왜 불균형한 경사로 설계되었을까?"

  Run 618: "비행기 창문 모서리가 둥글게 디자인된 이유" (why airplane window
  corners are rounded)

  Result in both cases: subject_kind was neither "physical_entity" nor
  "non_physical_concept", so CANONICAL_SUBJECT_GROUNDING_GATE_V1 blocked with
  "physical/non-physical subject kind is unresolved".

The gate itself (quality/canonical_subject_grounding.py) is correct and
untouched: a physical subject must have a resolved identity. The actual
problem, same pattern as the run 606 living-organism fix, is that the
Explorer-facing physical_entity definition in
ci_canonical_subject_grounding_hotfix.py's CANDIDATE_PATCH never told the
model that (a) large-scale built/civil infrastructure (a sewer system, road,
aqueduct, bridge, etc.) counts as a physical_entity even though it is large
and made of many components, and (b) a specific geometric/design feature of a
manufactured object (e.g. a window's rounded corner) counts as a
physical_entity even though the subject is a shape/feature rather than the
whole object.

This test asserts:
  1. the patch text explicitly extends physical_entity to civil infrastructure
     and to specific design/geometric features, so Explorer has a clear rule
     for candidates like the two above,
  2. the gate itself (unmodified) resolves a well-formed infrastructure
     candidate and a well-formed design-feature candidate as PASS/physical,
  3. the prior run-606 living-organism guidance is still present (no
     regression), and
  4. a genuinely non-physical/ambiguous candidate is still correctly blocked.
"""

from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding


def _load_candidate_patch():
    src = open("ci_canonical_subject_grounding_hotfix.py", encoding="utf-8").read()
    ns = {}
    src_no_apply = src.rsplit('append_once("content/candidate_explorer.py"', 1)[0]
    exec(compile(src_no_apply, "ci_canonical_subject_grounding_hotfix.py", "exec"), ns)
    return ns["CANDIDATE_PATCH"]


def test_physical_entity_definition_covers_civil_infrastructure():
    patch = _load_candidate_patch()

    assert "infrastructure" in patch.lower(), (
        "physical_entity definition must explicitly mention large-scale "
        "built/civil infrastructure (sewer systems, roads, aqueducts, etc.)"
    )
    assert "하수도" in patch, (
        "physical_entity definition should reference the run 619 sewer "
        "system example so Explorer has a concrete anchor"
    )


def test_physical_entity_definition_covers_design_features():
    patch = _load_candidate_patch()

    assert "geometric" in patch.lower() or "design feature" in patch.lower(), (
        "physical_entity definition must explicitly cover a specific "
        "geometric/design feature of a manufactured object (e.g. a window's "
        "rounded corner), not only the whole object"
    )
    assert "rounded corner" in patch.lower() or "둥근 모서리" in patch, (
        "physical_entity definition should reference the run 618 airplane "
        "window rounded-corner example so Explorer has a concrete anchor"
    )


def test_run_606_living_organism_guidance_still_present():
    patch = _load_candidate_patch()

    assert "living organism" in patch
    assert "microorganism" in patch
    assert "biological" in patch.lower()


def test_patch_still_parses_as_valid_python_once_applied():
    import ast

    patch = _load_candidate_patch()
    dummy_base = 'CANDIDATE_EXPLORER_PROMPT = """BASE"""\n'
    ast.parse(dummy_base + patch)


def test_gate_resolves_ancient_rome_sewer_system_as_physical():
    candidate = {
        "topic": "고대 로마의 하수도 시스템",
        "core_question": "고대 로마의 하수도 시스템은 왜 불균형한 경사로 설계되었을까?",
        "subject_kind": "physical_entity",
        "canonical_subject": "고대 로마의 하수도 시스템",
        "subject_identity_confidence": 0.9,
        "grounding_evidence": [
            {
                "evidence_type": "explicit_candidate_identity",
                "supports_subject": "고대 로마의 하수도 시스템",
                "source": "candidate_text",
                "detail": "candidate topic names the sewer system directly",
            }
        ],
    }
    result = evaluate_candidate_subject_grounding(candidate)
    assert result["status"] == "PASS", result
    assert result["subject_grounding"]["subject_kind"] == "physical_entity"


def test_gate_resolves_airplane_window_rounded_corner_as_physical():
    candidate = {
        "topic": "비행기 창문의 둥근 모서리가 둥글게 디자인된 이유",
        "core_question": "비행기 창문의 둥근 모서리는 왜 둥글게 디자인되었을까?",
        "subject_kind": "physical_entity",
        "canonical_subject": "비행기 창문의 둥근 모서리",
        "subject_identity_confidence": 0.9,
        "grounding_evidence": [
            {
                "evidence_type": "explicit_candidate_identity",
                "supports_subject": "비행기 창문의 둥근 모서리",
                "source": "candidate_text",
                "detail": "candidate topic names the rounded window corner directly",
            }
        ],
    }
    result = evaluate_candidate_subject_grounding(candidate)
    assert result["status"] == "PASS", result
    assert result["subject_grounding"]["subject_kind"] == "physical_entity"


def test_gate_still_blocks_genuinely_non_physical_ambiguous_subject():
    # A candidate whose subject_kind never resolves to a concrete category --
    # e.g. an abstract policy/emotion claim with no single identifiable
    # object -- must remain blocked. This must not regress just because the
    # physical_entity definition was broadened.
    candidate = {
        "topic": "행복이라는 감정은 왜 오래 지속되지 않을까",
        "core_question": "행복이라는 감정은 왜 금방 사라질까?",
        "subject_kind": "",
        "canonical_subject": "UNKNOWN",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }
    result = evaluate_candidate_subject_grounding(candidate)
    assert result["status"] == "BLOCK", result
    assert result["reason"] == "physical/non-physical subject kind is unresolved"


if __name__ == "__main__":
    test_physical_entity_definition_covers_civil_infrastructure()
    print("✓ test_physical_entity_definition_covers_civil_infrastructure")

    test_physical_entity_definition_covers_design_features()
    print("✓ test_physical_entity_definition_covers_design_features")

    test_run_606_living_organism_guidance_still_present()
    print("✓ test_run_606_living_organism_guidance_still_present")

    test_patch_still_parses_as_valid_python_once_applied()
    print("✓ test_patch_still_parses_as_valid_python_once_applied")

    test_gate_resolves_ancient_rome_sewer_system_as_physical()
    print("✓ test_gate_resolves_ancient_rome_sewer_system_as_physical")

    test_gate_resolves_airplane_window_rounded_corner_as_physical()
    print("✓ test_gate_resolves_airplane_window_rounded_corner_as_physical")

    test_gate_still_blocks_genuinely_non_physical_ambiguous_subject()
    print("✓ test_gate_still_blocks_genuinely_non_physical_ambiguous_subject")

    print("\n✅ All tests passed")

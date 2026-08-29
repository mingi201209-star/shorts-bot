from pathlib import Path


MARKER = "CANONICAL_SUBJECT_GROUNDING_GATE_V1"


def require(path, *needles):
    text = Path(path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, f"{path}: missing {needle!r}"
    return text


def test_candidate_contract_is_installed():
    text = require(
        "content/candidate_explorer.py",
        MARKER,
        '"subject_kind": "physical_entity" | "non_physical_concept"',
        '"canonical_subject": "UNKNOWN"',
        '"grounding_evidence": []',
        "_original_validate_candidate_before_subject_grounding",
    )
    assert "Never invent a source" in text


def test_pre_writer_boundary_is_fail_closed():
    text = require(
        "main.py",
        MARKER,
        "_canonical_subject_gate",
        "_original_generate_script_before_subject_grounding",
        "unresolved physical subject cannot reach Writer",
    )
    gate_position = text.index("def generate_script(topic_info, candidate):")
    writer_call_position = text.index(
        "_original_generate_script_before_subject_grounding(",
        gate_position,
    )
    block_position = text.index(
        "if grounding.get(\"status\") != \"PASS\"",
        gate_position,
    )
    assert block_position < writer_call_position


def test_fact_identity_precheck_runs_before_normal_fact_api_path():
    text = require(
        "quality/judge.py",
        MARKER,
        "fact_identity_precheck",
        "FACT identity precheck fail-closed before API call",
        "Question 2 is not evaluated when question 1 is unresolved",
    )
    wrapper_position = text.index(
        'def run_judge(judge_type, script_data, *, model="gpt-4o-mini"):'
    )
    precheck_position = text.index("fact_identity_precheck", wrapper_position)
    delegated_position = text.index(
        "_original_run_judge_before_subject_grounding(", wrapper_position
    )
    assert precheck_position < delegated_position


def test_existing_candidate_recovery_chain_installs_gate_without_new_retry():
    text = require(
        "ci_candidate_supply_recovery_hotfix.py",
        "import ci_canonical_subject_grounding_hotfix",
    )
    assert "CANDIDATE SUPPLY RECOVERY (1/1)" in text


if __name__ == "__main__":
    test_candidate_contract_is_installed()
    test_pre_writer_boundary_is_fail_closed()
    test_fact_identity_precheck_runs_before_normal_fact_api_path()
    test_existing_candidate_recovery_chain_installs_gate_without_new_retry()
    print("CANONICAL SUBJECT GROUNDING PRODUCTION WIRING: PASS")

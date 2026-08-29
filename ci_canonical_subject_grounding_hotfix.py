from pathlib import Path


MARKER = "# CANONICAL_SUBJECT_GROUNDING_GATE_V1"


CANDIDATE_PATCH = r'''

# CANONICAL_SUBJECT_GROUNDING_GATE_V1
# Structured identity metadata is produced by Candidate Explorer but validated
# independently. The Explorer is never allowed to turn an ambiguous surface
# description into a technical entity merely to complete a story.
from quality.canonical_subject_grounding import normalize_candidate_subject_metadata

CANDIDATE_EXPLORER_PROMPT += r"""

============================================================
14. CANONICAL SUBJECT GROUNDING GATE V1
============================================================

Before a Candidate can hand a physical object/part to the Writer, explicitly
separate object identity from the object's proposed function or mechanism.

For BOTH winner and runner_up add these fields:

"subject_kind": "physical_entity" | "non_physical_concept"
"canonical_subject": "..."
"subject_identity_confidence": 0.0~1.0
"grounding_evidence": []

Rules:

1. physical_entity
A concrete object, component, visible part, hole, mark, protrusion, plate, pin,
rod, structure, device, etc. whose function/purpose/mechanism is part of the
story.

Do NOT infer its canonical identity from its appearance or from a plausible
mechanism. Appearance-only descriptions are not identities.

If the Candidate itself explicitly names the established object, use that name
as canonical_subject and include evidence like:
{
  "evidence_type": "explicit_candidate_identity",
  "supports_subject": "same canonical name",
  "source": "candidate_text",
  "detail": "where the explicit identity appears"
}

If a real upstream source/evidence record identifies an otherwise ambiguous
object, preserve it as:
{
  "evidence_type": "source_backed_identity",
  "supports_subject": "canonical name",
  "source": "actual source handle",
  "detail": "identity-specific support"
}

Never invent a source, citation, technical name, or identity evidence. If the
physical object's identity is not actually established, return:

"canonical_subject": "UNKNOWN"
"subject_identity_confidence": 0.0
"grounding_evidence": []

Do not attach a function/mechanism to UNKNOWN merely because that mechanism is
true for some other object in the same location or category.

2. non_physical_concept
Use only when the Candidate's subject is genuinely a process, transition,
policy, historical sequence, abstract relation, or other non-physical concept.
Use:
"canonical_subject": "NOT_APPLICABLE"
"subject_identity_confidence": 1.0
"grounding_evidence": []

Do not classify a physical detail as non_physical_concept to bypass grounding.

The three identity fields are not FACT verification. They only establish what
the subject is before function/mechanism reasoning begins.
"""

_original_validate_candidate_before_subject_grounding = validate_candidate


def validate_candidate(candidate, *, prefix, runner_up=False):
    result = _original_validate_candidate_before_subject_grounding(
        candidate,
        prefix=prefix,
        runner_up=runner_up,
    )

    metadata = normalize_candidate_subject_metadata(candidate)
    kind = metadata["subject_kind"]

    # Compatibility is deliberately fail-closed at the later boundary: old
    # fixtures/payloads can still parse, but missing identity metadata becomes
    # unresolved rather than silently treated as grounded.
    if kind not in ("physical_entity", "non_physical_concept"):
        metadata = {
            "subject_kind": "unresolved",
            "canonical_subject": "UNKNOWN",
            "subject_identity_confidence": 0.0,
            "grounding_evidence": [],
        }

    result.update(metadata)
    return result
'''


MAIN_PATCH = r'''

# CANONICAL_SUBJECT_GROUNDING_GATE_V1
# Candidate -> Script boundary. This layer does not identify subjects; it only
# rejects unresolved identity before Writer code can infer a mechanism.
from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding

_original_evaluate_candidate_before_subject_grounding = evaluate_candidate
_original_generate_script_before_subject_grounding = generate_script


def _canonical_subject_gate(candidate, *, role):
    result = evaluate_candidate_subject_grounding(candidate)
    grounding = result.get("subject_grounding", {})
    if isinstance(candidate, dict):
        candidate["_subject_grounding"] = grounding

    if result.get("status") == "PASS":
        print(
            "🧭 CANONICAL_SUBJECT_GROUNDING PASS "
            f"role={role} kind={grounding.get('subject_kind')} "
            f"canonical={grounding.get('canonical_subject')} "
            f"confidence={grounding.get('subject_identity_confidence')}"
        )
        return result

    print(
        "🚫 CANONICAL_SUBJECT_GROUNDING BLOCK "
        f"role={role} canonical={grounding.get('canonical_subject', 'UNKNOWN')} "
        f"reason={result.get('reason', '')}"
    )
    return result


def evaluate_candidate(candidate, *, role="Winner"):
    editorial = _original_evaluate_candidate_before_subject_grounding(
        candidate,
        role=role,
    )
    if editorial.get("status") == "REGENERATE":
        return editorial

    grounding = _canonical_subject_gate(candidate, role=role)
    if grounding.get("status") != "PASS":
        return {
            "status": "REGENERATE",
            "failure_type": "SUBJECT_IDENTITY_UNRESOLVED",
            "reason": (
                "미확인 canonical subject identity: "
                f"{grounding.get('reason', '')}. "
                "기능/원리 추론 전에 물체 정체성과 근거가 필요합니다."
            ),
        }
    return editorial


def generate_script(topic_info, candidate):
    # Hard defense-in-depth. Fixed-topic editorial advisory or any alternate
    # Script caller cannot bypass the identity contract.
    grounding = _canonical_subject_gate(candidate, role="pre-Writer")
    if grounding.get("status") != "PASS":
        raise RuntimeError(
            "CANONICAL_SUBJECT_GROUNDING_GATE_V1 BLOCK: "
            "unresolved physical subject cannot reach Writer"
        )

    script_data = _original_generate_script_before_subject_grounding(
        topic_info,
        candidate,
    )
    if isinstance(script_data, dict):
        script_data["subject_grounding"] = grounding["subject_grounding"]
    return script_data
'''


JUDGE_PATCH = r'''

# CANONICAL_SUBJECT_GROUNDING_GATE_V1
# FACT defense-in-depth: identity is question 1; mechanism truth is question 2.
# Question 2 is not evaluated when question 1 is unresolved.
from quality.canonical_subject_grounding import fact_identity_precheck

_original_build_judge_prompt_before_subject_grounding = build_judge_prompt
_original_run_judge_before_subject_grounding = run_judge


def build_judge_prompt(judge_type, script_data):
    prompt = _original_build_judge_prompt_before_subject_grounding(
        judge_type,
        script_data,
    )
    if judge_type != "fact":
        return prompt

    grounding = script_data.get("subject_grounding", {})
    return prompt + f"""

============================================================
CANONICAL SUBJECT GROUNDING — FACT CONTRACT
============================================================

subject_grounding:
{json.dumps(grounding, ensure_ascii=False, indent=2)}

FACT 판단을 반드시 두 질문으로 분리한다.

1. 설명 대상 물체의 canonical identity가 실제로 확정되어 있는가?
2. 그 확정된 물체에 대해 대본이 말하는 기능/원리가 사실인가?

1번이 unresolved/UNKNOWN/근거 없음이면 2번의 일반적 plausibility로
보완하거나 PASS시키지 마라. 예를 들어 UNKNOWN small rod에 대해
wingtip vortex reduction이 일반적으로 사실이라는 이유만으로 해당 막대의
identity/function을 승인해서는 안 된다.
"""


def run_judge(judge_type, script_data, *, model="gpt-4o-mini"):
    if judge_type == "fact":
        blocked = fact_identity_precheck(script_data)
        if blocked is not None:
            print("🚫 FACT identity precheck fail-closed before API call")
            return blocked

    return _original_run_judge_before_subject_grounding(
        judge_type,
        script_data,
        model=model,
    )
'''


def append_once(path_string, patch):
    path = Path(path_string)
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"ℹ️ Canonical Subject Grounding already applied: {path_string}")
        return
    path.write_text(text + patch, encoding="utf-8")
    print(f"✅ Canonical Subject Grounding applied: {path_string}")


append_once("content/candidate_explorer.py", CANDIDATE_PATCH)
append_once("main.py", MAIN_PATCH)
append_once("quality/judge.py", JUDGE_PATCH)

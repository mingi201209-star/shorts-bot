from pathlib import Path


EXPLORER_PATH = Path("content/candidate_explorer.py")


def main():
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    marker = "AVIATION_SPECIFICITY_PROJECTION_V3"
    if marker in text:
        print("✅ Aviation specificity projection V3 already applied")
        return

    text += r'''

# AVIATION_SPECIFICITY_PROJECTION_V3
# Preserve the V1 schema-repair function, then deterministically copy an already
# grounded structured detail into Gate-visible narration. The projection itself
# makes zero API calls and cannot invent a new fact.
_aviation_specificity_schema_repair_v1 = _repair_aviation_specificity_output_if_needed


def _aviation_projection_failure_reason(candidate):
    if not isinstance(candidate, dict):
        return "candidate is not an object"
    ok, reason = aviation_candidate_quality_check(candidate)
    return "" if ok else str(reason or "")


def _aviation_projection_needed(candidate):
    if not isinstance(candidate, dict):
        return False
    reason = _aviation_projection_failure_reason(candidate)
    return bool(reason) and (
        "does not directly carry the concrete element" in reason
        or "generic why-design question without a concrete element" in reason
        or "generic benefit reveal without a concrete mechanism/constraint/trade-off" in reason
    )


def _aviation_first_grounded_detail(candidate):
    for field in _AVIATION_SPECIFICITY_FIELDS:
        value = str((candidate or {}).get(field) or "").strip()
        if value:
            return field, value
    return None, ""


def _aviation_project_existing_detail(data):
    if not isinstance(data, dict):
        return data
    winner = data.get("winner")
    if not isinstance(winner, dict):
        return data

    detail_field, detail = _aviation_first_grounded_detail(winner)
    if not detail:
        return data

    projected = dict(data)
    projected_winner = dict(winner)
    micro = dict(projected_winner.get("micro_narrative") or {})

    reveal = str(micro.get("reveal") or "").strip()
    reveal_norm = _aviation_norm(reveal)
    detail_norm = _aviation_norm(detail)
    if detail_norm and detail_norm not in reveal_norm:
        separator = " " if not reveal or reveal.endswith((".", "!", "?", "다.", "요.")) else ". "
        micro["reveal"] = f"{reveal}{separator}구체적으로는 {detail}.".strip()
    else:
        micro["reveal"] = reveal

    # Keep topic/core_question and all structured specificity fields byte-for-byte.
    # Only the reveal receives an exact copy of an existing grounded detail.
    projected_winner["micro_narrative"] = micro
    projected["winner"] = projected_winner
    print(
        "🧷 Aviation specificity deterministic projection: "
        f"field={detail_field} api_calls=0"
    )
    return projected


def _aviation_specificity_repair_needed(data):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return False
    if not isinstance(data, dict):
        return False
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return False
    winner = data.get("winner")
    return _aviation_specificity_output_missing(winner) or _aviation_projection_needed(winner)


def _repair_aviation_specificity_output_if_needed(data, *, model=MODEL):
    if os.environ.get("SHORTS_CANDIDATE_SCOPE", "").strip().lower() != "aviation":
        return data
    if not isinstance(data, dict):
        return data
    if str(data.get("status") or "").strip().upper() != "SELECTED":
        return data

    working = data
    winner = working.get("winner")

    # Missing structured specificity belongs to V1. Let that single bounded schema
    # repair run first; V3 never replaces it or spends a second LLM call.
    if _aviation_specificity_output_missing(winner):
        working = _aviation_specificity_schema_repair_v1(working, model=model)
        if not isinstance(working, dict):
            return working
        if str(working.get("status") or "").strip().upper() != "SELECTED":
            return working
        winner = working.get("winner")
        if _aviation_specificity_output_missing(winner):
            return {
                "status": "REGENERATE",
                "reason": "aviation specificity schema repair left no grounded detail",
            }

    ok, _ = aviation_candidate_quality_check(winner)
    if ok:
        return working

    if not _aviation_projection_needed(winner):
        return working

    projected = _aviation_project_existing_detail(working)
    projected_winner = projected.get("winner") or {}

    # Projection must not mutate any source-of-truth field. Only reveal may change.
    original_winner = working.get("winner") or {}
    for field in (
        "topic",
        "angle",
        "core_question",
        "fact_check_focus",
        "visual_proof",
        "selection_reason",
        *_AVIATION_SPECIFICITY_FIELDS,
    ):
        if projected_winner.get(field) != original_winner.get(field):
            return {
                "status": "REGENERATE",
                "reason": f"aviation deterministic projection changed protected field: {field}",
            }

    ok, reason = aviation_candidate_quality_check(projected_winner)
    if not ok:
        return {
            "status": "REGENERATE",
            "reason": f"aviation deterministic projection still weak: {reason}",
        }

    return projected


CANDIDATE_EXPLORER_PROMPT += """

[AVIATION SPECIFICITY PROJECTION — GATE-VISIBLE CONTRACT V3]
aviation Candidate에서 concrete detail을 별도 필드에만 숨기지 마라.
Candidate Gate가 직접 읽는 topic, core_question, micro_narrative.reveal에도 같은 구체 요소를 명시하라.
'왜 특정 형태인가 → 안전을 위해' 같은 일반론은 금지한다.
구체 관찰/제약/trade-off/조건/직관과 반대되는 결과가 질문 또는 Reveal 자체에 직접 보여야 한다.
새 사실을 만들어 구체적으로 보이게 하는 것은 금지한다.
"""
'''

    EXPLORER_PATH.write_text(text, encoding="utf-8")
    print("✅ Aviation deterministic gate-visible specificity projection V3 applied")


if __name__ == "__main__":
    main()
    # Candidate Pool Handoff must be installed after specificity helpers/projection
    # and before the existing bounded grounded/supply recovery composition.
    # These imports perform no model/Vision/image call.
    import ci_candidate_pool_handoff_hotfix  # noqa: F401,E402
    import ci_grounding_aware_candidate_supply_hotfix  # noqa: F401,E402

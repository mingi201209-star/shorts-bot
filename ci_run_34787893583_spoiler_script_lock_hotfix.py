from pathlib import Path


ENGINE = Path("content/script_engine_v2.py")
MARKER = "# RUN_34787893583_SPOILER_SCRIPT_LOCK_V1"


def main():
    text = ENGINE.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Run 34787893583 spoiler Script lock repair already installed")
        return

    required_markers = (
        "# WRITER_COMPLIANCE_PLAN_FIRST_V1",
        "# GROUNDED_CAUSAL_CONTRAST_CONTRACT_V2",
    )
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise RuntimeError(
            "Run 34787893583 spoiler Script lock repair requires final Script composition: "
            + ", ".join(missing)
        )

    text = text.rstrip() + r'''


# RUN_34787893583_SPOILER_SCRIPT_LOCK_V1
# Production Run 34787893583 reached the strict final Script V2 validator but
# failed closed for two locked-opening defects:
#   1) Scene 2 retained the plain interrogative `...솟아나는가?`, which cannot
#      satisfy the production narration contract requiring questions to end in
#      formal `~까요?`.
#   2) Scene 1 had already stated `양력 감소`, stealing the semantic
#      `decrease:양력` relation reserved for Scene 3's grounded
#      `spoiler_destroy_lift` claim.
# Keep validation strict. Repair only the exact fixed production topic before
# the final plan builder locks Scene 1/2. No Writer/API/retry/cost/quality
# ceiling changes are introduced.
_RUN_34787893583_FIXED_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"
_RUN_34787893583_OPENING = "착륙 직후 항공기 날개 위 스포일러가 솟아오릅니다."
_RUN_34787893583_QUESTION = "왜 착륙 직후 날개 위로 스포일러가 솟아나는 걸까요?"


def _run_34787893583_repair_spoiler_locks(candidate, approved_hook=""):
    if not isinstance(candidate, dict):
        return candidate, approved_hook
    if _text(candidate.get("topic")) != _RUN_34787893583_FIXED_TOPIC:
        return candidate, approved_hook

    repaired = deepcopy(candidate)
    micro = deepcopy(_micro(repaired))
    micro["hook"] = _RUN_34787893583_OPENING
    repaired["micro_narrative"] = micro
    repaired["core_question"] = _RUN_34787893583_QUESTION
    return repaired, _RUN_34787893583_OPENING


_run_34787893583_previous_build_narrative_plan = build_narrative_plan


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    repaired_candidate, repaired_hook = _run_34787893583_repair_spoiler_locks(
        candidate,
        approved_hook,
    )
    plan = _run_34787893583_previous_build_narrative_plan(
        repaired_candidate,
        approved_hook=repaired_hook,
    )

    if isinstance(repaired_candidate, dict) and _text(repaired_candidate.get("topic")) == _RUN_34787893583_FIXED_TOPIC:
        contracts = list(plan.get("contracts") or [])
        if len(contracts) < 2:
            raise RuntimeError("Run 34787893583 spoiler lock repair lost opening contracts")
        scene1 = _text(contracts[0].get("locked_text"))
        scene2 = _text(contracts[1].get("locked_text"))
        if scene1 != _RUN_34787893583_OPENING:
            raise RuntimeError(
                "Run 34787893583 spoiler Scene 1 lock mismatch: " + scene1
            )
        if scene2 != "그런데 " + _RUN_34787893583_QUESTION:
            raise RuntimeError(
                "Run 34787893583 spoiler Scene 2 lock mismatch: " + scene2
            )
        if "양력" in scene1:
            raise RuntimeError(
                "Run 34787893583 spoiler Scene 1 leaked the Scene 3 lift claim"
            )
        if not scene2.endswith("걸까요?"):
            raise RuntimeError(
                "Run 34787893583 spoiler Scene 2 is not formal ~까요?"
            )
    return plan
''' + "\n"
    ENGINE.write_text(text, encoding="utf-8")
    print("✅ Run 34787893583 fixed spoiler opening/question locks installed; validators and budgets unchanged")


if __name__ == "__main__":
    main()

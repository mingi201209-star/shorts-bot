from pathlib import Path


RUNNER_PATH = Path("content/script_engine_v2_runner.py")
MARKER = "# WINGLET_UNSUPPORTED_VISUAL_BEAT_RECOVERY_V1"


def main():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ winglet unsupported visual beat recovery already applied")
        return

    block = r'''

# WINGLET_UNSUPPORTED_VISUAL_BEAT_RECOVERY_V1
# Run 33169424813 reached Scene 7 with a FACT-accepted but visually unsupported
# winglet noise-benefit beat. Keep Script V2 calls unchanged and recover only
# after the existing writer/validation path has completed. The helper changes
# the script only when exact winglet context, grounding, and novelty checks pass.
_script_v2_generate_before_winglet_visual_recovery = generate_script_v2


def generate_script_v2(
    candidate: Dict[str, Any],
    approved_hook: str = "",
    *,
    call_fn: Callable[..., Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    original = _script_v2_generate_before_winglet_visual_recovery(
        candidate,
        approved_hook=approved_hook,
        call_fn=call_fn,
    )

    from content.winglet_visual_beat_recovery import (
        recover_unsupported_winglet_visual_beat,
    )

    recovered = recover_unsupported_winglet_visual_beat(original, candidate)
    if recovered == original:
        return original

    # Re-run only the deterministic Script V2 validator. No writer/local-repair
    # call is made here. If the replacement violates any existing contract, keep
    # the original script so the downstream visual path fails closed as before.
    candidate_for_plan, hook_for_plan = _normalize_candidate_opening(
        candidate,
        approved_hook,
    )
    plan = build_narrative_plan(candidate_for_plan, approved_hook=hook_for_plan)
    validation = validate_script_v2(recovered, plan)
    if not validation.get("valid"):
        print(
            "[WINGLET_UNSUPPORTED_VISUAL_BEAT_RECOVERY_V1] "
            "status=script_contract_rejected reasons="
            + " | ".join(validation.get("reasons") or [])
        )
        return original

    recovered["script_engine_v2_calls"] = original.get("script_engine_v2_calls", 0)
    return recovered
'''

    RUNNER_PATH.write_text(text.rstrip() + block + "\n", encoding="utf-8")
    print("✅ bounded winglet unsupported visual beat recovery applied")


if __name__ == "__main__":
    main()

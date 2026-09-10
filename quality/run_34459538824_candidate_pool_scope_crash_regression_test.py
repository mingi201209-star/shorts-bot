"""Authority regression for Run 34459538824.

RED authority:
- Production Run 34459538824 (main HEAD c3a9dbd66d6531bbe6913b7a13947a79c50d1bb2)
  dispatched an ordinary automatic-topic Candidate attempt (category=역사,
  direction=역사 속 사라진 생활 기술; SHORTS_TOPIC and SHORTS_CANDIDATE_SCOPE
  both blank -- nothing aviation-related). Candidate Explorer still returned
  status=CANDIDATE_POOL, because CANDIDATE_EXPLORER_PROMPT section 15
  (installed by ci_candidate_pool_handoff_hotfix.py) is always present
  regardless of runtime SHORTS_CANDIDATE_SCOPE. The Candidate Pool Handoff
  wrapper only recognized CANDIDATE_POOL under aviation_scope and otherwise
  fell straight through to the legacy SELECTED/REGENERATE-only validator,
  which raised an unhandled ValueError that crashed the whole production run
  on Candidate attempt 1 of 7 -- before the existing bounded retry loop ever
  got a chance to try again.

GREEN authority:
- Candidate Pool Handoff stays aviation-only exactly as before: a
  CANDIDATE_POOL response received outside aviation scope is still never
  validated or accepted (no winner, no candidate content read).
- Only the failure mode changes: a clean REGENERATE, the same
  bounded-retry-eligible outcome any other unusable Explorer response
  already produces, instead of an unhandled crash.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _runtime_explorer_module():
    import content.candidate_explorer as explorer_package

    return explorer_package._LEGACY


# Exact production counterexample shape: an unrelated automatic-topic pool
# response (aviation-flavored prompt section notwithstanding).
POOL = {
    "status": "CANDIDATE_POOL",
    "candidates": [
        {
            "topic": "다리미 없이 옷 주름을 펴던 옛 방법",
            "angle": "물과 돌로 옷감을 다린 전통 방식",
        }
    ],
}


def main() -> int:
    validate_explorer_output = _runtime_explorer_module().validate_explorer_output

    for scope in ("", "urban"):
        os.environ["SHORTS_CANDIDATE_SCOPE"] = scope
        result = validate_explorer_output(POOL)
        assert isinstance(result, dict), (scope, result)
        assert result.get("status") == "REGENERATE", (scope, result)
        assert "outside aviation scope" in result.get("reason", ""), (scope, result)
        assert "winner" not in result, (scope, result)
        assert "candidates" not in result, (scope, result)

    os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
    print("RUN_34459538824_CANDIDATE_POOL_SCOPE_CRASH_REGRESSION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

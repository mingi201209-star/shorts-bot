"""Regression for pre-Writer trusted grounding resupply.

A fixed-topic retry may produce a new Candidate after the Explorer validation
wrapper already supplied trusted identity. The production chain must re-apply
repo-owned trusted grounding before the existing pre-Writer gate, without
weakening that gate or adding calls/retries.

Run 34742040475 (#545) added a narrower counterexample: an LLM winner can retain
the exact pinned repo seed topic while lacking the deterministic seed object's
private record reference. The exact fixed-topic bridge may reuse the existing
repo record only when Candidate topic == SHORTS_TOPIC == one unique repo-owned
seed topic; everything else remains fail-closed.
"""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality.fixed_topic_seed_grounding import (
    exact_fixed_topic_seed_record,
    supply_exact_fixed_topic_seed_grounding,
)
from quality.grounding_aware_candidate_supply import all_trusted_candidate_records


SPOILER_TOPIC = "착륙 직후 날개 위로 솟는 스포일러"


def _run_34742040475_llm_candidate():
    return {
        "topic": SPOILER_TOPIC,
        "angle": "착륙 직후 올라오는 판이 양력을 줄여 바퀴 제동을 돕는 이유",
        "core_question": "왜 착륙하자마자 날개 위 판을 올릴까?",
        "micro_narrative": {
            "hook": "착륙 직후 날개 위 판이 올라옵니다.",
            "core_question": "왜 양력을 만드는 날개에서 판을 세울까요?",
            "reveal": "스포일러는 날개 위 흐름을 깨뜨립니다.",
            "payoff": "착륙 뒤 바퀴 제동을 돕습니다.",
        },
        "fact_check_focus": ["착륙 후 스포일러 기능"],
        "visual_proof": ["착륙 직후 날개 위에서 올라온 패널"],
        "selection_reason": "fixed-topic LLM winner regression",
        "subject_kind": "physical_entity",
        "canonical_subject": "스포일러",
        "subject_identity_confidence": 0.0,
        "grounding_evidence": [],
    }


def run():
    records = all_trusted_candidate_records()
    candidate = _run_34742040475_llm_candidate()

    # Run #545 authority: this is NOT a deterministic seed object and therefore
    # has no host-owned record reference. Exact fixed-topic seed ownership is the
    # only new authority allowed to recover its existing repo grounding.
    resolved = exact_fixed_topic_seed_record(
        candidate,
        SPOILER_TOPIC,
        trusted_records=records,
    )
    assert resolved is not None
    assert resolved.get("canonical_subject") == "aircraft wing spoilers"
    assert (resolved.get("seed_candidate") or {}).get("topic") == SPOILER_TOPIC

    exact_supply = supply_exact_fixed_topic_seed_grounding(
        candidate,
        SPOILER_TOPIC,
        trusted_records=records,
    )
    assert exact_supply is not None
    supplied, supplied_record = exact_supply
    assert supplied_record is resolved
    assert supplied.get("canonical_subject") == "aircraft wing spoilers"
    assert supplied.get("_trusted_grounding_evidence")
    assert supplied.get("_trusted_grounded_claims")
    assert supplied.get("angle") == candidate.get("angle")
    print("CASE #545 exact fixed-topic spoiler seed grounding: PASS")

    # Exact means exact: punctuation/wording drift, a different fixed topic, or
    # duplicate repo ownership must never gain this capability.
    altered = deepcopy(candidate)
    altered["topic"] = SPOILER_TOPIC + "!"
    assert exact_fixed_topic_seed_record(
        altered,
        SPOILER_TOPIC,
        trusted_records=records,
    ) is None

    unknown = deepcopy(candidate)
    unknown["topic"] = "등록되지 않은 고정 주제"
    assert supply_exact_fixed_topic_seed_grounding(
        unknown,
        "등록되지 않은 고정 주제",
        trusted_records=records,
    ) is None

    duplicate_records = tuple(records) + (deepcopy(resolved),)
    assert exact_fixed_topic_seed_record(
        candidate,
        SPOILER_TOPIC,
        trusted_records=duplicate_records,
    ) is None
    print("CASE exact-topic bridge remains unique and fail-closed: PASS")

    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)

    main_source = Path("main.py").read_text(encoding="utf-8")
    assert main_source.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1
    assert "supply_trusted_subject_grounding(" in main_source
    assert "supply_exact_fixed_topic_seed_grounding(" in main_source
    assert '_prewriter_os.environ.get("SHORTS_TOPIC", "")' in main_source
    assert "source=exact_fixed_topic_seed" in main_source
    assert "candidate.clear()" in main_source
    assert "candidate.update(supplied)" in main_source
    assert main_source.index("# CANONICAL_SUBJECT_GROUNDING_GATE_V1") < main_source.index(
        "# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1"
    )

    supply_source = Path("quality/canonical_subject_grounding_supply.py").read_text(
        encoding="utf-8"
    )
    assert supply_source.count("# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1") == 1

    # Idempotence: the production installer chain may be exercised repeatedly
    # by composition/regression jobs and must not stack wrappers.
    subprocess.run([sys.executable, "ci_candidate_grounded_recovery_hotfix.py"], check=True)
    main_source_2 = Path("main.py").read_text(encoding="utf-8")
    assert main_source_2.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1

    # Safety invariants: this fix does not alter the canonical gate itself and
    # introduces no model/API call, retry, threshold, or budget override.
    hotfix_source = Path("ci_prewriter_grounding_resupply_hotfix.py").read_text(
        encoding="utf-8"
    )
    helper_source = Path("quality/fixed_topic_seed_grounding.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "openai.chat",
        "authorize_call(",
        "MAX_TOPIC_REGENERATIONS",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
    )
    for token in forbidden:
        assert token not in hotfix_source, token
        assert token not in helper_source, token

    assert "seed_candidate" in helper_source
    assert "len(matches) != 1" in helper_source
    assert "supply_trusted_subject_grounding(" in helper_source

    print("PREWRITER TRUSTED GROUNDING RESUPPLY REGRESSION: PASS")


if __name__ == "__main__":
    run()
"""Authority regression for Run 34573647770: fixed-topic Canary #2 (topic
"비행기 창문 모서리는 왜 둥글까") was correctly, but avoidably, blocked by
CANONICAL_SUBJECT_GROUNDING_GATE_V1's pre-Writer check.

RED authority (Run 34573647770, exact main 702dd2740239aabffae90377e0fccd023e3b4b3a):
    Gate 결과: PASS  (editorial Candidate Gate)
    CANONICAL_SUBJECT_GROUNDING BLOCK role=Winner canonical=aircraft passenger window
        reason=no trusted evidence supports the canonical physical subject identity
    [FIXED_TOPIC_GATE_ADVISORY] 편집성 Candidate Gate 거절은 1회 피드백 후 advisory로 전환
    CANONICAL_SUBJECT_GROUNDING BLOCK role=pre-Writer canonical=aircraft passenger window
        reason=no trusted evidence supports the canonical physical subject identity
    V3.2.1.2 ERROR
    RuntimeError: CANONICAL_SUBJECT_GROUNDING_GATE_V1 BLOCK: unresolved physical
        subject cannot reach Writer

The Candidate model itself already self-reports subject_kind=physical_entity,
canonical_subject="aircraft passenger window", confidence>=0.80 -- the gate
blocks only because no TRUSTED record supports that identity
(quality/canonical_subject_grounding.py: "no trusted evidence supports the
canonical physical subject identity" is exactly the branch that fires when
`_trusted_grounding_evidence` is absent).

Root cause: this is a coverage gap, not a missing/weak identity. An FAA-backed
(De Havilland Comet lessons-learned), already-regression-tested trusted record
for exactly this subject -- "modern aircraft passenger window with
rounded/oval corners" -- already exists in
quality/candidate_pool_grounding_records.py::CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS
(covered by quality/run_33929837490_rounded_window_claims_regression_test.py),
but ci_prewriter_grounding_resupply_hotfix.py's pre-Writer resupply call --
the one exercised by a real workflow_dispatch fixed topic -- only ever
consulted quality/canonical_subject_grounding_supply.py::
PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS, which never had an aircraft-window
entry. quality/candidate_pool_handoff.py already safely reads BOTH registries
together via quality/grounding_aware_candidate_supply.py::
all_trusted_candidate_records() -- this fix reuses that exact existing
combinator in ci_prewriter_grounding_resupply_hotfix.py too, instead of adding
a second, duplicate trusted record. No identity, threshold, confidence, or
matching-logic change; no new API call, retry, or budget change.

An earlier attempt at this fix added a *new* aircraft-window record directly to
PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS (reusing the same evidence).  That
approach regressed quality/candidate_pool_handoff_regression_test.py TEST A:
once both registries are combined by all_trusted_candidate_records() (as
candidate_pool_handoff.py already does), two records with the same
canonical_subject both matched the same candidate, and
supply_trusted_subject_grounding()'s own competing-match fail-close rule
(`len(matches) != 1`) correctly refused to pick between them -- even though
both records agreed on the canonical subject. Reusing the existing record
instead of duplicating it avoids that failure mode entirely, which is why this
is the fix actually shipped here.
"""

from __future__ import annotations

import subprocess
import sys
from copy import deepcopy


def _apply_relevant_hotfixes():
    """Gate + Supply hotfixes -- Supply chain-imports flap/static-wick/
    prewriter-resupply, matching real production's main.yml chain exactly for
    everything this fix touches."""
    for script in (
        "ci_canonical_subject_grounding_hotfix.py",
        "ci_canonical_subject_grounding_supply_hotfix.py",
    ):
        subprocess.run([sys.executable, script], check=True)


def _candidate(topic, core_question, hook, reveal, payoff, *, angle="", self_reported=True):
    candidate = {
        "topic": topic,
        "angle": angle,
        "core_question": core_question,
        "micro_narrative": {
            "hook": hook,
            "core_question": core_question,
            "reveal": reveal,
            "payoff": payoff,
        },
    }
    if self_reported:
        # Mirrors the real Candidate model's own self-reported (untrusted)
        # fields, confirmed by Run 34573647770's actual log line.
        candidate.update(
            {
                "subject_kind": "physical_entity",
                "canonical_subject": "aircraft passenger window",
                "subject_identity_confidence": 0.85,
                "grounding_evidence": [],
            }
        )
    return candidate


def main():
    _apply_relevant_hotfixes()

    main_source = open("main.py", encoding="utf-8").read()
    assert main_source.count("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1") == 1
    assert "all_trusted_candidate_records" in main_source, (
        "fixed-topic pre-Writer resupply must consult the combined registry"
    )

    from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding
    from quality.canonical_subject_grounding_supply import (
        PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        supply_trusted_subject_grounding,
    )
    from quality.grounding_aware_candidate_supply import all_trusted_candidate_records

    combined = all_trusted_candidate_records()

    # No new identity record was added: PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS
    # itself is still exactly chevron + flap + wick (3), unchanged.
    assert len(PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS) == 3, (
        PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS
    )
    assert "modern aircraft passenger window with rounded/oval corners" not in [
        r["canonical_subject"] for r in PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS
    ], "fix must not duplicate the existing Candidate Pool window record"

    def check(name, candidate, *, expect_pass, expect_canonical=None):
        supplied = supply_trusted_subject_grounding(
            deepcopy(candidate), trusted_records=combined
        )
        result = evaluate_candidate_subject_grounding(supplied)
        status = result["status"]
        assert (status == "PASS") == expect_pass, (
            f"{name}: expected {'PASS' if expect_pass else 'BLOCK'}, got {status} "
            f"({result.get('reason')})"
        )
        if expect_pass and expect_canonical is not None:
            assert supplied.get("canonical_subject") == expect_canonical, supplied.get(
                "canonical_subject"
            )
        return supplied, result

    # RED -> GREEN: the exact Run 34573647770 counterexample (both real
    # attempt-1 and attempt-2 core_question phrasings, directly from the job log).
    check(
        "Run 34573647770 attempt-2 core_question (authority counterexample)",
        _candidate(
            "비행기 창문 모서리는 왜 둥글까",
            "비행기 창문 모서리가 둥글게 되어 있는 이유는 무엇일까?",
            "비행기 창문 모서리는 둥글게 생겼습니다.",
            "각진 모서리에는 응력이 집중됩니다.",
            "둥근 모서리는 응력 집중을 줄여줍니다.",
        ),
        expect_pass=True,
        expect_canonical="modern aircraft passenger window with rounded/oval corners",
    )
    check(
        "Run 34573647770 attempt-1 core_question phrasing",
        _candidate(
            "비행기 창문 모서리는 왜 둥글까",
            "비행기 창문 모서리가 둥글게 설계된 이유는 무엇일까?",
            "비행기 창문 모서리는 둥글게 설계되어 있습니다.",
            "각진 모서리에는 응력이 집중됩니다.",
            "둥근 모서리는 응력 집중을 줄여줍니다.",
        ),
        expect_pass=True,
        expect_canonical="modern aircraft passenger window with rounded/oval corners",
    )

    # Negative controls: must NOT cross-match unrelated/adjacent physical subjects.
    check(
        "negative: building window",
        _candidate(
            "건물 창문 모서리는 왜 둥글까",
            "건물 창문 모서리가 둥글게 되어 있는 이유는 무엇일까?",
            "건물 창문 모서리는 둥글게 생겼습니다.",
            "각진 모서리에는 응력이 집중됩니다.",
            "둥근 모서리는 안전합니다.",
        ),
        expect_pass=False,
    )
    check(
        "negative: car window",
        _candidate(
            "자동차 창문 모서리는 왜 둥글까",
            "자동차 창문 모서리가 둥글게 되어 있는 이유는 무엇일까?",
            "자동차 창문 모서리는 둥글게 생겼습니다.",
            "각진 모서리에는 응력이 집중됩니다.",
            "둥근 모서리는 안전합니다.",
        ),
        expect_pass=False,
    )
    check(
        "negative: generic window, no aircraft mention",
        _candidate(
            "창문은 왜 사각형일까",
            "창문은 왜 사각형 모양일까?",
            "창문은 사각형으로 생겼습니다.",
            "사각형은 만들기 쉽습니다.",
            "그래서 사각형이 흔합니다.",
        ),
        expect_pass=False,
    )
    check(
        "negative: aircraft cockpit windshield (not the cabin window)",
        _candidate(
            "비행기 조종석 앞유리는 왜 기울어져 있을까",
            "비행기 조종석 앞유리가 기울어진 이유는 무엇일까?",
            "비행기 조종석 앞유리는 기울어져 있습니다.",
            "기울어지면 빛 반사가 줄어듭니다.",
            "조종사 시야가 좋아집니다.",
        ),
        expect_pass=False,
    )
    check(
        "negative: aircraft window topic without corner/round framing",
        _candidate(
            "비행기 창문은 왜 작을까",
            "비행기 창문은 왜 작게 만들어질까?",
            "비행기 창문은 작게 생겼습니다.",
            "작은 창문은 동체 강도를 유지합니다.",
            "그래서 안전합니다.",
        ),
        expect_pass=False,
    )

    # Regression: existing PRODUCTION-registry subjects still resolve alone --
    # no competing-match fail-close introduced by combining the two registries.
    check(
        "regression: static wick (Canary #1 topic, own PRODUCTION record, no Pool wick record exists)",
        _candidate(
            "비행기 날개 끝의 작은 막대는 왜 달려 있을까",
            "비행기 날개 끝의 작은 막대는 어떤 역할을 할까?",
            "비행기 날개 끝의 작은 막대는 달려 있습니다.",
            "정전기를 방전합니다.",
            "무선 잡음이 줄어듭니다.",
            self_reported=False,
        )
        | {
            "subject_kind": "physical_entity",
            "canonical_subject": "aircraft static discharge wick",
            "subject_identity_confidence": 0.9,
            "grounding_evidence": [],
        },
        expect_pass=True,
        expect_canonical="aircraft static discharge wick",
    )
    check(
        "regression: chevron (own PRODUCTION record)",
        {
            "topic": "비행기 엔진 뒤는 왜 톱니처럼 생겼을까",
            "angle": "",
            "core_question": "비행기 엔진 뒤 톱니 모양은 어떤 역할을 할까?",
            "micro_narrative": {
                "hook": "비행기 엔진 뒤는 톱니처럼 생긴 가장자리가 있습니다.",
                "core_question": "비행기 엔진 뒤 톱니 모양은 어떤 역할을 할까?",
                "reveal": "배기 흐름과 주변 흐름이 섞이는 방식을 바꿉니다.",
                "payoff": "제트 소음이 줄어듭니다.",
            },
            "subject_kind": "physical_entity",
            "canonical_subject": "jet engine chevrons",
            "subject_identity_confidence": 0.9,
            "grounding_evidence": [],
        },
        expect_pass=True,
        expect_canonical="jet engine nacelle/nozzle chevrons",
    )
    check(
        "regression: flap (Canary #3 topic, own PRODUCTION record resolves alone)",
        _candidate(
            "비행기 날개의 플랩은 왜 펼쳐질까",
            "비행기 날개 뒤쪽 플랩은 왜 펼쳐질까?",
            "비행기 날개 뒤쪽 플랩은 펼쳐집니다.",
            "양력이 늘어납니다.",
            "착륙 속도가 낮아집니다.",
            self_reported=False,
        )
        | {
            "subject_kind": "physical_entity",
            "canonical_subject": "aircraft trailing-edge flap",
            "subject_identity_confidence": 0.9,
            "grounding_evidence": [],
        },
        expect_pass=True,
        expect_canonical="aircraft trailing-edge flap",
    )
    check(
        (
            "regression: flap with richer landing-approach phrasing (would also satisfy "
            "the Candidate Pool's own flap wording) still resolves to exactly one "
            "canonical -- no competing-match fail-close from combining registries"
        ),
        _candidate(
            "비행기 날개의 플랩은 왜 펼쳐질까",
            "착륙 접근 중인 비행기 날개 뒤쪽 플랩은 왜 펼쳐질까?",
            "비행기 날개 뒤쪽 플랩은 펼쳐집니다.",
            "양력이 늘어납니다.",
            "착륙 속도가 낮아집니다.",
            self_reported=False,
        )
        | {
            "subject_kind": "physical_entity",
            "canonical_subject": "aircraft trailing-edge flap",
            "subject_identity_confidence": 0.9,
            "grounding_evidence": [],
        },
        expect_pass=True,
        expect_canonical="aircraft trailing-edge flap",
    )

    # Safety invariants: no budget/retry/call surface touched by this fix.
    hotfix_source = open("ci_prewriter_grounding_resupply_hotfix.py", encoding="utf-8").read()
    for forbidden in (
        "openai.chat",
        "authorize_call(",
        "MAX_TOPIC_REGENERATIONS",
        "V3_MAX_API_CALLS",
        "V3_MAX_COST_USD",
    ):
        assert forbidden not in hotfix_source, forbidden

    print(
        "RUN 34573647770 AIRCRAFT WINDOW GROUNDING REGRESSION: PASS "
        "(coverage gap closed via existing combinator, no new record, no "
        "cross-domain false positives, no competing-match regression)"
    )


if __name__ == "__main__":
    main()

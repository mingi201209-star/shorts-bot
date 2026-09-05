"""Repo-owned trusted identity records used by Candidate Pool Handoff.

These are complete feature+context evidence records, not keyword mappings.
They are consumed only by the existing deterministic canonical grounding supplier.
"""

from __future__ import annotations

from typing import Any, Dict


FAA_COMET_LESSONS_SOURCE = (
    "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"
)


CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS: tuple[Dict[str, Any], ...] = (
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
        "identity_confidence": 0.97,
        "feature_descriptions": [
            "round or oval shaped airplane window with curved edges",
            "비행기 창문 가장자리의 둥근 모서리",
            "비행기 창문은 모서리가 둥글게 디자인",
        ],
        "context_descriptions": [
            "passenger window opening in a modern transport airplane fuselage",
            "현대 여객기 동체의 승객용 창문",
            "비행기 창문",
        ],
        "source": FAA_COMET_LESSONS_SOURCE,
        "detail": (
            "FAA De Havilland Comet lessons learned states that testing found high "
            "stress concentrations at the Comet window corners specifically because "
            "of the squarish window/window-frame shape; modern airplane windows are "
            "round or oval so stress flows around curved edges with minimal build-up; "
            "and the investigated high stress concentrations fatigued material around "
            "the window corners and could quickly lead to fuselage rupture."
        ),
        "supported_claims": [
            {
                "claim_id": "squarish_window_stress_concentration",
                "claim_type": "constraint",
                "evidence_summary": (
                    "초기 Comet의 각진 창문과 창틀은 창문 모서리에 특히 높은 응력 집중을 "
                    "만들었습니다."
                ),
                "source": FAA_COMET_LESSONS_SOURCE,
                "detail": (
                    "FAA: testing found high stress concentrations at the window corners; "
                    "the concentrations were high specifically because of the squarish "
                    "shape of the windows and window frames."
                ),
                "allowed_paraphrase_scope": [
                    "각진 창문 모서리에는 높은 응력이 집중됐습니다.",
                    "초기 Comet의 각진 창문 형태는 모서리에 큰 응력 집중을 만들었습니다.",
                    "squarish Comet windows created high stress concentrations at the corners",
                ],
            },
            {
                "claim_id": "rounded_window_stress_distribution",
                "claim_type": "mechanism_change",
                "evidence_summary": (
                    "현대 항공기의 둥근·타원형 창문에서는 응력이 곡선 가장자리를 따라 "
                    "흐르며 모서리에 쌓이는 응력이 최소화됩니다."
                ),
                "source": FAA_COMET_LESSONS_SOURCE,
                "detail": (
                    "FAA: modern airplane windows are round/oval; with modern windows, "
                    "stress flows freely around the curved edges with minimal build up."
                ),
                "allowed_paraphrase_scope": [
                    "둥근 모서리에서는 응력이 곡선을 따라 흘러 한 지점에 쌓이는 것을 줄입니다.",
                    "현대의 둥근·타원형 창문은 곡선 가장자리로 응력이 흐르게 합니다.",
                    "modern round or oval window edges let stress flow around the curve with minimal build-up",
                ],
            },
            {
                "claim_id": "squarish_window_fatigue_rupture",
                "claim_type": "result",
                "evidence_summary": (
                    "Comet의 각진 창문에서 생긴 높은 응력 집중은 창문 모서리 재료를 피로하게 "
                    "했고 동체 파열로 빠르게 이어질 수 있었습니다."
                ),
                "source": FAA_COMET_LESSONS_SOURCE,
                "detail": (
                    "FAA: investigative testing and Elba wreckage examination found that "
                    "the squarish windows created much-higher-than-anticipated stress "
                    "concentrations; those concentrations fatigued material around the "
                    "window corners and would quickly lead to rupture of the fuselage."
                ),
                "allowed_paraphrase_scope": [
                    "각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 이어질 수 있었습니다.",
                    "Comet에서는 창문 모서리의 높은 응력이 재료를 피로하게 하고 동체 파열로 이어졌습니다.",
                    "the high stress concentrations at the squarish window corners fatigued material and could lead to fuselage rupture",
                ],
            },
        ],
    },
)

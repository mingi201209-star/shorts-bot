"""Repo-owned trusted identity records used by Candidate Pool Handoff.

These are complete feature+context evidence records, not keyword mappings.
They are consumed only by the existing deterministic canonical grounding supplier.
"""

from __future__ import annotations

from typing import Any, Dict


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
        "source": (
            "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"
        ),
        "detail": (
            "FAA De Havilland Comet lessons learned identifies the squarish corners "
            "of early airplane windows as high stress-concentration locations and "
            "states that modern airplane windows have round or oval shapes so stress "
            "flows around the curved edges with minimal build-up."
        ),
        "supported_claims": [
            {
                "claim_id": "rounded_window_stress_distribution",
                "claim_type": "mechanism_change",
                "evidence_summary": (
                    "둥근·타원형 창문 가장자리는 하중으로 생기는 응력이 곡선을 따라 "
                    "흐르도록 해 모서리 한 지점에 응력이 집중되는 것을 줄입니다."
                ),
                "allowed_paraphrase_scope": [
                    "둥근 모서리는 응력이 한 지점에 집중되는 것을 줄입니다.",
                    "곡선 가장자리를 따라 응력이 더 고르게 흐릅니다.",
                    "round or oval window edges reduce stress concentration at corners",
                ],
            },
        ],
    },
)

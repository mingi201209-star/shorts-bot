"""Repo-owned trusted identity records used by Candidate Pool Handoff.

These are complete feature+context evidence records, not keyword mappings.
They are consumed only by the existing deterministic canonical grounding supplier.
"""

from __future__ import annotations

from typing import Any, Dict


FAA_COMET_LESSONS_SOURCE = (
    "https://www.faa.gov/lessons_learned/transport_airplane/accidents/G-ALYV"
)
FAA_PILOT_HANDBOOK_SOURCE = (
    "https://www.faa.gov/sites/faa.gov/files/pilot_handbook_1.pdf"
)
NASA_FLAPS_SOURCE = (
    "https://www.grc.nasa.gov/www/k-12/VirtualAero/BottleRocket/airplane/aflap.html"
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
                "evidence_summary": "초기 Comet의 각진 창문과 창틀은 창문 모서리에 특히 높은 응력 집중을 만들었습니다.",
                "source": FAA_COMET_LESSONS_SOURCE,
                "detail": "FAA: testing found high stress concentrations at the window corners specifically because of the squarish shape.",
                "allowed_paraphrase_scope": ["각진 창문 모서리에는 높은 응력이 집중됐습니다."],
            },
            {
                "claim_id": "rounded_window_stress_distribution",
                "claim_type": "mechanism_change",
                "evidence_summary": "현대 항공기의 둥근·타원형 창문에서는 응력이 곡선 가장자리를 따라 흐르며 모서리에 쌓이는 응력이 최소화됩니다.",
                "source": FAA_COMET_LESSONS_SOURCE,
                "detail": "FAA: modern airplane windows are round/oval and stress flows around curved edges with minimal build up.",
                "allowed_paraphrase_scope": ["둥근 모서리에서는 응력이 곡선을 따라 흘러 한 지점에 쌓이는 것을 줄입니다."],
            },
            {
                "claim_id": "squarish_window_fatigue_rupture",
                "claim_type": "result",
                "evidence_summary": "Comet의 각진 창문에서 생긴 높은 응력 집중은 창문 모서리 재료를 피로하게 했고 동체 파열로 빠르게 이어질 수 있었습니다.",
                "source": FAA_COMET_LESSONS_SOURCE,
                "detail": "FAA: the stress concentrations fatigued material around the window corners and could quickly lead to fuselage rupture.",
                "allowed_paraphrase_scope": ["각진 창문 모서리의 응력 집중은 재료 피로를 일으켜 동체 파열로 이어질 수 있었습니다."],
            },
        ],
    },
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft trailing-edge wing flaps deployed for landing",
        "identity_confidence": 0.97,
        "feature_descriptions": [
            "trailing-edge wing flaps extended downward or aft",
            "비행기 날개 뒤쪽 플랩이 아래쪽 또는 뒤쪽으로 펼쳐진 모습",
            "착륙할 때 비행기 날개 뒤쪽이 펼쳐지는 플랩",
        ],
        "context_descriptions": [
            "aircraft wing during approach or landing",
            "착륙 접근 중인 비행기 날개",
            "비행기가 착륙할 때 날개 뒤쪽",
        ],
        "source": FAA_PILOT_HANDBOOK_SOURCE,
        "detail": (
            "FAA describes flaps as trailing-edge high-lift devices that increase lift and drag, "
            "while NASA explains that moving/pivoting flaps changes wing area and effective camber "
            "to increase lift and that the flap's projected area increases drag, helping an airplane slow for landing."
        ),
        "supported_claims": [
            {
                "claim_id": "landing_flap_low_speed_need",
                "claim_type": "mechanism_input",
                "evidence_summary": "이착륙 때는 비행 속도가 상대적으로 낮아서 날개가 필요한 양력을 유지하도록 고양력 장치를 사용합니다.",
                "source": NASA_FLAPS_SOURCE,
                "detail": "NASA: during takeoff and landing aircraft velocity is relatively low, so designers increase wing area and change airfoil shape with moving wing surfaces.",
                "allowed_paraphrase_scope": [
                    "착륙할 때는 속도가 낮아 필요한 양력을 유지하기 위해 플랩 같은 고양력 장치를 사용합니다.",
                    "during landing the airplane is relatively slow, so high-lift devices help maintain lift",
                ],
            },
            {
                "claim_id": "flap_camber_lift_increase",
                "claim_type": "mechanism_change",
                "evidence_summary": "플랩을 내리면 날개의 유효 캠버가 커지고 같은 받음각에서 양력 계수가 증가합니다.",
                "source": FAA_PILOT_HANDBOOK_SOURCE,
                "detail": "FAA: a plain flap increases airfoil camber, resulting in a significant increase in coefficient of lift at a given angle of attack.",
                "allowed_paraphrase_scope": [
                    "플랩을 펼치면 날개의 굽음이 커져 같은 조건에서 더 큰 양력을 만들 수 있습니다.",
                    "flap deployment increases effective camber and lift coefficient",
                ],
            },
            {
                "claim_id": "flap_drag_increase",
                "claim_type": "mechanism_effect",
                "evidence_summary": "플랩을 펼치면 양력뿐 아니라 항력도 증가하며, 큰 플랩 전개에서는 항력 증가가 특히 커집니다.",
                "source": FAA_PILOT_HANDBOOK_SOURCE,
                "detail": "FAA: flaps increase both lift and induced drag; as flaps are extended, drag increases at a greater rate than lift.",
                "allowed_paraphrase_scope": [
                    "플랩을 내리면 항력도 함께 커집니다.",
                    "extending flaps increases drag as well as lift",
                ],
            },
            {
                "claim_id": "flap_low_landing_speed",
                "claim_type": "primary_result",
                "evidence_summary": "플랩은 순항 때는 접어 두고 필요할 때 펼쳐 높은 순항 속도와 낮은 착륙 속도 사이의 절충을 가능하게 합니다.",
                "source": FAA_PILOT_HANDBOOK_SOURCE,
                "detail": "FAA: flaps allow a compromise between high cruising speed and low landing speed because they can be extended when needed and retracted when not needed.",
                "allowed_paraphrase_scope": [
                    "필요할 때 플랩을 펼치면 더 낮은 착륙 속도를 사용할 수 있습니다.",
                    "flaps enable lower landing speeds while remaining retractable for cruise",
                ],
            },
        ],
    },
)

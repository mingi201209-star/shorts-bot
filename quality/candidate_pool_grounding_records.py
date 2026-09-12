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
FAA_AIM_PSTATIC_SOURCE = (
    "https://www.faa.gov/air_traffic/publications/atpubs/aim/aim0705.html"
)
FAA_PHAK_CH8_SOURCE = (
    "https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/phak/10_phak_ch8.pdf"
)
NASA_WINGLETS_SOURCE = (
    "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/winglets/"
)


CANDIDATE_POOL_TRUSTED_SUBJECT_IDENTITY_RECORDS: tuple[Dict[str, Any], ...] = (
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "modern aircraft passenger window with rounded/oval corners",
        "identity_confidence": 0.97,
        "visual_discriminators": ["window", "rounded", "oval", "curved"],
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
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft static discharger (static wick)",
        "identity_confidence": 0.99,
        "seed_priority": 100,
        "feature_descriptions": [
            "thin static discharger rods or wicks projecting from aircraft trailing edges",
            "비행기 날개나 꼬리 뒤 가장자리에 달린 가느다란 정전기 방전기",
            "날개 뒤쪽으로 튀어나온 가느다란 스태틱 윅",
        ],
        "context_descriptions": [
            "aircraft wing or tail trailing edge in flight",
            "비행기 날개 또는 꼬리의 뒤쪽 가장자리",
            "항공기 후연에 설치된 방전기",
        ],
        "source": FAA_AIM_PSTATIC_SOURCE,
        "detail": (
            "FAA AIM explains that precipitation-static charge can interfere with avionics and that "
            "static dischargers use fine metal points, carbon-coated rods, or carbon wicks to provide "
            "an easier path for accumulated negative charge to discharge into the airstream instead "
            "of building to a larger discharge from aircraft trailing edges."
        ),
        "supported_claims": [
            {
                "claim_id": "pstatic_charge_accumulation",
                "claim_type": "mechanism_input",
                "evidence_summary": "비행 중 항공기 표면에 정전기 전하가 쌓일 수 있습니다.",
                "source": FAA_AIM_PSTATIC_SOURCE,
                "detail": "FAA AIM section on precipitation static describes accumulated charge on the airframe.",
                "allowed_paraphrase_scope": ["비행 중 기체에는 정전기 전하가 축적될 수 있습니다."],
            },
            {
                "claim_id": "static_discharger_path",
                "claim_type": "mechanism_change",
                "evidence_summary": "스태틱 윅은 쌓인 전하가 공기 중으로 빠져나가기 쉬운 방전 경로를 만듭니다.",
                "source": FAA_AIM_PSTATIC_SOURCE,
                "detail": "FAA AIM: static dischargers create a relatively easy path for discharging negative charges using fine points, rods, or carbon wicks.",
                "allowed_paraphrase_scope": ["가느다란 방전기는 전하가 공기 중으로 빠져나가기 쉬운 길을 만듭니다."],
            },
            {
                "claim_id": "static_avionics_interference",
                "claim_type": "primary_result",
                "evidence_summary": "이 방전은 큰 정전기 방전이 항공전자 장비에 간섭하는 것을 줄이는 데 목적이 있습니다.",
                "source": FAA_AIM_PSTATIC_SOURCE,
                "detail": "FAA AIM links uncontrolled precipitation-static discharge to radio/avionics interference and explains static dischargers reduce static noise.",
                "allowed_paraphrase_scope": ["스태틱 윅은 정전기 때문에 무전·항공전자 장비에 생기는 간섭을 줄입니다."],
            },
        ],
        "seed_candidate": {
            "topic": "비행기 날개 뒤의 가느다란 스태틱 윅",
            "angle": "작은 막대가 공기역학 장치가 아니라 정전기 방전 경로라는 점",
            "core_question": "왜 비행기 날개와 꼬리 뒤쪽에 가느다란 방전기를 달아둘까?",
            "micro_narrative": {
                "hook": "비행기 날개 뒤의 가느다란 막대는 정전기를 빼내는 방전기입니다.",
                "core_question": "왜 굳이 날개와 꼬리의 뒤쪽 가장자리에 이런 장치를 달아둘까요?",
                "reveal": "스태틱 윅은 기체에 쌓인 전하가 큰 방전으로 튀기 전에 공기 중으로 빠져나가기 쉬운 길을 만듭니다.",
                "payoff": "목적은 비행 제어가 아니라 정전기가 무전과 항공전자 장비에 만드는 간섭을 줄이는 것입니다."
            },
            "fact_check_focus": [
                "정전기 방전기가 전하의 쉬운 방전 경로를 만든다는 점",
                "정전기 방전이 항공전자 간섭을 줄이는 목적"
            ],
            "visual_proof": ["비행기 날개 또는 꼬리 후연에 튀어나온 가느다란 스태틱 윅"],
            "selection_reason": "눈에 잘 보이지만 역할을 오해하기 쉬운 작은 구조를 실제 FAA 근거로 설명할 수 있습니다.",
            "specific_observation": "비행기 날개나 꼬리 뒤 가장자리에 가느다란 스태틱 윅이 튀어나와 있습니다.",
            "constraint": "기체에 쌓인 정전기가 큰 방전으로 항공전자 장비에 간섭하지 않도록 해야 합니다.",
            "counterintuitive_result": "이 작은 막대의 핵심 역할은 공기역학이 아니라 정전기 방전입니다.",
            "tradeoff": "",
            "concrete_condition": "비행 중 항공기 표면에 정전기 전하가 축적될 때 작동하는 수동 방전 경로입니다."
        },
    },
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft wing spoilers",
        "identity_confidence": 0.98,
        "seed_priority": 95,
        "feature_descriptions": [
            "spoiler panels raised from the upper surface of an aircraft wing",
            "착륙 직후 비행기 날개 윗면에서 위로 솟아오르는 스포일러 패널",
            "비행기 날개 위에서 올라오는 판 모양 스포일러",
        ],
        "context_descriptions": [
            "aircraft wing during descent or immediately after landing",
            "착륙하거나 하강하는 비행기의 날개 윗면",
            "착륙 직후 활주 중인 항공기 날개",
        ],
        "source": FAA_PILOT_HANDBOOK_SOURCE,
        "detail": (
            "FAA Pilot's Handbook explains that spoilers disturb smooth airflow to reduce lift and "
            "increase drag; when deployed on both wings after landing they destroy lift, transfer "
            "weight to the wheels, and improve braking effectiveness."
        ),
        "supported_claims": [
            {
                "claim_id": "spoiler_destroy_lift",
                "claim_type": "mechanism_change",
                "evidence_summary": "스포일러를 올리면 날개 위의 매끄러운 흐름을 깨뜨려 양력을 줄이고 항력을 늘립니다.",
                "source": FAA_PILOT_HANDBOOK_SOURCE,
                "detail": "FAA: spoilers are deployed from the wings to spoil smooth airflow, reducing lift and increasing drag.",
                "allowed_paraphrase_scope": ["날개 위 스포일러는 흐름을 깨뜨려 양력을 줄이고 항력을 늘립니다."],
            },
            {
                "claim_id": "spoiler_weight_to_wheels",
                "claim_type": "mechanism_effect",
                "evidence_summary": "착륙 뒤 양력을 없애면 항공기 무게가 바퀴에 더 실립니다.",
                "source": FAA_PILOT_HANDBOOK_SOURCE,
                "detail": "FAA: by destroying lift after landing, spoilers transfer weight to the wheels.",
                "allowed_paraphrase_scope": ["착륙 후 양력을 줄이면 무게가 바퀴에 더 실립니다."],
            },
            {
                "claim_id": "spoiler_braking_effectiveness",
                "claim_type": "primary_result",
                "evidence_summary": "바퀴에 하중이 더 실리면서 제동 효과가 좋아지고 지상 활주 거리를 줄이는 데 도움을 줍니다.",
                "source": FAA_PILOT_HANDBOOK_SOURCE,
                "detail": "FAA: spoilers help reduce ground roll after landing and improve braking effectiveness by transferring weight to the wheels.",
                "allowed_paraphrase_scope": ["스포일러는 바퀴 제동이 더 잘 먹도록 도와 착륙 후 활주를 줄입니다."],
            },
        ],
        "seed_candidate": {
            "topic": "착륙 직후 날개 위로 솟는 스포일러",
            "angle": "착륙하자마자 일부러 양력을 망가뜨려 바퀴 제동을 돕는 설계",
            "core_question": "왜 비행기는 착륙 직후 날개의 양력을 일부러 없앨까?",
            "micro_narrative": {
                "hook": "착륙 직후 날개 위 판이 올라오면 비행기는 일부러 양력을 줄입니다.",
                "core_question": "비행을 위해 만든 양력을 왜 땅에 닿자마자 없애는 걸까요?",
                "reveal": "스포일러가 날개 위 흐름을 깨뜨리면 양력이 줄고 항력이 늘어 기체 무게가 바퀴에 더 실립니다.",
                "payoff": "바퀴가 활주로를 더 강하게 누르면서 제동 효과가 좋아져 착륙 뒤 멈추는 데 도움이 됩니다."
            },
            "fact_check_focus": [
                "스포일러가 양력을 줄이고 항력을 늘리는 기능",
                "착륙 후 바퀴 하중 증가가 제동 효과를 높이는 연결"
            ],
            "visual_proof": ["착륙 직후 비행기 날개 윗면에서 스포일러 패널이 올라오는 장면"],
            "selection_reason": "비행기의 핵심인 양력을 착륙 뒤 일부러 없앤다는 역설이 화면과 바로 맞물립니다.",
            "specific_observation": "착륙 직후 날개 윗면의 판 모양 스포일러가 위로 솟습니다.",
            "constraint": "착륙 뒤에는 남은 양력보다 바퀴에 충분한 하중을 싣는 것이 제동에 유리합니다.",
            "counterintuitive_result": "비행 중 필요했던 양력을 땅에 닿자마자 의도적으로 망가뜨립니다.",
            "tradeoff": "공중에서는 양력이 필요하지만 착륙 뒤에는 양력을 빠르게 줄여 바퀴 제동을 돕습니다.",
            "concrete_condition": "착륙 직후 지상 활주 구간에서 양쪽 날개 스포일러를 전개합니다."
        },
    },
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft pitot tube",
        "identity_confidence": 0.99,
        "seed_priority": 90,
        "feature_descriptions": [
            "forward-facing pitot tube or probe exposed to the airstream",
            "비행기 바깥쪽에서 앞을 향해 튀어나온 작은 피토관",
            "기체나 날개에 설치된 앞을 향한 피토 튜브",
        ],
        "context_descriptions": [
            "aircraft exterior pitot-static system used by the airspeed indicator",
            "비행기 외부의 피토-정압 계통",
            "대기 흐름을 받는 항공기 외부 압력 측정 위치",
        ],
        "source": FAA_PHAK_CH8_SOURCE,
        "detail": (
            "FAA Pilot's Handbook chapter 8 explains that the pitot tube senses total pressure and "
            "the airspeed indicator also receives static pressure; opposing static pressure cancels, "
            "leaving dynamic pressure for the airspeed indication."
        ),
        "supported_claims": [
            {
                "claim_id": "pitot_total_pressure",
                "claim_type": "mechanism_input",
                "evidence_summary": "피토관은 비행기가 공기 속을 움직일 때 받는 총압을 받아들입니다.",
                "source": FAA_PHAK_CH8_SOURCE,
                "detail": "FAA PHAK chapter 8: the pitot tube measures total combined pressure and transmits it to the ASI.",
                "allowed_paraphrase_scope": ["피토관은 앞쪽 흐름에서 총압을 받아들입니다."],
            },
            {
                "claim_id": "asi_static_cancellation",
                "claim_type": "mechanism_change",
                "evidence_summary": "속도계는 피토 총압과 별도로 들어온 정압을 비교해 공기 흐름에 해당하는 동압을 남깁니다.",
                "source": FAA_PHAK_CH8_SOURCE,
                "detail": "FAA PHAK chapter 8: static pressure is delivered to the opposite side of the ASI, canceling static pressure and leaving dynamic pressure.",
                "allowed_paraphrase_scope": ["속도계는 총압에서 정압 성분을 상쇄해 동압을 이용합니다."],
            },
            {
                "claim_id": "dynamic_pressure_airspeed",
                "claim_type": "primary_result",
                "evidence_summary": "동압이 변하면 속도계의 지시 속도도 그 변화에 따라 달라집니다.",
                "source": FAA_PHAK_CH8_SOURCE,
                "detail": "FAA PHAK chapter 8: when dynamic pressure changes, the ASI shows an increase or decrease accordingly.",
                "allowed_paraphrase_scope": ["동압 변화가 속도계의 지시 속도로 나타납니다."],
            },
        ],
        "seed_candidate": {
            "topic": "비행기 밖으로 튀어나온 작은 피토관",
            "angle": "속도를 직접 감지하는 센서처럼 보이지만 실제로는 압력 차이를 이용하는 구조",
            "core_question": "앞을 향한 작은 피토관으로 비행기의 속도를 어떻게 알 수 있을까?",
            "micro_narrative": {
                "hook": "비행기 바깥의 작은 피토관은 속도 숫자를 직접 재는 장치가 아니라 공기의 압력을 받아들입니다.",
                "core_question": "그 압력만으로 비행 속도를 어떻게 알아낼까요?",
                "reveal": "피토관의 총압과 기체의 정압을 속도계에서 비교하면 공기 흐름 때문에 생긴 동압이 남습니다.",
                "payoff": "속도계는 회전 센서가 아니라 이 압력 차이의 변화를 비행 속도로 표시합니다."
            },
            "fact_check_focus": [
                "피토관이 총압을 측정한다는 점",
                "속도계가 총압과 정압의 차이에서 동압을 이용한다는 점"
            ],
            "visual_proof": ["비행기 기체나 날개에 앞을 향해 튀어나온 작은 피토관"],
            "selection_reason": "익숙한 속도 표시가 작은 외부 튜브의 압력 차이에서 나온다는 구조를 화면으로 설명할 수 있습니다.",
            "specific_observation": "비행기 외부에 앞을 향한 작은 피토관이 공기 흐름을 직접 받습니다.",
            "constraint": "속도계는 공기 흐름으로 생기는 동압을 정압과 분리해 알아내야 합니다.",
            "counterintuitive_result": "비행 속도는 외부 튜브가 받은 총압과 정압의 차이에서 계산되는 동압으로 표시됩니다.",
            "tradeoff": "",
            "concrete_condition": "피토관이 막히지 않고 외부 흐름을 정상적으로 받을 때 속도계가 압력 정보를 사용합니다."
        },
    },
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft winglet",
        "identity_confidence": 0.99,
        "seed_priority": 80,
        "feature_descriptions": [
            "upturned or nearly vertical winglet at an aircraft wing tip",
            "비행기 날개 끝에서 위로 꺾여 올라간 윙렛",
            "날개 끝의 거의 수직인 작은 날개 모양 윙렛",
        ],
        "context_descriptions": [
            "wing tip of a modern airliner or transport aircraft",
            "현대 여객기나 수송기의 날개 끝",
            "비행 중인 항공기 주날개 끝부분",
        ],
        "source": NASA_WINGLETS_SOURCE,
        "detail": (
            "NASA Glenn explains that winglets are upturned wing tips developed to reduce the "
            "strength of wingtip vortices and thereby reduce induced drag; NASA flight tests found "
            "meaningful fuel-use reductions when winglets were properly integrated into the wing."
        ),
        "supported_claims": [
            {
                "claim_id": "wingtip_vortex_induced_drag",
                "claim_type": "mechanism_input",
                "evidence_summary": "양력을 만드는 유한한 날개 끝에서는 팁 와류가 생기며 이것이 유도항력과 연결됩니다.",
                "source": NASA_WINGLETS_SOURCE,
                "detail": "NASA Glenn: tip vortices strongly influence induced drag on a three-dimensional lifting wing.",
                "allowed_paraphrase_scope": ["날개 끝의 와류는 유도항력을 만드는 중요한 원인입니다."],
            },
            {
                "claim_id": "winglet_vortex_reduction",
                "claim_type": "mechanism_change",
                "evidence_summary": "윙렛은 날개 끝 와류의 세기를 줄여 날개 주변 흐름을 더 효율적으로 만듭니다.",
                "source": NASA_WINGLETS_SOURCE,
                "detail": "NASA Glenn: the idea behind a winglet is to reduce tip-vortex strength and make the wing flow more two-dimensional.",
                "allowed_paraphrase_scope": ["윙렛은 날개 끝 와류의 세기를 줄입니다."],
            },
            {
                "claim_id": "winglet_induced_drag_result",
                "claim_type": "primary_result",
                "evidence_summary": "팁 와류를 약하게 만들면 유도항력을 줄여 항공기 효율을 높일 수 있습니다.",
                "source": NASA_WINGLETS_SOURCE,
                "detail": "NASA Glenn: winglets are used on modern airliners to reduce induced drag; flight tests showed lower fuel use.",
                "allowed_paraphrase_scope": ["윙렛은 유도항력을 줄여 효율 향상에 도움을 줍니다."],
            },
        ],
        "seed_candidate": {
            "topic": "비행기 날개 끝에서 위로 꺾인 윙렛",
            "angle": "날개를 단순히 길게 늘리는 대신 끝의 흐름을 바꿔 유도항력을 줄이는 설계",
            "core_question": "왜 비행기 날개 끝은 옆으로만 길어지지 않고 위로 꺾여 있을까?",
            "micro_narrative": {
                "hook": "날개 끝에서 위로 꺾인 윙렛은 장식이 아니라 날개 끝 와류를 약하게 만드는 장치입니다.",
                "core_question": "날개 끝을 위로 세우는 것만으로 왜 항력이 줄어들까요?",
                "reveal": "윙렛이 날개 끝 주변의 흐름을 바꾸면 팁 와류의 세기가 줄고 그 와류와 연결된 유도항력도 줄어듭니다.",
                "payoff": "그래서 날개 끝의 작은 형상 변화가 순항 효율과 연료 사용에 영향을 줄 수 있습니다."
            },
            "fact_check_focus": [
                "윙렛이 팁 와류의 세기를 줄이는 목적",
                "팁 와류와 유도항력의 관계"
            ],
            "visual_proof": ["여객기 주날개 끝에서 위로 꺾여 올라간 윙렛"],
            "selection_reason": "눈에 잘 보이는 날개 끝 형상과 보이지 않는 와류·항력을 직접 연결할 수 있습니다.",
            "specific_observation": "현대 여객기 날개 끝에는 위로 꺾이거나 거의 수직으로 선 윙렛이 보입니다.",
            "constraint": "유한한 날개가 양력을 만들면 날개 끝 와류와 유도항력이 생깁니다.",
            "counterintuitive_result": "날개 끝을 위로 세운 작은 구조가 팁 와류를 약하게 해 유도항력을 줄일 수 있습니다.",
            "tradeoff": "윙렛은 전체 날개 설계와 함께 통합되어야 효과적으로 작동합니다.",
            "concrete_condition": "양력을 만드는 날개 끝에서 팁 와류가 생기는 비행 상태입니다."
        },
    },
)

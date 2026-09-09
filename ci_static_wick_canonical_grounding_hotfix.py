from pathlib import Path


PATH = Path("quality/canonical_subject_grounding_supply.py")
MARKER = "# FIXED_TOPIC_STATIC_WICK_CANONICAL_GROUNDING_V1"

RECORD = r'''

# FIXED_TOPIC_STATIC_WICK_CANONICAL_GROUNDING_V1
PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS = (
    *PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft static discharge wick",
        "identity_confidence": 0.98,
        "feature_descriptions": [
            "thin static discharge wick or rod mounted at an aircraft wing tip or trailing outboard wing surface",
            "aircraft static discharger wick mounted on a wing tip",
            "비행기 날개 끝에 달린 가느다란 작은 막대",
            "비행기 날개 끝의 작은 막대",
            "비행기 날개 끝이나 바깥쪽 뒤 가장자리에 달린 정전기 방전용 가느다란 막대",
        ],
        "context_descriptions": [
            "aircraft wing tip or trailing outboard wing surface",
            "wing tips and trailing edges of aircraft control surfaces",
            "비행기 날개 끝",
            "항공기 날개 끝 또는 바깥쪽 뒤 가장자리",
        ],
        "source": "https://www.faa.gov/sites/faa.gov/files/2022-06/amt_airframe_hb_vol_2.pdf",
        "detail": (
            "FAA Aviation Maintenance Technician Handbook—Airframe states that static dischargers "
            "are normally mounted on trailing edges of control surfaces, wing tips, and the vertical "
            "stabilizer, where they dissipate precipitation-static charge away from avionics antennas "
            "to reduce radio-frequency interference."
        ),
        "supported_claims": [
            {
                "claim_id": "static_wick_location_identity",
                "claim_type": "observable_identity",
                "evidence_summary": "정전기 방전기는 항공기 날개 끝과 조종면 뒤 가장자리 등에 장착됩니다.",
                "source": "https://www.faa.gov/sites/faa.gov/files/2022-06/amt_airframe_hb_vol_2.pdf",
                "detail": "FAA Aviation Maintenance Technician Handbook—Airframe, static dischargers section.",
                "allowed_paraphrase_scope": [
                    "가느다란 막대는 날개 끝에 장착되는 정전기 방전기입니다.",
                    "정전기 방전기는 날개 끝이나 뒤 가장자리에 달립니다.",
                    "static dischargers are mounted on wing tips and trailing edges",
                ],
            },
            {
                "claim_id": "static_charge_dissipation",
                "claim_type": "mechanism_change",
                "evidence_summary": "정전기 방전기는 비행 중 쌓인 정전기 전하가 공기 중으로 빠져나갈 수 있는 방전 지점을 제공합니다.",
                "source": "https://www.faa.gov/sites/faa.gov/files/2022-06/amt_airframe_hb_vol_2.pdf",
                "detail": "FAA handbook explains that static dischargers dissipate built-up static energy in flight.",
                "allowed_paraphrase_scope": [
                    "비행 중 쌓인 정전기를 공기 중으로 흘려보냅니다.",
                    "쌓인 정전기 전하를 안전한 지점에서 방전합니다.",
                    "static dischargers dissipate built-up static energy in flight",
                ],
            },
            {
                "claim_id": "radio_interference_reduction",
                "claim_type": "primary_result",
                "evidence_summary": "이 방전 위치는 항공전자 안테나와 떨어져 있어 정전기로 생기는 무선 주파수 간섭과 잡음을 줄이는 데 도움이 됩니다.",
                "source": "https://www.faa.gov/sites/faa.gov/files/2022-06/amt_airframe_hb_vol_2.pdf",
                "detail": "FAA handbook says static dischargers reduce precipitation-static radio interference by discharging at points away from avionics antennas.",
                "allowed_paraphrase_scope": [
                    "무전과 항공전자 장비에 생기는 정전기 잡음을 줄입니다.",
                    "정전기 방전을 안테나에서 떨어진 곳으로 유도해 무선 간섭을 줄입니다.",
                    "the discharge point helps reduce precipitation-static radio interference",
                ],
            },
        ],
    },
)
'''


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Fixed Topic Static Wick Canonical Grounding V1 already installed")
        return
    if "PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS" not in text:
        raise RuntimeError("canonical subject grounding records boundary missing")
    PATH.write_text(text.rstrip() + RECORD + "\n", encoding="utf-8")
    print("✅ Fixed Topic Static Wick Canonical Grounding V1 installed")


main()

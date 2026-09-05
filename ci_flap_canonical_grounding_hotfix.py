from pathlib import Path


PATH = Path("quality/canonical_subject_grounding_supply.py")
MARKER = "# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1"

RECORD = r'''

# FIXED_TOPIC_FLAP_CANONICAL_GROUNDING_V1
PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS = (
    *PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
    {
        "record_type": "trusted_subject_identity",
        "subject_kind": "physical_entity",
        "canonical_subject": "aircraft trailing-edge flap",
        "identity_confidence": 0.97,
        "feature_descriptions": [
            "flap attached to the trailing edge of an aircraft wing",
            "trailing-edge flap on an aircraft wing",
            "비행기 날개 뒤쪽 플랩",
            "비행기 날개의 플랩",
        ],
        "context_descriptions": [
            "aircraft wing high-lift device used for low-speed flight",
            "trailing edge of the wing on an aircraft",
            "비행기 날개 뒤쪽의 고양력 장치",
            "비행기 날개 뒤쪽",
        ],
        "source": "https://www.faa.gov/sites/faa.gov/files/pilots/pilot_handbook.pdf",
        "detail": (
            "FAA Pilot's Handbook of Aeronautical Knowledge identifies trailing-edge flaps "
            "as high-lift devices that increase lift and drag, and explains that extending "
            "them when needed permits low landing speed while retaining high cruise speed."
        ),
        "supported_claims": [
            {
                "claim_id": "flap_trailing_edge_identity",
                "claim_type": "observable_identity",
                "evidence_summary": "플랩은 항공기 날개 뒤쪽에 붙는 고양력 장치입니다.",
                "source": "https://www.faa.gov/sites/faa.gov/files/pilots/pilot_handbook.pdf",
                "detail": "FAA Pilot's Handbook of Aeronautical Knowledge, Flight Controls, flaps.",
                "allowed_paraphrase_scope": [
                    "플랩은 날개 뒤쪽에 있습니다.",
                    "플랩은 날개 뒤쪽의 고양력 장치입니다.",
                    "flaps are trailing-edge high-lift devices",
                ],
            },
            {
                "claim_id": "flap_camber_lift_drag",
                "claim_type": "mechanism_change",
                "evidence_summary": "플랩을 내리면 날개 캠버가 커지고 양력과 항력이 증가합니다.",
                "source": "https://www.faa.gov/sites/faa.gov/files/pilots/pilot_handbook.pdf",
                "detail": "FAA Pilot's Handbook of Aeronautical Knowledge, Flight Controls, plain flap description.",
                "allowed_paraphrase_scope": [
                    "플랩은 날개의 캠버를 바꿔 양력을 늘립니다.",
                    "플랩 전개는 양력과 항력을 함께 늘립니다.",
                    "flap deflection increases camber, lift, and drag",
                ],
            },
            {
                "claim_id": "flap_low_landing_speed_tradeoff",
                "claim_type": "operational_purpose",
                "evidence_summary": "플랩은 필요할 때 전개해 낮은 착륙 속도를 가능하게 하면서 순항 때는 접어 고속 순항 성능을 유지할 수 있게 합니다.",
                "source": "https://www.faa.gov/sites/faa.gov/files/pilots/pilot_handbook.pdf",
                "detail": "FAA Pilot's Handbook of Aeronautical Knowledge states that flaps permit a compromise between high cruising speed and low landing speed because they can be extended when needed and retracted when not needed.",
                "allowed_paraphrase_scope": [
                    "플랩은 착륙 때 낮은 속도로 비행할 수 있게 돕습니다.",
                    "필요할 때 플랩을 펼치면 낮은 착륙 속도를 사용할 수 있습니다.",
                    "flaps permit low landing speed while being retractable for high-speed cruise",
                ],
            },
        ],
    },
)
'''


def main():
    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("✅ Fixed Topic Flap Canonical Grounding V1 already installed")
        return

    if "PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS" not in text:
        raise RuntimeError("canonical subject grounding records boundary missing")

    PATH.write_text(text.rstrip() + RECORD + "\n", encoding="utf-8")
    print("✅ Fixed Topic Flap Canonical Grounding V1 installed")


main()

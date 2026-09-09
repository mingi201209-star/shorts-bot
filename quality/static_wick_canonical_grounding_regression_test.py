from pathlib import Path
import runpy


TOPIC = "비행기 날개 끝의 작은 막대는 왜 달려 있을까"


def main():
    supply_path = Path("quality/canonical_subject_grounding_supply.py")
    original = supply_path.read_text(encoding="utf-8")
    try:
        runpy.run_path("ci_static_wick_canonical_grounding_hotfix.py", run_name="__main__")
        namespace = runpy.run_path(str(supply_path))
        supply = namespace["supply_trusted_subject_grounding"]
        records = namespace["PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS"]

        candidate = {
            "topic": TOPIC,
            "core_question": "왜 비행기 날개 끝에 작은 막대가 달려 있을까?",
            "specific_observation": "비행기 날개 끝에 가느다란 작은 막대가 보인다.",
            # Model-authored guesses must not be authority.
            "canonical_subject": "winglet",
        }
        grounded = supply(candidate, trusted_records=records)
        assert grounded.get("canonical_subject") == "aircraft static discharge wick"
        assert grounded.get("subject_kind") == "physical_entity"
        assert float(grounded.get("subject_identity_confidence", 0.0)) >= 0.80
        assert grounded.get("_trusted_grounding_evidence")
        claims = grounded.get("_trusted_grounded_claims") or []
        assert {c.get("claim_id") for c in claims} >= {
            "static_wick_location_identity",
            "static_charge_dissipation",
            "radio_interference_reduction",
        }

        flap_candidate = {
            "topic": "비행기 날개 뒤쪽 플랩은 왜 내려갈까",
            "core_question": "착륙할 때 날개 뒤쪽 플랩을 왜 내릴까?",
            "specific_observation": "비행기 날개 뒤쪽의 넓은 플랩이 내려간다.",
        }
        flap_grounded = supply(flap_candidate, trusted_records=records)
        assert flap_grounded.get("canonical_subject") != "aircraft static discharge wick"

        unrelated = {
            "topic": "비행기 창문은 왜 둥글까",
            "core_question": "왜 비행기 창문 모서리는 둥글까?",
        }
        unrelated_grounded = supply(unrelated, trusted_records=records)
        assert unrelated_grounded.get("canonical_subject") != "aircraft static discharge wick"

        text = supply_path.read_text(encoding="utf-8")
        assert text.count("# FIXED_TOPIC_STATIC_WICK_CANONICAL_GROUNDING_V1") == 1
        runpy.run_path("ci_static_wick_canonical_grounding_hotfix.py", run_name="__main__")
        assert supply_path.read_text(encoding="utf-8") == text
        print("STATIC WICK CANONICAL GROUNDING REGRESSION: PASS")
    finally:
        supply_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    main()

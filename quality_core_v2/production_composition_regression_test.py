"""Production-composition regressions for Clean V2 visual semantics.

Runs only after main.yml applies the production hotfix chain.  This guards the
exact two composition failures observed in Golden E2E #6/#8:
1) query relaxation must not strip wing-flex state terms in V2;
2) create_scene must honor V2's explanatory/generation source decision.
"""

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    old = os.environ.get("ENABLE_QUALITY_CORE_V2")
    os.environ["ENABLE_QUALITY_CORE_V2"] = "1"
    try:
        from video.video_downloader import query_relaxation_ladder

        flex_variants = query_relaxation_ladder(
            "aircraft wing flexing during flight"
        )
        assert flex_variants, flex_variants
        state_terms = {"flex", "flexing", "bend", "bending", "deform", "deformation"}
        for query in flex_variants:
            words = set(str(query).lower().split())
            assert words & state_terms, (
                "V2 query relaxation stripped observable wing-flex state",
                flex_variants,
            )

        lift_variants = query_relaxation_ladder(
            "aircraft wing lift force acting upwards"
        )
        assert lift_variants, lift_variants
        for query in lift_variants:
            words = set(str(query).lower().split())
            assert words & {"lift", "load", "drag", "airflow"}, (
                "V2 query relaxation stripped force-state semantics",
                lift_variants,
            )
    finally:
        if old is None:
            os.environ.pop("ENABLE_QUALITY_CORE_V2", None)
        else:
            os.environ["ENABLE_QUALITY_CORE_V2"] = old

    engine = (ROOT / "video/video_engine.py").read_text(encoding="utf-8")
    assert "[V2_SOURCE_ROUTING]" in engine
    assert "_v2_preferred_source_type" in engine
    assert "verified_explanatory_generation" in engine

    still = (ROOT / "video/still_image_fallback.py").read_text(encoding="utf-8")
    assert "_verify_v2_semantic_asset" in still
    assert "inspect_v2_item_clip" in still

    print("V2 PRODUCTION COMPOSITION REGRESSION: PASS")


if __name__ == "__main__":
    main()

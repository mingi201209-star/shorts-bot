from __future__ import annotations

import importlib
import subprocess
import sys


PREREQUISITES = [
    "ci_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_visual_specificity_hotfix.py",
    "ci_query_semantic_integrity_hotfix.py",
    "ci_concrete_visual_evidence_hotfix.py",
    "ci_visible_evidence_provenance_hotfix.py",
    "ci_general_scene_visual_parity_hotfix.py",
    "ci_cross_process_video_dedupe_hotfix.py",
    "ci_visual_subject_anchor_contract_v1_hotfix.py",
    "ci_visual_subject_anchor_contract_v1_completion_hotfix.py",
    "ci_visual_subject_anchor_contract_v2_hotfix.py",
    "ci_visual_subject_anchor_fallback_inheritance_hotfix.py",
    "ci_visual_claim_semantic_inheritance_hotfix.py",
]

for script in PREREQUISITES:
    subprocess.run([sys.executable, script], check=True)

import video.video_downloader as vd
importlib.reload(vd)


def candidate(metadata: str, *, cid: int = 1):
    return {
        "id": cid,
        "source_id": cid,
        "provider": "pixabay",
        "metadata": metadata,
        "url": f"https://example.invalid/{cid}.mp4",
    }


def assert_semantics(query: str, metadata: str, expected: bool, label: str):
    contract = vd._set_visual_claim_semantic_contract(query)
    actual, missing = vd._candidate_supports_explanatory_contract(candidate(metadata), contract)
    assert actual is expected, f"{label}: expected={expected} actual={actual} missing={missing} contract={contract}"


# Run 33250343057: subject-correct generic airplane/engine must not satisfy flow_interface.
assert_semantics(
    "jet engine flow interface",
    "commercial aircraft jet engine detail close up",
    False,
    "A generic engine lacks flow/interface semantics",
)
assert_semantics(
    "jet engine flow interface",
    "jet engine exhaust airflow meeting boundary interface",
    True,
    "B evidence-backed flow/interface",
)

# Scene 4: generic jet-engine identity alone is insufficient; chevron mixing semantics are required.
assert_semantics(
    "jet engine chevron flow mixing",
    "aircraft jet engine nacelle chevron close up",
    False,
    "C component-only chevron lacks explanatory flow/mixing",
)
assert_semantics(
    "jet engine chevron flow mixing",
    "aircraft jet engine nacelle chevron exhaust airflow mixing",
    True,
    "D chevron plus grounded mixing evidence",
)

# Scene 5: generic aircraft/engine must not stand in for the grounded acoustic result.
assert_semantics(
    "jet engine noise reduction",
    "aircraft jet engine detail",
    False,
    "E generic aircraft lacks noise semantics",
)
assert_semantics(
    "jet engine noise reduction",
    "aircraft jet engine acoustic noise reduction",
    True,
    "F grounded acoustic result",
)

# G: fallback wording cannot replace the original Scene authority.
vd._set_visual_claim_semantic_contract("jet engine flow interface")
tier, mode = vd.general_scene_unknown_safe_tier(
    candidate("commercial aircraft jet engine detail", cid=15271),
    "airplane engine detail",
)
assert tier == 5 and mode == "MISSING_REQUIRED_EXPLANATORY_SEMANTICS", (tier, mode)

# Generic decorative suffixes are not explanatory semantics.
assert_semantics(
    "jet engine flow interface",
    "aircraft engine stage 1 detail closeup",
    False,
    "decorative stage/detail does not count",
)

# Subject/chroma false-positive guards from #252/#253 remain fail-closed.
for metadata in (
    "gas stove burner unreal engine",
    "clock cogwheel engineering mechanism",
    "aircraft jet engine green screen chroma key",
):
    vd._set_visual_claim_semantic_contract("jet engine chevron flow mixing")
    ok, _ = vd._candidate_supports_explanatory_contract(candidate(metadata), vd.get_current_visual_claim_semantic_contract())
    assert not ok, metadata

print("RUN 33250343057 VISUAL CLAIM SEMANTIC INHERITANCE REGRESSION: PASS")

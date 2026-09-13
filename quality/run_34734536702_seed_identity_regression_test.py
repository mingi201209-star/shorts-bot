"""Trusted spoiler identity must survive Winner copying and pre-Writer resupply."""
from __future__ import annotations

import ast
from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import sys


def composed_checks():
    import types
    # No external API client is needed for deterministic validation.
    sys.modules["openai"] = types.ModuleType("openai")
    os.environ["SHORTS_CANDIDATE_SCOPE"] = "aviation"
    from content.candidate_explorer import _LEGACY
    validate_explorer_output = _LEGACY.validate_explorer_output
    from content.growth_candidate_ranker import annotate_explorer_output
    from quality.canonical_subject_grounding import evaluate_candidate_subject_grounding
    from quality.canonical_subject_grounding_supply import (
        PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS,
        supply_trusted_subject_grounding,
    )
    from quality.grounding_aware_candidate_supply import (
        all_trusted_candidate_records, grounded_seed_candidate_pool,
    )

    # Execute the installed pre-Writer wrapper with only its downstream call
    # stubbed: no Writer/API calls, and the real grounding gate still runs.
    source = Path("main.py").read_text(encoding="utf-8")
    tree = ast.parse(source[source.index("# PREWRITER_TRUSTED_GROUNDING_RESUPPLY_V1"):])
    nodes = []
    for node in tree.body:
        nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "generate_script":
            break
    def gate(topic_info, candidate):
        assert evaluate_candidate_subject_grounding(candidate)["status"] == "PASS"
        return candidate
    namespace = {"generate_script": gate}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "prewriter", "exec"), namespace)

    topics = []
    records = [r for r in all_trusted_candidate_records() if r.get("seed_candidate")]
    for _ in records:
        pool = grounded_seed_candidate_pool(recent_topics=topics, rejected_topics=[], max_candidates=1)
        topic = pool["candidates"][0]["topic"]
        topics.append(topic)
        selected = validate_explorer_output(pool)
        assert selected["status"] == "SELECTED", selected
        winner = selected["winner"]
        original = deepcopy(winner)
        selected = annotate_explorer_output(selected, history=[])
        winner = selected["winner"]
        if topic == "착륙 직후 날개 위로 솟는 스포일러":
            assert winner["canonical_subject"] == "aircraft wing spoilers"
            # Reproduce the old broad resolver's specific competing flap match.
            untrusted = deepcopy(winner)
            untrusted.pop("_trusted_grounding_evidence", None)
            drift = supply_trusted_subject_grounding(
                untrusted, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS)
            assert drift["canonical_subject"] == "aircraft trailing-edge flap", drift
            for invalid in ("mismatched", "low_confidence", "missing_source"):
                candidate = deepcopy(winner)
                if invalid == "mismatched":
                    candidate["_trusted_grounding_evidence"][0]["supports_subject"] = "unrelated part"
                elif invalid == "low_confidence":
                    candidate["subject_identity_confidence"] = 0.1
                else:
                    candidate["_trusted_grounding_evidence"][0]["source"] = ""
                supplied = supply_trusted_subject_grounding(
                    candidate, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS)
                assert supplied["canonical_subject"] == "aircraft trailing-edge flap", invalid
        winner = namespace["generate_script"]({}, winner)
        for field in ("canonical_subject", "subject_identity_confidence",
                      "grounding_evidence", "_trusted_grounding_evidence", "_trusted_grounded_claims"):
            assert winner.get(field) == original.get(field), (topic, field, winner.get(field))
        # Repeated supply, including the narrower Explorer registry, is stable.
        supplied = supply_trusted_subject_grounding(
            winner, trusted_records=PRODUCTION_TRUSTED_SUBJECT_IDENTITY_RECORDS)
        assert supplied == winner, topic
    assert "착륙 직후 날개 위로 솟는 스포일러" in topics
    print(f"Seed -> selection -> shadow Winner -> pre-Writer identity: PASS ({len(topics)} seeds)")


def main():
    from quality.run_34689059742_recovery_canonical_grounding_regression_test import _prepare_repo
    repo = _prepare_repo()
    try:
        subprocess.run([sys.executable, "-m", "quality.run_34734536702_seed_identity_regression_test", "--composed"], cwd=repo, check=True)
    finally:
        shutil.rmtree(repo.parent)


if __name__ == "__main__":
    composed_checks() if "--composed" in sys.argv else main()

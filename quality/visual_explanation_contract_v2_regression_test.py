from __future__ import annotations

import unittest

from quality.visual_contrast_evaluator import EvaluationStatus, RelationResult, evaluate_contrast
from quality.visual_explanation_contract_v2 import semantic_validate
from quality.visual_explanation_shadow import ShadowDecision, aggregate_shadow_decision
from quality.visual_state_evidence import EvidenceState, resolve_claim_evidence
from quality.visual_state_observation import RawVisionObservation, normalize_vision_observation
from quality.visual_state_registry import SubjectStateRegistry


def scene5_contract(presentation="SPLIT_SCREEN"):
    if presentation == "SPLIT_SCREEN":
        bindings = [
            {"claim_id": "landing_deployed", "slot": "LEFT"},
            {"claim_id": "cruise_retracted", "slot": "RIGHT"},
        ]
    else:
        bindings = [
            {"claim_id": "cruise_retracted", "sequence_index": 1, "start_sec": 23.0, "end_sec": 26.0},
            {"claim_id": "landing_deployed", "sequence_index": 0, "start_sec": 19.0, "end_sec": 22.5},
        ]
    visibility = {"level": "CLEAR", "requirements": {"not_occluded": True, "distinguishable_state": True, "sufficient_scale_for_mobile": True}}
    return {
        "version": "visual_explanation_contract_v2.1",
        "scene_id": 5,
        "mode": "shadow",
        "claims": [
            {"id": "landing_deployed", "subject": "flap", "context": "landing", "state": "DEPLOYED", "required": True, "visibility": visibility},
            {"id": "cruise_retracted", "subject": "flap", "context": "cruise", "state": "RETRACTED", "required": True, "visibility": visibility},
        ],
        "comparison_segments": [{"id": "cmp-landing-cruise", "presentation": presentation, "start_sec": 19.0, "end_sec": 28.0, "bindings": bindings}],
        "relations": [{"id": "landing_vs_cruise", "type": "CONTRAST", "members": ["landing_deployed", "cruise_retracted"], "comparison_segment_id": "cmp-landing-cruise", "required": True}],
    }


class VisualExplanationV21Regression(unittest.TestCase):
    def setUp(self):
        self.registry = SubjectStateRegistry()

    def test_run_34007556064_scene5_would_hold_but_production_unchanged(self):
        contract = scene5_contract()
        validation = semantic_validate(contract, self.registry)
        self.assertTrue(validation.ok, validation.errors)
        raw = {
            "landing_deployed": RawVisionObservation(True, "DEPLOYED", True),
            "cruise_retracted": RawVisionObservation(True, "DEPLOYED", True),
        }
        evidence = {}
        for claim in contract["claims"]:
            obs = normalize_vision_observation(claim["subject"], raw[claim["id"]], self.registry)
            evidence[claim["id"]] = resolve_claim_evidence(claim, obs)
        self.assertEqual(evidence["landing_deployed"], EvidenceState.VERIFIED)
        self.assertEqual(evidence["cruise_retracted"], EvidenceState.CONTRADICTED)
        evaluation = evaluate_contrast(contract, contract["relations"][0], evidence)
        self.assertEqual(evaluation.result, RelationResult.FAIL)
        shadow = aggregate_shadow_decision("PASS", validation, [evaluation])
        self.assertEqual(shadow.decision, ShadowDecision.WOULD_HOLD)
        self.assertEqual(shadow.production_decision, "PASS")

    def test_sequential_array_order_is_serialization_only(self):
        contract = scene5_contract("SEQUENTIAL")
        result = semantic_validate(contract, self.registry)
        self.assertTrue(result.ok, result.errors)

    def test_sequential_overlap_is_invalid(self):
        contract = scene5_contract("SEQUENTIAL")
        contract["comparison_segments"][0]["bindings"][0]["start_sec"] = 22.0
        result = semantic_validate(contract, self.registry)
        self.assertFalse(result.ok)
        self.assertTrue(any("overlap" in e for e in result.errors))

    def test_relation_binding_mismatch_invalid(self):
        contract = scene5_contract()
        contract["comparison_segments"][0]["bindings"][1]["claim_id"] = "landing_deployed"
        result = semantic_validate(contract, self.registry)
        self.assertFalse(result.ok)

    def test_unknown_vision_state_is_not_contradicted(self):
        contract = scene5_contract()
        claim = contract["claims"][0]
        obs = normalize_vision_observation("flap", RawVisionObservation(True, "LOWERED", True), self.registry)
        self.assertFalse(obs.state_distinguishable)
        self.assertIn("unknown vision state", obs.diagnostic or "")
        self.assertEqual(resolve_claim_evidence(claim, obs), EvidenceState.NOT_VERIFIED)

    def test_conservative_vision_alias_is_canonicalized(self):
        contract = scene5_contract()
        claim = contract["claims"][0]
        obs = normalize_vision_observation("flap", RawVisionObservation(True, "DOWN", True), self.registry)
        self.assertEqual(obs.observed_state, "DEPLOYED")
        self.assertEqual(resolve_claim_evidence(claim, obs), EvidenceState.VERIFIED)

    def test_writer_only_alias_not_accepted_as_vision_evidence(self):
        contract = scene5_contract()
        claim = contract["claims"][0]
        obs = normalize_vision_observation("flap", RawVisionObservation(True, "OPEN", True), self.registry)
        self.assertFalse(obs.state_distinguishable)
        self.assertEqual(resolve_claim_evidence(claim, obs), EvidenceState.NOT_VERIFIED)

    def test_missing_evidence_is_incomplete_not_keyerror(self):
        contract = scene5_contract()
        evaluation = evaluate_contrast(
            contract,
            contract["relations"][0],
            {"landing_deployed": EvidenceState.VERIFIED},
        )
        self.assertEqual(evaluation.status, EvaluationStatus.INCOMPLETE)
        self.assertIn("EVIDENCE_MISSING", evaluation.diagnostic or "")


if __name__ == "__main__":
    unittest.main()

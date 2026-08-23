"""Script Engine V2: deterministic narrative planning before LLM writing.

This module is intentionally side-by-side with the legacy generator. It does not
change production routing until regression fixtures prove the contract.
"""
from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


MAX_SCRIPT_API_CALLS = 3


@dataclass(frozen=True)
class SceneContract:
    index: int
    role: str
    locked: bool = False
    locked_text: str = ""
    required_concepts: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["required_concepts"] = list(self.required_concepts)
        data["forbidden"] = list(self.forbidden)
        return data


def _text(value: Any) -> str:
    return str(value or "").strip()


def _micro(candidate: Dict[str, Any]) -> Dict[str, Any]:
    value = candidate.get("micro_narrative") or {}
    if not isinstance(value, dict):
        raise ValueError("candidate.micro_narrative must be an object")
    return value


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    """Build the story skeleton without an API call.

    Opening question and ending answer are locked before the writer runs. The
    writer only fills causal/mechanism/consequence scenes.
    """
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    micro = _micro(candidate)
    hook = _text(approved_hook) or _text(micro.get("hook"))
    question = _text(candidate.get("core_question")) or _text(micro.get("core_question"))
    reveal = _text(micro.get("reveal"))
    payoff = _text(micro.get("payoff"))

    missing = [name for name, value in (
        ("hook", hook), ("core_question", question), ("reveal", reveal), ("payoff", payoff)
    ) if not value]
    if missing:
        raise ValueError("missing narrative locks: " + ", ".join(missing))

    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):
        raise ValueError("scene 1 hook must be an observable statement, not a question")

    if "?" not in question:
        question = f"그런데 {question.rstrip('.')}?"

    focus = [_text(x) for x in candidate.get("fact_check_focus", []) if _text(x)]
    visual = [_text(x) for x in candidate.get("visual_proof", []) if _text(x)]
    concepts = tuple((focus + visual)[:4])

    contracts = [
        SceneContract(1, "phenomenon", True, hook, forbidden=("question", "answer")),
        SceneContract(2, "question", True, question, forbidden=("answer",)),
        SceneContract(3, "causal_clue", required_concepts=concepts[:2], forbidden=("final_answer",)),
        SceneContract(4, "mechanism_1", required_concepts=concepts[:2]),
        SceneContract(5, "mechanism_2", required_concepts=concepts[1:3]),
        SceneContract(6, "consequence", required_concepts=concepts[2:4]),
        SceneContract(7, "reveal", True, reveal),
        SceneContract(8, "payoff", True, payoff),
    ]

    return {
        "version": "script-engine-v2",
        "topic": _text(candidate.get("topic")),
        "angle": _text(candidate.get("angle")),
        "api_call_budget": MAX_SCRIPT_API_CALLS,
        "contracts": [item.to_dict() for item in contracts],
    }


def apply_locked_scenes(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Reapply immutable narrative locks after writer/local repair output."""
    result = deepcopy(script)
    scenes = result.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("script.scenes must be a list")

    contracts = plan.get("contracts") or []
    if len(scenes) < len(contracts):
        raise ValueError("writer returned fewer scenes than the narrative plan")

    for contract in contracts:
        if not contract.get("locked"):
            continue
        idx = int(contract["index"]) - 1
        scene = scenes[idx]
        if not isinstance(scene, dict):
            raise ValueError(f"scene {idx + 1} must be an object")
        scene["text"] = contract["locked_text"]
        scene["role"] = contract["role"]

    result["scenes"] = scenes
    result["script_engine"] = "v2"
    return result


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Compact payload for one LLM writer call; locked scenes are explicit."""
    return {
        "topic": plan.get("topic"),
        "angle": plan.get("angle"),
        "facts": list(candidate.get("fact_check_focus") or []),
        "visual_proof": list(candidate.get("visual_proof") or []),
        "scene_contracts": plan.get("contracts") or [],
        "rules": {
            "formal_korean": True,
            "easy_language": True,
            "do_not_change_locked_text": True,
            "answer_only_in_reveal_payoff": True,
            "max_total_api_calls": MAX_SCRIPT_API_CALLS,
        },
    }

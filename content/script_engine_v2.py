"""Script Engine V2: deterministic planning and bounded local recovery."""
from copy import deepcopy
from dataclasses import dataclass, asdict
import re
from typing import Any, Dict

from content.retention_structure import build_retention_plan

MAX_SCRIPT_API_CALLS = 3
MAX_LOCAL_REPAIR_CALLS = 2


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


def _concept_window(concepts: tuple[str, ...], start: int, width: int = 2) -> tuple[str, ...]:
    if not concepts:
        return ()
    size = len(concepts)
    return tuple(concepts[(start + offset) % size] for offset in range(min(width, size)))


def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    """Build the narrative skeleton without spending an API call."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    micro = _micro(candidate)
    hook = _text(approved_hook) or _text(micro.get("hook"))
    question = _text(candidate.get("core_question")) or _text(micro.get("core_question"))
    reveal = _text(micro.get("reveal"))
    payoff = _text(micro.get("payoff"))

    missing = [
        name for name, value in (
            ("hook", hook),
            ("core_question", question),
            ("reveal", reveal),
            ("payoff", payoff),
        ) if not value
    ]
    if missing:
        raise ValueError("missing narrative locks: " + ", ".join(missing))

    if "?" in hook or hook.endswith(("까요", "나요", "어요", "예요")):
        raise ValueError("scene 1 hook must be an observable statement, not a question")

    if not question.startswith("그런데"):
        question = "그런데 " + question
    if "?" not in question:
        question = question.rstrip(".") + "?"

    focus = [_text(x) for x in candidate.get("fact_check_focus", []) if _text(x)]
    visual = [_text(x) for x in candidate.get("visual_proof", []) if _text(x)]
    concepts = tuple((focus + visual)[:6])

    retention = build_retention_plan(candidate)
    scene_count = max(7, min(13, int(retention["min_scenes"])))

    contracts = [
        SceneContract(1, "phenomenon", True, hook, forbidden=("question", "answer")),
        SceneContract(2, "question", True, question, forbidden=("answer",)),
        SceneContract(3, "causal_clue", required_concepts=_concept_window(concepts, 0), forbidden=("final_answer",)),
    ]

    middle_slots = scene_count - 5
    for offset in range(middle_slots):
        index = 4 + offset
        role = "consequence" if offset == middle_slots - 1 else f"mechanism_{offset + 1}"
        contracts.append(
            SceneContract(index, role, required_concepts=_concept_window(concepts, offset + 1))
        )

    contracts.extend([
        SceneContract(scene_count - 1, "reveal", True, reveal),
        SceneContract(scene_count, "payoff", True, payoff),
    ])

    return {
        "version": "script-engine-v2",
        "topic": _text(candidate.get("topic")),
        "angle": _text(candidate.get("angle")),
        "api_call_budget": MAX_SCRIPT_API_CALLS,
        "runtime_bucket": retention["runtime_bucket"],
        "target_scene_count": scene_count,
        "contracts": [item.to_dict() for item in contracts],
    }


def apply_locked_scenes(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(script)
    scenes = result.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("script.scenes must be a list")

    contracts = plan.get("contracts") or []
    if len(scenes) != len(contracts):
        raise ValueError(
            f"writer scene count mismatch: {len(scenes)}/{len(contracts)}"
        )

    for contract in contracts:
        index = int(contract["index"]) - 1
        scene = scenes[index]
        if not isinstance(scene, dict):
            raise ValueError(f"scene {index + 1} must be an object")
        scene["role"] = contract["role"]
        if index < 3:
            scene["retention_role"] = contract["role"]
        if contract.get("locked"):
            scene["text"] = contract["locked_text"]

    result["scenes"] = scenes
    result["script_engine"] = "v2"
    result["runtime_bucket"] = plan.get("runtime_bucket")
    return result


def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "topic": plan.get("topic"),
        "angle": plan.get("angle"),
        "facts": list(candidate.get("fact_check_focus") or []),
        "visual_proof": list(candidate.get("visual_proof") or []),
        "runtime_bucket": plan.get("runtime_bucket"),
        "target_scene_count": plan.get("target_scene_count"),
        "scene_contracts": plan.get("contracts") or [],
        "rules": {
            "formal_korean": True,
            "easy_language": True,
            "do_not_change_locked_text": True,
            "answer_only_in_reveal_payoff": True,
            "max_total_api_calls": MAX_SCRIPT_API_CALLS,
        },
    }


_ENDING_REPAIRS = (
    (r"줄여준다(?=[.!?…]*$)", "줄여줍니다"),
    (r"감소시킨다(?=[.!?…]*$)", "감소시킵니다"),
    (r"줄인다(?=[.!?…]*$)", "줄입니다"),
    (r"감소한다(?=[.!?…]*$)", "감소합니다"),
    (r"한다(?=[.!?…]*$)", "합니다"),
    (r"된다(?=[.!?…]*$)", "됩니다"),
    (r"이다(?=[.!?…]*$)", "입니다"),
    (r"있다(?=[.!?…]*$)", "있습니다"),
    (r"없다(?=[.!?…]*$)", "없습니다"),
)


def deterministic_scene_repair(text: str, role: str) -> str:
    value = _text(text)
    for pattern, replacement in _ENDING_REPAIRS:
        value = re.sub(pattern, replacement, value)
    if role == "causal_clue" and value and not any(
        token in value for token in (
            "원인", "압력", "공기", "구조", "차이", "힘", "흐름", "소용돌이"
        )
    ):
        value = "원인의 첫 단서는 " + value
    return value


def repair_failed_scenes(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
) -> Dict[str, Any]:
    """Repair only failed unlocked scenes; never regenerate Candidate or whole Script."""
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    contracts = plan.get("contracts") or []
    by_index = {int(item["index"]): item for item in contracts}

    for scene_index in failed_scene_indexes:
        contract = by_index.get(int(scene_index))
        if not contract or contract.get("locked"):
            continue
        index = int(scene_index) - 1
        if index < 0 or index >= len(scenes) or not isinstance(scenes[index], dict):
            continue
        scenes[index]["text"] = deterministic_scene_repair(
            scenes[index].get("text", ""), contract.get("role", "")
        )
        scenes[index]["role"] = contract.get("role", "")

    result["scenes"] = scenes
    return apply_locked_scenes(result, plan)


def local_repair_payload(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
    reasons: list[str],
) -> Dict[str, Any]:
    contracts = {int(item["index"]): item for item in plan.get("contracts") or []}
    scenes = script.get("scenes") or []
    targets = []
    for scene_index in failed_scene_indexes:
        contract = contracts.get(int(scene_index))
        index = int(scene_index) - 1
        if (
            contract
            and not contract.get("locked")
            and 0 <= index < len(scenes)
            and isinstance(scenes[index], dict)
        ):
            targets.append({
                "scene_index": int(scene_index),
                "role": contract.get("role"),
                "required_concepts": contract.get("required_concepts") or [],
                "current_text": _text(scenes[index].get("text")),
            })
    return {
        "targets": targets,
        "validation_reasons": list(reasons or []),
        "rules": {
            "repair_only_targets": True,
            "formal_korean": True,
            "easy_language": True,
            "do_not_rewrite_other_scenes": True,
            "max_local_repair_calls": MAX_LOCAL_REPAIR_CALLS,
        },
    }

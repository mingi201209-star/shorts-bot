"""Script Engine V2: deterministic planning and bounded local recovery."""
from copy import deepcopy
from dataclasses import dataclass, asdict
import re
from typing import Any, Dict

from content.retention_structure import build_retention_plan

MAX_SCRIPT_API_CALLS = 3
MAX_LOCAL_REPAIR_CALLS = 2
CAUSAL_CLUE_TOKENS = (
    "때문", "원인", "압력", "힘", "공기", "구조", "작동", "차이", "분산", "조절", "균형",
)


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


def _normalize_locked_narration(text: Any, role: str) -> str:
    """Keep locked meaning while enforcing the production speech contract."""
    value = _text(text)
    if not value:
        return value

    if role == "question":
        value = value.rstrip().rstrip(".?!")
        replacements = (
            (r"있을까$", "있을까요"),
            (r"할까$", "할까요"),
            (r"될까$", "될까요"),
            (r"일까$", "일까요"),
            (r"일까요$", "일까요"),
            (r"있을까요$", "있을까요"),
            (r"할까요$", "할까요"),
            (r"될까요$", "될까요"),
        )
        for pattern, replacement in replacements:
            converted, count = re.subn(pattern, replacement, value)
            if count:
                return converted + "?"
        return value + "?"

    return deterministic_scene_repair(value, role)


def _concept_window(concepts: tuple[str, ...], start: int, width: int = 2) -> tuple[str, ...]:
    if not concepts:
        return ()
    size = len(concepts)
    return tuple(concepts[(start + offset) % size] for offset in range(min(width, size)))


_QUESTION_HOOK_REPAIRS = (
    (r"있을까요$", "있습니다"),
    (r"없을까요$", "없습니다"),
    (r"일까요$", "입니다"),
    (r"될까요$", "됩니다"),
    (r"할까요$", "합니다"),
    (r"올까요$", "옵니다"),
    (r"갈까요$", "갑니다"),
)


_TOPIC_OBSERVATION_REPAIRS = (
    (r"지 않는$", "지 않습니다"),
    (r"하는$", "합니다"),
    (r"되는$", "됩니다"),
    (r"있는$", "있습니다"),
    (r"없는$", "없습니다"),
    (r"오는$", "옵니다"),
    (r"가는$", "갑니다"),
)


def _topic_to_observation(topic: Any) -> str:
    value = _text(topic).rstrip().rstrip(".?!")
    value = re.sub(r"\s+이유$", "", value)
    for pattern, replacement in _TOPIC_OBSERVATION_REPAIRS:
        converted, count = re.subn(pattern, replacement, value)
        if count:
            return converted + "."
    return ""


def _question_hook_to_observation(text: Any, topic: Any = "") -> str:
    """Convert only known Korean question endings; unsupported forms still fail closed."""
    value = re.sub(r"^(?:그런데\s+)?왜\s+", "", _text(text)).rstrip().rstrip(".?!")
    for pattern, replacement in _QUESTION_HOOK_REPAIRS:
        converted, count = re.subn(pattern, replacement, value)
        if count:
            return converted + "."
    if re.search(r"무엇일(?:까|까요)$", value):
        return _topic_to_observation(topic)
    return ""


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
        hook = _question_hook_to_observation(hook, candidate.get("topic"))
        if not hook:
            raise ValueError("scene 1 hook must be an observable statement, not a question")

    hook = _normalize_locked_narration(hook, "phenomenon")
    if not question.startswith("그런데"):
        question = "그런데 " + question
    question = _normalize_locked_narration(question, "question")
    reveal = _normalize_locked_narration(reveal, "reveal")
    payoff = _normalize_locked_narration(payoff, "payoff")

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
            scene["text"] = _normalize_locked_narration(
                contract["locked_text"], contract.get("role", "")
            )

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
    (r"높인다(?=[.!?…]*$)", "높입니다"),
    (r"감소한다(?=[.!?…]*$)", "감소합니다"),
    (r"줄어든다(?=[.!?…]*$)", "줄어듭니다"),
    (r"늘어난다(?=[.!?…]*$)", "늘어납니다"),
    (r"약해진다(?=[.!?…]*$)", "약해집니다"),
    (r"강해진다(?=[.!?…]*$)", "강해집니다"),
    (r"달라진다(?=[.!?…]*$)", "달라집니다"),
    (r"좋아진다(?=[.!?…]*$)", "좋아집니다"),
    (r"향상된다(?=[.!?…]*$)", "향상됩니다"),
    (r"발생한다(?=[.!?…]*$)", "발생합니다"),
    (r"만든다(?=[.!?…]*$)", "만듭니다"),
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
        token in value for token in CAUSAL_CLUE_TOKENS
    ):
        value = "원인의 첫 단서는 " + value
    return value


def repair_failed_scenes(
    script: Dict[str, Any],
    plan: Dict[str, Any],
    failed_scene_indexes: list[int],
) -> Dict[str, Any]:
    """Repair only failed narration; locked text remains immutable."""
    result = deepcopy(script)
    scenes = result.get("scenes") or []
    contracts = plan.get("contracts") or []
    by_index = {int(item["index"]): item for item in contracts}

    for scene_index in failed_scene_indexes:
        contract = by_index.get(int(scene_index))
        if not contract:
            continue
        index = int(scene_index) - 1
        if index < 0 or index >= len(scenes) or not isinstance(scenes[index], dict):
            continue
        if contract.get("locked"):
            scenes[index]["text"] = _normalize_locked_narration(
                contract.get("locked_text", ""), contract.get("role", "")
            )
        else:
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
    """Allow metadata repair on locked scenes while keeping locked narration immutable."""
    contracts = {int(item["index"]): item for item in plan.get("contracts") or []}
    scenes = script.get("scenes") or []
    targets = []
    for scene_index in failed_scene_indexes:
        contract = contracts.get(int(scene_index))
        index = int(scene_index) - 1
        if (
            contract
            and 0 <= index < len(scenes)
            and isinstance(scenes[index], dict)
        ):
            targets.append({
                "scene_index": int(scene_index),
                "role": contract.get("role"),
                "required_concepts": contract.get("required_concepts") or [],
                "current_text": _text(scenes[index].get("text")),
                "text_locked": bool(contract.get("locked")),
                "locked_text": _text(contract.get("locked_text")) if contract.get("locked") else "",
                "current_visual_goal": _text(scenes[index].get("visual_goal")),
                "current_keyword": _text(scenes[index].get("keyword")),
            })
    return {
        "targets": targets,
        "validation_reasons": list(reasons or []),
        "rules": {
            "repair_only_targets": True,
            "formal_korean": True,
            "easy_language": True,
            "do_not_rewrite_other_scenes": True,
            "locked_scene_text_is_immutable": True,
            "metadata_on_locked_scenes_may_be_repaired": True,
            "max_local_repair_calls": MAX_LOCAL_REPAIR_CALLS,
        },
    }

"""Script Engine V2: deterministic planning and bounded local recovery."""
from copy import deepcopy
from dataclasses import dataclass, asdict
import re
from typing import Any, Dict

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

def build_narrative_plan(candidate: Dict[str, Any], approved_hook: str = "") -> Dict[str, Any]:
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")
    micro = _micro(candidate)
    hook = _text(approved_hook) or _text(micro.get("hook"))
    question = _text(candidate.get("core_question")) or _text(micro.get("core_question"))
    reveal = _text(micro.get("reveal")); payoff = _text(micro.get("payoff"))
    missing = [n for n,v in (("hook",hook),("core_question",question),("reveal",reveal),("payoff",payoff)) if not v]
    if missing: raise ValueError("missing narrative locks: " + ", ".join(missing))
    if "?" in hook or hook.endswith(("까요","나요","어요","예요")):
        raise ValueError("scene 1 hook must be an observable statement, not a question")
    if "?" not in question: question = f"그런데 {question.rstrip('.')}?"
    focus=[_text(x) for x in candidate.get("fact_check_focus",[]) if _text(x)]
    visual=[_text(x) for x in candidate.get("visual_proof",[]) if _text(x)]
    concepts=tuple((focus+visual)[:4])
    contracts=[
        SceneContract(1,"phenomenon",True,hook,forbidden=("question","answer")),
        SceneContract(2,"question",True,question,forbidden=("answer",)),
        SceneContract(3,"causal_clue",required_concepts=concepts[:2],forbidden=("final_answer",)),
        SceneContract(4,"mechanism_1",required_concepts=concepts[:2]),
        SceneContract(5,"mechanism_2",required_concepts=concepts[1:3]),
        SceneContract(6,"consequence",required_concepts=concepts[2:4]),
        SceneContract(7,"reveal",True,reveal), SceneContract(8,"payoff",True,payoff),]
    return {"version":"script-engine-v2","topic":_text(candidate.get("topic")),"angle":_text(candidate.get("angle")),"api_call_budget":MAX_SCRIPT_API_CALLS,"contracts":[x.to_dict() for x in contracts]}

def apply_locked_scenes(script: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    result=deepcopy(script); scenes=result.get("scenes")
    if not isinstance(scenes,list): raise ValueError("script.scenes must be a list")
    contracts=plan.get("contracts") or []
    if len(scenes)<len(contracts): raise ValueError("writer returned fewer scenes than the narrative plan")
    for c in contracts:
        idx=int(c["index"])-1
        if c.get("locked"):
            if not isinstance(scenes[idx],dict): raise ValueError(f"scene {idx+1} must be an object")
            scenes[idx]["text"]=c["locked_text"]; scenes[idx]["role"]=c["role"]
        elif isinstance(scenes[idx],dict): scenes[idx]["role"]=c["role"]
    result["scenes"]=scenes; result["script_engine"]="v2"; return result

def writer_payload(candidate: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    return {"topic":plan.get("topic"),"angle":plan.get("angle"),"facts":list(candidate.get("fact_check_focus") or []),"visual_proof":list(candidate.get("visual_proof") or []),"scene_contracts":plan.get("contracts") or [],"rules":{"formal_korean":True,"easy_language":True,"do_not_change_locked_text":True,"answer_only_in_reveal_payoff":True,"max_total_api_calls":MAX_SCRIPT_API_CALLS}}

# Deterministic repairs cover only safe sentence-final style failures seen in production.
_ENDING_REPAIRS=((r"줄여준다(?=[.!?…]*$)","줄여줍니다"),(r"감소시킨다(?=[.!?…]*$)","감소시킵니다"),(r"줄인다(?=[.!?…]*$)","줄입니다"),(r"감소한다(?=[.!?…]*$)","감소합니다"),(r"한다(?=[.!?…]*$)","합니다"),(r"된다(?=[.!?…]*$)","됩니다"),(r"이다(?=[.!?…]*$)","입니다"),(r"있다(?=[.!?…]*$)","있습니다"),(r"없다(?=[.!?…]*$)","없습니다"))

def deterministic_scene_repair(text: str, role: str) -> str:
    value=_text(text)
    for pattern,replacement in _ENDING_REPAIRS: value=re.sub(pattern,replacement,value)
    if role=="causal_clue" and value and not any(token in value for token in ("원인","압력","공기","구조","차이","힘","흐름","소용돌이")):
        value="원인의 첫 단서는 " + value
    return value

def repair_failed_scenes(script: Dict[str, Any], plan: Dict[str, Any], failed_scene_indexes: list[int]) -> Dict[str, Any]:
    """Repair only failed unlocked scenes. Never regenerate Candidate or whole Script."""
    result=deepcopy(script); scenes=result.get("scenes") or []; contracts=plan.get("contracts") or []
    by_index={int(c["index"]):c for c in contracts}
    for scene_index in failed_scene_indexes:
        contract=by_index.get(int(scene_index))
        if not contract or contract.get("locked"): continue
        idx=int(scene_index)-1
        if idx<0 or idx>=len(scenes) or not isinstance(scenes[idx],dict): continue
        scenes[idx]["text"]=deterministic_scene_repair(scenes[idx].get("text",""),contract.get("role",""))
        scenes[idx]["role"]=contract.get("role","")
    result["scenes"]=scenes
    return apply_locked_scenes(result,plan)

def local_repair_payload(script: Dict[str, Any], plan: Dict[str, Any], failed_scene_indexes: list[int], reasons: list[str]) -> Dict[str, Any]:
    """Payload for at most two LLM local-repair calls after deterministic repair fails."""
    contracts={int(c["index"]):c for c in plan.get("contracts") or []}
    scenes=script.get("scenes") or []
    targets=[]
    for i in failed_scene_indexes:
        c=contracts.get(int(i)); idx=int(i)-1
        if c and not c.get("locked") and 0<=idx<len(scenes): targets.append({"scene_index":int(i),"role":c.get("role"),"required_concepts":c.get("required_concepts") or [],"current_text":_text((scenes[idx] or {}).get("text"))})
    return {"targets":targets,"validation_reasons":list(reasons or []),"rules":{"repair_only_targets":True,"formal_korean":True,"easy_language":True,"do_not_rewrite_other_scenes":True,"max_local_repair_calls":MAX_LOCAL_REPAIR_CALLS}}

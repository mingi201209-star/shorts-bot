"""Regression fixtures distilled from repeated production Script failures."""
from content.script_engine_v2 import build_narrative_plan, repair_failed_scenes, local_repair_payload

CANDIDATE={"topic":"비행기 날개 끝이 위로 꺾인 이유","angle":"윙렛과 유도항력","core_question":"왜 비행기 날개 끝은 위로 꺾여 있을까요?","micro_narrative":{"hook":"비행기 날개 끝이 위로 꺾여 있습니다.","core_question":"왜 비행기 날개 끝은 위로 꺾여 있을까요?","reveal":"날개 끝 소용돌이를 약하게 만들어 유도항력을 줄입니다.","payoff":"그래서 연료를 덜 쓰는 데 도움이 됩니다."},"fact_check_focus":["압력 차이","날개 끝 소용돌이","유도항력"],"visual_proof":["윙렛","날개 끝 공기 흐름"]}

def script_with(scene3, scene4):
    texts=[CANDIDATE["micro_narrative"]["hook"],CANDIDATE["core_question"],scene3,scene4,"공기 흐름이 바뀝니다.","결과적으로 효율이 좋아집니다.",CANDIDATE["micro_narrative"]["reveal"],CANDIDATE["micro_narrative"]["payoff"]]
    return {"scenes":[{"text":x} for x in texts]}

def main():
    plan=build_narrative_plan(CANDIDATE)
    # Exact classes seen in production: non-formal ending + missing explicit causal clue.
    broken=script_with("날개 끝에서 서로 다른 공기가 만나게 된다.","이 구조가 소용돌이를 줄여준다.")
    repaired=repair_failed_scenes(broken,plan,[3,4])
    assert repaired["scenes"][2]["text"].startswith("원인의 첫 단서는 ")
    assert repaired["scenes"][2]["text"].endswith("됩니다.")
    assert repaired["scenes"][3]["text"].endswith("줄여줍니다.")
    # Locked scenes cannot be modified even if a validator reports them.
    tampered=script_with("압력 차이가 생깁니다.","소용돌이가 감소시킨다.")
    tampered["scenes"][0]["text"]="왜 꺾였을까요?"
    tampered["scenes"][6]["text"]="정답을 바꾼다."
    repaired2=repair_failed_scenes(tampered,plan,[1,4,7])
    assert repaired2["scenes"][0]["text"]==CANDIDATE["micro_narrative"]["hook"]
    assert repaired2["scenes"][3]["text"].endswith("감소시킵니다.")
    assert repaired2["scenes"][6]["text"]==CANDIDATE["micro_narrative"]["reveal"]
    # If deterministic repair is insufficient, only failed unlocked scenes enter LLM payload.
    payload=local_repair_payload(repaired2,plan,[1,3,4,7],["scene 3 lacks causal clue","scene 4 speech style"])
    assert [x["scene_index"] for x in payload["targets"]]==[3,4]
    assert payload["rules"]["max_local_repair_calls"]==2
    assert payload["rules"]["do_not_rewrite_other_scenes"] is True
    print("PASS: Script Engine V2 production failure fixtures")

if __name__=="__main__": main()

from pathlib import Path
import os, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HOTFIXES=(
"ci_hotfix.py","ci_novelty_budget_hotfix.py","ci_fact_critical_hotfix.py","ci_speech_style_hotfix.py",
"ci_hook_generation_hotfix.py","ci_hook_pool_guard_hotfix.py","ci_retention_hotfix.py","ci_first5_retention_tts_hotfix.py",
"ci_first5_visual_contract_hotfix.py","ci_video_provider_hotfix.py","ci_topic_input_hotfix.py","ci_aviation_candidate_context_hotfix.py",
"ci_output_quality_hotfix.py","ci_curiosity_retention_hotfix.py","ci_visual_specificity_hotfix.py","ci_design_causality_hotfix.py",
"ci_query_semantic_integrity_hotfix.py","ci_concrete_visual_evidence_hotfix.py","ci_visible_evidence_provenance_hotfix.py",
"ci_hook_production_parity_hotfix.py","ci_hook_fallback_quality_floor_hotfix.py","ci_ai_visual_fallback_hotfix.py",
"ci_ai_visual_mechanism_fallback_hotfix.py")
for h in HOTFIXES: subprocess.run([sys.executable,h],check=True)

from video import hook_visual as hv
from video import video_downloader as vd
from video import ai_visual_provider as ai

q="airplane window rounded corner"
scene={"text":"비행기 창문이 둥근 데는 이유가 있다.","keyword":q,"visual_goal":"aircraft window rounded detail"}
mechanism_scene={"text":"압력 차이를 견디는 구조를 설명합니다.","keyword":"aircraft window pressure structure","visual_goal":"aircraft window pressure mechanism","visual_type":"educational mechanism"}
def c(i,title): return {"id":i,"source_id":i,"provider":"pexels","url":f"https://x/{i}.mp4","title":title,"tags":title,"search_position":i,"width":1080,"height":1920,"duration":8}
wing=c(1,"airplane wing clouds"); unknown=c(2,"aircraft cabin passenger window"); verified=c(3,"aircraft window rounded detail")
vd.register_visual_evidence(wing,visible_components=["aircraft"],source="vision",definitive=True)
vd.register_visual_evidence(verified,visible_components=["aircraft","window"],source="vision",definitive=True)

# A/B: good stock or verified reuse means no AI trigger condition.
assert hv._hook_fallback_quality(verified,q)["label"]=="DIRECT_VERIFIED"
vd._SAFE_REUSE_HISTORY.clear(); vd._SAFE_REUSE_COUNTS.clear(); vd._SAFE_REUSE_HISTORY[vd._safe_reuse_key(verified)]=dict(verified); vd._SAFE_REUSE_COUNTS[vd._safe_reuse_key(verified)]=0
cand,qual,_=hv._choose_hook_fallback([{"candidate":wing,"total_score":9}],q)
assert qual["label"]=="VERIFIED_COMPATIBLE_REUSE"

# C/G/H/I: adapter budget, Hook + mechanism eligibility, prompt safety; no real API calls.
os.environ["AI_VISUAL_FALLBACK_ENABLED"]="1"
ai.AI_VISUAL_FALLBACK_ENABLED=True; ai.AI_MAX_GENERATIONS_PER_VIDEO=1; ai.reset_generation_budget()
assert ai.ai_visual_eligible(scene,hook=True)
assert ai.ai_visual_eligible(mechanism_scene,hook=False)
assert not ai.ai_visual_eligible({"text":"분위기 있는 배경","visual_goal":"ambient mood","keyword":"sky"},hook=False)
p=ai.build_visual_prompt(scene,required_components=["aircraft","window"],hook=True)
assert "Do not invent hidden technical structure" in p and "design intent" in p
calls=[]
ai._create_job=lambda prompt:(calls.append(prompt) or {"id":"video_test"})
ai._wait_for_job=lambda vid:{"id":vid,"status":"completed","seconds":"4"}
ai._download_content=lambda vid,h:"/tmp/fake.mp4"
r=ai.generate_ai_visual(scene,required_components=["aircraft","window"],hook=True,trigger_reason="test")
assert r and r["provider"]=="openai_sora" and len(calls)==1
assert ai.generate_ai_visual(mechanism_scene,required_components=["aircraft","window"],hook=False,trigger_reason="budget") is None

# D/E/F/J: generated candidate is only accepted after existing vision verifies component/dominance.
orig_gen=ai.generate_ai_visual; orig_dom=hv.evaluate_hook_subject_dominance
try:
    ai.generate_ai_visual=lambda *a,**k:{"id":"video_ai","source_id":"video_ai","provider":"openai_sora","source_type":"ai_generated","generation_id":"video_ai","scene_id":"0","prompt_hash":"abc","url":"/tmp/fake.mp4","title":"aircraft window","tags":"aircraft window"}
    hv.evaluate_hook_subject_dominance=lambda cand,s:{"pass":True,"visible_components":["aircraft","window"],"obvious_generation_artifact":False,"factual_visual_contradiction":False,"subject_dominance":9,"action_match":10,"competing_subject_risk":1,"vertical_crop_subject_visible":True}
    got=hv._try_ai_generated_hook_visual(scene,q,"scarcity")
    assert got and got["provider"]=="openai_sora"
    hv.evaluate_hook_subject_dominance=lambda cand,s:{"pass":False,"visible_components":["aircraft"],"obvious_generation_artifact":False,"factual_visual_contradiction":False}
    assert hv._try_ai_generated_hook_visual(scene,q,"reject") is None
    ai.generate_ai_visual=lambda *a,**k:None
    assert hv._try_ai_generated_hook_visual(scene,q,"provider_exception") is None
finally:
    ai.generate_ai_visual=orig_gen; hv.evaluate_hook_subject_dominance=orig_dom

# Production parity: a verified generated local MP4 reaches the renderer handoff without HTTP.
with tempfile.TemporaryDirectory() as td:
    src=Path(td)/"generated.mp4"; dst=Path(td)/"scene.mp4"
    src.write_bytes(b"fake-mp4-bytes")
    class NeverHTTP:
        def get(self,*a,**k): raise AssertionError("local AI handoff must not use HTTP")
    assert vd.download_video(str(src),str(dst),requests_module=NeverHTTP())==str(dst)
    assert dst.read_bytes()==src.read_bytes()

# General-scene production selector records the final stock quality for the mechanism trigger.
vd._LAST_GENERAL_SELECTION=None
vd.choose_best_candidate([wing],subject_filter_query=q)
general=vd.get_last_general_selection()
assert general and int(general["decision"]["level"])>=4

# K/L provider isolation behavior remains.
origp,origx,key=vd.search_pexels_candidates,vd.search_pixabay_candidates,vd.PIXABAY_API_KEY
try:
    def fail(*a,**k): raise RuntimeError("x")
    def pix(*a,**k): return [{"id":11,"provider":"pixabay","source_id":11,"url":"x","download_url":"x","source_url":"x","title":"aircraft window","tags":"aircraft window","search_position":1,"width":1080,"height":1920,"duration":8}]
    def pex(*a,**k): return [{"id":12,"url":"y","page_url":"y","search_position":1}]
    vd.PIXABAY_API_KEY="test"; vd.search_pexels_candidates,vd.search_pixabay_candidates=fail,pix
    assert vd.search_video_candidates("aircraft window",per_page=3)[0]["provider"]=="pixabay"
    vd.search_pexels_candidates,vd.search_pixabay_candidates=pex,fail
    assert vd.search_video_candidates("aircraft window",per_page=3)[0]["provider"]=="pexels"
finally: vd.search_pexels_candidates,vd.search_pixabay_candidates,vd.PIXABAY_API_KEY=origp,origx,key

# #20-#28 core contracts still present behaviorally.
assert hv._hook_fallback_quality(wing,q)["tier"] < hv._hook_fallback_quality(unknown,q)["tier"]
assert hv.hook_render_contract({"candidate_id":"openai_sora:video_ai","url":"/tmp/fake.mp4","selection_mode":"AI_GENERATED_VERIFIED","visual_evidence":"TRUE"},render_start=0,render_duration=3,final_url="/tmp/fake.mp4")["final_url_match"]
print("PASS: AI visual fallback A-L, Hook+mechanism eligibility, local render handoff, #20-#28 contracts, provider isolation; no paid API calls")

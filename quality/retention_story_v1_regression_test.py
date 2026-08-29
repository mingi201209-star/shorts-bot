import importlib
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for hotfix in (
    "ci_design_causality_hotfix.py",
    "ci_causal_information_progression_hotfix.py",
    "ci_script_production_parity_hotfix.py",
    "ci_script_production_parity_bridge_hotfix.py",
    "ci_adaptive_scene_count_hotfix.py",
):
    runpy.run_path(str(ROOT / hotfix), run_name="__main__")

sg = importlib.reload(importlib.import_module("content.script_generator"))
runtime = getattr(sg, "_SCRIPT_PARITY_RUNTIME", None) or getattr(sg, "_LEGACY", None)
assert runtime is not None


def s(text, role, keyword):
    return {
        "text": text,
        "role": role,
        "visual_goal": f"{keyword} 장면을 직접 보여주는 구체적 시각 증거",
        "keyword": keyword,
    }


# Run 33223881121 counterexample: scene 6/7 are generic restatement/filler.
flap = [
    s("비행기 날개 뒤쪽 플랩은 이착륙 때 펼쳐집니다.", "phenomenon", "aircraft flap extending"),
    s("그런데 왜 비행기 날개 뒤쪽 플랩은 이착륙 때 펼쳐질까요?", "question", "aircraft flap takeoff"),
    s("플랩이 펼쳐지면 날개 아래쪽의 공기 압력이 증가합니다.", "causal_clue", "aircraft flap airflow"),
    s("이로 인해 양력이 향상됩니다.", "mechanism_1", "aircraft wing lift"),
    s("비행기가 낮은 속도에서도 안정적으로 이륙할 수 있습니다.", "mechanism_2", "aircraft low speed takeoff"),
    s("플랩은 비행기의 이착륙 성능을 높입니다.", "mechanism_3", "aircraft flap performance"),
    s("이착륙 시 플랩의 역할은 매우 중요합니다.", "mechanism_4", "aircraft wing important role"),
    s("플랩 각도는 이륙과 착륙 조건에 따라 달라집니다.", "evidence", "aircraft flap angle"),
    s("조종사는 필요한 플랩 설정을 선택합니다.", "evidence", "aircraft flap cockpit control"),
    s("그래서 플랩은 낮은 속도의 이착륙을 가능하게 합니다.", "payoff", "aircraft flap landing"),
]
compressed = runtime.retention_story_compress_scenes(flap)
texts = [scene["text"] for scene in compressed]
assert len(compressed) == 8, len(compressed)
assert "플랩은 비행기의 이착륙 성능을 높입니다." not in texts
assert "이착륙 시 플랩의 역할은 매우 중요합니다." not in texts
assert all("important role" not in scene["keyword"] for scene in compressed)
assert compressed[0]["role"] == "phenomenon"
assert compressed[1]["role"] == "question"
assert compressed[-1]["role"] == "payoff"
assert any("양력" in text for text in texts)
assert any("낮은 속도" in text for text in texts)

# Phrase is not banned: concrete new causal information must survive.
concrete_help = s(
    "플랩은 항력을 늘려 착륙 속도를 낮추는 데 도움이 됩니다.",
    "mechanism_2",
    "aircraft flap drag landing",
)
probe = flap[:5] + [concrete_help] + flap[7:]
probe_out = runtime.retention_story_compress_scenes(probe)
assert any(scene["text"] == concrete_help["text"] for scene in probe_out)

# A genuinely information-bearing 10-scene script must not be reduced merely
# because it is longer than the preferred 6-8 scene range.
dense = [
    s("날개 끝에서는 아래쪽의 높은 압력 공기가 위쪽으로 돌아갑니다.", "phenomenon", "wingtip airflow curl"),
    s("왜 이 흐름이 연료 소비와 연결될까요?", "question", "wingtip vortex question"),
    s("압력 차이 때문에 날개 끝에 회전하는 와류가 생깁니다.", "causal_clue", "wingtip vortex formation"),
    s("와류는 공기를 아래로 더 강하게 밀어 유도항력을 만듭니다.", "mechanism_1", "wingtip induced drag"),
    s("유도항력이 커지면 같은 비행에 더 많은 추력이 필요합니다.", "mechanism_2", "aircraft thrust drag"),
    s("윙렛은 날개 끝의 압력 흐름 방향을 바꿉니다.", "mechanism_3", "winglet airflow direction"),
    s("그 변화가 와류의 세기와 유도항력을 줄입니다.", "mechanism_4", "winglet vortex reduction"),
    s("항력이 줄면 순항에 필요한 추력도 줄어듭니다.", "evidence", "aircraft cruise thrust"),
    s("그만큼 같은 항로에서 연료 사용을 줄일 수 있습니다.", "evidence", "aircraft fuel efficiency"),
    s("즉 날개 끝의 작은 구조가 공기 흐름을 바꿔 효율을 얻는 것입니다.", "payoff", "winglet airflow payoff"),
]
dense_out = runtime.retention_story_compress_scenes(dense)
assert len(dense_out) == 10, len(dense_out)

print("PASS: Retention Story V1 removes Run 33223881121 filler and preserves dense 10-scene scripts")

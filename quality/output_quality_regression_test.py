import ast
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Apply the same production patch order so this test validates the real runtime shape.
for script in (
    "ci_hotfix.py",
    "ci_novelty_budget_hotfix.py",
    "ci_fact_critical_hotfix.py",
    "ci_speech_style_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_hook_pool_guard_hotfix.py",
    "ci_retention_hotfix.py",
    "ci_first5_retention_tts_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py",
):
    subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def exec_named(source, names, namespace=None):
    namespace = dict(namespace or {})
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.Assign, ast.AnnAssign)):
            node_names = []
            if isinstance(node, ast.FunctionDef):
                node_names = [node.name]
            elif isinstance(node, ast.Assign):
                node_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                node_names = [node.target.id]
            if set(node_names) & set(names):
                selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, "<focused-regression>", "exec"), namespace)
    return namespace


hook = read("content/hook_experiment.py")
dominance = read("video/hook_visual_dominance.py")
downloader = read("video/video_downloader.py")
script_generator = read("content/script_generator.py")
explanation = read("quality/explanation_judge.py")
rewrite = read("quality/rewrite_engine.py")
workflow = read(".github/workflows/main.yml")
candidate_explorer = read("content/candidate_explorer.py")
provider = read("video/video_providers.py")

# A. Generic question Hook is rejected; natural declarative ~다 form is accepted.
hook_ns = exec_named(
    hook,
    {"_GENERIC_QUESTION_ENDINGS", "_output_quality_is_declarative_hook"},
    {"re": re},
)
check_hook = hook_ns["_output_quality_is_declarative_hook"]
assert check_hook("비행기 창문에는 작은 구멍이 있다.") is True
assert check_hook("비행기 창문 구멍의 역할은 뭘까요?") is False
assert check_hook("왜 그럴까요?") is False
assert "[DECLARATIVE HOOK CONTRACT]" in hook

# B. Exact Hook detail visibility is an explicit first-frame gate.
assert "hook_subject_visibility (0-10)" in dominance
assert "HOOK_SUBJECT_VISIBILITY_MIN = 8.0" in dominance
assert 'result["hook_subject_visibility"]' in dominance
assert "MOST SPECIFIC concrete subject/detail" in dominance

# C. Current narration-specific visual match outranks category-only metadata.
def normalize_search_query(value):
    value = re.sub(r"[^a-z0-9\\s-]", " ", str(value or "").lower())
    return re.sub(r"\\s+", " ", value).strip()


def _candidate_metadata(candidate):
    return normalize_search_query(candidate.get("metadata", ""))


direct_ns = exec_named(
    downloader,
    {"_DIRECT_MATCH_GENERIC_TERMS", "current_narration_semantic_match"},
    {
        "normalize_search_query": normalize_search_query,
        "_candidate_metadata": _candidate_metadata,
    },
)
semantic_score = direct_ns["current_narration_semantic_match"]
scene_query = "airplane window condensation layers"
direct = {"metadata": "close up airplane window condensation moisture layers"}
generic = {"metadata": "airplane cockpit pilot flight controls"}
assert semantic_score(direct, scene_query) > semantic_score(generic, scene_query)
assert semantic_score(direct, scene_query) >= 3.0
assert "CURRENT_NARRATION_SEMANTIC_MATCH" in downloader

# D. Repetition/filler is rejected without imposing a fixed duration target.
density_ns = exec_named(
    script_generator,
    {
        "_INFORMATION_DENSITY_FILLER_PATTERNS",
        "_INFORMATION_DENSITY_STOPWORDS",
        "_output_quality_information_tokens",
        "detect_information_density_issue",
    },
    {"re": re},
)
detect_density = density_ns["detect_information_density_issue"]
filler = [
    {"text": "창문 사이 압력을 조절해 바깥쪽 유리에 부담을 줄인다."},
    {"text": "이 구조는 창문 사이 압력을 조절해 유리 부담을 줄이는 역할을 합니다."},
]
dense = [
    {"text": "기내 압력은 비행 중 바깥 공기보다 높아진다."},
    {"text": "작은 구멍은 창문 사이 공간의 압력을 객실 쪽과 맞춘다."},
    {"text": "그래서 바깥쪽 유리가 대부분의 압력 차이를 견디게 된다."},
]
assert detect_density(filler) is not None
assert detect_density(dense) is None
assert "40~50초대 종료도 허용" in script_generator
assert "55초 이상도 허용" in script_generator
assert "INFORMATION DENSITY" in explanation
assert "[INFORMATION DENSITY 수정]" in rewrite

# E. Fixed topic and candidate_scope remain wired.
assert "SHORTS_TOPIC: ${{ inputs.topic }}" in workflow
assert "SHORTS_CANDIDATE_SCOPE: ${{ inputs.candidate_scope }}" in workflow
assert "fixed_topic" in candidate_explorer
assert "SHORTS_CANDIDATE_SCOPE" in candidate_explorer

# F. Unified Pexels + Pixabay pool/fallback remains intact.
for token in (
    "search_video_candidates",
    "provider=pexels",
    "provider=pixabay",
    "VIDEO_PROVIDER_SKIP",
    "merge_provider_candidates",
):
    assert token in downloader or token in provider, token

# G. Existing production contracts are not removed/lowered.
for token in (
    "ci_fact_critical_hotfix.py",
    "ci_hook_generation_hotfix.py",
    "ci_first5_visual_contract_hotfix.py",
    "ci_video_provider_hotfix.py",
    "ci_topic_input_hotfix.py",
    "ci_aviation_candidate_context_hotfix.py",
    "ci_output_quality_hotfix.py",
):
    assert token in workflow, token

assert "HOOK_SUBJECT_DOMINANCE_MIN" in dominance
assert "HOOK_ACTION_MATCH_MIN" in dominance
assert "HOOK_MAX_COMPETING_SUBJECT_RISK" in dominance

# Syntax check all touched runtime modules after the exact patch chain.
for target in (
    "content/hook_experiment.py",
    "video/hook_visual_dominance.py",
    "video/video_downloader.py",
    "content/script_generator.py",
    "quality/explanation_judge.py",
    "quality/rewrite_engine.py",
):
    compile(read(target), target, "exec")

print("PASS: declarative hook, exact hook visibility, direct scene match, information density, production contracts")

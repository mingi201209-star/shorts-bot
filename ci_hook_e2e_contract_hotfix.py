from pathlib import Path


path = Path("quality/hook_e2e_fixture.py")
text = path.read_text(encoding="utf-8")

import_marker = "import json\n\nfrom moviepy.editor import AudioFileClip\n"
import_replacement = "import json\nfrom types import SimpleNamespace\n\nfrom moviepy.editor import AudioFileClip\n"
if import_replacement not in text:
    if text.count(import_marker) != 1:
        raise RuntimeError("Hook E2E import marker mismatch")
    text = text.replace(import_marker, import_replacement, 1)

old_function = '''def _fixture_request_candidates(
    topic_info,
    candidate,
    generation_round,
):
    del topic_info, candidate, generation_round
    print("🧪 HOOK FIXTURE CANDIDATES GENERATED: 5")
    return hook_experiment._normalize_candidates({
        "candidates": copy.deepcopy(HOOK_CANDIDATE_FIXTURE),
    })
'''
new_function = '''def _fixture_openai_create(*args, **kwargs):
    del args, kwargs
    raw_payload = json.dumps(
        {"candidates": copy.deepcopy(HOOK_CANDIDATE_FIXTURE)},
        ensure_ascii=False,
    )
    print("🧪 HOOK RAW RESPONSE FIXTURE GENERATED: 5")
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=raw_payload),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=200,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0),
        ),
    )
'''
if new_function not in text:
    if text.count(old_function) != 1:
        raise RuntimeError("Hook E2E request fixture marker mismatch")
    text = text.replace(old_function, new_function, 1)

old_block = '''    original_request = hook_experiment._request_candidates
    hook_experiment._request_candidates = _fixture_request_candidates
    try:
        selected, audit = select_hook(
            TOPIC_INFO,
            WINNER,
        )
    finally:
        hook_experiment._request_candidates = original_request

    print_hook_audit(audit)

    if not selected:
        raise AssertionError(
            "Hook selector did not return a threshold-passing fixture hook"
        )

    if audit["attempts"][0]["candidate_count"] != 5:
        raise AssertionError("Hook E2E fixture did not exercise five candidates")
'''
new_block = '''    original_create = hook_experiment.openai.chat.completions.create
    hook_experiment.openai.chat.completions.create = _fixture_openai_create
    try:
        selected, audit = select_hook(
            TOPIC_INFO,
            WINNER,
        )
    finally:
        hook_experiment.openai.chat.completions.create = original_create

    print_hook_audit(audit)

    if not selected:
        raise AssertionError(
            "Hook selector did not return a threshold-passing fixture hook"
        )

    attempt = audit["attempts"][0]
    if attempt.get("raw_candidate_count") != 5:
        raise AssertionError("Hook E2E raw generation contract did not produce five candidates")
    if attempt.get("parsed_candidate_count") != 5:
        raise AssertionError("Hook E2E raw JSON did not parse five candidates")
    if attempt.get("scoring_pool_count", 0) < 5:
        raise AssertionError("Hook E2E did not build a five-candidate scoring pool")
    if attempt.get("cumulative_scoring_pool_count", 0) < 5:
        raise AssertionError("Hook E2E cumulative scoring pool is below five")
    if audit.get("fallback"):
        raise AssertionError("Hook E2E unexpectedly used legacy fallback")
'''
if new_block not in text:
    if text.count(old_block) != 1:
        raise RuntimeError("Hook E2E build block marker mismatch")
    text = text.replace(old_block, new_block, 1)

path.write_text(text, encoding="utf-8")
print("✅ Hook E2E raw generation + diagnostics contract hotfix applied")

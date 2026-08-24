from pathlib import Path


PATH = Path("content/script_generator.py")
text = PATH.read_text(encoding="utf-8")


def replace_once(source, old, new, label):
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label} marker count mismatch: {count}")
    return source.replace(old, new, 1)


# Install before script-production-parity hotfixes so the compatibility runtime
# captures the retention contract as part of the authoritative generator.
import_marker = "import re\n\nimport openai\n"
import_replacement = '''import re\n\nimport openai\n\nfrom content.retention_structure import (\n    annotate_script,\n    build_retention_plan,\n    density_prompt_contract,\n    first5_prompt_contract,\n    runtime_instruction,\n    validate_density,\n    validate_first5_progression,\n)\n'''
text = replace_once(text, import_marker, import_replacement, "retention imports")

candidate_marker = '''    candidate = validate_candidate(\n        candidate\n    )\n\n    category = str(\n'''
candidate_replacement = '''    candidate = validate_candidate(\n        candidate\n    )\n\n    # RETENTION_STRUCTURE_EXPERIMENT_V2\n    retention_plan = build_retention_plan(candidate)\n\n    category = str(\n'''
text = replace_once(text, candidate_marker, candidate_replacement, "retention plan")

runtime_marker = '''새 소재를 탐색하지 말고 확정 Winner를 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초,\n{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.\n'''
runtime_replacement = '''새 소재를 탐색하지 말고 확정 Winner를 아래 retention runtime contract에 맞춰 발전시켜라.\n{runtime_instruction(retention_plan)}\nScene 수 역시 위 retention runtime contract를 따른다.\n'''
text = replace_once(text, runtime_marker, runtime_replacement, "runtime prompt")

story_marker = '''[STORY]\nHook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.\n'''
story_replacement = '''{first5_prompt_contract()}\n{density_prompt_contract()}\n[STORY]\nHook → Curiosity → Explanation → Reveal → Payoff의 흐름을 만든다.\n'''
text = replace_once(text, story_marker, story_replacement, "retention prompt contracts")

length_marker = '''[LENGTH]\n전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다.\n너무 짧은 문장을 억지로 Scene 수만 맞추려고 잘게 쪼개지 마라.\n'''
length_replacement = '''[LENGTH]\n전체 TTS는 retention runtime contract의 초 범위를 따른다.\n짧은 bucket을 기존 길이로 패딩하지 말고, 긴 bucket도 필요한 causal beat를 억지로 삭제하지 마라.\n너무 짧은 문장을 Scene 수만 맞추려고 잘게 쪼개지 마라.\n'''
text = replace_once(text, length_marker, length_replacement, "retention length prompt")

output_marker = '''    {{\n      "text": "한국어 Scene 대사",\n      "visual_goal": "이 Scene에서 실제로 보여야 하는 구체적인 화면",\n      "keyword": "specific english visual search"\n    }}\n'''
output_replacement = '''    {{\n      "text": "한국어 Scene 대사",\n      "visual_goal": "이 Scene에서 실제로 보여야 하는 구체적인 화면",\n      "keyword": "specific english visual search",\n      "retention_role": "첫 3 Scene만 phenomenon | question | causal_clue, 이후 빈 문자열"\n    }}\n'''
if output_replacement not in text:
    if text.count(output_marker) != 1:
        raise RuntimeError(f"retention output schema marker count mismatch: {text.count(output_marker)}")
    text = text.replace(output_marker, output_replacement, 1)

validation_marker = '''            valid, reason = validate_script(\n                generated\n            )\n\n            if not valid:\n'''
validation_replacement = '''            retention_ok, retention_reason = validate_first5_progression(\n                generated.get("scenes", [])\n            )\n            if retention_ok:\n                retention_ok, retention_reason = validate_density(\n                    generated.get("scenes", [])\n                )\n\n            if not retention_ok:\n                last_error = f"Retention structure 실패: {retention_reason}"\n                print("🚫 Retention structure 실패: " + retention_reason)\n                continue\n\n            valid, reason = validate_script(\n                generated\n            )\n\n            if not valid:\n'''
text = replace_once(text, validation_marker, validation_replacement, "retention validation")

clean_marker = '''                    "visual_type": str(\n                        scene.get(\n                            "visual_type",\n                            "real_world_broll",\n                        )\n                    ).strip()\n                    or "real_world_broll",\n                    "keyword": " ".join(\n'''
clean_replacement = '''                    "visual_type": str(\n                        scene.get(\n                            "visual_type",\n                            "real_world_broll",\n                        )\n                    ).strip()\n                    or "real_world_broll",\n                    "retention_role": str(\n                        scene.get("retention_role", "")\n                    ).strip(),\n                    "keyword": " ".join(\n'''
text = replace_once(text, clean_marker, clean_replacement, "retention role preservation")

result_marker = '''            result = {\n                "title": str(\n                    generated["title"]\n                ).strip(),\n'''
result_replacement = '''            result = {\n                "title": str(\n                    generated["title"]\n                ).strip(),\n                "runtime_bucket": retention_plan["runtime_bucket"],\n                "retention_structure": retention_plan,\n'''
text = replace_once(text, result_marker, result_replacement, "retention result metadata")

print_marker = '''            print("🎬 장면:", len(result["scenes"]))\n            print("➡️ 다음 단계: 독립 Judge Committee")\n'''
print_replacement = '''            print("🎬 장면:", len(result["scenes"]))\n            print("⏱️ Retention runtime bucket:", result["runtime_bucket"])\n            print("➡️ 다음 단계: 독립 Judge Committee")\n'''
text = replace_once(text, print_marker, print_replacement, "retention observability")

PATH.write_text(text, encoding="utf-8")
print("✅ retention structure experiment hotfix applied")
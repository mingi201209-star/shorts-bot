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


# This patch runs after retention-structure planning and before script-production
# parity wrapping, so the authoritative production generator captures it.
config_marker = "from config import (\n"
subscriber_import = '''from content.subscriber_conversion import (\n    apply_subscriber_conversion,\n    build_subscriber_conversion_plan,\n    subscriber_conversion_prompt_contract,\n)\n\nfrom config import (\n'''
text = replace_once(text, config_marker, subscriber_import, "subscriber imports")

plan_marker = '''    # RETENTION_STRUCTURE_EXPERIMENT_V1\n    retention_plan = build_retention_plan(candidate)\n\n    category = str(\n'''
plan_replacement = '''    # RETENTION_STRUCTURE_EXPERIMENT_V1\n    retention_plan = build_retention_plan(candidate)\n\n    # SUBSCRIBER_CONVERSION_LAYER_V1\n    subscriber_plan = build_subscriber_conversion_plan(candidate)\n\n    category = str(\n'''
text = replace_once(text, plan_marker, plan_replacement, "subscriber plan")

prompt_marker = '''{density_prompt_contract()}\n[STORY]\n'''
prompt_replacement = '''{density_prompt_contract()}\n{subscriber_conversion_prompt_contract(subscriber_plan)}\n[STORY]\n'''
text = replace_once(text, prompt_marker, prompt_replacement, "subscriber prompt contract")

result_marker = '''                "scenes": cleaned_scenes,\n            }\n\n            print("")\n'''
result_replacement = '''                "scenes": cleaned_scenes,\n            }\n\n            result = apply_subscriber_conversion(\n                result,\n                candidate,\n                subscriber_plan,\n            )\n\n            print("")\n'''
text = replace_once(text, result_marker, result_replacement, "subscriber result application")

print_marker = '''            print("⏱️ Retention runtime bucket:", result["runtime_bucket"])\n            print("➡️ 다음 단계: 독립 Judge Committee")\n'''
print_replacement = '''            print("⏱️ Retention runtime bucket:", result["runtime_bucket"])\n            print("🔔 Subscriber conversion:", result.get("subscriber_conversion_mode"), "added=", result.get("cta_added"))\n            print("➡️ 다음 단계: 독립 Judge Committee")\n'''
text = replace_once(text, print_marker, print_replacement, "subscriber observability")

PATH.write_text(text, encoding="utf-8")
print("✅ subscriber conversion layer hotfix applied")

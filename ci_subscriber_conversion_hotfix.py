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


def replace_retention_plan_once(source):
    """Install subscriber planning after the active retention plan.

    Retention V2 is the current production contract. Keep the V1 marker as a
    compatibility fallback so this hotfix remains safe when replayed against an
    older production fixture, without weakening or rewriting the retention
    contract itself.
    """
    subscriber_marker = "    # SUBSCRIBER_CONVERSION_LAYER_V1\n"
    if subscriber_marker in source:
        return source

    for version in ("V2", "V1"):
        marker = f'''    # RETENTION_STRUCTURE_EXPERIMENT_{version}\n    retention_plan = build_retention_plan(candidate)\n\n    category = str(\n'''
        replacement = f'''    # RETENTION_STRUCTURE_EXPERIMENT_{version}\n    retention_plan = build_retention_plan(candidate)\n\n    # SUBSCRIBER_CONVERSION_LAYER_V1\n    subscriber_plan = build_subscriber_conversion_plan(candidate)\n\n    category = str(\n'''
        count = source.count(marker)
        if count == 1:
            return source.replace(marker, replacement, 1)
        if count > 1:
            raise RuntimeError(
                f"subscriber plan marker count mismatch for {version}: {count}"
            )

    raise RuntimeError(
        "subscriber plan marker count mismatch: no supported retention marker"
    )


# This patch runs after retention-structure planning and before script-production
# parity wrapping, so the authoritative production generator captures it.
config_marker = "from config import (\n"
subscriber_import = '''from content.subscriber_conversion import (\n    apply_subscriber_conversion,\n    build_subscriber_conversion_plan,\n    subscriber_conversion_prompt_contract,\n)\n\nfrom config import (\n'''
text = replace_once(text, config_marker, subscriber_import, "subscriber imports")

text = replace_retention_plan_once(text)

prompt_marker = '''{density_prompt_contract()}\n[STORY]\n'''
prompt_replacement = '''{density_prompt_contract()}\n{subscriber_conversion_prompt_contract(subscriber_plan)}\n[STORY]\n'''
text = replace_once(text, prompt_marker, prompt_replacement, "subscriber prompt contract")

result_marker = '''                "scenes": cleaned_scenes,\n            }\n\n            print("")\n'''
result_replacement = '''                "scenes": cleaned_scenes,\n            }\n\n            result = apply_subscriber_conversion(\n                result,\n                candidate,\n                subscriber_plan,\n            )\n\n            print("")\n'''
text = replace_once(text, result_marker, result_replacement, "subscriber result application")

print_marker = '''            print("⏱️ Retention runtime bucket:", result["runtime_bucket"])\n            print("➡️ 다음 단계: 독립 Judge Committee")\n'''
print_replacement = '''            print("⏱️ Retention runtime bucket:", result["runtime_bucket"])\n            print("🔔 Subscriber conversion:", result.get("subscriber_conversion_mode"), "added=", result.get("cta_added"))\n            print("➡️ 다음 단계: 독립 Judge Committee")\n'''
text = replace_once(text, print_marker, print_replacement, "subscriber observability")

# SCRIPT_PARITY_LEGACY_MARKER_BRIDGE_V1
# Retention structure intentionally replaces the old duration prompt before the
# script-production-parity hotfix runs. The parity hotfix still installs semantic
# validator/runtime wrappers but historically used those old prompt strings as
# installation sentinels. Keep inert copies so that installer remains compatible
# with the evolved retention prompt without reverting the actual runtime contract.
if "SCRIPT_PARITY_LEGACY_MARKER_BRIDGE_V1" not in text:
    text += r'''

# SCRIPT_PARITY_LEGACY_MARKER_BRIDGE_V1
_SCRIPT_PARITY_LEGACY_INSTALL_SENTINELS = r"""
새 소재를 탐색하지 말고 확정 Winner를 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초,
{MIN_SCENES}~{MAX_SCENES} Scene의 Shorts로 발전시켜라.

[LENGTH]
전체 TTS가 {TARGET_MIN_SECONDS}~{TARGET_MAX_SECONDS}초가 되도록 충분한 문장 분량을 만든다.
너무 짧은 문장을 억지로 Scene 수만 맞추려고 잘게 쪼개지 마라.
"""
'''

PATH.write_text(text, encoding="utf-8")
print("✅ subscriber conversion layer hotfix applied")

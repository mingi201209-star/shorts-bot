from pathlib import Path

path = Path("content/script_generator.py")
text = path.read_text(encoding="utf-8")

marker = "SCRIPT_PRODUCTION_EXPORT_PARITY_V1"
if marker not in text:
    text += r'''

# SCRIPT_PRODUCTION_EXPORT_PARITY_V1
# Some production hotfixes expose script generation through a compatibility module
# backed by `_LEGACY`. Bridge the exported entrypoint to the already-patched legacy
# validator context without depending on local response variable names.
try:
    _SCRIPT_PARITY_RUNTIME = _LEGACY
except NameError:
    _SCRIPT_PARITY_RUNTIME = None

if (
    _SCRIPT_PARITY_RUNTIME is not None
    and hasattr(_SCRIPT_PARITY_RUNTIME, "_SCRIPT_PARITY_ACTIVE_CONTEXT")
    and hasattr(_SCRIPT_PARITY_RUNTIME, "_script_parity_context")
):
    _script_parity_export_original_generate_script = generate_script

    def generate_script(topic_info, candidate):
        target = _SCRIPT_PARITY_RUNTIME
        previous = target._SCRIPT_PARITY_ACTIVE_CONTEXT
        target._SCRIPT_PARITY_ACTIVE_CONTEXT = target._script_parity_context(candidate)
        try:
            return _script_parity_export_original_generate_script(topic_info, candidate)
        finally:
            target._SCRIPT_PARITY_ACTIVE_CONTEXT = previous
'''

path.write_text(text, encoding="utf-8")
print("✅ Script production parity wrapper bridge applied")

from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label} marker mismatch count={text.count(old)}")
    return text.replace(old, new, 1)


# Preserve stable physical lineage fields through final semantic QA.
qa_path = Path("quality/final_visual_semantic_qa.py")
qa = qa_path.read_text(encoding="utf-8")
old = '''            "provider": str(selection.get("provider") or ""),
            "source_id": str(selection.get("source_id") or ""),
            "metadata": str(selection.get("metadata") or "")[:500],
'''
new = '''            "provider": str(selection.get("provider") or ""),
            "source_id": str(selection.get("source_id") or ""),
            "physical_signature": str(selection.get("physical_signature") or ""),
            "source_asset_id": str(selection.get("source_asset_id") or ""),
            "template_type": str(selection.get("template_type") or ""),
            "metadata": str(selection.get("metadata") or "")[:500],
'''
qa = replace_once(qa, old, new, "final visual physical lineage")
qa_path.write_text(qa, encoding="utf-8")

# Repair-local exclusion: never reuse the repeated physical still during that
# repair attempt, while leaving normal future reuse behavior unchanged.
still_path = Path("video/still_image_fallback.py")
still = still_path.read_text(encoding="utf-8")
import_anchor = "from config import OPENAI_KEY\n"
if "from quality.visual_diversity_context import is_physical_asset_excluded" not in still:
    still = replace_once(
        still,
        import_anchor,
        import_anchor + "from quality.visual_diversity_context import is_physical_asset_excluded\n",
        "still exclusion import",
    )
cache_anchor = '''        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        image_path = Path(str(cached.get("image_path") or ""))
'''
cache_replacement = '''        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        if is_physical_asset_excluded(cached.get("source_id")):
            print(
                f"[VISUAL_DIVERSITY_EXCLUDE] scene={_scene_id(scene)} "
                f"source_id={cached.get('source_id', '')}"
            )
            continue
        image_path = Path(str(cached.get("image_path") or ""))
'''
still = replace_once(still, cache_anchor, cache_replacement, "still repair exclusion")
still_path.write_text(still, encoding="utf-8")

# The Visual Explanation hotfix is already installed by the production chain.
# Carry its underlying physical asset and transform template into lineage.
engine_path = Path("video/video_engine.py")
engine = engine_path.read_text(encoding="utf-8")n
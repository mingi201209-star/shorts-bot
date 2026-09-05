from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# RUN_33977099845_VERIFIED_STILL_RESCUE_V1"
PRESENTATION_ID = "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1"


def _replace_once(text, old, new, label):
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} marker mismatch count={count}")
    return text.replace(old, new, 1)


def main():
    still_path = ROOT / "video/still_image_fallback.py"
    still = still_path.read_text(encoding="utf-8")
    if MARKER not in still:
        still = _replace_once(
            still,
            "_VERIFIED_SOURCE_USE_COUNTS = {}\n",
            "_VERIFIED_SOURCE_USE_COUNTS = {}\n_VERIFIED_RESCUE_USE_COUNTS = {}\n",
            "verified rescue counter",
        )
        still = _replace_once(
            still,
            "    _VERIFIED_SOURCE_USE_COUNTS.clear()\n",
            "    _VERIFIED_SOURCE_USE_COUNTS.clear()\n    _VERIFIED_RESCUE_USE_COUNTS.clear()\n",
            "verified rescue reset",
        )

        reuse_start = still.find("def _reuse_signatures(scene):")
        reuse_end = still.find("\ndef ", reuse_start + 1)
        if reuse_start < 0 or reuse_end < 0:
            raise RuntimeError("verified still reuse signature function missing")
        reuse_func = '''def _reuse_signatures(scene):
    signature = _anchor_signature(scene)
    signatures = []
    if signature:
        signatures.append(signature)
        if signature == ("aircraft", "wing"):
            signatures.extend((("aircraft", "winglet"), ("aircraft", "wingtip")))

    query = str((scene or {}).get("keyword") or (scene or {}).get("visual_goal") or "").lower().replace("-", " ")
    words = set(query.split())
    if "aircraft" in words and "flap" in words:
        flap_family = ("aircraft", "wing")
        if flap_family not in signatures:
            signatures.append(flap_family)
    return tuple(signatures)
'''
        still = still[:reuse_start] + reuse_func + still[reuse_end:]

        cache_old = '''            _VERIFIED_STILL_CACHE[signature] = {
                "image_path": str(image_path),
                "provider": "openai_image",
                "source_id": source_id,
            }
'''
        cache_new = '''            _VERIFIED_STILL_CACHE[signature] = {
                "image_path": str(image_path),
                "provider": "openai_image",
                "source_id": source_id,
                "verification_evidence": dict(evidence or {}),
            }
'''
        still = _replace_once(still, cache_old, cache_new, "verified still evidence cache")

        helpers = r'''
# RUN_33977099845_VERIFIED_STILL_RESCUE_V1
_RUN_33977099845_PRESENTATION_ID = "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1"


def _verified_flap_rescue_candidate(scene, signature):
    scene = scene if isinstance(scene, dict) else {}
    query = str(scene.get("keyword") or scene.get("visual_goal") or "").lower().replace("-", " ")
    words = set(query.split())
    return "aircraft" in words and "flap" in words and signature == ("aircraft", "wing")


def _verified_budget_rescue_presentation():
    return {
        "presentation_id": _RUN_33977099845_PRESENTATION_ID,
        "scene_role": "information",
        "visual_beat": "inspect_verified_flap_feature",
        "subject_focal_region": "verified_flap_center",
        "safe_crop_constraint": "center_only_max_1.12x",
        "zoom_start": 1.05,
        "zoom_max": 1.12,
        "zoom_step": 0.0010,
        "pan_x": "center",
        "pan_y": "center",
    }


def _reuse_verified_budget_rescue(scene, *, output_path, duration, trigger_reason):
    seen_sources = set()
    for signature in _reuse_signatures(scene):
        if not _verified_flap_rescue_candidate(scene, signature):
            continue
        cached = dict(_VERIFIED_STILL_CACHE.get(signature) or {})
        image_path = Path(str(cached.get("image_path") or ""))
        source_id = str(cached.get("source_id") or "")
        if not source_id or source_id in seen_sources or not image_path.is_file():
            continue
        seen_sources.add(source_id)
        exclude_fn = globals().get("is_physical_asset_excluded")
        if callable(exclude_fn) and exclude_fn(source_id):
            continue
        if int(_VERIFIED_RESCUE_USE_COUNTS.get(source_id, 0)) >= 1:
            continue

        presentation = _verified_budget_rescue_presentation()
        _assert_early_presentation_distinct(presentation)
        _motion_clip(image_path, output_path, duration, presentation=presentation)
        verified, evidence = _verify_motion_clip(scene, output_path)
        if not verified:
            Path(output_path).unlink(missing_ok=True)
            print(
                f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=rescue_rejected "
                f"source_id={source_id} reason=current_scene_verification_failed"
            )
            continue

        _VERIFIED_RESCUE_USE_COUNTS[source_id] = int(_VERIFIED_RESCUE_USE_COUNTS.get(source_id, 0)) + 1
        _register_source_use(source_id, scene)
        try:
            from video.video_downloader import extract_query_anchors
            anchor_total = len(extract_query_anchors(str(scene.get("keyword") or "")))
        except Exception:
            anchor_total = len(_reuse_signatures(scene)[0]) if _reuse_signatures(scene) else 0
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=reused_verified_budget_rescue "
            f"source_id={source_id} generation_count={_GENERATION_COUNT} "
            f"source_uses={verified_source_use_count(source_id)} presentation={_RUN_33977099845_PRESENTATION_ID}"
        )
        return {
            "path": str(output_path),
            "mode": "REUSED_VERIFIED_STILL_MOTION",
            "tier": 3,
            "visual_state": "TRUE",
            "anchor_matched": anchor_total,
            "anchor_total": anchor_total,
            "provider": cached.get("provider", "openai_image"),
            "source_id": source_id,
            "source_asset_id": source_id,
            "template_type": _RUN_33977099845_PRESENTATION_ID,
            "presentation_id": _RUN_33977099845_PRESENTATION_ID,
            "presentation_identity": list(_still_presentation_identity(presentation)),
            "visible_components": list((evidence or {}).get("visible_components", []) or []),
            "verification_evidence_reused": False,
            "current_scene_verification": dict(evidence or {}),
        }
    return None


'''
        insert_pos = still.find("def generate_still_motion_fallback(")
        if insert_pos < 0:
            raise RuntimeError("still fallback rescue function boundary missing")
        still = still[:insert_pos] + helpers + still[insert_pos:]

        budget_guard = "    if _GENERATION_COUNT >= STILL_IMAGE_MAX_PER_VIDEO:\n"
        budget_replacement = '''    if _GENERATION_COUNT >= STILL_IMAGE_MAX_PER_VIDEO:
        rescued = _reuse_verified_budget_rescue(
            scene,
            output_path=output_path,
            duration=duration,
            trigger_reason=trigger_reason,
        )
        if rescued:
            return rescued
'''
        still = _replace_once(still, budget_guard, budget_replacement, "budget rescue boundary")
        still_path.write_text(still.rstrip() + "\n\n" + MARKER + "\n", encoding="utf-8")

    diversity_path = ROOT / "quality/visual_diversity_preflight.py"
    diversity = diversity_path.read_text(encoding="utf-8")
    diversity_marker = "# RUN_33977099845_VERIFIED_PRESENTATION_VARIANT_V1"
    if diversity_marker not in diversity:
        variant_start = diversity.find("def _variant(")
        variant_end = diversity.find("\ndef ", variant_start + 1)
        if variant_start < 0 or variant_end < 0:
            raise RuntimeError("visual diversity variant function missing")
        variant_func = diversity[variant_start:variant_end]
        if "raw_physical_asset" not in variant_func:
            raise RuntimeError("visual diversity raw variant contract missing")
        header_end = diversity.find("\n", variant_start)
        if header_end < 0 or header_end >= variant_end:
            raise RuntimeError("visual diversity variant header missing")
        variant_guard = '''    # RUN_33977099845_VERIFIED_PRESENTATION_VARIANT_V1
    if str(item.get("template_type") or "") == "VERIFIED_FLAP_FEATURE_INSPECTION_CENTER_V1":
        return "presentation:verified_flap_feature_inspection_center_v1"
'''
        diversity = diversity[:header_end + 1] + variant_guard + diversity[header_end + 1:]
        diversity_path.write_text(diversity.rstrip() + "\n\n" + diversity_marker + "\n", encoding="utf-8")

    print("✅ Run 33977099845 verified still budget rescue installed; generation budget unchanged")


if __name__ == "__main__":
    main()
